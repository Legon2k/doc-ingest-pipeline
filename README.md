# AI-Driven Resume Tailoring Pipeline

An automated, local, event-driven pipeline designed for high-precision adaptation (tailoring) of a master resume to specific technical job descriptions. The project is architected following a "sniper approach" to effectively clear initial screenings and Applicant Tracking Systems (ATS) in the highly competitive Remote Senior .NET / Full Stack market.

## Project Purpose

The primary objective of the system is to eliminate the manual routine of mapping a resume to employer requirements while minimizing engineer interaction. Taking a single vacancy screenshot as the initial input, the pipeline automatically spins up the entire workflow, generating an organized artifact directory and a structured markdown note inside an Obsidian vault, ready for submission.

## Architecture & Features

The pipeline is split into three isolated stages. This protects the LLM's context window from being diluted by corporate fluff (preventing the *Lost in the Middle* effect) and guarantees 100% preservation of the master resume's original structure:

1. **OCR Stage — Screenshot → Raw Text:**
   * A local multimodal vision model performs OCR on the raw vacancy screenshot.
   * Two vision models are supported and switchable via `.env`:
     * `GLM-OCR` — a dedicated OCR model; requires `LOCAL_LLM_CHAT_MODE=true` (native Ollama `/api/chat` endpoint) to reliably apply `num_ctx` overrides.
     * `minicpm-v:latest` — a general-purpose vision model; works with the default OpenAI-compatible `/v1/chat/completions` endpoint (`LOCAL_LLM_CHAT_MODE=false`).
   * Both models run at `temperature=0.0` for deterministic transcription.

2. **Compression Stage — Raw Text → Dense Tech Profile:**
   * A reasoning model (`gemma4` series) running at `temperature=0.0` filters the raw OCR output. All corporate clutter, benefits, soft skills, and company overviews are discarded.
   * The system outputs an ultra-dense technical profile (`*_vacancy_extraction.md`) containing only hard engineering facts: Target Role, Core Tech Stack, Cloud/Infrastructure, and Databases/Brokers.
   * A strict generation limit (`num_predict`) and context window (`num_ctx`) are applied via Ollama options to accelerate inference and prevent rambling.

3. **Resume Tailoring Stage — Profile + Template → Tailored Resume:**
   * The same local reasoning model maps the candidate's master resume template against the compressed technical profile.
   * The engine executes targeted adjustments (e.g., substituting equivalent patterns such as *Azure Functions → AWS Lambda*), maintaining strict chronological accuracy without hallucinations.
   * Due to the isolated, noise-free context, the model preserves the complete resume structure, including trailing sections (Education, Certifications).

4. **Export & Artifact Archiving:**
   * A dedicated timestamped folder (`YYYY-MM-DD_Company_Category`) is created inside the configured Google Drive archive path.
   * All artifacts are saved together: original screenshot, raw vacancy text (`*_vacancy.md`), compressed profile (`*_vacancy_extraction.md`), tailored resume (`*_resume.md`), and a PDF placeholder.
   * A structured Markdown note with YAML frontmatter (company, role, date, status, archive path) is written to the Obsidian vault for searchable application tracking.

## Tech Stack

* **Core Engine:** Python 3.11+, `pathlib`, `uv`
* **Vision / OCR:** `GLM-OCR` (native Ollama API) or `minicpm-v:latest` (OpenAI-compatible)
* **LLM / Reasoning:** `gemma4:e4b` / `gemma4:26b` (scalable to external endpoints: AWS Bedrock, OpenRouter)
* **Knowledge Management:** Obsidian Markdown (YAML frontmatter)
* **Target Environment:** Local workstation or headless Proxmox VE instance with Nvidia GPU

## Configuration

All parameters are controlled via `.env` (see `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `LOCAL_LLM_URL` | `http://localhost:11434/v1` | Ollama endpoint (OpenAI-compatible base URL) |
| `VISION_MODEL` | `llava:latest` | Vision/OCR model name |
| `LOCAL_LLM_CHAT_MODE` | `false` | `true` = native `/api/chat`; `false` = `/v1/chat/completions`. Use `true` for GLM-OCR |
| `LOCAL_LLM_NUM_CTX` | `8192` | Context window for vision requests. Raise if you hit `exceed_context_size_error` |
| `LOCAL_LLM_TIMEOUT` | `180` | Vision request timeout in seconds |
| `CLOUD_TEXT_MODEL` | `llama3.1:latest` | Reasoning model for compression and tailoring |
| `CLOUD_LLM_TIMEOUT` | `1800` | Reasoning request timeout in seconds |
| `GOOGLE_DRIVE_PATH` | `./google_drive` | Root path for artifact archiving |
| `OBSIDIAN_VAULT_PATH` | `./obsidian_vault` | Root path of the Obsidian vault |
| `TEMPLATES_DIR` | `./templates` | Directory containing per-category resume templates |

`LOCAL_LLM_CHAT_MODE` accepts `true/1/yes` or `false/0/no` (case-insensitive).

## Quick Start

```bash
# 1. Install dependencies
uv sync

# 2. Configure environment
cp .env.example .env
# Edit .env: set your Ollama host, model names, and storage paths

# 3. Add a vacancy file (image or text) under vacancies/<category>/
mkdir -p vacancies/developer_dotnet
cp screenshot.png "vacancies/developer_dotnet/Acme_Senior Net Developer.png"

# 4. Add a matching resume template under TEMPLATES_DIR
# File must be named <category>.md, e.g. developer_dotnet.md

# 5. Run
make run
```

## Utilities

### `md2pdf.py` — Standalone Markdown → PDF Converter

A one-off utility that converts any Markdown file to a styled PDF using the same CSS and rendering pipeline as the main exporter. Useful for re-generating a PDF from an already-tailored resume without running the full pipeline.

**Direct:**
```bash
uv run md2pdf.py "D:\My Drive\...\file_resume.md"
```

**Via Make:**
```bash
make md2pdf FILE="D:\My Drive\...\file_resume.md"
```

The output PDF is written next to the source file with the same stem (`file_resume.pdf`).

## Performance Metrics

Based on a local Nvidia mobile GPU setup (Ollama on a remote host):

| Stage | Time |
|---|---|
| OCR (GLM-OCR, native `/api/chat`) | ~15 s |
| Profile Compression | ~73 s |
| Resume Tailoring | ~77 s |
| **Total (TTP)** | **~2.5 min** |