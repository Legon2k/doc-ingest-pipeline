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

        #"Act as a precise OCR engine. Read the text from this image and list the technologies exactly as they appear. Do not extrapolate, do not add missing punctuation, and do not invent neighboring context. Output only the found text."
        response = self.local_client.chat.completions.create(
            model=Config.VISION_MODEL,
            temperature=0.0,
            timeout=Config.LOCAL_LLM_TIMEOUT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Act as a dumb, precise OCR scanner. Your only task is to read the image from top to bottom "
                                "and transcribe EVERY single visible word, line by line. "
                                "CRITICAL RULES:\n"
                                "1. Start from the very first pixel at the top (extract the main job title, company name, location, and citizenship requirements).\n"
                                "2. Do NOT summarize, do NOT rephrase, and do NOT skip any sections.\n"
                                "3. Keep lists and technologies exactly where they are physically located. Do NOT merge 'Nice to have' into 'Responsibilities'.\n"
                                "4. Output ONLY the raw transcribed text. No introductions, no Markdown improvements, no explanations."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{encoded}"
                            },
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
            "You are an expert technical resume writer. Your task is to tailor a candidate's base resume "
            "to a specific job vacancy using strict, fact-based adaptation.\n\n"
            "CRITICAL RULES:\n"
            "- STRUCTURE: Preserve the original Markdown structure and layout of the template exactly. Do NOT merge, split, or delete any job positions or chronological sections.\n"
            "- NO DELETIONS: Do NOT delete any professional achievements, bullet points, or engineering metrics. Keep the rich technical context of the resume intact.\n"
            "- TRUTHFULNESS & CHRONOLOGY: Be completely truthful. Never hallucinate or inject modern technologies into older job positions if they did not exist or were not used there (e.g., never add React.js, .NET 8, or AWS Lambda to jobs from 2014 unless it is already written in the base template).\n"
            "- HOW TO TAILOR: Adapt by shifting emphasis, NOT by lying. Rewrite or rephrase existing bullet points to highlight transferable skills that align with the vacancy (e.g., if the vacancy requires OpenSearch and the user has ElasticSearch, emphasize the search architecture skills; if the vacancy requires AWS Lambda, highlight event-driven architecture and scalable microservices).\n"
            "- OUTPUT: Return ONLY the tailored resume in Markdown. No introduction, no commentary, no markdown code block backticks. Start directly with the resume text."
        )
        user_prompt = (
            f"## Job Vacancy\n\n{vacancy_text}\n\n"
            f"## Resume Template\n\n{template_md}\n\n"
            "Tailor the resume template to best match the job vacancy above."
        )	
        
        response = self.cloud_client.chat.completions.create(
            model=Config.CLOUD_TEXT_MODEL,
            timeout=Config.CLOUD_LLM_TIMEOUT,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or ""
