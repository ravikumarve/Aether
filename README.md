# 🌌 AETHER - Autonomous Environmental & Thermal Habitat Efficiency Regulator

> **Multi-agent orchestration framework for autonomous habitat management in extreme environments**

AETHER is a sophisticated multi-agent system that uses a "Distributed Intelligence" model to manage the delicate balance between energy harvesting, life support, and structural integrity in extreme environments without requiring constant human oversight.

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- MQTT broker (e.g., Mosquitto) - optional for simulation-only mode
- pip package manager

### Installation

1. **Clone the repository**
   ```bash
   cd /media/matrix/DATA/opencode_projects/AETHER
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run the system**
   ```bash
   python src/main.py
   ```

### Basic Usage

Run a 24-cycle simulation:
```bash
python src/main.py --cycles 24
```

Run without MQTT (simulation only):
```bash
python src/main.py --no-mqtt --cycles 10
```

Enable verbose logging:
```bash
python src/main.py --verbose --cycles 5
```

## 🏗️ Architecture

### System Overview

AETHER uses an **Agents Orchestrator** pattern to coordinate three specialized agents:

```
┌─────────────────────────────────────────────────────────────┐
│                    Agents Orchestrator                        │
│                   (Pipeline Manager)                          │
│  - Coordinates agent handoffs                                 │
│  - Enforces quality gates                                    │
│  - Manages retry logic & escalation                           │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Solara     │ │   Veridian   │ │   Hal-90     │
│  (Energy)    │ │  (Bio-Regen) │ │  (Mediator)  │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       └────────────────┼────────────────┘
                        │
                ┌───────▼────────┐
                │  MQTT Broker   │
                │  (Mosquitto)   │
                └───────┬────────┘
                        │
                ┌───────▼────────┐
                │  SimPy Engine  │
                │  (Simulation) │
                └────────────────┘
```

### Agent Architecture

#### 🌞 Solara (Energy Grid Optimizer)
- **Goal**: Maintain battery >40% while maximizing solar intake
- **Tools**: PowerGridAnalyzer, WeatherForecaster, ArrayInclinometer
- **Behavior**: Prioritizes power efficiency; views inefficient usage as systemic failure

#### 🌿 Veridian (Bio-Regenerative Supervisor)
- **Goal**: Regulate O2/CO2 exchange and hydroponic nutrient delivery
- **Tools**: BiomassSensor, AtmosphericScrubber, NutrientInjector
- **Behavior**: Protective of "Green Lung"; prioritizes oxygen-producing moss over non-essential lighting

#### 🤖 Hal-90 (Habitat Mediator & Command)
- **Goal**: Resolve conflicts between Solara and Veridian; ensure human safety
- **Tools**: ConflictResolutionMatrix, SafetyProtocolOverride, ResourceArbitrator
- **Behavior**: Cold, analytical; cares only about the "Goldilocks Zone" for human survival

## 🔄 Pipeline Phases

### Phase 1: System Initialization
- Load environment variables and validate MQTT connection
- Start SimPy simulation engine with solar day cycle
- Register agents with Orchestrator
- **Quality Gate**: All agents registered, MQTT verified, SimPy running

### Phase 2: Solara Power Audit
- Scan solar radiation and current battery level
- Forecast 24h power limits with confidence scoring
- Calculate battery projection and 40% threshold
- **Quality Gate**: Forecast confidence >85%, battery projection verified

### Phase 3: Veridian Biological Audit
- Calculate water/light/power requirements for O2 maintenance
- Verify O2 production rate and nutrient schedule
- Check if power request exceeds Solara's threshold
- **Quality Gate**: O2 calculation verified, power request within realistic bounds

### Phase 4: Hal-90 Mediation (Conditional)
- Only triggered if Veridian's request > Solara's threshold
- Run conflict resolution matrix
- Apply Goldilocks Zone constraints (battery >40%, O2 >19.5%, temp 18-26°C)
- **Quality Gate**: Goldilocks Zone maintained, safety priority verified

### Phase 5: Resource Allocation
- Execute final resource allocation based on mediation or direct approval
- Publish allocation decision via MQTT
- Update simulation state with new resource distribution
- **Quality Gate**: Allocation published, simulation state updated

### Phase 6: Continuous Anomaly Loop
- Monitor MQTT topics for anomalies (dust storms, pressure leaks, O2 drops)
- Classify anomaly type and spawn appropriate response agent
- Validate emergency response effectiveness
- **Quality Gate**: Anomaly detected, response validated, simulation updated

## 📊 Project Structure

```
aether/
├── src/
│   ├── main.py              # Entry point for orchestrator loop
│   ├── orchestrator.py      # Agents Orchestrator implementation
│   ├── sim_engine.py        # SimPy environment simulation
│   ├── agents/              # Agent implementations
│   │   ├── solara.py        # Energy Grid Optimizer
│   │   ├── veridian.py      # Bio-Regenerative Supervisor
│   │   └── hal_90.py        # Habitat Mediator & Command
│   ├── mqtt_client.py       # MQTT communication layer
│   └── tools.py             # Agent tool classes (planned)
├── docs/
│   ├── README.md            # This file
│   └── AGENTS.md            # Agent specifications and workflow
├── requirements.txt         # Python dependencies
└── .env.example             # Environment variables template
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```bash
# MQTT Configuration
MQTT_BROKER=localhost
MQTT_PORT=1883
MQTT_USERNAME=
MQTT_PASSWORD=
MQTT_TOPIC_PREFIX=aether

# Simulation Configuration
SIMULATION_SPEED=1.0
SOLAR_DAY_LENGTH=24
ANOMALY_PROBABILITY=0.05

# Agent Configuration
SOLARA_FORECAST_HORIZON=24
VERIDIAN_O2_TARGET=21.0
HAL_90_BATTERY_THRESHOLD=40.0

# AI Configuration (optional)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```

### MQTT Topics

AETHER uses the following MQTT topics:

- `aether/solara/forecast` - Power forecasts and battery projections
- `aether/veridian/request` - Resource requests and O2 requirements
- `aether/hal_90/decision` - Final resource allocation decisions
- `aether/anomaly/alert` - Emergency anomaly notifications
- `aether/orchestrator/status` - Pipeline state and progress updates

## 🎯 Success Metrics

The AETHER system aims to achieve:

- **Pipeline Health**: >95% successful cycles
- **Average Cycle Time**: <5 seconds
- **Agent Reliability**: >98% success rate per agent
- **Quality Gate Pass Rate**: >99%
- **Anomaly Response Time**: <1 second
- **Emergency Response Effectiveness**: >95%

## 🚨 Error Handling & Retry Logic

| Agent | Max Retries | Escalation Trigger | Fallback Action |
|-------|-------------|-------------------|-----------------|
| **Solara** | 3 | Forecast confidence < 70% | Use conservative power estimate |
| **Veridian** | 3 | O2 calculation fails | Use minimum O2 production mode |
| **Hal-90** | 2 | Goldilocks Zone violation | Emergency safety override |
| **MQTT** | 5 | Connection timeout | Buffer messages, retry connection |
| **SimPy** | 2 | Simulation state corruption | Restart simulation from checkpoint |

## 🧪 Testing

Run the system with different configurations:

```bash
# Quick test (5 cycles, no MQTT)
python src/main.py --no-mqtt --cycles 5

# Full test (24 cycles, with MQTT)
python src/main.py --cycles 24

# Extended test (100 cycles, verbose)
python src/main.py --verbose --cycles 100
```

## 📈 Monitoring

### Pipeline Status

The orchestrator publishes pipeline status to `aether/orchestrator/status`:

```json
{
  "timestamp": "2024-01-15T10:30:00",
  "pipeline_summary": {
    "current_phase": "resource_allocation",
    "cycle_count": 12,
    "agent_status": {
      "solara": "complete",
      "veridian": "complete",
      "hal_90": "idle"
    },
    "quality_gates": {
      "initialization": "pass",
      "solara_audit": "pass",
      "veridian_audit": "pass"
    }
  },
  "environmental_summary": {
    "battery_level": 75.5,
    "o2_level": 21.0,
    "temperature": 22.0,
    "is_goldilocks_zone": true
  }
}
```

### Log Files

The system generates detailed logs in `aether.log`:

```
2024-01-15 10:30:00 - INFO - AETHER system starting
2024-01-15 10:30:01 - INFO - Phase 1: System Initialization
2024-01-15 10:30:02 - INFO - Phase 2: Solara Power Audit
2024-01-15 10:30:03 - INFO - Solara: Power audit complete (confidence: 0.92)
```

## 🔮 Future Enhancements

### Planned Features

- [ ] Integration with real hardware sensors
- [ ] Machine learning models for improved forecasting
- [ ] Web-based monitoring dashboard
- [ ] Mobile app for remote monitoring
- [ ] Integration with external AI services (OpenAI, Anthropic)
- [ ] Advanced anomaly detection using ML
- [ ] Multi-habitat coordination
- [ ] Historical data analysis and reporting

### Technical Debt

- [ ] Add comprehensive unit tests
- [ ] Implement integration tests
- [ ] Add performance profiling
- [ ] Improve error messages
- [ ] Add configuration validation
- [ ] Document API endpoints

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- **SimPy** - Discrete event simulation framework
- **paho-mqtt** - MQTT client library
- **agency-agents** - Agent patterns and inspiration

## 📞 Support

For issues, questions, or contributions:

- Open an issue on GitHub
- Check the documentation in `docs/AGENTS.md`
- Review the code comments and docstrings

## 🌟 Star History

If you find this project useful, please consider giving it a star!

---

**AETHER v1.0.0 - MVP Release**

*Autonomous habitat management for the extreme environments of tomorrow.*