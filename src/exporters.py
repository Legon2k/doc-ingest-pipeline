"""
Exporters module.

Responsible for persisting all pipeline artifacts to:
  1. A timestamped archive folder inside Google Drive.
  2. A structured Markdown note inside an Obsidian vault.
"""

import shutil
from datetime import date
from pathlib import Path

import markdown as md_lib
from xhtml2pdf import pisa

from src.config import Config

# Inline CSS applied to every generated PDF resume.
# xhtml2pdf requires @page for margin control and built-in ReportLab fonts
# (Helvetica, Times-Roman) to avoid font resolution issues on Windows.
# Update: direct targeting of generated HTML list tags (ul, li).
_RESUME_CSS = """
@page {
    size: letter;
    margin: 15mm 20mm 15mm 20mm;
}
body {
    font-family: Helvetica, Arial, sans-serif;
    line-height: 1.5;
    font-size: 10pt;
    color: #333333;
}
h1 {
    font-size: 22pt;
    margin-bottom: 2px;
    text-transform: uppercase;
    color: #111111;
}
h2 {
    font-size: 13pt;
    border-bottom: 1px solid #cccccc;
    margin-top: 15px;
    padding-bottom: 2px;
    color: #222222;
}
h3 {
    font-size: 11pt;
    margin-top: 10px;
    margin-bottom: 2px;
    color: #111111;
}
p {
    margin-top: 0px;
    margin-bottom: 4px;
    word-wrap: break-word;
}
ul {
    margin-top: 2px;
    margin-bottom: 6px;
    padding-left: 20pt; /* Indent the entire list */
}
li {
    margin-bottom: 3px;
    list-style-type: disc; /* Use a bullet point */
    text-align: left;
}
hr {
    border: 0;
    border-top: 1px solid #cccccc;
    margin: 10px 0;
}
"""


class LocalArchiveExporter:
    """Archives pipeline artifacts to Google Drive and creates an Obsidian note."""

    def archive_all_artifacts(
        self,
        category: str,
        company: str,
        file_name_stem: str,
        source_file: Path,
        vacancy_text: str,
        vacancy_profile: str,
        tailored_md: str,
    ) -> None:
        """Copy all artifacts to a dated archive folder and create an Obsidian note.

        Archive folder naming convention:
            <GOOGLE_DRIVE_PATH>/Archive/YYYY-MM-DD_<Company>_<Category>/

        Artifacts written:
            - Original source file (screenshot or text)
            - <stem>_vacancy.md    — raw extracted vacancy text
            - <stem>_extraction.md — compressed tech profile (fluff stripped)
            - <stem>_resume.md     — tailored resume in Markdown
            - <stem>_resume.pdf    — compiled PDF resume

        Args:
            category:        Vacancy category / template name (e.g. "architect").
            company:         Company name parsed from the filename.
            file_name_stem:  Filename without extension (e.g. "Acme_Solution_Architect").
            source_file:     Path to the original vacancy file.
            vacancy_text:    Raw extracted vacancy content as Markdown.
            vacancy_profile: Compressed tech profile (output of extract_vacancy_profile).
            tailored_md:     Tailored resume content as Markdown.
        """
        today = date.today().strftime("%Y-%m-%d")
        folder_name = f"{today}_{company}_{category}"
        archive_dir = Config.GOOGLE_DRIVE_PATH / "Archive" / folder_name
        archive_dir.mkdir(parents=True, exist_ok=True)

        # 1. Copy the original source file (screenshot or text)
        shutil.copy2(source_file, archive_dir / source_file.name)

        # 2. Save raw extracted vacancy text
        (archive_dir / f"{file_name_stem}_vacancy.md").write_text(
            vacancy_text, encoding="utf-8"
        )

        # 3. Save compressed tech profile (fluff stripped)
        (archive_dir / f"{file_name_stem}_vacancy_extraction.md").write_text(
            vacancy_profile, encoding="utf-8"
        )

        # 4. Save the tailored resume
        (archive_dir / f"{file_name_stem}_resume.md").write_text(
            tailored_md, encoding="utf-8"
        )

        # 5. Compile and save the PDF resume
        _compile_md_to_pdf(tailored_md, archive_dir / f"{file_name_stem}_resume.pdf")

        print(f"[Exporter] Artifacts archived → {archive_dir}")

        # 6. Create an Obsidian note
        self._create_obsidian_note(
            category=category,
            company=company,
            file_name_stem=file_name_stem,
            archive_path=archive_dir,
            tailored_md=tailored_md,
            today=today,
        )

    def _create_obsidian_note(
        self,
        category: str,
        company: str,
        file_name_stem: str,
        archive_path: Path,
        tailored_md: str,
        today: str,
    ) -> None:
        """Write a structured Markdown note to the Obsidian vault.

        Note location:
            <OBSIDIAN_VAULT_PATH>/JobSearch/Applications/YYYY-MM-DD_<Company>_<Category>.md

        The note contains YAML frontmatter followed by the tailored resume content,
        making it fully searchable inside Obsidian.
        """
        notes_dir = Config.OBSIDIAN_VAULT_PATH / "JobSearch" / "Applications"
        notes_dir.mkdir(parents=True, exist_ok=True)

        # Derive a human-readable role from the filename stem.
        # Convention: "<Company>_<Role_Words>" → join remaining parts with spaces.        
        role_parts = file_name_stem.split("_")[1:]
        role = " ".join(role_parts) if role_parts else file_name_stem

        frontmatter = (
            "---\n"
            f"type: job-application\n"
            f"company: \"{company}\"\n"
            f"role: \"{role}\"\n"
            f"date: {today}\n"
            f"status: applied\n"
            f"archive_path: \"{archive_path}\"\n"
            "---\n\n"
        )

        note_path = notes_dir / f"{today}_{company}_{category}.md"
        note_path.write_text(frontmatter + tailored_md, encoding="utf-8")

        print(f"[Exporter] Obsidian note created → {note_path}")


def _compile_md_to_pdf(md_text: str, output_path: Path) -> None:
    """Convert a Markdown string to a styled PDF file using xhtml2pdf.

    xhtml2pdf runs on pure Python (reportlab backend) with no native
    system libraries required — works on Windows out of the box.

    Args:
        md_text:     Resume content in Markdown format.
        output_path: Destination path for the generated .pdf file.
    """
    # Step 0: Safe cleaning incoming markdown text from Rich Text artifacts
    # Replace non-breaking spaces (U+00A0) often introduced by copying from
    # Google Docs/Word/HTML with standard spaces, which xhtml2pdf requires
    # for consistent list processing [cite: integration plan].
    #md_text = md_text.replace('\xa0', ' ') # Replace U+00A0 with standard space

    # Step 1: Basic conversion of MD to HTML
    # This extension converts Markdown syntax into HTML tags like <ul> and <li>.
    html_body = md_lib.markdown(md_text, extensions=["extra", "smarty"])

    # Step 2: Form the full HTML with CSS.
    # The CSS is applied to generated HTML tags.
    styled_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <style>
        {_RESUME_CSS}
    </style>
</head>
<body>
    {html_body}
</body>
</html>"""

    # Step 3: Generate the PDF document using xhtml2pdf (pisa).
    # Reverted from DEBUG mode to functional mode [cite: integrate logic].
    with output_path.open("wb") as pdf_file:
        pisa_status = pisa.CreatePDF(
            styled_html,
            dest=pdf_file,
            encoding="utf-8",
        )

    if pisa_status.err:
        print(f"[Exporter] ERROR compiling PDF for {output_path.name}")