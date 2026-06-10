# AETHER — Quick Start Guide

Autonomous Environmental & Thermal Habitat Efficiency Regulator.

## Prerequisites

- **Python 3.11+** installed on your system
- **pip** package manager

## Installation

```bash
# Clone the repository
git clone https://github.com/aether/aether.git
cd aether

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Quick Run

```bash
python src/main.py --no-mqtt --cycles 24
```

This runs a 24-cycle simulation of the AETHER agent orchestration pipeline without requiring an MQTT broker.

### Expected Output

```
====================================================
AETHER PIPELINE COMPLETION REPORT
====================================================
Final Status: completed
Total Cycles: 24
Anomalies Handled: 6
Emergency Responses: 8
...
Quality Gates:
  ✓ initialization: PASS
  ✓ solara_audit: PASS
  ✓ veridian_audit: PASS
  ✓ resource_allocation: PASS
  ✓ continuous_loop: PASS
====================================================
```

All **5 quality gates** should report **PASS**. The pipeline orchestrates Solara (energy), Veridian (biology), and Hal-90 (mediation) across a full solar day cycle, handling anomalies and emergency responses autonomously.

## Next Steps

- **Simulation Core License** ($49): [Get on Gumroad](https://gumroad.com/l/aether-sim)
- **Orchestrator Pro License** ($199): [Get on Gumroad](https://gumroad.com/l/aether-pro)
- Full documentation and MQTT hardware integration guides available with Pro tier.

## License

MIT License — see [LICENSE](LICENSE) for details.
Orchestrator Pro tier requires a separate commercial license.
