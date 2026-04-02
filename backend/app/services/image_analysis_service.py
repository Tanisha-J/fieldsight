import google.generativeai as genai
import os
import json

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")

async def analyze_image(image_bytes: bytes) -> dict:
    response = model.generate_content([
        {
            "mime_type": "image/jpeg",
            "data": image_bytes
        },
        """
        You are a plant health visual assessment assistant. Analyze the provided plant image using only visible evidence.

        Task:
        Assess plant health from the image only. Do not infer hidden conditions, lab results, or non-visible causes.

        Evaluate visible indicators:
        - Leaf discoloration (yellowing, browning, blackening, pale color)
        - Spotting patterns (circular lesions, irregular spots, fungal-like patterns)
        - Edge burn or necrosis
        - Wilting or drooping
        - Mold, mildew, powdery coatings
        - Leaf curling or deformation
        - Stem damage
        - Uneven coloration
        - Pest-like chewing/mining damage
        - Patchy chlorophyll loss
        - Dry/brittle tissue

        Possible causes (choose one):
        - fungal infection
        - bacterial infection
        - viral infection
        - nutrient deficiency
        - water stress
        - heat stress
        - physical damage
        - pest damage
        - natural aging
        - unknown

         Severity rules (integer only):
        - 0 = healthy, no visible symptoms
        - 3 = moderate, clear damage, spreading
        - 6 = severe, large portions affected, major decline

        Rules:
        - Report only visually supported findings.
        - If evidence is weak/unclear, use "likely_cause": "unknown" and "confidence": "low"

        Return raw JSON only, no markdown, no extra text, using exactly this schema:
        {
            "disease_status": "DISEASED" or "HEALTHY",
            "severity": 0 or 3 or 6,
            "likely_cause": "fungal infection | bacterial infection | viral infection | nutrient deficiency | water stress | heat stress | physical damage | pest damage | natural aging | unknown",
            "confidence": "low" or "medium" or "high",
            "short_explanation": "brief visual-evidence-based explanation"
        }

        severity must be 0 if disease_status is HEALTHY.
        """


    ])

    result = json.loads(response.text.strip())
    return result

   