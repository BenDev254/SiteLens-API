# app/services/gemini_service.py

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

import httpx

from app.core.config import settings
from app.core.logging import request_id_ctx_var

from google import genai
from google.genai import types
from google import genai
from google.genai import types


logger = logging.getLogger(__name__)



def _configure_google_client() -> genai.Client:
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    return genai.Client(api_key=settings.GEMINI_API_KEY)


async def _call_gemini(prompt: str, model: Optional[str] = None) -> Dict[str, Any]:
    client = _configure_google_client()
    model_name = model or settings.GEMINI_MODEL

    def sync_call():
        return client.models.generate_content(
            model=model_name,
            contents=[{"text": prompt}],
        )

    try:
        response = await asyncio.to_thread(sync_call)
        return {"text": getattr(response, "output_text", str(response))}
    except Exception as exc:
        # If quota exhausted, return simple message
        err_str = str(exc)
        if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str:
            return {"text": "You have run out of quota. Please check your plan or billing."}
        return {"text": f"AI service error: {err_str}"}


async def analyze_document(
    file_bytes: bytes,
    prompt: str,
    mime_type: str = "application/pdf",  # default
    model: Optional[str] = None,
) -> dict:
    client = _configure_google_client()
    model_name = model or settings.GEMINI_MODEL

    def sync_call():
        return client.models.generate_content(
            model=model_name,
            contents=[
                {"inline_data": {"mime_type": mime_type, "data": file_bytes}},
                {"text": prompt},
            ],
        )

    try:
        response = await asyncio.to_thread(sync_call)
        return {
            "raw": response,
            "text": getattr(response, "output_text", str(response)),
        }
    except Exception as exc:
        err_str = str(exc)
        if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str:
            return {"text": "You have run out of quota. Please check your plan or billing."}
        return {"text": f"AI service error: {err_str}"}


async def analyze_video(
    *,
    project_id: int,
    video_bytes: bytes,
    prompt: str,
    mime_type: str = "video/mp4",
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyze a video using Gemini multimodal capabilities.

    The project_id is injected into the prompt to ensure traceability
    and contextual grounding for downstream persistence and audits.
    """
    client = _configure_google_client()
    model_name = model or settings.GEMINI_MODEL

    enriched_prompt = (
        f"Project ID: {project_id}\n"
        "You are an expert construction safety and risk analyst.\n"
        "Analyze the following video and extract:\n"
        "- Safety hazards\n"
        "- Risk severity levels\n"
        "- Visible locations or zones\n"
        "- Recommended mitigations\n\n"
        f"{prompt}"
    )

    def sync_call():
        return client.models.generate_content(
            model=model_name,
            contents=[
                {
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": video_bytes,
                    }
                },
                {"text": enriched_prompt},
            ],
        )

    try:
        response = await asyncio.to_thread(sync_call)
        return {
            "project_id": project_id,
            "raw": response,
            "text": getattr(response, "output_text", str(response)),
        }

    except Exception as exc:
        err_str = str(exc)
        if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str:
            return {
                "project_id": project_id,
                "text": "You have run out of quota. Please check your plan or billing.",
            }

        logger.exception(
            "Video analysis failed",
            extra={
                "project_id": project_id,
                "request_id": request_id_ctx_var.get(),
            },
        )

        return {
            "project_id": project_id,
            "text": f"AI service error: {err_str}",
        }


async def analyze_image(
    image_bytes: bytes,
    prompt: str,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    client = _configure_google_client()
    model_name = model or settings.GEMINI_MODEL

    def sync_call():
        return client.models.generate_content(
            model=model_name,
            contents=[
                {"inline_data": {"mime_type": "image/jpeg", "data": image_bytes}},
                {"text": prompt},
            ],
        )

    try:
        response = await asyncio.to_thread(sync_call)
        return {
            "raw": response,
            "text": getattr(response, "output_text", str(response)),
        }
    except Exception as exc:
        err_str = str(exc)
        if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str:
            return {"text": "You have run out of quota. Please check your plan or billing."}
        return {"text": f"AI service error: {err_str}"}



async def search_web(query: str, num_results: int = 3) -> List[Dict[str, Any]]:
    if not settings.GOOGLE_API_KEY or not settings.GOOGLE_SEARCH_CX:
        logger.debug("Google Search keys missing; returning empty grounding")
        return []

    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": settings.GOOGLE_API_KEY,
        "cx": settings.GOOGLE_SEARCH_CX,
        "q": query,
        "num": num_results,
    }

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

    results = []
    for item in data.get("items", []):
        results.append(
            {
                "title": item.get("title"),
                "snippet": item.get("snippet"),
                "link": item.get("link"),
            }
        )

    return results


async def analyze_assessment(
    texts: List[str],
    context_query: Optional[str] = None,
) -> Dict[str, Any]:
    grounding = []
    if context_query:
        grounding = await search_web(context_query)

    prompt_parts = [
        "You are an expert construction safety assessor. "
        "Analyze the following inputs and list findings, risk levels, locations, and recommendations."
    ]

    if grounding:
        prompt_parts.append(
            "Ground your analysis with the following web findings:\n"
            + "\n".join(
                [
                    f"- {g['title']}: {g['link']} ({g['snippet']})"
                    for g in grounding
                ]
            )
        )

    prompt_parts.extend([f"Input {i + 1}: {t}" for i, t in enumerate(texts)])
    prompt = "\n\n".join(prompt_parts)

    response = await _call_gemini(prompt)
    return {"response": response, "grounding": grounding}


async def archive_assessment(
    assessment_id: int,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    logger.info(
        "Archiving assessment %s",
        assessment_id,
        extra={"request_id": request_id_ctx_var.get()},
    )
    return {"archived": assessment_id, "notes": notes}


async def log_trend(
    project_id: int,
    metric: str,
    value: float,
    timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    ts = timestamp or datetime.utcnow().isoformat()
    logger.info(
        "Trend log",
        extra={
            "project_id": project_id,
            "metric": metric,
            "value": value,
            "ts": ts,
        },
    )
    return {"ok": True}


async def verify_compliance(
    text: str,
    regulation_query: Optional[str] = None,
) -> Dict[str, Any]:
    grounding = []
    if regulation_query:
        grounding = await search_web(regulation_query)

    prompt_parts = [
        "You are an expert regulatory compliance assistant. "
        "Given the following document, analyze whether it meets the requirements:"
    ]

    if grounding:
        prompt_parts.append(
            "Reference materials:\n"
            + "\n".join([g["link"] for g in grounding])
        )

    prompt_parts.append(text)
    prompt = "\n\n".join(prompt_parts)

    response = await _call_gemini(prompt)
    return {"verdict": response, "grounding": grounding}


async def transcribe_audio(
    audio_bytes: bytes,
    language_code: str = "en-US",
) -> str:
    try:
        from google.cloud import speech_v1p1beta1 as speech

        client = speech.SpeechClient()
        audio = speech.RecognitionAudio(content=audio_bytes)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code=language_code,
        )
        response = client.recognize(config=config, audio=audio)
        transcripts = [
            r.alternatives[0].transcript
            for r in response.results
            if r.alternatives
        ]
        return " ".join(transcripts)
    except Exception as exc:
        logger.debug("Speech-to-text not available or failed: %s", exc)

    try:
        preview = audio_bytes[:64]
        prompt = (
            "You are a speech transcription assistant. "
            "A short audio binary was provided (truncated). "
            "If possible, infer a brief description. "
            "Otherwise reply with '[transcription unavailable]'.\n"
            f"AudioPreviewBytes={preview!r}"
        )
        response = await _call_gemini(prompt)
        text = response.get("text")
        if text:
            return text
    except Exception:
        logger.debug("Gemini fallback transcription failed")

    return "[transcription unavailable]"
