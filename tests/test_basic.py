"""
Basic smoke tests for AETHER system.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_orchestrator_initialization():
    """Test that orchestrator initializes correctly."""
    from orchestrator import AgentsOrchestrator
    from sim_engine import SimPyEnvironment
    
    sim_engine = SimPyEnvironment()
    orchestrator = AgentsOrchestrator(sim_engine, None)
    
    assert orchestrator is not None
    assert orchestrator.solara is not None
    assert orchestrator.veridian is not None
    assert orchestrator.hal_90 is not None
    print("✓ Orchestrator initialization test passed")

def test_solara_power_audit():
    """Test that Solara can perform power audit."""
    from agents.solara import SolaraAgent
    
    solara = SolaraAgent()
    forecast = solara.perform_power_audit(
        battery_level=75.0,
        power_generation=1000.0,
        power_consumption=500.0,
        forecast_horizon=24
    )
    
    assert forecast is not None
    assert forecast.confidence >= 0.0
    assert forecast.power_threshold_40pct > 0
    print("✓ Solara power audit test passed")

def test_veridian_biological_audit():
    """Test that Veridian can perform biological audit."""
    from agents.veridian import VeridianAgent
    
    veridian = VeridianAgent()
    requirements = veridian.perform_biological_audit(
        occupant_count=4,
        current_o2_level=21.0,
        current_co2_level=400.0,
        power_constraint=1000.0
    )
    
    assert requirements is not None
    assert requirements.o2_target_level == 21.0
    assert requirements.power_requirement_watts > 0
    print("✓ Veridian biological audit test passed")

if __name__ == "__main__":
    test_orchestrator_initialization()
    test_solara_power_audit()
    test_veridian_biological_audit()
    print("\n✅ All smoke tests passed!")
