"""
LLM client module.

Implements a hybrid routing architecture with two separate OpenAI-compatible
client instances:

  - local_client  → Ollama (vision model for OCR / screenshot extraction)
  - cloud_client  → Ollama *temporarily*, ready to be swapped for
                    AWS Bedrock, OpenRouter, or any OpenAI-compatible endpoint.
"""

import base64
import re
from pathlib import Path

from openai import OpenAI

from src.config import Config


def _clean_llm_output(text: str) -> str:
    """Remove reasoning artifacts and markdown fences from LLM output.

    Strips DeepSeek / Gemma <think>…</think> blocks and ```markdown fences
    so only clean prose / Markdown is returned to the caller.
    """
    # Drop everything up to and including the closing </think> tag
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    # Remove opening ```markdown or plain ``` fences
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text.strip(), flags=re.MULTILINE)
    text = re.sub(r"```$", "", text.strip(), flags=re.MULTILINE)
    return text.strip()


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
    # Cloud pre-processing: raw vacancy → dense tech profile
    # ------------------------------------------------------------------

    def extract_vacancy_profile(self, raw_vacancy_text: str) -> str:
        """Strip corporate fluff from a raw vacancy and return a dense tech profile.

        Removes benefits, soft skills, company descriptions, and filler text,
        leaving only engineering facts relevant to resume tailoring.
        Also cleans reasoning artifacts emitted by DeepSeek/Gemma models.

        Args:
            raw_vacancy_text: Full raw text of the job vacancy.

        Returns:
            Compressed Markdown tech profile.
        """
        system_prompt = (
            "You are an advanced technical analyst. Your job is to strip all corporate fluff, "
            "benefits, soft skills, and company descriptions from a job description, "
            "leaving only dense engineering facts."
        )
        user_prompt = (
            f"Extract ONLY the core technical profile from this vacancy.\n\n"
            f"## Raw Vacancy:\n{raw_vacancy_text}\n\n"
            "Output a brief Markdown list with: Target Role, Core Tech Stack (languages/frameworks), "
            "Cloud/Infrastructure, and Databases/Brokers. "
            "Be extremely dense and concise. No chat, no commentary."
        )

        response = self.cloud_client.chat.completions.create(
            model=Config.CLOUD_TEXT_MODEL,
            timeout=Config.CLOUD_LLM_TIMEOUT,
            temperature=0.0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        raw = response.choices[0].message.content or ""
        return _clean_llm_output(raw)

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
            "You are a strict, fact-based technical resume adaptation engine. Your task is to update "
            "the phrasing of a resume to align with a vacancy without altering the document structure."
        )

        user_prompt = (
            f"## Job Vacancy\n\n{vacancy_text}\n\n"
            f"## Resume Template\n\n{template_md}\n\n"
            f"### MANDATORY INSTRUCTIONS FOR THE OUTPUT:\n"
            f"1. You are strictly FORBIDDEN from deleting any bullet points or achievements. If a job position has 6 bullets in the template, it MUST have exactly 6 bullets in your response.\n"
            f"2. Do NOT drop non-.NET experience (e.g., Python, Go). Keep it completely intact to preserve the candidate's seniority.\n"
            f"3. Tailor ONLY by rewriting or rephrasing existing sentences to highlight transferable skills (e.g., map ElasticSearch to OpenSearch context, or emphasize general microservices scale for AWS Lambda).\n"
            f"4. Maintain strict chronological truth. Never add React or modern tech to jobs from 2014.\n"
            f"5. Output ONLY the raw Markdown text of the resume. No chat, no commentary, no backticks. Start directly with the text."
            f"CRITICAL: Keep your internal thinking (<think> process) short, concise, and focused strictly on structural validation. Do not over-analyze."
        )

        #f"CRITICAL: Keep your internal thinking (<think> process) extremely short. Do not rewrite the entire resume inside the think tag. Just verify constraints and output the Markdown directly."

        response = self.cloud_client.chat.completions.create(
            model=Config.CLOUD_TEXT_MODEL,
            timeout=Config.CLOUD_LLM_TIMEOUT,
            temperature=0.0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            extra_body={
                "options": {
                    "num_predict": 16384,  # Максимальное количество токенов на вывод (включая <think>)
                    "num_ctx": 32768      # Общее окно контекста (чтобы влез шаблон + вакансия)
                }
            }            
        )

        message = response.choices[0].message

        # 1. Проверяем стандартный content
        content = message.content or ""

        # 2. Если там пусто, вытаскиваем текст из полей рассуждений (характерно для R1/Gemma)
        if not content.strip():
            # Проверяем официальное поле OpenAI для рассуждений или кастомное от Ollama
            content = getattr(message, "reasoning_content", None) or getattr(message, "reasoning", None) or ""

        return _clean_llm_output(content)
