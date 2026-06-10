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

def test_hal_90_mediation():
    """Test that Hal-90 can mediate a forced resource conflict."""
    from agents.hal_90 import Hal90Agent, MediationResult
    
    hal_90 = Hal90Agent()
    
    # Scenario: Veridian's request (500W) exceeds Solara's threshold (300W)
    # Battery is low (25%) and O2 is warning (19.2%) — conflict scenario
    # Total power must be high enough so reserve stays positive
    allocation = hal_90.mediate_conflict(
        solara_threshold=300.0,
        veridian_request=500.0,
        current_battery=25.0,
        current_o2=19.2,
        current_temperature=22.0,
        total_power=800.0  # Enough to keep reserve >= 100W
    )
    
    assert allocation is not None
    assert allocation.power_distribution is not None
    assert allocation.power_distribution['veridian'] > 0
    assert allocation.power_distribution['reserve'] >= 100.0, f"Reserve {allocation.power_distribution['reserve']} < 100"
    assert allocation.safety_verification is True, f"Safety verification failed: {allocation}"
    assert allocation.mediation_result in [MediationResult.APPROVED, MediationResult.MODIFIED, 
                                           MediationResult.REJECTED, MediationResult.EMERGENCY_OVERRIDE]
    print(f"✓ Hal-90 mediation test passed (result: {allocation.mediation_result.value})")


if __name__ == "__main__":
    test_orchestrator_initialization()
    test_solara_power_audit()
    test_veridian_biological_audit()
    test_hal_90_mediation()
    print("\n✅ All smoke tests passed!")
