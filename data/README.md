# Data Directory

Data storage location for SELENE. Most subdirectories are gitignored to protect privacy and reduce repository size.

## Directory Structure

```
data/
├── metadata/           # Static metadata (tracked in git)
│   ├── stages.json
│   └── README.md
├── papers/             # Reference documents (tracked selectively)
│   └── *.pdf
├── models/             # Downloaded models (gitignored)
├── output/             # Generated outputs (gitignored)
│   └── *.json
├── reports/            # Generated reports (gitignored)
│   └── *.json
└── user_data/          # User data storage (gitignored, PRIVATE)
    ├── user_profile.json
    ├── pulse_history.json
    ├── backups/
    └── user_med_db/    # ChromaDB storage
```

## Current State

**Note**: Currently, these directories exist in the root. This README documents the recommended structure.

Existing directories in root:
- `../metadata/` - Move to `data/metadata/`
- `../papers/` - Move to `data/papers/`
- `../models/` - Move to `data/models/`
- `../output/` - Move to `data/output/`
- `../reports/` - Move to `data/reports/`
- `../user_data/` - Move to `data/user_data/`

## Tracked vs Gitignored

### ✅ Tracked in Git
- `metadata/` - Configuration and static data needed for app to run
- `papers/README.md` - Documentation about reference papers

### ❌ Gitignored (Privacy & Size)
- `papers/*.pdf` - Large reference documents
- `models/` - Downloaded ML models (large files)
- `output/` - Generated JSON exports
- `reports/` - Generated clinical reports
- `user_data/` - **PRIVATE** user data (never commit!)

## Migration Steps

To consolidate data directories:

1. **Update settings.py paths**:
   ```python
   BASE_DIR = Path(__file__).resolve().parent
   DATA_DIR = BASE_DIR / "data"
   
   USER_DATA_DIR = DATA_DIR / "user_data"
   STAGES_METADATA_PATH = DATA_DIR / "metadata" / "stages.json"
   REPORTS_DIR = DATA_DIR / "reports"
   OUTPUT_DIR = DATA_DIR / "output"
   PAPERS_DIR = DATA_DIR / "papers"
   ```

2. **Move directories**:
   ```bash
   mv metadata data/
   mv papers data/
   mv models data/
   mv output data/
   mv reports data/
   mv user_data data/
   ```

3. **Test all functionality** - Ensure app still works with new paths

4. **Update .gitignore** - Update paths if needed

## Data Privacy

**⚠️ CRITICAL**: `user_data/` contains sensitive health information.

- Never commit user_data/ to version control
- Ensure proper file permissions on production systems
- Regular backups stored securely
- Consider encryption for sensitive deployments

## Sample Data

For testing and examples, you can create sample data:

```python
# examples/create_sample_data.py
import json
from pathlib import Path

sample_profile = {
    "stage": "Perimenopause",
    "neuro_symptoms": ["Brain fog", "Mood changes"]
}

data_dir = Path("data/user_data")
data_dir.mkdir(parents=True, exist_ok=True)

with open(data_dir / "user_profile.json", "w") as f:
    json.dump(sample_profile, f, indent=2)
```

## Backup Recommendations

- user_data/ backed up daily
- Reports archived periodically
- Metadata version controlled
- Papers stored separately (large files)
