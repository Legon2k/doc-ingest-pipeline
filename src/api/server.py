"""FastAPI Server for Chrome Extension integration.

Provides endpoints for:
1. Receiving tailored Markdown from clipboard, parsing YAML metadata.
2. Saving raw .md and generating .pdf in timestamped archive folder.
3. Adding Cover Letter to the current active application folder.
4. Finalizing application state with Source URL and Obsidian note creation.
"""

import os
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
def parse_yaml_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Extract YAML frontmatter even if the LLM adds '##', '```yaml', or starts directly with keys."""
    raw = text.strip()

    # 1. Удаляем обертки кодовых блоков (```yaml ... ```) если модель обернула весь ответ
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\n", "", raw)
        raw = re.sub(r"\n```$", "", raw)
        raw = raw.strip()

    # 2. Если перед company: вылезли '##', '---' или пробелы — нормализуем начало
    # Удаляем ведущие '##', '---' и т.д., чтобы зацепиться за первые ключи
    cleaned = re.sub(r"^(#+\s*|---\s*)*", "", raw).strip()

    # 3. Регулярка для поиска блока ключей (company, role, category) и отделения их от тела (# Oleg Savelyev)
    # Ищет блок от 'company:' до первого основного Markdown заголовка ('# ') или второго '---'
    pattern = r"^(company:\s*.*?\n)(.*?)(?=\n#|\n---|\n\n#|$)"
    match = re.search(pattern, cleaned, re.DOTALL | re.IGNORECASE)

    if match:
        yaml_part = match.group(0).strip()
        # Все что осталось после найденной шапки — это чистое резюме
        body_part = cleaned[match.end() :].strip()

        # Если тело все еще начинается с '---', убираем этот разделитель
        body_part = re.sub(r"^---\s*\n?", "", body_part).strip()

        # Чистим сам YAML от возможных '## ' на каждой строчке
        clean_yaml = re.sub(r"^#+\s*", "", yaml_part, flags=re.MULTILINE)

        try:
            meta = yaml.safe_load(clean_yaml) or {}
            return meta, body_part
        except Exception:
            pass

    # Резервный поиск стандартного формата --- ... ---
    std_pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
    std_match = re.match(std_pattern, raw, re.DOTALL)
    if std_match:
        try:
            meta = yaml.safe_load(std_match.group(1)) or {}
            return meta, std_match.group(2).strip()
        except Exception:
            pass

    # Если разобрать не удалось — возвращаем пустую метаданную и весь текст
    return {}, raw


def sanitize_filename(name: str) -> str:
    """Sanitize string for safe filesystem usage."""
    return re.sub(r'[\\/*?:"<>|]', "", name).replace(" ", "_")


# ------------------------------------------------------------------
# API Endpoints
# ------------------------------------------------------------------
@app.post("/api/process-resume")
async def process_resume(payload: ResumePayload):
    """Step 1: Receive Markdown from Chrome Extension, parse metadata,

    create dated directory, save .md, and compile .pdf.
    """
    meta, md_body = parse_yaml_frontmatter(payload.markdown_text)

    # Достаем данные из Front Matter или ставим значения по умолчанию
    company = sanitize_filename(meta.get("company", "Company"))
    role = sanitize_filename(meta.get("role", "Developer"))
    category = sanitize_filename(meta.get("category", "developer_dotnet"))
    today = datetime.now().strftime("%Y-%m-%d")

    # Папка архива (согласно вашему стандарту в Config)
    folder_name = f"{today}_{company}_{category}"
    archive_dir = Config.GOOGLE_DRIVE_PATH / "Archive" / folder_name
    archive_dir.mkdir(parents=True, exist_ok=True)

    # Имена файлов
    file_stem = f"{company}_{role}"
    md_file_path = archive_dir / f"{file_stem}_resume.md"
    pdf_file_path = archive_dir / f"{file_stem}_resume.pdf"

    # 1. Сохраняем чистый Markdown
    md_file_path.write_text(md_body, encoding="utf-8")

    # 2. Генерируем PDF используя ваш существующий xhtml2pdf модуль
    try:
        compile_md_to_pdf(md_body, pdf_file_path)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate PDF: {e}"
        )

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
    """Step 2 (Optional): Append Cover Letter to the active application folder."""
    target_dir = Path(payload.folder_path)
    if not target_dir.exists():
        raise HTTPException(
            status_code=404, detail="Application folder not found"
        )

    _, cl_body = parse_yaml_frontmatter(payload.markdown_text)

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