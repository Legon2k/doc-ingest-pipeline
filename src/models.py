"""
LLM client module.

Implements a hybrid routing architecture with two separate OpenAI-compatible
client instances:

  - local_client  → Ollama (vision model for OCR / screenshot extraction)
  - cloud_client  → Ollama *temporarily*, ready to be swapped for
                    AWS Bedrock, OpenRouter, or any OpenAI-compatible endpoint.
"""

import base64
from pathlib import Path

from openai import OpenAI

from src.config import Config


class LLMClient:
    """Manages communication with the local and cloud LLM endpoints."""

    def __init__(self) -> None:
        # Local Ollama client — used for vision tasks (OCR, screenshot parsing).
        self.local_client = OpenAI(
            base_url=Config.LOCAL_LLM_URL,
            api_key=Config.LOCAL_LLM_KEY,
        )

        # Cloud client — used for deep reasoning and resume tailoring.
        # Temporarily points to the same local Ollama instance.
        # Swap base_url and api_key here (or via .env) for AWS Bedrock / OpenRouter.
        self.cloud_client = OpenAI(
            base_url=Config.CLOUD_LLM_URL,
            api_key=Config.CLOUD_LLM_KEY,
        )

    # ------------------------------------------------------------------
    # Vision: screenshot → structured Markdown
    # ------------------------------------------------------------------

    def extract_text_from_screenshot(self, image_path: Path) -> str:
        """Send an image to the local vision model and return extracted text as Markdown.

        Args:
            image_path: Absolute or relative path to the image file (.png / .jpg).

        Returns:
            Extracted text content formatted as Markdown.
        """
        raw_bytes = image_path.read_bytes()
        encoded = base64.b64encode(raw_bytes).decode("utf-8")

        suffix = image_path.suffix.lower().lstrip(".")
        mime_type = "image/png" if suffix == "png" else "image/jpeg"

        response = self.local_client.chat.completions.create(
            model=Config.VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{encoded}"
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                "Extract all text from this job vacancy screenshot. "
                                "Preserve the original structure and formatting as Markdown. "
                                "Return only the extracted text — no commentary or preamble."
                            ),
                        },
                    ],
                }
            ],
        )
        return response.choices[0].message.content or ""

    # ------------------------------------------------------------------
    # Cloud reasoning: vacancy + template → tailored resume
    # ------------------------------------------------------------------

    def tailor_resume_via_cloud(self, vacancy_text: str, template_md: str) -> str:
        """Tailor a resume template to a specific job vacancy using the cloud model.

        Args:
            vacancy_text: The full text of the job vacancy (plain text or Markdown).
            template_md:  The abstract resume template in Markdown format.

        Returns:
            Tailored resume in Markdown format.
        """
        system_prompt = (
            "You are an expert career coach and senior technical writer. "
            "Your task is to tailor a resume/CV template to a specific job vacancy. "
            "Rules:\n"
            "- Preserve the Markdown structure of the template exactly.\n"
            "- Emphasise skills and experiences that match the job requirements.\n"
            "- Remove or downplay irrelevant sections.\n"
            "- Be concise, professional, and truthful — no embellishments.\n"
            "- Return only the tailored resume in Markdown. No commentary."
        )
        user_prompt = (
            f"## Job Vacancy\n\n{vacancy_text}\n\n"
            f"## Resume Template\n\n{template_md}\n\n"
            "Tailor the resume template to best match the job vacancy above."
        )

        response = self.cloud_client.chat.completions.create(
            model=Config.CLOUD_TEXT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or ""
