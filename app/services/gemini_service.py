"""
Gemini Service — G6: only called with explicit trigger.
G4: API key stays server-side.
Implements Skills 2, 3, 4 from doc 11.
"""

import json
import httpx

from app.settings import settings
from app.schemas.enriched_contract import (
    validate_quote_extraction,
    validate_analysis,
    validate_po_extraction,
    QuoteExtraction,
    AnalysisData,
    POExtraction,
)

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


async def extract_quote_from_document(
    file_bytes: bytes,
    mime_type: str,
    rfq_items_json: str,
    schema_json: str,
) -> QuoteExtraction:
    """
    Skill 2: extract_quote_document.
    Extracts structured data from a quote PDF/image using Gemini.
    """
    import base64
    b64_data = base64.b64encode(file_bytes).decode()

    system_prompt = (
        "Eres un asistente especializado en procurement B2B chileno. "
        "Extrae datos estructurados de documentos de cotización.\n"
        "REGLAS ESTRICTAS:\n"
        "- Responde ÚNICAMENTE con JSON válido. Sin texto adicional.\n"
        "- Si un campo no está presente, usa null.\n"
        "- Precios son números sin puntos de miles.\n"
        "- Moneda: CLP, USD, EUR, UF.\n"
        "- match_confidence entre 0 y 1."
    )

    user_prompt = (
        f"Extrae los datos de esta cotización. Ítems del RFQ:\n{rfq_items_json}\n\n"
        f"Schema exacto:\n{schema_json}"
    )

    raw = await _call_gemini_multimodal(system_prompt, user_prompt, b64_data, mime_type, 0.1)
    data = _parse_json_response(raw)
    return validate_quote_extraction(data)


async def generate_comparative_analysis(
    rfq_title: str,
    items_summary: dict,
    context: str = "",
) -> AnalysisData:
    """
    Skill 3: generate_comparative_analysis.
    Generates procurement strategy from comparative price table.
    """
    system_prompt = (
        "Eres un Director de Adquisiciones Senior con 15 años de experiencia. "
        "Analizas tablas comparativas y recomiendas estrategias.\n"
        "Estrategias: BTC, CONSOLIDACION, HIBRIDA.\n"
        "Responde ÚNICAMENTE con JSON válido."
    )

    user_prompt = (
        f'Analiza cotizaciones para RFQ "{rfq_title}":\n'
        f"Resumen:\n{json.dumps(items_summary, default=str)}\n"
        f"Contexto: {context}"
    )

    raw = await _call_gemini_text(system_prompt, user_prompt, 0.3)
    data = _parse_json_response(raw)
    return validate_analysis(data)


async def extract_po_data(
    file_bytes: bytes,
    mime_type: str,
) -> POExtraction:
    """
    Skill 4: extract_po_data.
    Extracts data from a Purchase Order document.
    """
    import base64
    b64_data = base64.b64encode(file_bytes).decode()

    system_prompt = (
        "Eres un especialista en documentos de compra chilenos. "
        "Extrae datos de Órdenes de Compra (OC/PO).\n"
        "Responde ÚNICAMENTE con JSON válido.\n"
        "Si no identificas proveedor: supplier_identification_confidence = 'unknown'."
    )

    user_prompt = "Extrae los datos de esta Orden de Compra."

    raw = await _call_gemini_multimodal(system_prompt, user_prompt, b64_data, mime_type, 0.1)
    data = _parse_json_response(raw)
    return validate_po_extraction(data)


async def _call_gemini_text(system: str, user: str, temperature: float) -> str:
    url = f"{GEMINI_BASE}/{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
    payload = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"parts": [{"text": user}]}],
        "generationConfig": {
            "temperature": temperature,
            "response_mime_type": "application/json",
        },
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


async def _call_gemini_multimodal(
    system: str, user: str, b64_data: str, mime_type: str, temperature: float
) -> str:
    url = f"{GEMINI_BASE}/{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
    payload = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{
            "parts": [
                {"text": user},
                {"inline_data": {"mime_type": mime_type, "data": b64_data}},
            ]
        }],
        "generationConfig": {
            "temperature": temperature,
            "response_mime_type": "application/json",
        },
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


def _parse_json_response(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Gemini devolvió JSON inválido: {e}")
