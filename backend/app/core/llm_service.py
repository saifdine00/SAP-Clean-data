"""
LLM Service — single public interface for AI-powered correction suggestions.

DESIGN CONTRACT:
  - This module is the ONLY place that imports or calls the Gemini API.
  - All other modules must call suggest_correction(value, context) from here.
  - To swap to Ollama: replace the body of _call_llm() and the __init__ only.
"""

import json
import logging
from typing import Optional
import google.generativeai as genai
from app.config import settings

logger = logging.getLogger(__name__)

# ── Singleton service ──────────────────────────────────────────────────────────

_service_instance: Optional["LLMService"] = None


def get_llm_service() -> "LLMService":
    global _service_instance
    if _service_instance is None:
        _service_instance = LLMService()
    return _service_instance


# ── Service class ──────────────────────────────────────────────────────────────

class LLMService:
    """
    Wraps the Gemini API. Swap to Ollama by replacing _call_llm().
    Public API: suggest_correction(value, context) → dict
    """

    MODEL = "gemini-2.0-flash"

    def __init__(self):
        if not settings.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY is not set — LLM suggestions will be disabled.")
            self._enabled = False
            return
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self._model = genai.GenerativeModel(self.MODEL)
        self._enabled = True
        logger.info("LLMService initialized with Gemini model: %s", self.MODEL)

    # ── Public method (the only entry-point for the rest of the codebase) ──────

    async def suggest_correction(self, value: str, context: dict) -> dict:
        """
        Ask the LLM to suggest a correction for a data anomaly.

        Args:
            value:   The raw / erroneous value extracted from the file.
            context: Dict with keys: anomaly_type, column_name, column_values (sample),
                     message, row_data (optional).

        Returns:
            {
              "suggested_value": str | None,
              "confidence":      float (0-1),
              "explanation":     str,
              "alternatives":    list[str]   # optional alternatives
            }
        """
        if not self._enabled:
            return self._disabled_response()

        prompt = self._build_prompt(value, context)
        try:
            raw = await self._call_llm(prompt)
            return self._parse_response(raw)
        except Exception as exc:
            logger.error("LLM call failed: %s", exc, exc_info=True)
            return self._error_response(str(exc))

    # ── Private helpers ────────────────────────────────────────────────────────

    def _build_prompt(self, value: str, context: dict) -> str:
        anomaly_type = context.get("anomaly_type", "unknown")
        column_name = context.get("column_name", "")
        message = context.get("message", "")
        sample_values = context.get("column_values", [])[:10]
        row_data = context.get("row_data", {})

        return f"""You are an expert SAP data migration consultant.
A data quality issue was detected in a file being prepared for SAP S/4HANA import.

ANOMALY TYPE: {anomaly_type}
COLUMN: {column_name}
PROBLEMATIC VALUE: "{value}"
ISSUE DESCRIPTION: {message}
OTHER VALUES IN THE SAME COLUMN (sample): {json.dumps(sample_values, ensure_ascii=False)}
FULL ROW DATA: {json.dumps(row_data, ensure_ascii=False)}

Your task:
1. Suggest the most likely correct value for "{value}".
2. Assign a confidence score from 0.0 (no idea) to 1.0 (certain).
3. Briefly explain your reasoning in one sentence.
4. Optionally list 1–3 alternative corrections.

Return ONLY a JSON object with this exact structure:
{{
  "suggested_value": "<corrected value or null>",
  "confidence": <float 0-1>,
  "explanation": "<one sentence>",
  "alternatives": ["<alt1>", "<alt2>"]
}}
Do NOT include markdown fences or any text outside the JSON."""

    async def _call_llm(self, prompt: str) -> str:
        """Call Gemini API — swap this method body to use Ollama."""
        response = await self._model.generate_content_async(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.2,
                max_output_tokens=512,
            ),
        )
        return response.text

    def _parse_response(self, raw: str) -> dict:
        """Parse JSON from LLM output, falling back gracefully."""
        raw = raw.strip()
        # Strip markdown code fences if model ignores instruction
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        try:
            data = json.loads(raw)
            return {
                "suggested_value": data.get("suggested_value"),
                "confidence": float(data.get("confidence", 0.5)),
                "explanation": data.get("explanation", ""),
                "alternatives": data.get("alternatives", []),
            }
        except json.JSONDecodeError:
            return {
                "suggested_value": None,
                "confidence": 0.0,
                "explanation": "LLM returned an unparseable response.",
                "alternatives": [],
            }

    @staticmethod
    def _disabled_response() -> dict:
        return {
            "suggested_value": None,
            "confidence": 0.0,
            "explanation": "LLM suggestions are disabled (GEMINI_API_KEY not configured).",
            "alternatives": [],
        }

    @staticmethod
    def _error_response(error: str) -> dict:
        return {
            "suggested_value": None,
            "confidence": 0.0,
            "explanation": f"LLM call failed: {error}",
            "alternatives": [],
        }
