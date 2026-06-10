"""
AETHER Operational Dashboard — FastAPI + HTMX + Alpine.js
Serves the real-time simulation dashboard with pipeline state,
agent health, quality gates, telemetry, and anomaly feed.
"""

import logging
import sys
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

# Load env
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ── Module-level cache ──────────────────────────────────────────
# Holds the latest completion report and per-cycle telemetry

completion_report: Optional[Dict] = None
cycle_telemetry: List[Dict] = []
simulation_running: bool = False

# ── FastAPI app ──────────────────────────────────────────────────

templates_dir = Path(__file__).parent / "templates"
templates_dir.mkdir(exist_ok=True)

app = FastAPI(
    title="AETHER Dashboard",
    description="Autonomous Environmental & Thermal Habitat Efficiency Regulator — Operational Dashboard",
    version="1.0.0"
)

templates = Jinja2Templates(directory=str(templates_dir))


# ── Simulation Runner ────────────────────────────────────────────

def _run_simulation(max_cycles: int = 24) -> tuple:
    """
    Run the full AETHER pipeline, capturing per-cycle telemetry.

    Returns:
        Tuple of (completion_report_dict, cycle_telemetry_list)
    """
    global simulation_running
    simulation_running = True

    try:
        from sim_engine import SimPyEnvironment
        from orchestrator import AgentsOrchestrator

        sim_engine = SimPyEnvironment()
        orchestrator = AgentsOrchestrator(sim_engine, None)

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

            # Phase 6: Continuous Anomaly Monitoring
            orchestrator._phase_6_continuous_loop()

            # Update cycle count (done in run_pipeline after phases)
            orchestrator.pipeline_state.cycle_count += 1

            # Capture telemetry snapshot for this cycle
            env_summary = sim_engine.get_environmental_summary()
            gate_summary = {
                name: status.value
                for name, status in orchestrator.pipeline_state.quality_gates.items()
            }
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
                'phase': orchestrator.pipeline_state.current_phase.value,
                'quality_gates': gate_summary,
            })

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
        simulation_running = False


def _get_status_payload() -> Dict:
    """
    Build the merged status payload from the cached completion report.
    Returns a pipeline-state + environmental-summary merged dict.
    """
    global completion_report

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
            'simulation_running': simulation_running
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
        'simulation_running': simulation_running
    }


# ── Routes ───────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Render the main dashboard HTML page."""
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "app_title": "AETHER Control",
            "current_year": datetime.now().year
        }
    )


@app.get("/api/v1/status")
async def api_status():
    """
    GET /api/v1/status
    Returns merged pipeline state + environmental summary.
    """
    return JSONResponse(content=_get_status_payload())


@app.post("/api/v1/simulate")
async def api_simulate():
    """
    POST /api/v1/simulate
    Runs the AETHER pipeline (24 cycles), caches results, returns report.
    """
    global completion_report, cycle_telemetry

    if simulation_running:
        return JSONResponse(
            content={'status': 'error', 'message': 'Simulation already running'},
            status_code=409
        )

    report, telemetry = _run_simulation(max_cycles=24)

    # Cache results
    completion_report = report
    cycle_telemetry = telemetry

    return JSONResponse(content=_get_status_payload())


@app.get("/api/v1/history")
async def api_history():
    """
    GET /api/v1/history
    Returns per-cycle telemetry array.
    """
    global cycle_telemetry
    return JSONResponse(content=cycle_telemetry)


@app.get("/api/v1/health")
async def api_health():
    """Simple health check endpoint."""
    return JSONResponse(content={
        'status': 'healthy',
        'simulation_running': simulation_running,
        'has_report': completion_report is not None,
        'telemetry_points': len(cycle_telemetry)
    })


# ── CLI entry point ──────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('DASHBOARD_PORT', '8000'))
    logger.info(f"Starting AETHER Dashboard on http://0.0.0.0:{port}")
    uvicorn.run("dashboard:app", host="0.0.0.0", port=port, reload=True)
