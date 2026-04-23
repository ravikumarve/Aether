"""
AETHER Agent: Hal-90
Habitat Mediator & Command - Resolves conflicts and ensures human safety.
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import numpy as np


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MediationResult(Enum):
    """Result of conflict mediation."""
    APPROVED = "approved"  # Request approved as-is
    MODIFIED = "modified"  # Request modified to fit constraints
    REJECTED = "rejected"  # Request rejected
    EMERGENCY_OVERRIDE = "emergency_override"  # Safety override triggered


@dataclass
class GoldilocksZone:
    """The Goldilocks Zone parameters for human survival."""
    battery_min: float = 40.0  # Percentage
    o2_min: float = 19.5  # Percentage
    o2_max: float = 21.5  # Percentage
    temperature_min: float = 18.0  # Celsius
    temperature_max: float = 26.0  # Celsius
    
    def is_in_zone(self, battery: float, o2: float, temperature: float) -> bool:
        """Check if parameters are within Goldilocks Zone."""
        return (
            self.battery_min <= battery <= 100.0 and
            self.o2_min <= o2 <= self.o2_max and
            self.temperature_min <= temperature <= self.temperature_max
        )
    
    def get_violations(self, battery: float, o2: float, temperature: float) -> List[str]:
        """Get list of Goldilocks Zone violations."""
        violations = []
        
        if battery < self.battery_min:
            violations.append(f"Battery below {self.battery_min}%")
        
        if o2 < self.o2_min:
            violations.append(f"O2 below {self.o2_min}%")
        elif o2 > self.o2_max:
            violations.append(f"O2 above {self.o2_max}%")
        
        if temperature < self.temperature_min:
            violations.append(f"Temperature below {self.temperature_min}°C")
        elif temperature > self.temperature_max:
            violations.append(f"Temperature above {self.temperature_max}°C")
        
        return violations


@dataclass
class ResourceAllocation:
    """Final resource allocation decision."""
    timestamp: datetime
    mediation_result: MediationResult
    power_distribution: Dict[str, float]  # solara, veridian, reserve
    o2_target: float
    safety_verification: bool
    override_authority_used: bool
    conflict_resolution_details: Dict[str, any]
    recommendations: List[str]


class ConflictResolutionMatrix:
    """Matrix for resolving conflicts between agent requests."""
    
    def __init__(self):
        self.resolution_history: List[Dict] = []
        self.priority_weights = {
            'safety': 1.0,
            'battery': 0.9,
            'o2': 0.85,
            'comfort': 0.5
        }
    
    def resolve_conflict(self, solara_threshold: float,
                       veridian_request: float,
                       current_battery: float,
                       current_o2: float) -> Tuple[MediationResult, Dict]:
        """
        Resolve conflict between Solara and Veridian requests.
        
        Args:
            solara_threshold: Solara's power threshold (Watts)
            veridian_request: Veridian's power request (Watts)
            current_battery: Current battery level (percentage)
            current_o2: Current O2 level (percentage)
            
        Returns:
            Tuple of (MediationResult, resolution_details)
        """
        power_deficit = veridian_request - solara_threshold
        
        # Calculate priority scores
        battery_priority = self._calculate_battery_priority(current_battery)
        o2_priority = self._calculate_o2_priority(current_o2)
        
        resolution_details = {
            'power_deficit': power_deficit,
            'battery_priority': battery_priority,
            'o2_priority': o2_priority,
            'solara_threshold': solara_threshold,
            'veridian_request': veridian_request
        }
        
        # Decision logic
        if power_deficit <= 0:
            # No conflict - approve request
            result = MediationResult.APPROVED
            resolution_details['reason'] = "No conflict - request within threshold"
        
        elif battery_priority > o2_priority:
            # Battery priority higher - reject or modify request
            if current_battery < 30:
                result = MediationResult.REJECTED
                resolution_details['reason'] = "Battery critical - reject request"
            else:
                result = MediationResult.MODIFIED
                resolution_details['reason'] = "Battery priority - modify request"
                resolution_details['modified_power'] = solara_threshold
        
        elif o2_priority > battery_priority:
            # O2 priority higher - approve with battery warning
            if current_o2 < 19.0:
                result = MediationResult.EMERGENCY_OVERRIDE
                resolution_details['reason'] = "O2 critical - emergency override"
            else:
                result = MediationResult.APPROVED
                resolution_details['reason'] = "O2 priority - approve request"
        
        else:
            # Equal priority - compromise
            result = MediationResult.MODIFIED
            resolution_details['reason'] = "Equal priority - compromise"
            resolution_details['modified_power'] = (solara_threshold + veridian_request) / 2
        
        # Record resolution
        self.resolution_history.append({
            'timestamp': datetime.now(),
            'result': result.value,
            **resolution_details
        })
        
        return result, resolution_details
    
    def _calculate_battery_priority(self, battery_level: float) -> float:
        """Calculate battery priority score (0.0 to 1.0)."""
        if battery_level < 20:
            return 1.0  # Critical
        elif battery_level < 40:
            return 0.8  # High
        elif battery_level < 60:
            return 0.5  # Medium
        else:
            return 0.2  # Low
    
    def _calculate_o2_priority(self, o2_level: float) -> float:
        """Calculate O2 priority score (0.0 to 1.0)."""
        if o2_level < 19.0:
            return 1.0  # Critical
        elif o2_level < 19.5:
            return 0.9  # High
        elif o2_level < 20.0:
            return 0.6  # Medium
        else:
            return 0.3  # Low


class SafetyProtocolOverride:
    """Manages safety protocol overrides."""
    
    def __init__(self):
        self.override_history: List[Dict] = []
        self.override_authority = True
    
    def can_override(self, reason: str, severity: float) -> bool:
        """
        Check if override is authorized.
        
        Args:
            reason: Reason for override
            severity: Severity level (0.0 to 1.0)
            
        Returns:
            True if override is authorized
        """
        if not self.override_authority:
            return False
        
        # High severity overrides are always authorized
        if severity >= 0.8:
            return True
        
        # Medium severity requires specific reasons
        if severity >= 0.5:
            valid_reasons = ['o2_critical', 'battery_critical', 'temperature_critical']
            return any(reason.startswith(valid) for valid in valid_reasons)
        
        return False
    
    def execute_override(self, reason: str, action: Dict) -> bool:
        """
        Execute safety override.
        
        Args:
            reason: Reason for override
            action: Override action to execute
            
        Returns:
            True if override executed successfully
        """
        logger.warning(f"Executing safety override: {reason}")
        
        self.override_history.append({
            'timestamp': datetime.now(),
            'reason': reason,
            'action': action
        })
        
        return True


class ResourceArbitrator:
    """Arbitrates resource allocation decisions."""
    
    def __init__(self):
        self.allocation_history: List[Dict] = []
    
    def allocate_resources(self, total_power: float,
                         mediation_result: MediationResult,
                         solara_threshold: float,
                         veridian_request: float) -> Dict[str, float]:
        """
        Allocate resources based on mediation result.
        
        Args:
            total_power: Total power available (Watts)
            mediation_result: Result of conflict mediation
            solara_threshold: Solara's power threshold
            veridian_request: Veridian's power request
            
        Returns:
            Dictionary with power distribution
        """
        if mediation_result == MediationResult.APPROVED:
            # Full approval
            veridian_power = veridian_request
            reserve_power = total_power - veridian_power
        
        elif mediation_result == MediationResult.MODIFIED:
            # Modified approval
            veridian_power = solara_threshold
            reserve_power = total_power - veridian_power
        
        elif mediation_result == MediationResult.REJECTED:
            # Rejected - minimal allocation
            veridian_power = solara_threshold * 0.5
            reserve_power = total_power - veridian_power
        
        elif mediation_result == MediationResult.EMERGENCY_OVERRIDE:
            # Emergency override - full allocation
            veridian_power = veridian_request
            reserve_power = max(0, total_power - veridian_power)
        
        else:
            # Default allocation
            veridian_power = total_power * 0.6
            reserve_power = total_power * 0.4
        
        allocation = {
            'solara': 0.0,  # Solara doesn't consume power
            'veridian': veridian_power,
            'reserve': reserve_power
        }
        
        # Record allocation
        self.allocation_history.append({
            'timestamp': datetime.now(),
            'allocation': allocation,
            'mediation_result': mediation_result.value
        })
        
        return allocation


class Hal90Agent:
    """
    Hal-90 - Habitat Mediator & Command Agent.
    
    Resolves conflicts between Solara and Veridian to ensure
    human occupant safety through the Goldilocks Zone.
    """
    
    def __init__(self, mqtt_client=None):
        """
        Initialize Hal-90 agent.
        
        Args:
            mqtt_client: MQTT client for communication
        """
        self.name = "Hal-90"
        self.role = "Habitat Mediator & Command"
        self.mqtt_client = mqtt_client
        
        # Tools
        self.conflict_matrix = ConflictResolutionMatrix()
        self.safety_override = SafetyProtocolOverride()
        self.resource_arbitrator = ResourceArbitrator()
        self.goldilocks_zone = GoldilocksZone()
        
        # State
        self.current_allocation: Optional[ResourceAllocation] = None
        self.retry_count = 0
        self.max_retries = 2
        
        logger.info(f"Hal-90 agent initialized")
    
    def mediate_conflict(self, solara_threshold: float,
                        veridian_request: float,
                        current_battery: float,
                        current_o2: float,
                        current_temperature: float,
                        total_power: float) -> ResourceAllocation:
        """
        Mediate conflict between Solara and Veridian requests.
        
        Args:
            solara_threshold: Solara's power threshold (Watts)
            veridian_request: Veridian's power request (Watts)
            current_battery: Current battery level (percentage)
            current_o2: Current O2 level (percentage)
            current_temperature: Current temperature (Celsius)
            total_power: Total power available (Watts)
            
        Returns:
            ResourceAllocation object with final decision
        """
        logger.info(f"Hal-90: Mediating conflict (Solara: {solara_threshold}W, Veridian: {veridian_request}W)")
        
        try:
            # Step 1: Check Goldilocks Zone
            goldilocks_violations = self.goldilocks_zone.get_violations(
                current_battery, current_o2, current_temperature
            )
            
            is_in_zone = len(goldilocks_violations) == 0
            
            # Step 2: Resolve conflict
            mediation_result, resolution_details = self.conflict_matrix.resolve_conflict(
                solara_threshold, veridian_request, current_battery, current_o2
            )
            
            # Step 3: Check for emergency override
            override_used = False
            if not is_in_zone:
                severity = len(goldilocks_violations) / 3.0  # Normalize to 0-1
                reason = f"Goldilocks Zone violations: {', '.join(goldilocks_violations)}"
                
                if self.safety_override.can_override(reason, severity):
                    self.safety_override.execute_override(reason, resolution_details)
                    override_used = True
                    mediation_result = MediationResult.EMERGENCY_OVERRIDE
            
            # Step 4: Allocate resources
            power_distribution = self.resource_arbitrator.allocate_resources(
                total_power, mediation_result, solara_threshold, veridian_request
            )
            
            # Step 5: Set O2 target
            if current_o2 < 19.5:
                o2_target = 21.0  # Boost O2
            elif current_o2 > 21.5:
                o2_target = 21.0  # Reduce O2
            else:
                o2_target = 21.0  # Maintain
            
            # Step 6: Verify safety
            safety_verification = self._verify_safety(
                power_distribution, o2_target, current_battery, current_o2, current_temperature
            )
            
            # Step 7: Generate recommendations
            recommendations = self._generate_recommendations(
                mediation_result, goldilocks_violations, safety_verification
            )
            
            # Create allocation object
            allocation = ResourceAllocation(
                timestamp=datetime.now(),
                mediation_result=mediation_result,
                power_distribution=power_distribution,
                o2_target=o2_target,
                safety_verification=safety_verification,
                override_authority_used=override_used,
                conflict_resolution_details=resolution_details,
                recommendations=recommendations
            )
            
            self.current_allocation = allocation
            self.retry_count = 0  # Reset retry count on success
            
            logger.info(f"Hal-90: Mediation complete (result: {mediation_result.value}, safety: {safety_verification})")
            
            return allocation
            
        except Exception as e:
            logger.error(f"Hal-90: Error during mediation: {e}")
            self.retry_count += 1
            raise
    
    def _verify_safety(self, power_distribution: Dict[str, float],
                     o2_target: float,
                     current_battery: float,
                     current_o2: float,
                     current_temperature: float) -> bool:
        """Verify that allocation maintains safety."""
        # Check that reserve power is sufficient
        if power_distribution['reserve'] < 100:
            return False
        
        # Check O2 target is reasonable
        if not (19.0 <= o2_target <= 22.0):
            return False
        
        # Check current conditions are not critical
        if current_battery < 20 or current_o2 < 18.0:
            return False
        
        return True
    
    def _generate_recommendations(self, mediation_result: MediationResult,
                                 violations: List[str],
                                 safety_verified: bool) -> List[str]:
        """Generate operational recommendations."""
        recommendations = []
        
        # Mediation result recommendations
        if mediation_result == MediationResult.APPROVED:
            recommendations.append("INFO: Request approved - proceed with allocation")
        elif mediation_result == MediationResult.MODIFIED:
            recommendations.append("WARNING: Request modified to fit constraints")
        elif mediation_result == MediationResult.REJECTED:
            recommendations.append("CRITICAL: Request rejected - safety priority")
        elif mediation_result == MediationResult.EMERGENCY_OVERRIDE:
            recommendations.append("EMERGENCY: Safety override activated")
        
        # Goldilocks Zone recommendations
        if violations:
            recommendations.append(f"WARNING: Goldilocks Zone violations: {', '.join(violations)}")
        
        # Safety verification recommendations
        if not safety_verified:
            recommendations.append("CRITICAL: Safety verification failed - review allocation")
        
        return recommendations
    
    def get_status(self) -> Dict:
        """Get current agent status."""
        return {
            'name': self.name,
            'role': self.role,
            'retry_count': self.retry_count,
            'current_allocation': self.current_allocation.__dict__ if self.current_allocation else None,
            'goldilocks_zone': {
                'battery_min': self.goldilocks_zone.battery_min,
                'o2_min': self.goldilocks_zone.o2_min,
                'o2_max': self.goldilocks_zone.o2_max,
                'temperature_min': self.goldilocks_zone.temperature_min,
                'temperature_max': self.goldilocks_zone.temperature_max
            },
            'override_authority': self.safety_override.override_authority,
            'resolution_count': len(self.conflict_matrix.resolution_history)
        }
