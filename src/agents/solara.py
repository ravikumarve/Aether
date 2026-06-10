"""
AETHER Agent: Solara
Energy Grid Optimizer - Maintains battery >40% while maximizing solar intake.
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np
from enum import Enum


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ForecastConfidence(Enum):
    """Confidence levels for power forecasts."""
    HIGH = "high"  # >85%
    MEDIUM = "medium"  # 70-85%
    LOW = "low"  # <70%


@dataclass
class PowerForecast:
    """Power forecast for a time period."""
    timestamp: datetime
    forecast_horizon: int  # hours
    solar_radiation_avg: float  # W/m²
    power_generation_avg: float  # Watts
    power_generation_peak: float  # Watts
    battery_projection: List[float]  # Battery level over time
    confidence: float  # 0.0 to 1.0
    confidence_level: ForecastConfidence
    power_threshold_40pct: float  # Watts threshold to maintain 40% battery
    recommendations: List[str]


class PowerGridAnalyzer:
    """Analyzes power grid status and trends."""
    
    def __init__(self):
        self.historical_data: List[Dict] = []
    
    def analyze_current_status(self, battery_level: float, 
                             power_generation: float,
                             power_consumption: float) -> Dict:
        """Analyze current power grid status."""
        net_power = power_generation - power_consumption
        
        status = {
            'battery_level': battery_level,
            'power_generation': power_generation,
            'power_consumption': power_consumption,
            'net_power': net_power,
            'is_charging': net_power > 0,
            'battery_trend': 'increasing' if net_power > 0 else 'decreasing',
            'time_to_depletion': self._calculate_time_to_depletion(battery_level, net_power),
            'efficiency_score': self._calculate_efficiency_score(power_generation, power_consumption)
        }
        
        self.historical_data.append({
            'timestamp': datetime.now(),
            **status
        })
        
        return status
    
    def _calculate_time_to_depletion(self, battery_level: float, net_power: float) -> Optional[float]:
        """Calculate time until battery depletion in hours."""
        if net_power >= 0:
            return None  # Not depleting
        
        battery_capacity = 10000  # Wh
        current_charge = battery_level / 100 * battery_capacity
        time_hours = current_charge / abs(net_power)
        return time_hours
    
    def _calculate_efficiency_score(self, generation: float, consumption: float) -> float:
        """Calculate power efficiency score (0.0 to 1.0)."""
        if consumption == 0:
            return 1.0
        
        efficiency = min(1.0, generation / consumption)
        return efficiency


class WeatherForecaster:
    """Forecasts weather conditions affecting power generation."""
    
    def __init__(self):
        self.forecast_history: List[Dict] = []
    
    def forecast_solar_radiation(self, hours_ahead: int = 24) -> List[float]:
        """
        Forecast solar radiation for the next N hours.
        
        Args:
            hours_ahead: Number of hours to forecast
            
        Returns:
            List of solar radiation values (W/m²)
        """
        # Simplified model: sinusoidal pattern with some randomness
        forecast = []
        current_hour = datetime.now().hour
        
        for i in range(hours_ahead):
            hour = (current_hour + i) % 24
            
            # Base sinusoidal pattern (peak at noon)
            if 6 <= hour <= 18:
                solar_angle = ((hour - 12) / 6) * (3.14159 / 2)
                base_radiation = max(0, 1000 * (1 - abs(solar_angle / (3.14159 / 2))))
            else:
                base_radiation = 0.0
            
            # Add some randomness for weather variability
            weather_factor = np.random.uniform(0.7, 1.0)
            radiation = base_radiation * weather_factor
            
            forecast.append(radiation)
        
        return forecast
    
    def calculate_confidence(self, forecast: List[float]) -> float:
        """
        Calculate confidence score for a forecast.
        
        Args:
            forecast: List of forecasted values
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        if len(forecast) < 2:
            return 0.5
        
        forecast_arr = np.array(forecast)
        
        # Nighttime detection: if current + next 5 hours are all near-zero,
        # return baseline confidence (solar is predictably zero at night)
        if np.all(forecast_arr[:6] < 1.0):
            return 0.85
        
        # Daytime: use coefficient of variation on significant (>10 W/m²) values.
        # This measures forecast stability relative to signal strength.
        # A deterministic sinusoidal forecast has cv ~0.5 → confidence ~0.92.
        # Random weather noise (factor 0.7-1.0) adds only ±15% variation.
        significant = forecast_arr[forecast_arr > 10.0]
        if len(significant) > 1:
            mean_val = np.mean(significant)
            std_val = np.std(significant)
            cv = std_val / mean_val if mean_val > 0 else 1.0
            confidence = max(0.70, 1.0 - cv * 0.15)
            return confidence
        
        return 0.85


class ArrayInclinometer:
    """Optimizes solar array inclination for maximum power generation."""
    
    def __init__(self):
        self.current_angle = 0.0  # Degrees from horizontal
        self.optimal_angle = 45.0  # Default optimal angle
    
    def calculate_optimal_angle(self, hour: int, day_of_year: int) -> float:
        """
        Calculate optimal solar array angle for given time.
        
        Args:
            hour: Hour of day (0-23)
            day_of_year: Day of year (1-365)
            
        Returns:
            Optimal angle in degrees
        """
        # Simplified calculation based on sun position
        # In reality, this would use complex astronomical calculations
        
        # Seasonal adjustment (higher angle in winter, lower in summer)
        seasonal_factor = -23.45 * np.cos((2 * np.pi / 365) * (day_of_year + 10))
        
        # Daily adjustment (track sun during day)
        if 6 <= hour <= 18:
            daily_factor = (hour - 12) * 2  # Tilt toward sun
        else:
            daily_factor = 0
        
        optimal_angle = 45 + seasonal_factor + daily_factor
        
        # Clamp to reasonable range
        optimal_angle = max(0, min(90, optimal_angle))
        
        return optimal_angle
    
    def adjust_array(self, target_angle: float) -> bool:
        """
        Adjust solar array to target angle.
        
        Args:
            target_angle: Target angle in degrees
            
        Returns:
            True if adjustment successful
        """
        # In reality, this would control physical motors
        self.current_angle = target_angle
        logger.info(f"Adjusted solar array to {target_angle:.1f}°")
        return True


class SolaraAgent:
    """
    Solara - Energy Grid Optimizer Agent.
    
    Maintains habitat battery levels above 40% while maximizing
    solar array intake through intelligent forecasting and optimization.
    """
    
    def __init__(self, mqtt_client=None):
        """
        Initialize Solara agent.
        
        Args:
            mqtt_client: MQTT client for communication
        """
        self.name = "Solara"
        self.role = "Energy Grid Optimizer"
        self.mqtt_client = mqtt_client
        
        # Tools
        self.grid_analyzer = PowerGridAnalyzer()
        self.weather_forecaster = WeatherForecaster()
        self.inclinometer = ArrayInclinometer()
        
        # State
        self.current_forecast: Optional[PowerForecast] = None
        self.retry_count = 0
        self.max_retries = 3
        
        logger.info(f"Solara agent initialized")
    
    def perform_power_audit(self, battery_level: float, 
                          power_generation: float,
                          power_consumption: float,
                          forecast_horizon: int = 24) -> PowerForecast:
        """
        Perform comprehensive power audit and forecast.
        
        Args:
            battery_level: Current battery level (percentage)
            power_generation: Current power generation (Watts)
            power_consumption: Current power consumption (Watts)
            forecast_horizon: Hours to forecast ahead
            
        Returns:
            PowerForecast object with complete analysis
        """
        logger.info(f"Solara: Performing power audit (battery: {battery_level}%, generation: {power_generation}W)")
        
        try:
            # Step 1: Analyze current grid status
            grid_status = self.grid_analyzer.analyze_current_status(
                battery_level, power_generation, power_consumption
            )
            
            # Step 2: Forecast solar radiation
            solar_forecast = self.weather_forecaster.forecast_solar_radiation(forecast_horizon)
            
            # Step 3: Calculate power generation forecast
            # Assume 20% efficiency and 10m² solar array
            power_forecast = [radiation * 10 * 0.2 for radiation in solar_forecast]
            
            # Step 4: Project battery levels over time
            battery_projection = self._project_battery_levels(
                battery_level, power_forecast, power_consumption, forecast_horizon
            )
            
            # Step 5: Calculate forecast confidence
            confidence = self.weather_forecaster.calculate_confidence(solar_forecast)
            
            # Step 6: Determine confidence level
            if confidence >= 0.85:
                confidence_level = ForecastConfidence.HIGH
            elif confidence >= 0.70:
                confidence_level = ForecastConfidence.MEDIUM
            else:
                confidence_level = ForecastConfidence.LOW
            
            # Step 7: Calculate power threshold to maintain 40% battery
            power_threshold = self._calculate_power_threshold(
                battery_level, power_consumption, forecast_horizon
            )
            
            # Step 8: Generate recommendations
            recommendations = self._generate_recommendations(
                grid_status, battery_projection, confidence_level, power_threshold
            )
            
            # Step 9: Optimize solar array angle
            current_hour = datetime.now().hour
            day_of_year = datetime.now().timetuple().tm_yday
            optimal_angle = self.inclinometer.calculate_optimal_angle(current_hour, day_of_year)
            self.inclinometer.adjust_array(optimal_angle)
            
            # Create forecast object
            forecast = PowerForecast(
                timestamp=datetime.now(),
                forecast_horizon=forecast_horizon,
                solar_radiation_avg=np.mean(solar_forecast),
                power_generation_avg=np.mean(power_forecast),
                power_generation_peak=max(power_forecast),
                battery_projection=battery_projection,
                confidence=confidence,
                confidence_level=confidence_level,
                power_threshold_40pct=power_threshold,
                recommendations=recommendations
            )
            
            self.current_forecast = forecast
            self.retry_count = 0  # Reset retry count on success
            
            logger.info(f"Solara: Power audit complete (confidence: {confidence:.2f}, threshold: {power_threshold:.1f}W)")
            
            return forecast
            
        except Exception as e:
            logger.error(f"Solara: Error during power audit: {e}")
            self.retry_count += 1
            raise
    
    def _project_battery_levels(self, initial_battery: float, 
                              power_forecast: List[float],
                              power_consumption: float,
                              hours: int) -> List[float]:
        """Project battery levels over time."""
        battery_capacity = 10000  # Wh
        projection = []
        current_battery = initial_battery
        
        for power_gen in power_forecast:
            net_power = power_gen - power_consumption
            battery_change = (net_power / battery_capacity) * 100
            current_battery = max(0, min(100, current_battery + battery_change))
            projection.append(current_battery)
        
        return projection
    
    def _calculate_power_threshold(self, current_battery: float,
                                   power_consumption: float,
                                   hours: int) -> float:
        """Calculate power threshold to maintain 40% battery."""
        battery_capacity = 10000  # Wh
        target_battery = 40.0
        battery_drop_needed = current_battery - target_battery
        energy_needed = (battery_drop_needed / 100) * battery_capacity
        avg_power_needed = energy_needed / hours
        
        # Add power consumption to get total generation needed
        power_threshold = power_consumption + avg_power_needed
        
        return power_threshold
    
    def _generate_recommendations(self, grid_status: Dict,
                                 battery_projection: List[float],
                                 confidence_level: ForecastConfidence,
                                 power_threshold: float) -> List[str]:
        """Generate operational recommendations."""
        recommendations = []
        
        # Battery level recommendations
        if grid_status['battery_level'] < 50:
            recommendations.append("WARNING: Battery level below 50%")
        if grid_status['battery_level'] < 40:
            recommendations.append("CRITICAL: Battery level below 40% - initiate conservation")
        
        # Power balance recommendations
        if not grid_status['is_charging']:
            recommendations.append("WARNING: System discharging - reduce non-essential loads")
        
        # Forecast confidence recommendations
        if confidence_level == ForecastConfidence.LOW:
            recommendations.append("CAUTION: Low forecast confidence - use conservative estimates")
        
        # Battery projection recommendations
        min_battery = min(battery_projection)
        if min_battery < 40:
            recommendations.append(f"WARNING: Battery projected to drop to {min_battery:.1f}%")
        
        # Efficiency recommendations
        if grid_status['efficiency_score'] < 0.8:
            recommendations.append("OPTIMIZATION: Power efficiency below 80% - review consumption")
        
        return recommendations
    
    def get_status(self) -> Dict:
        """Get current agent status."""
        return {
            'name': self.name,
            'role': self.role,
            'retry_count': self.retry_count,
            'current_forecast': self.current_forecast.__dict__ if self.current_forecast else None,
            'grid_analyzer_data_points': len(self.grid_analyzer.historical_data),
            'solar_array_angle': self.inclinometer.current_angle
        }
