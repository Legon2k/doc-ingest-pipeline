# **doc-ingest-pipeline**

# 1. Install dependencies
uv sync

# 2. Configure environment
cp .env.example .env
# Edit .env — set GOOGLE_DRIVE_PATH, OBSIDIAN_VAULT_PATH, models

# 3. Add a vacancy file
mkdir -p vacancies/architect
cp your_screenshot.png vacancies/architect/Acme_Solution_Architect.png

# 4. Run
uv run main.py