"""
AETHER Operational Dashboard — FastAPI + HTMX + Alpine.js
Serves the real-time simulation dashboard with pipeline state,
agent health, quality gates, telemetry, and anomaly feed.
Multi-page product with Settings, Scenarios, Agents Console, and History.
"""

import logging
import sys
import json
import os
import math
import random
import threading
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
from pathlib import Path
from enum import Enum

from fastapi import FastAPI, Request, Body
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime/date/enum objects."""
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)


# Load env
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Suppress verbose agent/orchestrator logs in dashboard context
for noisy_logger in ['agents.solara', 'agents.veridian', 'agents.hal_90',
                      'orchestrator', 'sim_engine', 'mqtt_client']:
    logging.getLogger(noisy_logger).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


# ── Module-level cache ──────────────────────────────────────────
# Holds the latest completion report and per-cycle telemetry

completion_report: Optional[Dict] = None
cycle_telemetry: List[Dict] = []
simulation_running: bool = False
live_payload: Optional[Dict] = None  # Updated each cycle during simulation for live mode

# MQTT client instance (lazy-initialized on connect)
mqtt_client_instance: Optional[any] = None

MQTT_STATE: Dict = {
    'is_connected': False,
    'broker': None,
    'port': None,
    'messages_published': 0,
    'messages_received': 0,
    'connection_errors': 0,
    'buffered_messages': 0,
    'registered_handlers': 0,
}


# ── Default Configuration ───────────────────────────────────────
# Full set of configurable parameters for the AETHER simulation

DEFAULT_CONFIG: Dict = {
    'max_cycles': 24,
    'anomaly_probability': 0.05,
    'solar_day_length': 24,
    'array_efficiency': 8,
    'battery_capacity': 10000,
    'initial_battery': 50.0,
    'initial_o2': 19.8,
    'initial_temperature': 22.0,
    'initial_co2': 400.0,
    'initial_humidity': 45.0,
    'initial_power_consumption': 500.0,
    'occupant_count': 4,
    'solara_retries': 3,
    'veridian_retries': 3,
    'hal90_retries': 2,
    'o2_target': 21.0,
    'battery_threshold': 40.0,
    'forecast_horizon': 24,
    'hal90_priority_safety': 1.0,
    'hal90_priority_battery': 0.9,
    'hal90_priority_o2': 0.85,
    'hal90_priority_comfort': 0.5,
}

current_config: Dict = DEFAULT_CONFIG.copy()
simulation_history: List[Dict] = []  # Each entry: {id, timestamp, config, anomaly_schedule, report, telemetry}
history_counter: int = 0


# ── FastAPI app ──────────────────────────────────────────────────

templates_dir = Path(__file__).parent / "templates"
templates_dir.mkdir(exist_ok=True)
(templates_dir / "pages").mkdir(exist_ok=True)

app = FastAPI(
    title="AETHER Dashboard",
    description="Autonomous Environmental & Thermal Habitat Efficiency Regulator — Operational Dashboard",
    version="1.0.0"
)

templates = Jinja2Templates(directory=str(templates_dir))

# Make FastAPI use our custom JSON encoder globally
from starlette.responses import Response


# ── Simulation Runner ────────────────────────────────────────────

# Mapping from config keys to environment variable names
# Used to apply overrides before agent initialization
ENV_MAP: Dict[str, str] = {
    'anomaly_probability': 'ANOMALY_PROBABILITY',
    'solar_day_length': 'SOLAR_DAY_LENGTH',
    'forecast_horizon': 'SOLARA_FORECAST_HORIZON',
    'o2_target': 'VERIDIAN_O2_TARGET',
    'battery_threshold': 'HAL_90_BATTERY_THRESHOLD',
    'array_efficiency': 'SOLAR_ARRAY_EFFICIENCY',
    'battery_capacity': 'BATTERY_CAPACITY',
    'solara_retries': 'SOLARA_MAX_RETRIES',
    'veridian_retries': 'VERIDIAN_MAX_RETRIES',
    'hal90_retries': 'HAL_90_MAX_RETRIES',
}

# ── Sweep Parameters ─────────────────────────────────────────────
# Defines which parameters can be swept and their display metadata

SWEEP_PARAMS: Dict[str, Dict] = {
    'array_efficiency': {'label': 'Solar Array Efficiency', 'unit': '%', 'min': 1, 'max': 30, 'step': 1, 'default': 8},
    'battery_capacity': {'label': 'Battery Capacity', 'unit': 'Wh', 'min': 2000, 'max': 20000, 'step': 1000, 'default': 10000},
    'anomaly_probability': {'label': 'Anomaly Probability', 'unit': '', 'min': 0.01, 'max': 0.5, 'step': 0.02, 'default': 0.05},
    'initial_battery': {'label': 'Initial Battery', 'unit': '%', 'min': 10, 'max': 100, 'step': 5, 'default': 50.0},
    'initial_o2': {'label': 'Initial O₂', 'unit': '%', 'min': 15, 'max': 25, 'step': 0.5, 'default': 19.8},
    'battery_threshold': {'label': 'Battery Threshold', 'unit': '%', 'min': 10, 'max': 80, 'step': 5, 'default': 40},
    'solar_day_length': {'label': 'Solar Day Length', 'unit': 'h', 'min': 12, 'max': 30, 'step': 1, 'default': 24},
    'initial_power_consumption': {'label': 'Base Power Consumption', 'unit': 'W', 'min': 200, 'max': 1000, 'step': 50, 'default': 500.0},
}


def _run_simulation(max_cycles: int = 24,
                    config_overrides: Optional[Dict] = None,
                    anomaly_schedule: Optional[List[Dict]] = None) -> tuple:
    """
    Run the full AETHER pipeline with optional config overrides and anomaly schedule.

    Args:
        max_cycles: Number of cycles to run
        config_overrides: Dict of config keys to override defaults
        anomaly_schedule: List of dicts with keys: type, severity, trigger_cycle

    Returns:
        Tuple of (completion_report_dict, cycle_telemetry_list)
    """
    global simulation_running, live_payload
    was_running = simulation_running
    simulation_running = True
    live_payload = None

    # Merge config defaults with overrides
    merged = {**current_config, **(config_overrides or {})}

    # Save original env vars and apply overrides so agents/os.getenv() pick them up
    original_env: Dict[str, Optional[str]] = {}
    for config_key, env_key in ENV_MAP.items():
        if config_key in merged:
            original_env[env_key] = os.environ.get(env_key)
            os.environ[env_key] = str(merged[config_key])

    try:
        from sim_engine import SimPyEnvironment, AnomalyEvent, AnomalyType
        from orchestrator import AgentsOrchestrator

        sim_engine = SimPyEnvironment()

        # Apply configurable simulation parameters (array efficiency, battery capacity)
        sim_engine.array_efficiency = float(merged.get('array_efficiency', 8))
        sim_engine.battery_capacity = float(merged.get('battery_capacity', 10000))

        # Apply initial conditions from config (override hardcoded defaults)
        sim_engine.state.battery_level = float(merged.get('initial_battery', 50.0))
        sim_engine.state.o2_level = float(merged.get('initial_o2', 19.8))
        sim_engine.state.temperature = float(merged.get('initial_temperature', 22.0))
        sim_engine.state.co2_level = float(merged.get('initial_co2', 400.0))
        sim_engine.state.humidity = float(merged.get('initial_humidity', 45.0))
        sim_engine.state.power_consumption = float(merged.get('initial_power_consumption', 500.0))
        sim_engine.state.occupant_count = int(merged.get('occupant_count', 4))

        # Pass MQTT client instance if connected, else None
        mqtt_client = mqtt_client_instance if mqtt_client_instance and mqtt_client_instance.is_connected else None
        orchestrator = AgentsOrchestrator(sim_engine, mqtt_client)

        # Apply Hal-90 priority weights from dashboard config
        hal90_weights = {
            'safety': float(merged.get('hal90_priority_safety', 1.0)),
            'battery': float(merged.get('hal90_priority_battery', 0.9)),
            'o2': float(merged.get('hal90_priority_o2', 0.85)),
            'comfort': float(merged.get('hal90_priority_comfort', 0.5)),
        }
        orchestrator.hal_90.set_priority_weights(hal90_weights)

        # Phase 1: Initialization
        orchestrator._phase_1_initialization()

        telemetry: List[Dict] = []

        # Main simulation loop (replicates orchestrator.run_pipeline with capture)
        while orchestrator.pipeline_state.cycle_count < max_cycles and sim_engine.is_running():
            # Advance SimPy simulation by 1 time unit (1 hour)
            sim_engine.env.run(until=sim_engine.env.now + 1)

            # Phase 2: Solara Audit
            solara_result = orchestrator._phase_2_solara_audit()

            # Phase 3: Veridian Audit
            veridian_result = orchestrator._phase_3_veridian_audit(solara_result)

            # Phase 4: Hal-90 Mediation (if needed)
            if veridian_result.power_requirement_watts > solara_result.power_threshold_40pct:
                hal_90_result = orchestrator._phase_4_hal_90_mediation(solara_result, veridian_result)
                mediation_result = hal_90_result
            else:
                mediation_result = None

            # Phase 5: Resource Allocation
            orchestrator._phase_5_resource_allocation(mediation_result, veridian_result)

            # Inject scheduled anomalies from scenario designer
            if anomaly_schedule:
                current_cycle = orchestrator.pipeline_state.cycle_count + 1
                for scheduled in anomaly_schedule:
                    if scheduled.get('trigger_cycle') == current_cycle:
                        anomaly_type = AnomalyType(scheduled['type'])
                        anomaly = AnomalyEvent(
                            anomaly_type=anomaly_type,
                            severity=float(scheduled.get('severity', 0.5)),
                            start_time=sim_engine.state.time,
                            duration=timedelta(hours=2),
                            description=(
                                f"Scheduled {scheduled['type']}"
                                f" (severity: {scheduled.get('severity', 0.5)})"
                            ),
                            affected_systems=[]
                        )
                        sim_engine.anomalies.append(anomaly)
                        for callback in sim_engine.anomaly_callbacks:
                            callback(anomaly)

            # Phase 6: Continuous Anomaly Monitoring
            orchestrator._phase_6_continuous_loop()

            # Update cycle count
            orchestrator.pipeline_state.cycle_count += 1

            # Capture telemetry snapshot for this cycle
            env_summary = sim_engine.get_environmental_summary()
            gate_summary = {
                name: status.value
                for name, status in orchestrator.pipeline_state.quality_gates.items()
            }
            # Collect unique active anomaly types for this cycle
            active_anomaly_types = list(dict.fromkeys(
                a.anomaly_type.value
                for a in sim_engine.anomalies
                if a.start_time + a.duration > sim_engine.state.time
            ))
            telemetry.append({
                'cycle': orchestrator.pipeline_state.cycle_count,
                'battery': round(env_summary['battery_level'], 1),
                'o2': round(env_summary['o2_level'], 1),
                'temperature': round(env_summary['temperature'], 1),
                'solar_radiation': round(env_summary['solar_radiation'], 1),
                'power_generation': round(env_summary['power_generation'], 1),
                'power_consumption': round(env_summary['power_consumption'], 1),
                'is_goldilocks_zone': env_summary['is_goldilocks_zone'],
                'active_anomalies': env_summary['active_anomalies'],
                'anomaly_types': active_anomaly_types,
                'phase': orchestrator.pipeline_state.current_phase.value,
                'quality_gates': gate_summary,
            })

            # Update live payload for real-time dashboard display
            live_payload = {
                'status': 'RUNNING',
                'total_cycles': orchestrator.pipeline_state.cycle_count,
                'anomalies_handled': orchestrator.pipeline_state.anomalies_detected,
                'emergency_responses': orchestrator.pipeline_state.emergency_responses,
                'completion_time': datetime.now().isoformat(),
                'pipeline_summary': {
                    'current_phase': orchestrator.pipeline_state.current_phase.value,
                    'cycle_count': orchestrator.pipeline_state.cycle_count,
                    'anomalies_detected': orchestrator.pipeline_state.anomalies_detected,
                    'emergency_responses': orchestrator.pipeline_state.emergency_responses,
                    'uptime': (datetime.now() - orchestrator.pipeline_state.start_time).total_seconds(),
                },
                'environmental_summary': {
                    'time': env_summary.get('time', datetime.now().isoformat()),
                    'battery_level': env_summary['battery_level'],
                    'o2_level': env_summary['o2_level'],
                    'temperature': env_summary['temperature'],
                    'solar_radiation': env_summary['solar_radiation'],
                    'power_generation': env_summary['power_generation'],
                    'power_consumption': env_summary['power_consumption'],
                    'is_goldilocks_zone': env_summary['is_goldilocks_zone'],
                    'active_anomalies': env_summary['active_anomalies'],
                    'anomaly_types': active_anomaly_types,
                },
                'agent_status': {
                    name: 'running' if status in ('running', 'complete') else 'idle'
                    for name, status in orchestrator.pipeline_state.agent_status.items()
                },
                'quality_gates': gate_summary,
            }

            # Check for completion
            if orchestrator.pipeline_state.cycle_count >= max_cycles:
                break

        # Generate completion report
        report = orchestrator._generate_completion_report()

        logger.info(f"Simulation completed: {report['final_status']}, {len(telemetry)} cycles captured")

        return report, telemetry

    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            'final_status': 'ERROR',
            'error': str(e),
            'total_cycles': 0,
            'pipeline_summary': {},
            'environmental_summary': {},
            'agent_status': {},
            'quality_gates': {},
            'anomalies_handled': 0,
            'emergency_responses': 0,
            'completion_time': datetime.now().isoformat()
        }, []

    finally:
        # Restore original env vars
        for env_key, original_val in original_env.items():
            if original_val is not None:
                os.environ[env_key] = original_val
            else:
                os.environ.pop(env_key, None)
        simulation_running = was_running


def _get_status_payload() -> Dict:
    """
    Build the merged status payload from the cached completion report or live payload.
    Returns a pipeline-state + environmental-summary merged dict.
    """
    global completion_report, live_payload

    # During active simulation, return live per-cycle payload if available
    if simulation_running and live_payload is not None:
        return {
            **live_payload,
            'simulation_running': True
        }

    if completion_report is None:
        return {
            'status': 'idle',
            'pipeline_summary': {
                'current_phase': 'idle',
                'cycle_count': 0,
                'anomalies_detected': 0,
                'emergency_responses': 0,
                'uptime': 0.0
            },
            'environmental_summary': {
                'time': datetime.now().isoformat(),
                'battery_level': 0.0,
                'o2_level': 0.0,
                'temperature': 0.0,
                'solar_radiation': 0.0,
                'power_generation': 0.0,
                'power_consumption': 0.0,
                'is_goldilocks_zone': False,
                'active_anomalies': 0
            },
            'agent_status': {},
            'quality_gates': {},
            'anomalies_handled': 0,
            'emergency_responses': 0,
            'simulation_running': False
        }

    report = completion_report
    return {
        'status': report.get('final_status', 'UNKNOWN'),
        'pipeline_summary': report.get('pipeline_summary', {}),
        'environmental_summary': report.get('environmental_summary', {}),
        'agent_status': report.get('agent_status', {}),
        'quality_gates': report.get('quality_gates', {}),
        'anomalies_handled': report.get('anomalies_handled', 0),
        'emergency_responses': report.get('emergency_responses', 0),
        'total_cycles': report.get('total_cycles', 0),
        'completion_time': report.get('completion_time', ''),
        'simulation_running': False
    }


# ══════════════════════════════════════════════════════════════════
# PAGE ROUTES (HTMX fragments)
# ══════════════════════════════════════════════════════════════════


@app.get("/", response_class=HTMLResponse)
async def shell_page(request: Request):
    """Serve the layout shell with sidebar + initial dashboard content."""
    return templates.TemplateResponse("layout.html", {
        "request": request,
        "app_title": "AETHER Control",
        "current_year": datetime.now().year
    })


def _is_htmx(request: Request) -> bool:
    """Check if the request is an HTMX fragment request."""
    return request.headers.get("hx-request") == "true"


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Serve the dashboard content fragment (or full page for direct access)."""
    ctx = {"request": request, "current_year": datetime.now().year}
    if _is_htmx(request):
        return templates.TemplateResponse("pages/dashboard.html", ctx)
    ctx["initial_page"] = "dashboard"
    return templates.TemplateResponse("layout.html", ctx)


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Serve the settings page fragment (or full page for direct access)."""
    ctx = {"request": request, "config": current_config, "current_year": datetime.now().year}
    if _is_htmx(request):
        return templates.TemplateResponse("pages/settings.html", ctx)
    ctx["initial_page"] = "settings"
    return templates.TemplateResponse("layout.html", ctx)


@app.get("/scenarios", response_class=HTMLResponse)
async def scenarios_page(request: Request):
    """Serve the scenarios page fragment (or full page for direct access)."""
    ctx = {"request": request, "config": current_config, "current_year": datetime.now().year}
    if _is_htmx(request):
        return templates.TemplateResponse("pages/scenarios.html", ctx)
    ctx["initial_page"] = "scenarios"
    return templates.TemplateResponse("layout.html", ctx)


@app.get("/agents", response_class=HTMLResponse)
async def agents_page(request: Request):
    """Serve the agents console page fragment (or full page for direct access)."""
    ctx = {"request": request, "config": current_config, "completion_report": completion_report, "current_year": datetime.now().year}
    if _is_htmx(request):
        return templates.TemplateResponse("pages/agents.html", ctx)
    ctx["initial_page"] = "agents"
    return templates.TemplateResponse("layout.html", ctx)


@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    """Serve the history browser page fragment (or full page for direct access)."""
    ctx = {"request": request, "history": simulation_history, "current_year": datetime.now().year}
    if _is_htmx(request):
        return templates.TemplateResponse("pages/history.html", ctx)
    ctx["initial_page"] = "history"
    return templates.TemplateResponse("layout.html", ctx)


@app.get("/mqtt", response_class=HTMLResponse)
async def mqtt_page(request: Request):
    """Serve the MQTT console page fragment (or full page for direct access)."""
    ctx = {
        "request": request,
        "mqtt_state": MQTT_STATE,
        "current_year": datetime.now().year
    }
    if _is_htmx(request):
        return templates.TemplateResponse("pages/mqtt.html", ctx)
    ctx["initial_page"] = "mqtt"
    return templates.TemplateResponse("layout.html", ctx)


# ══════════════════════════════════════════════════════════════════
# LEGACY ROUTE (backward compat with existing frontend)
# ══════════════════════════════════════════════════════════════════

@app.get("/legacy", response_class=HTMLResponse)
async def legacy_dashboard_page(request: Request):
    """Render the original standalone dashboard HTML page (backward compat)."""
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "app_title": "AETHER Control",
            "current_year": datetime.now().year
        }
    )


# ══════════════════════════════════════════════════════════════════
# API ROUTES
# ══════════════════════════════════════════════════════════════════


@app.get("/api/v1/status")
async def api_status():
    """
    GET /api/v1/status
    Returns merged pipeline state + environmental summary.
    """
    return Response(
        content=json.dumps(_get_status_payload(), cls=DateTimeEncoder),
        media_type="application/json"
    )


@app.post("/api/v1/simulate")
async def api_simulate():
    """
    POST /api/v1/simulate
    Runs the AETHER pipeline with current config, caches results, returns report.
    """
    global completion_report, cycle_telemetry, simulation_history, history_counter

    if simulation_running:
        return Response(
            content=json.dumps({'status': 'error', 'message': 'Simulation already running'}, cls=DateTimeEncoder),
            status_code=409,
            media_type="application/json"
        )

    report, telemetry = _run_simulation(
        max_cycles=current_config['max_cycles'],
        config_overrides=current_config
    )

    # Cache results
    completion_report = report
    cycle_telemetry = telemetry

    # Store in history
    history_counter += 1
    simulation_history.append({
        'id': history_counter,
        'timestamp': datetime.now().isoformat(),
        'config': dict(current_config),
        'anomaly_schedule': [],
        'report': report,
        'telemetry': telemetry
    })

    return Response(
        content=json.dumps(_get_status_payload(), cls=DateTimeEncoder),
        media_type="application/json"
    )


@app.get("/api/v1/history")
async def api_history():
    """
    GET /api/v1/history
    Returns per-cycle telemetry array.
    """
    global cycle_telemetry
    return Response(
        content=json.dumps(cycle_telemetry, cls=DateTimeEncoder),
        media_type="application/json"
    )


@app.get("/api/v1/health")
async def api_health():
    """Simple health check endpoint."""
    return Response(
        content=json.dumps({
            'status': 'healthy',
            'simulation_running': simulation_running,
            'has_report': completion_report is not None,
            'telemetry_points': len(cycle_telemetry)
        }, cls=DateTimeEncoder),
        media_type="application/json"
    )


# ── MQTT API ──


@app.get("/api/v1/mqtt/status")
async def api_mqtt_status():
    """GET /api/v1/mqtt/status — Return MQTT client state."""
    global mqtt_client_instance, MQTT_STATE

    if mqtt_client_instance:
        try:
            stats = mqtt_client_instance.get_statistics()
            MQTT_STATE.update(stats)
        except Exception:
            pass

    return Response(
        content=json.dumps(MQTT_STATE, cls=DateTimeEncoder),
        media_type="application/json"
    )


@app.post("/api/v1/mqtt/connect")
async def api_mqtt_connect():
    """POST /api/v1/mqtt/connect — Connect to MQTT broker."""
    global mqtt_client_instance, MQTT_STATE

    if mqtt_client_instance and mqtt_client_instance.is_connected:
        return Response(
            content=json.dumps({"status": "already_connected", "broker": MQTT_STATE.get("broker")}),
            media_type="application/json"
        )

    try:
        from mqtt_client import AetherMQTTClient

        broker = os.getenv('MQTT_BROKER', 'localhost')
        port = int(os.getenv('MQTT_PORT', '1883'))

        mqtt_client_instance = AetherMQTTClient(broker=broker, port=port)
        connected = mqtt_client_instance.connect()

        if connected:
            MQTT_STATE.update(mqtt_client_instance.get_statistics())
            MQTT_STATE['broker'] = broker
            MQTT_STATE['port'] = port
            return Response(
                content=json.dumps({"status": "connected", "broker": broker, "port": port}),
                media_type="application/json"
            )
        else:
            return Response(
                content=json.dumps({"status": "error", "message": "Connection failed"}),
                status_code=502,
                media_type="application/json"
            )
    except Exception as e:
        return Response(
            content=json.dumps({"status": "error", "message": str(e)}),
            status_code=500,
            media_type="application/json"
        )


@app.post("/api/v1/mqtt/disconnect")
async def api_mqtt_disconnect():
    """POST /api/v1/mqtt/disconnect — Disconnect from MQTT broker."""
    global mqtt_client_instance, MQTT_STATE

    if mqtt_client_instance:
        try:
            mqtt_client_instance.disconnect()
        except Exception:
            pass
        mqtt_client_instance = None

    MQTT_STATE = {
        'is_connected': False,
        'broker': None,
        'port': None,
        'messages_published': 0,
        'messages_received': 0,
        'connection_errors': 0,
        'buffered_messages': 0,
        'registered_handlers': 0,
    }

    return Response(
        content=json.dumps({"status": "disconnected"}),
        media_type="application/json"
    )


# ── Config API ──


@app.get("/api/v1/config")
async def api_get_config():
    """Return current configuration."""
    return Response(
        content=json.dumps(current_config, cls=DateTimeEncoder),
        media_type="application/json"
    )


@app.post("/api/v1/config")
async def api_update_config(data: Dict = Body(...)):
    """Update configuration with partial or full payload."""
    global current_config
    for key, value in data.items():
        if key in current_config:
            default_val = DEFAULT_CONFIG[key]
            if isinstance(default_val, float):
                current_config[key] = float(value)
            elif isinstance(default_val, int):
                current_config[key] = int(value)
            else:
                current_config[key] = value
    return Response(
        content=json.dumps({"status": "saved", "config": current_config}, cls=DateTimeEncoder),
        media_type="application/json"
    )


@app.post("/api/v1/config/reset")
async def api_reset_config():
    """Reset configuration to defaults."""
    global current_config
    current_config = DEFAULT_CONFIG.copy()
    return Response(
        content=json.dumps({"status": "reset", "config": current_config}, cls=DateTimeEncoder),
        media_type="application/json"
    )


# ── Scenario Storage ──

SCENARIOS_DIR = Path(__file__).resolve().parent.parent / "scenarios"
SCENARIOS_DIR.mkdir(parents=True, exist_ok=True)

def _scenario_path(name: str) -> Path:
    """Get the filesystem path for a scenario file, sanitizing the name."""
    safe = name.strip().replace(" ", "_").replace("/", "_").replace("\\", "_")
    return SCENARIOS_DIR / f"{safe}.json"

def _list_scenarios() -> List[Dict]:
    """Return list of saved scenario presets with metadata."""
    results = []
    if not SCENARIOS_DIR.exists():
        return results
    for f in sorted(SCENARIOS_DIR.iterdir()):
        if f.suffix == ".json":
            try:
                data = json.loads(f.read_text())
                results.append({
                    "name": f.stem.replace("_", " "),
                    "filename": f.name,
                    "saved_at": data.get("_saved_at", ""),
                    "conditions": {k: v for k, v in data.items() if k != "anomalies" and not k.startswith("_")},
                    "anomaly_count": len(data.get("anomalies", [])),
                })
            except Exception:
                continue
    return results

# ── Scenario API ──


@app.get("/api/v1/scenarios")
async def api_list_scenarios():
    """GET /api/v1/scenarios — List saved scenario presets."""
    return Response(
        content=json.dumps(_list_scenarios(), cls=DateTimeEncoder),
        media_type="application/json"
    )


@app.post("/api/v1/scenarios/save")
async def api_save_scenario(data: Dict = Body(...)):
    """
    POST /api/v1/scenarios/save
    Body: { "name": "My Scenario", "conditions": {...}, "anomalies": [...] }
    """
    name = data.get("name", "").strip()
    if not name:
        return Response(
            content=json.dumps({"status": "error", "message": "Name is required"}),
            status_code=400,
            media_type="application/json"
        )
    payload = {
        "_saved_at": datetime.now().isoformat(),
        "_updated_at": datetime.now().isoformat(),
        "conditions": data.get("conditions", {}),
        "anomalies": data.get("anomalies", []),
    }
    path = _scenario_path(name)
    path.write_text(json.dumps(payload, cls=DateTimeEncoder, indent=2))
    return Response(
        content=json.dumps({"status": "ok", "name": name, "path": str(path)}),
        media_type="application/json"
    )


@app.get("/api/v1/scenarios/load/{scenario_name:path}")
async def api_load_scenario(scenario_name: str):
    """GET /api/v1/scenarios/load/{name} — Load a saved scenario."""
    path = _scenario_path(scenario_name)
    if not path.exists():
        return Response(
            content=json.dumps({"status": "error", "message": f"Scenario '{scenario_name}' not found"}),
            status_code=404,
            media_type="application/json"
        )
    try:
        data = json.loads(path.read_text())
        return Response(
            content=json.dumps({**data, "status": "ok"}, cls=DateTimeEncoder),
            media_type="application/json"
        )
    except Exception as e:
        return Response(
            content=json.dumps({"status": "error", "message": str(e)}),
            status_code=500,
            media_type="application/json"
        )


@app.delete("/api/v1/scenarios/{scenario_name:path}")
async def api_delete_scenario(scenario_name: str):
    """DELETE /api/v1/scenarios/{name} — Delete a saved scenario."""
    path = _scenario_path(scenario_name)
    if not path.exists():
        return Response(
            content=json.dumps({"status": "error", "message": f"Scenario '{scenario_name}' not found"}),
            status_code=404,
            media_type="application/json"
        )
    path.unlink()
    return Response(
        content=json.dumps({"status": "ok", "message": f"Deleted '{scenario_name}'"}),
        media_type="application/json"
    )


@app.post("/api/v1/scenario/script/generate")
async def api_scenario_script_generate(data: Dict = Body(...)):
    """
    POST /api/v1/scenario/script/generate
    Execute a Python script that generates a list of anomaly dicts.
    Body: { "script": "def generate():\\n    return [{\\"type\\": \\"dust_storm\\", \\"severity\\": 0.5, \\"trigger_cycle\\": 5}]" }
    Returns: { "anomalies": [...], "error": null }
    """
    script: str = data.get('script', '').strip()
    if not script:
        return Response(
            content=json.dumps({"anomalies": [], "error": "Script is empty"}),
            media_type="application/json"
        )

    from sim_engine import AnomalyType

    # Restricted builtins — only safe functions
    safe_builtins = {
        'True': True, 'False': False, 'None': None,
        'int': int, 'float': float, 'bool': bool, 'str': str,
        'len': len, 'list': list, 'dict': dict, 'tuple': tuple,
        'range': range, 'min': min, 'max': max, 'sum': sum,
        'abs': abs, 'round': round, 'enumerate': enumerate,
        'zip': zip, 'reversed': reversed, 'sorted': sorted,
        'isinstance': isinstance, 'type': type,
        'AnomalyType': AnomalyType,
    }

    try:
        # Compile the script first to catch syntax errors
        code = compile(script, '<anomaly_script>', 'exec')

        # Exec with restricted globals
        namespace = {'__builtins__': safe_builtins}
        exec(code, namespace)

        if 'generate' not in namespace or not callable(namespace['generate']):
            return Response(
                content=json.dumps({"anomalies": [], "error": "Script must define a function named 'generate' that returns a list of anomaly dicts"}),
                media_type="application/json"
            )

        result = namespace['generate']()

        if not isinstance(result, list):
            return Response(
                content=json.dumps({"anomalies": [], "error": "generate() must return a list"}),
                media_type="application/json"
            )

        # Validate each anomaly
        valid_types = {t.value for t in AnomalyType}
        validated = []
        for i, a in enumerate(result):
            if not isinstance(a, dict):
                return Response(
                    content=json.dumps({"anomalies": [], "error": f"Item {i} is not a dict"}),
                    media_type="application/json"
                )
            if 'type' not in a or a['type'] not in valid_types:
                return Response(
                    content=json.dumps({"anomalies": [], "error": f"Item {i}: invalid or missing 'type'. Valid types: {sorted(valid_types)}"}),
                    media_type="application/json"
                )
            severity = float(a.get('severity', 0.5))
            severity = max(0.1, min(1.0, severity))
            trigger = int(a.get('trigger_cycle', 1))
            trigger = max(1, trigger)
            validated.append({
                'type': a['type'],
                'severity': round(severity, 2),
                'trigger_cycle': trigger,
                'description': a.get('description', f"{a['type'].replace('_', ' ').title()} (severity {severity:.1f})"),
            })

        return Response(
            content=json.dumps({"anomalies": validated, "error": None}),
            media_type="application/json"
        )

    except SyntaxError as e:
        return Response(
            content=json.dumps({"anomalies": [], "error": f"Syntax error: {e.msg} (line {e.lineno})"}),
            media_type="application/json"
        )
    except Exception as e:
        return Response(
            content=json.dumps({"anomalies": [], "error": f"Runtime error: {str(e)}"}),
            media_type="application/json"
        )


@app.post("/api/v1/scenario/run")
async def api_run_scenario(data: Dict = Body(...)):
    """
    Run simulation with custom initial conditions and anomaly schedule.
    Body: { "conditions": {...}, "anomalies": [...], "max_cycles": 24 }
    """
    global completion_report, cycle_telemetry, simulation_history, history_counter

    if simulation_running:
        return Response(
            content=json.dumps({'status': 'error', 'message': 'Already running'}),
            status_code=409,
            media_type="application/json"
        )

    conditions = data.get('conditions', {})
    anomalies = data.get('anomalies', [])
    max_cycles = data.get('max_cycles', current_config['max_cycles'])

    # Merge conditions into config overrides
    overrides = {**current_config, **conditions}

    report, telemetry = _run_simulation(
        max_cycles=max_cycles,
        config_overrides=overrides,
        anomaly_schedule=anomalies
    )

    completion_report = report
    cycle_telemetry = telemetry

    # Store in history
    history_counter += 1
    simulation_history.append({
        'id': history_counter,
        'timestamp': datetime.now().isoformat(),
        'config': dict(current_config),
        'anomaly_schedule': anomalies,
        'report': report,
        'telemetry': telemetry
    })

    return Response(
        content=json.dumps(_get_status_payload(), cls=DateTimeEncoder),
        media_type="application/json"
    )


# ── Multi-Run API ──

# In-memory storage for batch results
multi_run_batches: Dict[int, Dict] = {}
_batch_counter: int = 0
_batch_lock = threading.Lock()


def _compute_aggregate(metrics: List[float]) -> Dict:
    """Compute mean, min, max, stddev for a list of metrics."""
    n = len(metrics)
    if n == 0:
        return {'mean': 0, 'min': 0, 'max': 0, 'stddev': 0}
    mean = sum(metrics) / n
    variance = sum((x - mean) ** 2 for x in metrics) / n
    return {
        'mean': round(mean, 2),
        'min': round(min(metrics), 2),
        'max': round(max(metrics), 2),
        'stddev': round(math.sqrt(variance), 2)
    }


def _run_with_randomized_config(base_config: Dict, run_index: int) -> tuple:
    """
    Run a single simulation with optional randomization applied to base_config.
    Returns (report, telemetry).
    """
    config = dict(base_config)
    # Add slight randomness to anomaly probability and array efficiency
    from sim_engine import AnomalyType
    anomaly_options = [t.value for t in AnomalyType]
    config['anomaly_probability'] = min(1.0, max(0.01,
        float(base_config.get('anomaly_probability', 0.15)) * random.uniform(0.5, 1.5)
    ))
    config['array_efficiency'] = max(1,
        float(base_config.get('array_efficiency', 8)) * random.uniform(0.7, 1.3)
    )
    # Optionally randomize initial battery
    if random.random() < 0.5:
        config['initial_battery'] = random.uniform(30, 80)
    return _run_simulation(
        max_cycles=int(base_config.get('max_cycles', 24)),
        config_overrides=config
    )


@app.post("/api/v1/multi-run")
async def api_multi_run(data: Dict = Body(...)):
    """
    POST /api/v1/multi-run
    Run N simulations with optional randomization.
    Body: { "count": 5, "base_config": {...}, "randomize": true }
    """
    global _batch_counter, simulation_running

    if simulation_running:
        return Response(
            content=json.dumps({'status': 'error', 'message': 'Simulation already running'}),
            status_code=409,
            media_type="application/json"
        )

    count = min(max(int(data.get('count', 5)), 2), 20)
    randomize = bool(data.get('randomize', True))
    base_config = data.get('base_config', {})

    runs = []
    simulation_running = True

    try:
        for i in range(count):
            if randomize:
                report, telemetry = _run_with_randomized_config(base_config, i)
            else:
                report, telemetry = _run_simulation(
                    max_cycles=int(base_config.get('max_cycles', 24)),
                    config_overrides=base_config
                )
            runs.append({
                'run_index': i,
                'report': report,
                'telemetry': telemetry,
                'final_battery': telemetry[-1]['battery'] if telemetry else 0,
                'final_o2': telemetry[-1]['o2'] if telemetry else 0,
                'anomalies_handled': report.get('anomalies_handled', 0),
                'emergency_responses': report.get('emergency_responses', 0),
                'total_cycles': report.get('total_cycles', 0),
                'final_status': report.get('final_status', 'UNKNOWN'),
            })
    finally:
        simulation_running = False

    # Compute aggregates
    batteries = [r['final_battery'] for r in runs]
    o2s = [r['final_o2'] for r in runs]
    anomalies = [r['anomalies_handled'] for r in runs]
    emergencies = [r['emergency_responses'] for r in runs]

    # Find best/worst run by final battery
    best = max(runs, key=lambda r: r['final_battery'])
    worst = min(runs, key=lambda r: r['final_battery'])

    with _batch_lock:
        _batch_counter += 1
        batch_id = _batch_counter
        batch = {
            'id': batch_id,
            'timestamp': datetime.now().isoformat(),
            'count': count,
            'randomize': randomize,
            'base_config': base_config,
            'aggregates': {
                'final_battery': _compute_aggregate(batteries),
                'final_o2': _compute_aggregate(o2s),
                'anomalies_handled': _compute_aggregate(anomalies),
                'emergency_responses': _compute_aggregate(emergencies),
            },
            'best_run': {'index': best['run_index'], 'final_battery': best['final_battery']},
            'worst_run': {'index': worst['run_index'], 'final_battery': worst['final_battery']},
            'runs': runs,
        }
        multi_run_batches[batch_id] = batch

    # Return summary (without full telemetry per run — too large)
    summary = {k: v for k, v in batch.items() if k != 'runs'}
    summary['status'] = 'ok'
    return Response(
        content=json.dumps(summary, cls=DateTimeEncoder),
        media_type="application/json"
    )


@app.get("/api/v1/multi-run/{batch_id}")
async def api_multi_run_detail(batch_id: int):
    """GET /api/v1/multi-run/{id} — Full details for a batch including all runs."""
    batch = multi_run_batches.get(batch_id)
    if not batch:
        return Response(
            content=json.dumps({"error": "batch not found"}),
            status_code=404,
            media_type="application/json"
        )
    return Response(
        content=json.dumps(batch, cls=DateTimeEncoder),
        media_type="application/json"
    )


@app.post("/api/v1/multi-run/clear")
async def api_multi_run_clear():
    """Clear all multi-run batch results."""
    global multi_run_batches, _batch_counter
    multi_run_batches = {}
    _batch_counter = 0
    return Response(
        content=json.dumps({"status": "cleared"}),
        media_type="application/json"
    )


# ── Sweep API ──

# In-memory storage for sweep results
sweep_results: Dict[int, Dict] = {}
_sweep_counter: int = 0
_sweep_lock = threading.Lock()


def _run_sweep(param: str, min_val: float, max_val: float, steps: int,
               runs_per_step: int = 3, base_config: Optional[Dict] = None) -> Dict:
    """
    Run a parameter sweep: vary `param` from `min_val` to `max_val` in `steps` increments,
    running `runs_per_step` simulations per value. Returns aggregated results.
    """
    param_def = SWEEP_PARAMS.get(param)
    if not param_def:
        raise ValueError(f"Unknown sweep parameter: {param}")

    step_values = []
    for i in range(steps):
        if steps == 1:
            val = (min_val + max_val) / 2
        else:
            val = min_val + (max_val - min_val) * i / (steps - 1)
        # Round to reasonable precision
        val = round(val, 4)
        step_values.append(val)

    step_data = []

    for val in step_values:
        batteries, o2s, anomalies, emergencies = [], [], [], []
        run_details = []

        for r in range(runs_per_step):
            config = dict(base_config or {})
            config[param] = val
            report, telemetry = _run_simulation(
                max_cycles=int(config.get('max_cycles', 24)),
                config_overrides=config
            )
            bat = telemetry[-1]['battery'] if telemetry else 0
            o2 = telemetry[-1]['o2'] if telemetry else 0
            anom = report.get('anomalies_handled', 0)
            emrg = report.get('emergency_responses', 0)
            batteries.append(bat)
            o2s.append(o2)
            anomalies.append(anom)
            emergencies.append(emrg)
            run_details.append({
                'run_index': r,
                'final_battery': bat,
                'final_o2': o2,
                'anomalies_handled': anom,
                'emergency_responses': emrg,
            })

        step_data.append({
            'value': val,
            'aggregates': {
                'final_battery': _compute_aggregate(batteries),
                'final_o2': _compute_aggregate(o2s),
                'anomalies_handled': _compute_aggregate(anomalies),
                'emergency_responses': _compute_aggregate(emergencies),
            },
            'runs': run_details,
        })

    return {
        'param': param,
        'param_def': param_def,
        'min': min_val,
        'max': max_val,
        'steps': steps,
        'runs_per_step': runs_per_step,
        'total_simulations': steps * runs_per_step,
        'step_data': step_data,
    }


@app.get("/api/v1/sweep/params")
async def api_sweep_params():
    """Return available sweep parameters and their metadata."""
    return Response(
        content=json.dumps(SWEEP_PARAMS, cls=DateTimeEncoder),
        media_type="application/json"
    )


@app.post("/api/v1/sweep")
async def api_sweep(data: Dict = Body(...)):
    """
    POST /api/v1/sweep
    Run a parameter sweep.
    Body: { "param": "array_efficiency", "min": 1, "max": 30, "steps": 10, "runs_per_step": 3, "base_config": {...} }
    """
    global _sweep_counter, simulation_running

    if simulation_running:
        return Response(
            content=json.dumps({'status': 'error', 'message': 'Simulation already running'}),
            status_code=409,
            media_type="application/json"
        )

    param = str(data.get('param', ''))
    param_def = SWEEP_PARAMS.get(param)
    if not param_def:
        return Response(
            content=json.dumps({'status': 'error', 'message': f'Unknown parameter: {param}. Available: {list(SWEEP_PARAMS.keys())}'}),
            status_code=400,
            media_type="application/json"
        )

    min_val = float(data.get('min', param_def['min']))
    max_val = float(data.get('max', param_def['max']))
    steps = min(max(int(data.get('steps', 10)), 2), 30)
    runs_per_step = min(max(int(data.get('runs_per_step', 3)), 1), 10)
    base_config = data.get('base_config', {})

    # Clamp to param bounds
    min_val = max(min_val, param_def['min'])
    max_val = min(max_val, param_def['max'])
    if min_val >= max_val:
        max_val = min_val + param_def['step']

    simulation_running = True
    try:
        result = _run_sweep(param, min_val, max_val, steps, runs_per_step, base_config)
    finally:
        simulation_running = False

    with _sweep_lock:
        _sweep_counter += 1
        sweep_id = _sweep_counter
        entry = {
            'id': sweep_id,
            'timestamp': datetime.now().isoformat(),
            **result,
        }
        sweep_results[sweep_id] = entry

    return Response(
        content=json.dumps({'status': 'ok', 'id': sweep_id, 'result': entry}, cls=DateTimeEncoder),
        media_type="application/json"
    )


@app.get("/api/v1/sweep/{sweep_id}")
async def api_sweep_detail(sweep_id: int):
    """GET /api/v1/sweep/{id} — Full sweep result."""
    entry = sweep_results.get(sweep_id)
    if not entry:
        return Response(
            content=json.dumps({"error": "sweep result not found"}),
            status_code=404,
            media_type="application/json"
        )
    return Response(
        content=json.dumps(entry, cls=DateTimeEncoder),
        media_type="application/json"
    )


@app.post("/api/v1/sweep/clear")
async def api_sweep_clear():
    """Clear all sweep results."""
    global sweep_results, _sweep_counter
    sweep_results = {}
    _sweep_counter = 0
    return Response(
        content=json.dumps({"status": "cleared"}),
        media_type="application/json"
    )


# ── History API ──


@app.get("/api/v1/history/list")
async def api_history_list():
    """Return list of past runs (summary only, no full telemetry)."""
    summary_list = []
    for h in simulation_history:
        summary_list.append({
            'id': h['id'],
            'timestamp': h['timestamp'],
            'total_cycles': h['report'].get('total_cycles', 0),
            'anomalies_handled': h['report'].get('anomalies_handled', 0),
            'emergency_responses': h['report'].get('emergency_responses', 0),
            'final_status': h['report'].get('final_status', 'UNKNOWN'),
        })
    return Response(
        content=json.dumps(summary_list, cls=DateTimeEncoder),
        media_type="application/json"
    )


@app.get("/api/v1/history/{history_id}")
async def api_history_detail(history_id: int):
    """Return full details for a specific run."""
    for h in simulation_history:
        if h['id'] == history_id:
            return Response(
                content=json.dumps(h, cls=DateTimeEncoder),
                media_type="application/json"
            )
    return Response(
        content=json.dumps({"error": "not found"}),
        status_code=404,
        media_type="application/json"
    )


@app.post("/api/v1/history/clear")
async def api_history_clear():
    """Clear all simulation history."""
    global simulation_history, history_counter
    simulation_history = []
    history_counter = 0
    return Response(
        content=json.dumps({"status": "cleared"}),
        media_type="application/json"
    )


# ── Agents Override API ──


@app.post("/api/v1/agents/override")
async def api_agents_override(data: Dict = Body(...)):
    """Apply agent-specific overrides to current config."""
    global current_config
    agent = data.get('agent', '')
    overrides = data.get('overrides', {})

    # Map agent override keys to config keys
    mapping = {
        'solara': {
            'forecast_horizon': 'forecast_horizon',
            'retries': 'solara_retries',
        },
        'veridian': {
            'o2_target': 'o2_target',
            'retries': 'veridian_retries',
            'co2_target': None,
        },
        'hal90': {
            'battery_threshold': 'battery_threshold',
            'retries': 'hal90_retries',
            'priority_safety': 'hal90_priority_safety',
            'priority_battery': 'hal90_priority_battery',
            'priority_o2': 'hal90_priority_o2',
            'priority_comfort': 'hal90_priority_comfort',
        },
    }

    if agent in mapping:
        for override_key, config_key in mapping[agent].items():
            if override_key in overrides and config_key and config_key in current_config:
                default_val = DEFAULT_CONFIG[config_key]
                val = overrides[override_key]
                if isinstance(default_val, float):
                    current_config[config_key] = float(val)
                elif isinstance(default_val, int):
                    current_config[config_key] = int(val)
                else:
                    current_config[config_key] = val

    return Response(
        content=json.dumps({"status": "applied", "config": current_config}, cls=DateTimeEncoder),
        media_type="application/json"
    )


# ── CLI entry point ──────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('DASHBOARD_PORT', '8000'))
    logger.info(f"Starting AETHER Dashboard on http://0.0.0.0:{port}")
    uvicorn.run("dashboard:app", host="0.0.0.0", port=port, reload=True)
