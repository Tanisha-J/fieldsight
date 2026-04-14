import os
import json
import google.genai as genai
from google.genai import types

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

Evaluate visible indicators:
- Leaf discoloration (yellowing, browning, blackening)
- Spotting patterns (circular lesions, irregular spots)
- Edge burn or necrosis
- Wilting or drooping
- Mold or powdery coatings
- Leaf curling or deformation
- Stem damage
- Pest-like chewing or mining damage

Severity rules:
- 0 = healthy, no visible symptoms
- 3 = moderate, clear damage, spreading
- 6 = severe, large portions affected, major decline

Rules:
- Report only visually supported findings
- If image is unclear or evidence is weak, set confidence_score below 50
- severity must be 0 if disease_status is HEALTHY

Return raw JSON only, no markdown, no extra text:
{
    "disease_status": "DISEASED" or "HEALTHY",
    "severity": 0 or 3 or 6,
    "confidence_score": 0 to 100,
    "short_explanation": "brief visual explanation of what you see"
}
""")
            ])
        ]
    )
    result = json.loads(response.text.strip())
    return result