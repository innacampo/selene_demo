# Scripts

Utility scripts and tools that are not part of the main application package.

## Current Scripts

Scripts currently in root directory:
- `../setup_project.sh` - Automated project setup
- `../update_kb_chroma.py` - Knowledge base management utility

## Purpose

This directory should contain:
- Setup/installation scripts
- Database management tools
- Data import/export utilities
- Development helper scripts
- Maintenance tasks
- One-off migration scripts

## Usage Examples

```bash
# Run setup script
bash setup_project.sh

# Update knowledge base
python update_kb_chroma.py output/medgemma_kb_*.json
```

## Migration Note

To organize scripts:
1. Move `setup_project.sh` → `scripts/setup_project.sh`
2. Move `update_kb_chroma.py` → `scripts/update_kb_chroma.py`
3. Update references in README.md and CONTRIBUTING.md
4. Make scripts executable: `chmod +x scripts/*.sh`

Scripts here are meant to be run directly, not imported as modules.
