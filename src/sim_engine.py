"""
AETHER Simulation Engine
Environmental flux modeling using SimPy for habitat management simulation.
"""

import os
import simpy
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum


class AnomalyType(Enum):
    """Types of environmental anomalies that can occur."""
    DUST_STORM = "dust_storm"
    PRESSURE_LEAK = "pressure_leak"
    O2_DROP = "o2_drop"
    TEMPERATURE_SPIKE = "temperature_spike"
    SOLAR_FLARE = "solar_flare"


@dataclass
class EnvironmentalState:
    """Current state of the habitat environment."""
    battery_level: float  # Percentage (0-100)
    o2_level: float  # Percentage (19.5-21.5% is normal)
    temperature: float  # Celsius (18-26°C is Goldilocks Zone)
    co2_level: float  # PPM
    humidity: float  # Percentage
    solar_radiation: float  # W/m²
    power_generation: float  # Watts
    power_consumption: float  # Watts
    occupant_count: int
    time: datetime
    
    def is_goldilocks_zone(self) -> bool:
        """Check if environment is in the Goldilocks Zone for human survival."""
        return (
            self.battery_level >= 40.0 and
            19.5 <= self.o2_level <= 21.5 and
            18.0 <= self.temperature <= 26.0
        )


@dataclass
class AnomalyEvent:
    """Represents an environmental anomaly event."""
    anomaly_type: AnomalyType
    severity: float  # 0.0 to 1.0
    start_time: datetime
    duration: timedelta
    description: str
    affected_systems: List[str]


class SimPyEnvironment:
    """
    SimPy-based environmental simulation for AETHER habitat management.
    
    Manages time progression, solar day cycles, environmental state,
    and anomaly injection for testing agent responses.
    """
    
    def __init__(self, env: Optional[simpy.Environment] = None):
        """
        Initialize the simulation environment.
        
        Args:
            env: SimPy environment (creates new one if None)
        """
        self.env = env if env else simpy.Environment()
        self.state = EnvironmentalState(
            battery_level=75.0,
            o2_level=21.0,
            temperature=22.0,
            co2_level=400.0,
            humidity=45.0,
            solar_radiation=0.0,
            power_generation=0.0,
            power_consumption=500.0,
            occupant_count=4,
            time=datetime.now()
        )
        
        # Simulation parameters (from env with fallbacks)
        self.anomaly_probability = float(os.getenv('ANOMALY_PROBABILITY', '0.05'))
        self.solar_day_length = int(os.getenv('SOLAR_DAY_LENGTH', '24'))
        self.simulation_speed = float(os.getenv('SIMULATION_SPEED', '1.0'))
        
        # Event tracking
        self.anomalies: List[AnomalyEvent] = []
        self.anomaly_callbacks: List[Callable[[AnomalyEvent], None]] = []
        
        # Resource allocation tracking
        self.current_allocation: Dict[str, float] = {
            'solara': 0.0,
            'veridian': 0.0,
            'reserve': 0.0
        }
        
        # Start simulation processes
        self.env.process(self._solar_day_cycle())
        self.env.process(self._anomaly_generator())
    
    def start_solar_day_cycle(self) -> None:
        """Start the solar day cycle process."""
        self.env.process(self._solar_day_cycle())
    
    def _solar_day_cycle(self) -> None:
        """
        Simulate the solar day cycle affecting power generation.
        
        Solar radiation follows a sinusoidal pattern throughout the day,
        with peak at noon and zero at night.
        """
        while True:
            # Calculate time of day (0-24 hours)
            hour_of_day = self.state.time.hour + self.state.time.minute / 60.0
            
            # Calculate solar radiation (sinusoidal pattern)
            if 6 <= hour_of_day <= 18:  # Daylight hours
                # Peak at noon (12 hours), normalized to 0-1000 W/m²
                solar_angle = ((hour_of_day - 12) / 6) * (3.14159 / 2)  # -π/2 to π/2
                self.state.solar_radiation = max(0, 1000 * (1 - abs(solar_angle / (3.14159 / 2))))
            else:
                self.state.solar_radiation = 0.0
            
            # Calculate power generation based on solar radiation
            # Assume 8% efficiency and 10m² solar array (deliberately low to create resource contention)
            self.state.power_generation = self.state.solar_radiation * 10 * 0.08
            
            # Update battery level based on net power
            net_power = self.state.power_generation - self.state.power_consumption
            battery_capacity = 10000  # Wh
            battery_change = (net_power / battery_capacity) * 100  # Percentage change
            self.state.battery_level = max(0, min(100, self.state.battery_level + battery_change))
            
            # Advance time by 1 hour
            yield self.env.timeout(1)
            self.state.time += timedelta(hours=1)
    
    def _anomaly_generator(self) -> None:
        """
        Randomly generate environmental anomalies for testing.
        
        Anomalies occur with a probability defined by self.anomaly_probability
        and can affect various systems in the habitat.
        """
        while True:
            # Wait for next check (1 hour)
            yield self.env.timeout(1)
            
            # Random chance to generate anomaly
            if random.random() < self.anomaly_probability:
                anomaly = self._generate_random_anomaly()
                self.anomalies.append(anomaly)
                
                # Apply anomaly effects to environment
                self._apply_anomaly_effects(anomaly)
                
                # Notify callbacks
                for callback in self.anomaly_callbacks:
                    callback(anomaly)
    
    def _generate_random_anomaly(self) -> AnomalyEvent:
        """Generate a random anomaly event."""
        anomaly_type = random.choice(list(AnomalyType))
        severity = random.uniform(0.3, 1.0)
        duration = timedelta(hours=random.randint(1, 6))
        
        descriptions = {
            AnomalyType.DUST_STORM: "Dust storm reducing solar efficiency",
            AnomalyType.PRESSURE_LEAK: "Hull pressure leak detected",
            AnomalyType.O2_DROP: "Oxygen level dropping rapidly",
            AnomalyType.TEMPERATURE_SPIKE: "Temperature spike detected",
            AnomalyType.SOLAR_FLARE: "Solar flare radiation event"
        }
        
        affected_systems = {
            AnomalyType.DUST_STORM: ["solar_array", "power_generation"],
            AnomalyType.PRESSURE_LEAK: ["life_support", "atmosphere"],
            AnomalyType.O2_DROP: ["life_support", "o2_generation"],
            AnomalyType.TEMPERATURE_SPIKE: ["thermal_control", "life_support"],
            AnomalyType.SOLAR_FLARE: ["communications", "electronics"]
        }
        
        return AnomalyEvent(
            anomaly_type=anomaly_type,
            severity=severity,
            start_time=self.state.time,
            duration=duration,
            description=descriptions[anomaly_type],
            affected_systems=affected_systems[anomaly_type]
        )
    
    def _apply_anomaly_effects(self, anomaly: AnomalyEvent) -> None:
        """Apply the effects of an anomaly to the environment."""
        if anomaly.anomaly_type == AnomalyType.DUST_STORM:
            # Reduce solar efficiency
            self.state.solar_radiation *= (1 - anomaly.severity * 0.5)
            self.state.power_generation *= (1 - anomaly.severity * 0.5)
        
        elif anomaly.anomaly_type == AnomalyType.PRESSURE_LEAK:
            # Increase CO2, decrease O2
            self.state.co2_level += anomaly.severity * 100
            self.state.o2_level -= anomaly.severity * 0.5
        
        elif anomaly.anomaly_type == AnomalyType.O2_DROP:
            # Rapid O2 decrease
            self.state.o2_level -= anomaly.severity * 2.0
        
        elif anomaly.anomaly_type == AnomalyType.TEMPERATURE_SPIKE:
            # Temperature increase
            self.state.temperature += anomaly.severity * 10
        
        elif anomaly.anomaly_type == AnomalyType.SOLAR_FLARE:
            # Electronics stress, potential power issues
            self.state.power_consumption += anomaly.severity * 200
    
    def register_anomaly_callback(self, callback: Callable[[AnomalyEvent], None]) -> None:
        """Register a callback to be notified of anomalies."""
        self.anomaly_callbacks.append(callback)
    
    def apply_resource_allocation(self, allocation: Dict[str, float]) -> None:
        """
        Apply a resource allocation to the environment.
        
        Args:
            allocation: Dictionary with 'solara', 'veridian', 'reserve' power allocations
        """
        self.current_allocation = allocation
        
        # Adjust power consumption based on allocation
        base_consumption = 500.0  # Base habitat consumption
        veridian_power = allocation.get('veridian', 0)
        
        # Veridian's power affects O2 generation
        if veridian_power > 0:
            # More power = better O2 maintenance
            o2_generation_rate = veridian_power / 1000.0  # Simplified
            self.state.o2_level = min(21.5, max(19.5, self.state.o2_level + o2_generation_rate * 0.1))
        
        # Update total consumption
        self.state.power_consumption = base_consumption + veridian_power
    
    def get_battery_level(self) -> float:
        """Get current battery level."""
        return self.state.battery_level
    
    def get_o2_level(self) -> float:
        """Get current O2 level."""
        return self.state.o2_level
    
    def get_occupant_count(self) -> int:
        """Get current occupant count."""
        return self.state.occupant_count
    
    def get_current_time(self) -> datetime:
        """Get current simulation time."""
        return self.state.time
    
    def should_start_new_cycle(self) -> bool:
        """Check if a new orchestration cycle should start."""
        # Start new cycle every hour
        return self.state.time.minute == 0
    
    def is_running(self) -> bool:
        """Simulation is always running — battery can recharge when sun returns."""
        return True
    
    def get_environmental_summary(self) -> Dict:
        """Get a summary of the current environmental state."""
        return {
            'time': self.state.time.isoformat(),
            'battery_level': self.state.battery_level,
            'o2_level': self.state.o2_level,
            'temperature': self.state.temperature,
            'solar_radiation': self.state.solar_radiation,
            'power_generation': self.state.power_generation,
            'power_consumption': self.state.power_consumption,
            'is_goldilocks_zone': self.state.is_goldilocks_zone(),
            'active_anomalies': len([a for a in self.anomalies if a.start_time + a.duration > self.state.time])
        }
    
    def run(self, duration: float = 24.0) -> None:
        """
        Run the simulation for a specified duration.
        
        Args:
            duration: Duration in hours to run the simulation
        """
        self.env.run(until=duration)
