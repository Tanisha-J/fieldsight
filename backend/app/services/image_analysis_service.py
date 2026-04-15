import os
import json
import google.genai as genai
from google.genai import types


class ImageAnalysisError(Exception):
    pass


def _get_genai_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY")
    return genai.Client(api_key=api_key)

async def analyze_image(image_bytes: bytes) -> dict:
    
    client = _get_genai_client()
        
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Content(parts=[
                types.Part(inline_data=types.Blob(mime_type="image/jpeg", data=image_bytes)),
                types.Part(text="""
You are a plant health visual assessment assistant. Analyze the provided plant image using only visible evidence.


Evaluate these visible indicators:
- Yellowing: yellow discoloration on leaves
- Browning: brown discoloration on leaves
- Brown spots: discrete brown spots or lesions
- Blackening: dark black areas on leaves or stem
- Pale color: unusually light or washed out leaf color
- Circular lesions: round, defined spots indicating fungal patterns
- Irregular spots: uneven, spreading spots
- Edge burn: browning or necrosis along leaf edges
- Wilting: drooping or limp leaves/stems
- Leaf curl: leaves curling inward or outward
- Mold: visible mold or mildew growth
- Powdery coating: white or grey powdery substance on leaves
- Stem damage: visible cracks, discoloration, or rot on stem
- Pest damage: chewing marks, holes, or mining trails
- Dry tissue: dry, brittle, or crispy leaf texture
- Patchy chlorophyll loss: uneven green loss across leaf surface
                           
Severity rules:
- 0 = HEALTHY: none of the above indicators are visible
- 1 = MILD: 1-2 indicators visible, affecting less than 25% of visible plant area
- 2 = MODERATE: 2-4 indicators visible, affecting 25-60% of visible plant area
- 3 = SEVERE: 4+ indicators visible, or any indicator affecting more than 60% of visible plant area
- severity must be 0 if disease_status is HEALTHY

Rules:
- Report only visually supported findings
- If image is unclear or evidence is weak, set confidence_score below 50
- severity must be 0 if disease_status is HEALTHY

Return raw JSON only, no markdown, no extra text:
{
    "disease_status": "DISEASED" or "HEALTHY",
    "severity":  0, 1, 2, or 3,
    "confidence_score": 0 to 100,
    "short_explanation": "brief visual explanation of what you see"
}
""")
            ])
        ]
    )
    text = (response.text or "").strip()
    if not text:
        raise ImageAnalysisError("Analysis unavailable (empty model response)")
    
    text = text.replace("```json", "").replace("```", "").strip()

    try:
        result = json.loads(text)
    except Exception:
        raise ImageAnalysisError("Invalid JSON response from model")

    disease_status = str(result.get("disease_status", "")).upper()
    if disease_status not in {"DISEASED", "HEALTHY", "NO PLANT"}:
        raise ImageAnalysisError(f"Invalid disease_status from model: {disease_status!r}")

    try:
        severity = int(result.get("severity", 0))
    except (TypeError, ValueError):
        raise ImageAnalysisError("Invalid severity from model")

    try:
        confidence_score = int(result.get("confidence_score", 0))
    except (TypeError, ValueError):
        raise ImageAnalysisError("Invalid confidence_score from model")

    if disease_status == "HEALTHY":
        severity = 0

    short_explanation = str(result.get("short_explanation", "")).strip()

    return {
        "disease_status": disease_status,
        "severity": severity,
        "confidence_score": confidence_score,
        "short_explanation": short_explanation,
    }
