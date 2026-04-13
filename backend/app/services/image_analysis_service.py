import google.generativeai as genai
import os
import json

genai.configure(api_key =os. getenv ("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")

async def analyze_image(image_bytes: bytes) -> dict:
    response = model.generate_content([
        {
            "mime_type": "image/jpeg",
            "data": image_bytes
        },
"""
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
- Only use symptoms from the indicators list above

Return raw JSON only, no markdown, no extra text:
{
    "disease_status": "DISEASED" or "HEALTHY",
    "severity": 0, 1, 2, or 3,
    "confidence_score": 0 to 100,
    "symptoms_observed": ["indicator name from list", "indicator name from list"]
}
"""
    ])

    result = json.loads(response.text.strip())
    return result

   