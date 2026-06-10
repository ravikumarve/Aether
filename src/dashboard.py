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
        simulation_running = False


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


# ── Scenario API ──


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
