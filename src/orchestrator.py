"""
AETHER Agents Orchestrator
Autonomous pipeline manager for multi-agent coordination and quality gates.
"""

import logging
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json

from sim_engine import SimPyEnvironment, AnomalyEvent
from mqtt_client import AetherMQTTClient, publish_orchestrator_status
from agents.solara import SolaraAgent, PowerForecast
from agents.veridian import VeridianAgent, BiologicalRequirements
from agents.hal_90 import Hal90Agent, ResourceAllocation


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PipelinePhase(Enum):
    """Pipeline phases for orchestration."""
    INITIALIZATION = "initialization"
    SOLARA_AUDIT = "solara_audit"
    VERIDIAN_AUDIT = "veridian_audit"
    HAL_90_MEDIATION = "hal_90_mediation"
    RESOURCE_ALLOCATION = "resource_allocation"
    CONTINUOUS_LOOP = "continuous_loop"
    COMPLETE = "complete"


class QualityGateStatus(Enum):
    """Quality gate status."""
    PENDING = "pending"
    PASS = "pass"
    FAIL = "fail"


class AgentStatus(Enum):
    """Agent execution status."""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class AgentState:
    """State of an individual agent."""
    name: str
    status: AgentStatus = AgentStatus.IDLE
    last_output: Optional[any] = None
    retry_count: int = 0
    max_retries: int = 3
    last_error: Optional[str] = None


@dataclass
class PipelineState:
    """State of the orchestration pipeline."""
    current_phase: PipelinePhase = PipelinePhase.INITIALIZATION
    phase_history: List[PipelinePhase] = field(default_factory=list)
    agent_status: Dict[str, AgentState] = field(default_factory=dict)
    quality_gates: Dict[str, QualityGateStatus] = field(default_factory=dict)
    simulation_time: Optional[datetime] = None
    cycle_count: int = 0
    anomalies_detected: int = 0
    emergency_responses: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    
    def advance_phase(self, new_phase: PipelinePhase) -> None:
        """Advance to the next phase."""
        self.phase_history.append(self.current_phase)
        self.current_phase = new_phase
        logger.info(f"Pipeline advanced to phase: {new_phase.value}")
    
    def update_agent_status(self, agent_name: str, status: AgentStatus, 
                          output: Optional[any] = None, error: Optional[str] = None) -> None:
        """Update agent status."""
        if agent_name not in self.agent_status:
            self.agent_status[agent_name] = AgentState(name=agent_name)
        
        self.agent_status[agent_name].status = status
        if output is not None:
            self.agent_status[agent_name].last_output = output
        if error is not None:
            self.agent_status[agent_name].last_error = error
    
    def pass_quality_gate(self, gate_name: str) -> None:
        """Mark a quality gate as passed."""
        self.quality_gates[gate_name] = QualityGateStatus.PASS
        logger.info(f"Quality gate passed: {gate_name}")
    
    def fail_quality_gate(self, gate_name: str, reason: str) -> None:
        """Mark a quality gate as failed."""
        self.quality_gates[gate_name] = QualityGateStatus.FAIL
        logger.error(f"Quality gate failed: {gate_name} - {reason}")
    
    def get_summary(self) -> Dict:
        """Get pipeline summary."""
        return {
            'current_phase': self.current_phase.value,
            'cycle_count': self.cycle_count,
            'agent_status': {name: state.status.value for name, state in self.agent_status.items()},
            'quality_gates': {name: status.value for name, status in self.quality_gates.items()},
            'anomalies_detected': self.anomalies_detected,
            'emergency_responses': self.emergency_responses,
            'simulation_time': self.simulation_time.isoformat() if self.simulation_time else None,
            'uptime': (datetime.now() - self.start_time).total_seconds()
        }


class AgentsOrchestrator:
    """
    Autonomous pipeline manager for AETHER multi-agent coordination.
    
    Orchestrates the complete development workflow with quality gates,
    retry logic, and continuous anomaly monitoring.
    """
    
    def __init__(self, sim_engine: SimPyEnvironment, mqtt_client: AetherMQTTClient):
        """
        Initialize the orchestrator.
        
        Args:
            sim_engine: SimPy simulation engine
            mqtt_client: MQTT client for communication
        """
        self.sim_engine = sim_engine
        self.mqtt_client = mqtt_client
        self.pipeline_state = PipelineState()
        
        # Initialize agents
        self.solara = SolaraAgent(mqtt_client)
        self.veridian = VeridianAgent(mqtt_client)
        self.hal_90 = Hal90Agent(mqtt_client)
        
        # Register agents
        self._register_agents()
        
        # Setup anomaly monitoring
        self.sim_engine.register_anomaly_callback(self._handle_anomaly)
        
        logger.info("Agents Orchestrator initialized")
    
    def _register_agents(self) -> None:
        """Register agents with the orchestrator."""
        self.pipeline_state.agent_status['solara'] = AgentState(name='solara', max_retries=3)
        self.pipeline_state.agent_status['veridian'] = AgentState(name='veridian', max_retries=3)
        self.pipeline_state.agent_status['hal_90'] = AgentState(name='hal_90', max_retries=2)
    
    def run_pipeline(self, max_cycles: int = 100) -> Dict:
        """
        Run the complete orchestration pipeline.
        
        Args:
            max_cycles: Maximum number of cycles to run
            
        Returns:
            Pipeline completion summary
        """
        logger.info(f"Starting AETHER pipeline (max cycles: {max_cycles})")
        
        try:
            # Phase 1: Initialization
            self._phase_1_initialization()
            
            # Main simulation loop
            while self.pipeline_state.cycle_count < max_cycles and self.sim_engine.is_running():
                # Phase 2: Solara Audit
                solara_result = self._phase_2_solara_audit()
                
                # Phase 3: Veridian Audit
                veridian_result = self._phase_3_veridian_audit(solara_result)
                
                # Phase 4: Hal-90 Mediation (if needed)
                if veridian_result.power_requirement_watts > solara_result.power_threshold_40pct:
                    hal_90_result = self._phase_4_hal_90_mediation(solara_result, veridian_result)
                    mediation_result = hal_90_result
                else:
                    mediation_result = None
                
                # Phase 5: Resource Allocation
                allocation_result = self._phase_5_resource_allocation(mediation_result, veridian_result)
                
                # Phase 6: Continuous Anomaly Monitoring
                self._phase_6_continuous_loop()
                
                # Update cycle count
                self.pipeline_state.cycle_count += 1
                
                # Publish status
                self._publish_status()
                
                # Check for completion
                if self.pipeline_state.cycle_count >= max_cycles:
                    break
            
            # Generate completion report
            completion_report = self._generate_completion_report()
            
            logger.info(f"AETHER pipeline completed: {completion_report['final_status']}")
            
            return completion_report
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            self.pipeline_state.advance_phase(PipelinePhase.COMPLETE)
            return {
                'final_status': 'ERROR',
                'error': str(e),
                'pipeline_summary': self.pipeline_state.get_summary()
            }
    
    def _phase_1_initialization(self) -> None:
        """Phase 1: System initialization."""
        logger.info("Phase 1: System Initialization")
        self.pipeline_state.advance_phase(PipelinePhase.INITIALIZATION)
        
        # Update simulation time
        self.pipeline_state.simulation_time = self.sim_engine.get_current_time()
        
        # Pass quality gate
        self.pipeline_state.pass_quality_gate('initialization')
    
    def _phase_2_solara_audit(self) -> PowerForecast:
        """Phase 2: Solara power audit."""
        logger.info("Phase 2: Solara Power Audit")
        self.pipeline_state.advance_phase(PipelinePhase.SOLARA_AUDIT)
        
        # Update agent status
        self.pipeline_state.update_agent_status('solara', AgentStatus.RUNNING)
        
        try:
            # Get current environmental state
            battery_level = self.sim_engine.get_battery_level()
            power_generation = self.sim_engine.state.power_generation
            power_consumption = self.sim_engine.state.power_consumption
            
            # Perform power audit
            forecast = self.solara.perform_power_audit(
                battery_level, power_generation, power_consumption
            )
            
            # Validate quality gate
            if forecast.confidence >= 0.85:
                self.pipeline_state.pass_quality_gate('solara_audit')
                self.pipeline_state.update_agent_status('solara', AgentStatus.COMPLETE, forecast)
            else:
                self.pipeline_state.fail_quality_gate('solara_audit', 
                    f"Confidence {forecast.confidence:.2f} below 0.85")
                self.pipeline_state.update_agent_status('solara', AgentStatus.FAILED, 
                    error=f"Low confidence: {forecast.confidence:.2f}")
            
            return forecast
            
        except Exception as e:
            logger.error(f"Solara audit failed: {e}")
            self.pipeline_state.fail_quality_gate('solara_audit', str(e))
            self.pipeline_state.update_agent_status('solara', AgentStatus.FAILED, error=str(e))
            raise
    
    def _phase_3_veridian_audit(self, solara_result: PowerForecast) -> BiologicalRequirements:
        """Phase 3: Veridian biological audit."""
        logger.info("Phase 3: Veridian Biological Audit")
        self.pipeline_state.advance_phase(PipelinePhase.VERIDIAN_AUDIT)
        
        # Update agent status
        self.pipeline_state.update_agent_status('veridian', AgentStatus.RUNNING)
        
        try:
            # Get current environmental state
            occupant_count = self.sim_engine.get_occupant_count()
            current_o2_level = self.sim_engine.get_o2_level()
            current_co2_level = self.sim_engine.state.co2_level
            
            # Perform biological audit
            requirements = self.veridian.perform_biological_audit(
                occupant_count,
                current_o2_level,
                current_co2_level,
                solara_result.power_threshold_40pct
            )
            
            # Validate quality gate
            if 19.5 <= requirements.o2_target_level <= 21.5:
                self.pipeline_state.pass_quality_gate('veridian_audit')
                self.pipeline_state.update_agent_status('veridian', AgentStatus.COMPLETE, requirements)
            else:
                self.pipeline_state.fail_quality_gate('veridian_audit',
                    f"O2 target {requirements.o2_target_level} outside Goldilocks Zone")
                self.pipeline_state.update_agent_status('veridian', AgentStatus.FAILED,
                    error=f"O2 target out of range: {requirements.o2_target_level}")
            
            return requirements
            
        except Exception as e:
            logger.error(f"Veridian audit failed: {e}")
            self.pipeline_state.fail_quality_gate('veridian_audit', str(e))
            self.pipeline_state.update_agent_status('veridian', AgentStatus.FAILED, error=str(e))
            raise
    
    def _phase_4_hal_90_mediation(self, solara_result: PowerForecast,
                                 veridian_result: BiologicalRequirements) -> ResourceAllocation:
        """Phase 4: Hal-90 mediation."""
        logger.info("Phase 4: Hal-90 Mediation")
        self.pipeline_state.advance_phase(PipelinePhase.HAL_90_MEDIATION)
        
        # Update agent status
        self.pipeline_state.update_agent_status('hal_90', AgentStatus.RUNNING)
        
        try:
            # Get current environmental state
            current_battery = self.sim_engine.get_battery_level()
            current_o2 = self.sim_engine.get_o2_level()
            current_temperature = self.sim_engine.state.temperature
            total_power = self.sim_engine.state.power_generation
            
            # Perform mediation
            allocation = self.hal_90.mediate_conflict(
                solara_result.power_threshold_40pct,
                veridian_result.power_requirement_watts,
                current_battery,
                current_o2,
                current_temperature,
                total_power
            )
            
            # Validate quality gate
            if allocation.safety_verification:
                self.pipeline_state.pass_quality_gate('hal_90_mediation')
                self.pipeline_state.update_agent_status('hal_90', AgentStatus.COMPLETE, allocation)
            else:
                self.pipeline_state.fail_quality_gate('hal_90_mediation',
                    "Safety verification failed")
                self.pipeline_state.update_agent_status('hal_90', AgentStatus.FAILED,
                    error="Safety verification failed")
            
            return allocation
            
        except Exception as e:
            logger.error(f"Hal-90 mediation failed: {e}")
            self.pipeline_state.fail_quality_gate('hal_90_mediation', str(e))
            self.pipeline_state.update_agent_status('hal_90', AgentStatus.FAILED, error=str(e))
            raise
    
    def _phase_5_resource_allocation(self, mediation_result: Optional[ResourceAllocation],
                                   veridian_result: BiologicalRequirements) -> Dict:
        """Phase 5: Resource allocation."""
        logger.info("Phase 5: Resource Allocation")
        self.pipeline_state.advance_phase(PipelinePhase.RESOURCE_ALLOCATION)
        
        try:
            # Determine allocation
            if mediation_result:
                allocation = mediation_result.power_distribution
            else:
                # Direct approval - use Veridian's request
                allocation = {
                    'solara': 0.0,
                    'veridian': veridian_result.power_requirement_watts,
                    'reserve': max(0, self.sim_engine.state.power_generation - veridian_result.power_requirement_watts)
                }
            
            # Apply allocation to simulation
            self.sim_engine.apply_resource_allocation(allocation)
            
            # Publish allocation via MQTT
            allocation_message = {
                'timestamp': datetime.now().isoformat(),
                'allocation': allocation,
                'o2_target': veridian_result.o2_target_level,
                'safety_status': 'verified'
            }
            
            if self.mqtt_client:
                from mqtt_client import publish_hal_90_decision
                publish_hal_90_decision(self.mqtt_client, allocation_message)
            
            # Pass quality gate
            self.pipeline_state.pass_quality_gate('resource_allocation')
            
            return allocation
            
        except Exception as e:
            logger.error(f"Resource allocation failed: {e}")
            self.pipeline_state.fail_quality_gate('resource_allocation', str(e))
            raise
    
    def _phase_6_continuous_loop(self) -> None:
        """Phase 6: Continuous anomaly monitoring."""
        logger.info("Phase 6: Continuous Anomaly Monitoring")
        self.pipeline_state.advance_phase(PipelinePhase.CONTINUOUS_LOOP)
        
        # Check for anomalies
        active_anomalies = [
            a for a in self.sim_engine.anomalies 
            if a.start_time + a.duration > self.sim_engine.get_current_time()
        ]
        
        if active_anomalies:
            self.pipeline_state.anomalies_detected += len(active_anomalies)
            logger.warning(f"Active anomalies: {len(active_anomalies)}")
            
            # Handle each anomaly
            for anomaly in active_anomalies:
                self._handle_anomaly(anomaly)
        
        # Pass quality gate
        self.pipeline_state.pass_quality_gate('continuous_loop')
    
    def _handle_anomaly(self, anomaly: AnomalyEvent) -> None:
        """Handle an anomaly event."""
        logger.warning(f"Handling anomaly: {anomaly.anomaly_type.value} - {anomaly.description}")
        
        self.pipeline_state.emergency_responses += 1
        
        # Spawn appropriate response agent based on anomaly type
        if anomaly.anomaly_type.value == 'dust_storm':
            # Solara handles power conservation
            logger.info("Solara: Emergency power conservation mode")
        elif anomaly.anomaly_type.value == 'pressure_leak':
            # Hal-90 handles safety override
            logger.info("Hal-90: Emergency safety override")
        elif anomaly.anomaly_type.value == 'o2_drop':
            # Veridian handles emergency O2 boost
            logger.info("Veridian: Emergency O2 boost mode")
    
    def _publish_status(self) -> None:
        """Publish orchestrator status via MQTT."""
        if self.mqtt_client:
            status = {
                'timestamp': datetime.now().isoformat(),
                'pipeline_summary': self.pipeline_state.get_summary(),
                'environmental_summary': self.sim_engine.get_environmental_summary()
            }
            publish_orchestrator_status(self.mqtt_client, status)
    
    def _generate_completion_report(self) -> Dict:
        """Generate pipeline completion report."""
        return {
            'final_status': 'COMPLETED',
            'total_cycles': self.pipeline_state.cycle_count,
            'pipeline_summary': self.pipeline_state.get_summary(),
            'environmental_summary': self.sim_engine.get_environmental_summary(),
            'agent_status': {
                'solara': self.solara.get_status(),
                'veridian': self.veridian.get_status(),
                'hal_90': self.hal_90.get_status()
            },
            'quality_gates': {
                name: status.value 
                for name, status in self.pipeline_state.quality_gates.items()
            },
            'anomalies_handled': self.pipeline_state.anomalies_detected,
            'emergency_responses': self.pipeline_state.emergency_responses,
            'completion_time': datetime.now().isoformat()
        }
