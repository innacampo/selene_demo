# Examples

Example code, notebooks, and demonstrations of SELENE usage.

## Recommended Contents

```
examples/
├── basic_usage.py          # Simple usage example
├── advanced_features.py    # Advanced feature demonstrations
├── api_integration.py      # API integration examples
├── data_analysis.py        # Data analysis examples
└── notebooks/              # Jupyter notebooks
    ├── getting_started.ipynb
    ├── symptom_analysis.ipynb
    └── custom_reports.ipynb
```

## Purpose

This directory should contain:
- Standalone example scripts showing how to use SELENE
- Jupyter notebooks for interactive demonstrations
- Sample configurations
- Tutorial code
- Integration examples

## Example: Basic Usage

```python
# examples/basic_usage.py
"""
Basic example of using SELENE programmatically.
"""
from selene import med_logic, data_manager

# Initialize
profile = data_manager.load_user_profile()

# Query chat
response = med_logic.query_chat("What helps with hot flashes?", profile)
print(response)
```

## Example: Creating a Report

```python
# examples/generate_report.py
"""
Generate a clinical insights report.
"""
from datetime import datetime, timedelta
from selene.insights_generator import generate_hybrid_summary
from selene import data_manager

# Load data
pulse_data = data_manager.load_pulse_history()

# Generate report for last 30 days
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

report = generate_hybrid_summary(pulse_data, start_date, end_date)
print(report)
```

## Getting Started

1. Install SELENE in editable mode: `pip install -e .`
2. Copy an example: `cp examples/basic_usage.py my_script.py`
3. Modify and run: `python my_script.py`

## Contributing Examples

Have a useful example? Please contribute!
1. Create a clear, documented example
2. Add it to this directory
3. Update this README with a description
4. Submit a Pull Request

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.
