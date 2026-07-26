"""FastAPI Server for Chrome Extension integration.

Provides endpoints for:
1. Receiving tailored Markdown from clipboard, parsing YAML metadata.
2. Saving raw .md and generating .pdf in timestamped archive folder.
3. Adding Cover Letter to the current active application folder.
4. Finalizing application state with Source URL and Obsidian note creation.
"""

import os
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.core.config import Config
from src.core.exporters import LocalArchiveExporter, compile_md_to_pdf

app = FastAPI(title="Resume Tailor Automation API", version="1.0.0")

# Включаем CORS, чтобы Chrome Extension мог без проблем делать fetch()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене можно ограничить id расширения
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------
# DTO Models
# ------------------------------------------------------------------
class ResumePayload(BaseModel):
    markdown_text: str
    url: Optional[str] = ""


class CoverLetterPayload(BaseModel):
    folder_path: str
    markdown_text: str


class FinalizePayload(BaseModel):
    folder_path: str
    url: str
    company: str
    role: str
    category: Optional[str] = "developer_dotnet"


# ------------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------------
def parse_payload_from_clipboard(text: str) -> tuple[dict[str, Any], str]:
    """Separates readable Markdown (Section 1) from compact JSON metadata (Section 2)."""
    raw = text.strip()

    # 1. Извлекаем блок после маркера ---JSON_START---
    if "---JSON_START---" in raw:
        parts = raw.split("---JSON_START---")

        # Все, что ДО маркера — чистое резюме (Секция 1)
        md_body = parts[0].strip()

        # Все, что ПОСЛЕ маркера — компактный JSON (Секция 2)
        json_part = parts[1].strip()

        # Очищаем от возможных кодовых блоков ```json ... ```
        json_part = re.sub(r"^```[a-zA-Z]*\n?", "", json_part)
        json_part = re.sub(r"\n?```$", "", json_part).strip()

        try:
            meta = json.loads(json_part)
            return meta, md_body
        except json.JSONDecodeError as exc:
            print(f"[API Warning] Could not parse mini-JSON: {exc}")
            return {}, md_body

    # 2. Если скопирован ТОЛЬКО сам JSON блок (быстрый тестер)
    if raw.startswith("{") and raw.endswith("}"):
        try:
            meta = json.loads(raw)
            return meta, meta.get("resume_markdown", "")
        except Exception:
            pass

    # 3. Резервный фоллбэк: если маркера нет совсем, отдаем весь текст
    return {}, raw


def sanitize_filename(name: str) -> str:
    """Sanitize string for safe filesystem usage."""
    return re.sub(r'[\\/*?:"<>|]', "", name).replace(" ", "_")


# ------------------------------------------------------------------
# API Endpoints
# ------------------------------------------------------------------
@app.post("/api/process-resume")
async def process_resume(payload: ResumePayload):
    meta, md_body = parse_payload_from_clipboard(payload.markdown_text)

    if not md_body:
        raise HTTPException(
            status_code=400, detail="Could not extract resume content"
        )

    # Забираем метаданные из Секции 2 (или берем фоллбэк)
    company = sanitize_filename(meta.get("company", "Company"))
    role = sanitize_filename(meta.get("role", "Developer"))
    category = sanitize_filename(meta.get("category", "developer_dotnet"))
    today = datetime.now().strftime("%Y-%m-%d")

    # Формируем пути
    folder_name = f"{today}_{company}_{category}"
    archive_dir = Config.GOOGLE_DRIVE_PATH / "Archive" / folder_name
    archive_dir.mkdir(parents=True, exist_ok=True)

    file_stem = f"{company}_{role}"
    md_file_path = archive_dir / f"{file_stem}_resume.md"
    pdf_file_path = archive_dir / f"{file_stem}_resume.pdf"

    # Сохраняем чистый Markdown из Секции 1
    md_file_path.write_text(md_body, encoding="utf-8")

    # Сборка PDF (позиционные аргументы: текст, путь)
    compile_md_to_pdf(md_body, pdf_file_path)

    return {
        "status": "success",
        "company": company,
        "role": role,
        "folder_path": str(archive_dir.resolve()),
        "pdf_path": str(pdf_file_path.resolve()),
        "md_path": str(md_file_path.resolve()),
    }

@app.post("/api/add-cover-letter")
async def add_cover_letter(payload: CoverLetterPayload):
    target_dir = Path(payload.folder_path)
    if not target_dir.exists():
        raise HTTPException(
            status_code=404, detail="Application folder not found"
        )

    # Используем наш универсальный парсер (заберет Markdown Секции 1)
    _, cl_body = parse_payload_from_clipboard(payload.markdown_text)

    cl_md_path = target_dir / "Cover_Letter.md"
    cl_pdf_path = target_dir / "Cover_Letter.pdf"

    cl_md_path.write_text(cl_body, encoding="utf-8")
    compile_md_to_pdf(cl_body, cl_pdf_path)

    return {
        "status": "success",
        "cover_letter_pdf": str(cl_pdf_path.resolve()),
    }

@app.post("/api/finalize-application")
async def finalize_application(payload: FinalizePayload):
    """Step 3: Save metadata card and generate note in Obsidian vault."""
    target_dir = Path(payload.folder_path)
    today = datetime.now().strftime("%Y-%m-%d")

    # 1. Записываем мета-карточку отклика в папку архива
    card_data = {
        "company": payload.company,
        "role": payload.role,
        "applied_date": today,
        "source_url": payload.url,
        "status": "applied",
    }
    card_path = target_dir / "application_card.yaml"
    with open(card_path, "w", encoding="utf-8") as f:
        yaml.dump(card_data, f, allow_unicode=True)

    # 2. Создаем заметку в Obsidian с помощью вашего класса LocalArchiveExporter
    try:
        exporter = LocalArchiveExporter()
        # Извлекаем текст резюме из сохраненного файла
        resume_md_files = list(target_dir.glob("*_resume.md"))
        tailored_md = (
            resume_md_files[0].read_text(encoding="utf-8")
            if resume_md_files
            else ""
        )

        exporter._create_obsidian_note(
            category=payload.category,
            company=payload.company,
            file_name_stem=f"{payload.company}_{payload.role}",
            archive_path=target_dir,
            tailored_md=tailored_md,
            today=today,
        )
    except Exception as exc:
        print(f"[API Warning] Failed to create Obsidian note: {exc}")

    return {"status": "completed", "obsidian_synced": True}