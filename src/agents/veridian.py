"""
AETHER Agent: Veridian
Bio-Regenerative Supervisor - Regulates O2/CO2 exchange and hydroponic nutrient delivery.
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


class O2Status(Enum):
    """O2 level status categories."""
    CRITICAL = "critical"  # <19.5%
    WARNING = "warning"  # 19.5-20.0%
    NORMAL = "normal"  # 20.0-21.5%
    HIGH = "high"  # >21.5%


@dataclass
class BiologicalRequirements:
    """Biological system requirements for habitat maintenance."""
    timestamp: datetime
    occupant_count: int
    o2_target_level: float  # Percentage
    current_o2_level: float  # Percentage
    water_requirement_liters: float
    light_requirement_watts: float
    power_requirement_watts: float
    o2_production_rate: float  # Liters/hour
    co2_scrubbing_rate: float  # Liters/hour
    nutrient_schedule: Dict[str, float]
    o2_status: O2Status
    recommendations: List[str]


class BiomassSensor:
    """Monitors biomass and plant health in the habitat."""
    
    def __init__(self):
        self.biomass_levels: Dict[str, float] = {}
        self.plant_health: Dict[str, float] = {}
    
    def measure_biomass(self, zone: str) -> float:
        """Measure biomass level in a specific zone."""
        # Simplified measurement
        if zone not in self.biomass_levels:
            self.biomass_levels[zone] = np.random.uniform(0.7, 1.0)
        return self.biomass_levels[zone]
    
    def assess_plant_health(self, zone: str) -> float:
        """Assess plant health (0.0 to 1.0)."""
        if zone not in self.plant_health:
            self.plant_health[zone] = np.random.uniform(0.8, 1.0)
        return self.plant_health[zone]
    
    def get_o2_production_capacity(self, zone: str) -> float:
        """Calculate O2 production capacity for a zone."""
        biomass = self.measure_biomass(zone)
        health = self.assess_plant_health(zone)
        capacity = biomass * health * 10.0  # Liters/hour
        return capacity


class AtmosphericScrubber:
    """Manages CO2 scrubbing and atmospheric balance."""
    
    def __init__(self):
        self.scrubbing_efficiency = 0.95
        self.co2_levels: List[float] = []
    
    def calculate_scrubbing_requirement(self, current_co2: float, 
                                       target_co2: float = 400.0) -> float:
        """
        Calculate CO2 scrubbing requirement.
        
        Args:
            current_co2: Current CO2 level in PPM
            target_co2: Target CO2 level in PPM
            
        Returns:
            Required scrubbing rate in Liters/hour
        """
        co2_excess = max(0, current_co2 - target_co2)
        scrubbing_rate = co2_excess * 0.1  # Simplified conversion
        return scrubbing_rate
    
    def scrub_co2(self, rate: float) -> bool:
        """Perform CO2 scrubbing at specified rate."""
        # In reality, this would control scrubbing equipment
        logger.info(f"Scrubbing CO2 at {rate:.1f} L/h")
        return True


class NutrientInjector:
    """Manages nutrient delivery to hydroponic systems."""
    
    def __init__(self):
        self.nutrient_levels: Dict[str, float] = {
            'nitrogen': 0.8,
            'phosphorus': 0.7,
            'potassium': 0.75,
            'calcium': 0.6,
            'magnesium': 0.65
        }
        self.injection_schedule: Dict[str, float] = {}
    
    def calculate_nutrient_requirements(self, biomass: float, 
                                       health: float) -> Dict[str, float]:
        """
        Calculate nutrient requirements based on biomass and health.
        
        Args:
            biomass: Total biomass level
            health: Overall plant health
            
        Returns:
            Dictionary of nutrient requirements
        """
        base_requirements = {
            'nitrogen': 10.0,
            'phosphorus': 5.0,
            'potassium': 8.0,
            'calcium': 3.0,
            'magnesium': 2.0
        }
        
        # Adjust based on biomass and health
        factor = biomass * health
        requirements = {
            nutrient: amount * factor 
            for nutrient, amount in base_requirements.items()
        }
        
        return requirements
    
    def inject_nutrients(self, schedule: Dict[str, float]) -> bool:
        """Inject nutrients according to schedule."""
        self.injection_schedule = schedule
        logger.info(f"Injecting nutrients: {schedule}")
        return True
    
    def get_nutrient_status(self) -> Dict[str, float]:
        """Get current nutrient levels."""
        return self.nutrient_levels.copy()


class VeridianAgent:
    """
    Veridian - Bio-Regenerative Supervisor Agent.
    
    Regulates O2/CO2 exchange rates and manages hydroponic nutrient
    delivery to maintain habitat life support systems.
    """
    
    def __init__(self, mqtt_client=None):
        """
        Initialize Veridian agent.
        
        Args:
            mqtt_client: MQTT client for communication
        """
        self.name = "Veridian"
        self.role = "Bio-Regenerative Supervisor"
        self.mqtt_client = mqtt_client
        
        # Tools
        self.biomass_sensor = BiomassSensor()
        self.atmospheric_scrubber = AtmosphericScrubber()
        self.nutrient_injector = NutrientInjector()
        
        # State
        self.current_requirements: Optional[BiologicalRequirements] = None
        self.retry_count = 0
        self.max_retries = 3
        
        # Configuration
        self.o2_target = 21.0  # Percentage
        self.co2_target = 400.0  # PPM
        
        logger.info(f"Veridian agent initialized")
    
    def perform_biological_audit(self, occupant_count: int,
                                current_o2_level: float,
                                current_co2_level: float,
                                power_constraint: float) -> BiologicalRequirements:
        """
        Perform comprehensive biological resource audit.
        
        Args:
            occupant_count: Number of occupants in habitat
            current_o2_level: Current O2 level (percentage)
            current_co2_level: Current CO2 level (PPM)
            power_constraint: Maximum power available (Watts)
            
        Returns:
            BiologicalRequirements object with complete analysis
        """
        logger.info(f"Veridian: Performing biological audit (occupants: {occupant_count}, O2: {current_o2_level}%)")
        
        try:
            # Step 1: Assess O2 status
            o2_status = self._assess_o2_status(current_o2_level)
            
            # Step 2: Calculate O2 production requirements
            o2_production_needed = self._calculate_o2_requirement(
                occupant_count, current_o2_level
            )
            
            # Step 3: Calculate CO2 scrubbing requirements
            co2_scrubbing_needed = self.atmospheric_scrubber.calculate_scrubbing_requirement(
                current_co2_level, self.co2_target
            )
            
            # Step 4: Assess biomass and plant health
            total_biomass = 0.0
            total_health = 0.0
            zones = ['green_lung', 'hydroponics_a', 'hydroponics_b']
            
            for zone in zones:
                biomass = self.biomass_sensor.measure_biomass(zone)
                health = self.biomass_sensor.assess_plant_health(zone)
                total_biomass += biomass
                total_health += health
            
            avg_biomass = total_biomass / len(zones)
            avg_health = total_health / len(zones)
            
            # Step 5: Calculate resource requirements
            water_requirement = self._calculate_water_requirement(
                avg_biomass, avg_health, occupant_count
            )
            
            light_requirement = self._calculate_light_requirement(
                avg_biomass, avg_health
            )
            
            power_requirement = self._calculate_power_requirement(
                light_requirement, o2_production_needed, co2_scrubbing_needed
            )
            
            # Step 6: Check power constraint
            if power_requirement > power_constraint:
                logger.warning(f"Veridian: Power requirement ({power_requirement:.1f}W) exceeds constraint ({power_constraint:.1f}W)")
                # Adjust requirements to fit constraint
                power_requirement = power_constraint
                light_requirement = power_requirement * 0.6  # 60% for lighting
                o2_production_needed = power_requirement * 0.3  # 30% for O2
                co2_scrubbing_needed = power_requirement * 0.1  # 10% for CO2
            
            # Step 7: Calculate nutrient schedule
            nutrient_schedule = self.nutrient_injector.calculate_nutrient_requirements(
                avg_biomass, avg_health
            )
            
            # Step 8: Generate recommendations
            recommendations = self._generate_recommendations(
                o2_status, current_o2_level, avg_biomass, avg_health, power_requirement
            )
            
            # Create requirements object
            requirements = BiologicalRequirements(
                timestamp=datetime.now(),
                occupant_count=occupant_count,
                o2_target_level=self.o2_target,
                current_o2_level=current_o2_level,
                water_requirement_liters=water_requirement,
                light_requirement_watts=light_requirement,
                power_requirement_watts=power_requirement,
                o2_production_rate=o2_production_needed,
                co2_scrubbing_rate=co2_scrubbing_needed,
                nutrient_schedule=nutrient_schedule,
                o2_status=o2_status,
                recommendations=recommendations
            )
            
            self.current_requirements = requirements
            self.retry_count = 0  # Reset retry count on success
            
            logger.info(f"Veridian: Biological audit complete (power: {power_requirement:.1f}W, O2: {o2_production_needed:.1f}L/h)")
            
            return requirements
            
        except Exception as e:
            logger.error(f"Veridian: Error during biological audit: {e}")
            self.retry_count += 1
            raise
    
    def _assess_o2_status(self, o2_level: float) -> O2Status:
        """Assess O2 level status."""
        if o2_level < 19.5:
            return O2Status.CRITICAL
        elif o2_level < 20.0:
            return O2Status.WARNING
        elif o2_level <= 21.5:
            return O2Status.NORMAL
        else:
            return O2Status.HIGH
    
    def _calculate_o2_requirement(self, occupant_count: int, 
                                  current_o2_level: float) -> float:
        """Calculate O2 production requirement."""
        # Base O2 consumption per person: ~0.5 L/h
        base_consumption = occupant_count * 0.5
        
        # Calculate O2 deficit
        o2_deficit = max(0, self.o2_target - current_o2_level)
        
        # Additional production needed to reach target
        additional_production = o2_deficit * 10  # Simplified conversion
        
        total_requirement = base_consumption + additional_production
        
        return total_requirement
    
    def _calculate_water_requirement(self, biomass: float, 
                                    health: float,
                                    occupant_count: int) -> float:
        """Calculate water requirement in liters."""
        # Water for plants: ~5 L per biomass unit
        plant_water = biomass * health * 5.0
        
        # Water for occupants: ~2 L per person per day
        occupant_water = occupant_count * 2.0 / 24.0  # Per hour
        
        total_water = plant_water + occupant_water
        
        return total_water
    
    def _calculate_light_requirement(self, biomass: float, 
                                    health: float) -> float:
        """Calculate light requirement in watts."""
        # Base lighting: ~100 W per biomass unit
        base_lighting = biomass * health * 100.0
        
        # Adjust for health (less healthy plants need more light)
        health_factor = 1.0 + (1.0 - health) * 0.5
        light_requirement = base_lighting * health_factor
        
        return light_requirement
    
    def _calculate_power_requirement(self, light_watts: float,
                                    o2_production: float,
                                    co2_scrubbing: float) -> float:
        """Calculate total power requirement."""
        # Lighting power
        lighting_power = light_watts
        
        # O2 production power (simplified: 10 W per L/h)
        o2_power = o2_production * 10.0
        
        # CO2 scrubbing power (simplified: 5 W per L/h)
        co2_power = co2_scrubbing * 5.0
        
        # Base system power
        base_power = 50.0  # Pumps, controls, etc.
        
        total_power = lighting_power + o2_power + co2_power + base_power
        
        return total_power
    
    def _generate_recommendations(self, o2_status: O2Status,
                                 current_o2_level: float,
                                 biomass: float,
                                 health: float,
                                 power_requirement: float) -> List[str]:
        """Generate operational recommendations."""
        recommendations = []
        
        # O2 status recommendations
        if o2_status == O2Status.CRITICAL:
            recommendations.append("CRITICAL: O2 level critical - initiate emergency O2 boost")
        elif o2_status == O2Status.WARNING:
            recommendations.append("WARNING: O2 level low - increase O2 production")
        
        # Biomass recommendations
        if biomass < 0.7:
            recommendations.append("WARNING: Biomass levels low - review plant health")
        
        # Health recommendations
        if health < 0.8:
            recommendations.append("OPTIMIZATION: Plant health below 80% - adjust nutrients/lighting")
        
        # Power recommendations
        if power_requirement > 1000:
            recommendations.append("OPTIMIZATION: High power requirement - consider efficiency improvements")
        
        # General recommendations
        if current_o2_level > 21.5:
            recommendations.append("INFO: O2 level elevated - can reduce production")
        
        return recommendations
    
    def get_status(self) -> Dict:
        """Get current agent status."""
        return {
            'name': self.name,
            'role': self.role,
            'retry_count': self.retry_count,
            'current_requirements': self.current_requirements.__dict__ if self.current_requirements else None,
            'nutrient_levels': self.nutrient_injector.get_nutrient_status(),
            'o2_target': self.o2_target,
            'co2_target': self.co2_target
        }
