from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image
from dotenv import load_dotenv
from groq import Groq
import base64
import io
import json
import os
from typing import Optional, List

load_dotenv(dotenv_path=".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("❌ GROQ_API_KEY not found in .env file")

client = Groq(api_key=GROQ_API_KEY)

MAX_IMAGE_SIZE_MB = 8
MAX_IMAGE_SIZE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
GROQ_VISION_MODEL = os.getenv(
    "GROQ_VISION_MODEL",
    "meta-llama/llama-4-scout-17b-16e-instruct",
)
GROQ_CHAT_MODEL = os.getenv("GROQ_CHAT_MODEL", "llama-3.1-8b-instant")

print("✅ Groq-only backend mode active.")

app = FastAPI(
    title="DermaCare AI Backend",
    description="AI-powered skin and wound triage backend",
    version="2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str
    context: Optional[str] = ""


class TopPrediction(BaseModel):
    condition: str
    confidence: float


class AnalysisResponse(BaseModel):
    top_prediction: str
    top_3_predictions: List[TopPrediction]
    emergency_warning: str
    possible_condition: str
    confidence: str
    risk_level: str
    ai_report: str
    disclaimer: str


def validate_image_upload(file: UploadFile, file_bytes: bytes) -> bool:
    if len(file_bytes) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds {MAX_IMAGE_SIZE_MB}MB size limit.",
        )

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Allowed types: JPEG, PNG, WebP, GIF.",
        )

    try:
        image = Image.open(io.BytesIO(file_bytes))
        image.verify()
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Corrupted or invalid image file: {str(e)}",
        )

    return True


def is_likely_screenshot(image: Image.Image) -> bool:
    """
    Lightweight guard for obvious screenshots/documents.

    This is intentionally conservative. It rejects images with lots of flat
    color, sharp rectangular edges, or very low natural-photo variation.
    """

    sample = image.resize((96, 96)).convert("RGB")
    pixels = list(sample.getdata())
    total = len(pixels)
    unique_ratio = len(set(pixels)) / total

    near_white = sum(1 for r, g, b in pixels if r > 235 and g > 235 and b > 235) / total
    near_dark = sum(1 for r, g, b in pixels if r < 35 and g < 35 and b < 35) / total

    horizontal_edges = 0
    vertical_edges = 0
    for y in range(1, 96):
        row_change = 0
        for x in range(96):
            p1 = sample.getpixel((x, y - 1))
            p2 = sample.getpixel((x, y))
            row_change += sum(abs(p1[i] - p2[i]) for i in range(3))
        if row_change > 6500:
            horizontal_edges += 1

    for x in range(1, 96):
        col_change = 0
        for y in range(96):
            p1 = sample.getpixel((x - 1, y))
            p2 = sample.getpixel((x, y))
            col_change += sum(abs(p1[i] - p2[i]) for i in range(3))
        if col_change > 6500:
            vertical_edges += 1

    return (
        unique_ratio < 0.18
        or near_white > 0.55
        or near_dark > 0.55
        or (horizontal_edges + vertical_edges) > 34
    )


def reject_non_medical_image(reason: str) -> AnalysisResponse:
    report_text = (
        f"{reason}\n\n"
        "Please upload a clear, close-up photo of the affected skin or wound area "
        "in good lighting. Avoid screenshots, webpages, documents, full-page images, "
        "or unrelated photos."
    )

    return AnalysisResponse(
        top_prediction="Image not suitable for skin/wound analysis",
        top_3_predictions=[
            TopPrediction(condition="Non-medical or unsupported image", confidence=100.0),
            TopPrediction(condition="No reliable skin/wound finding", confidence=0.0),
            TopPrediction(condition="Upload a close-up skin/wound photo", confidence=0.0),
        ],
        emergency_warning="No medical triage was generated because the uploaded image is not suitable for analysis.",
        possible_condition="Image not suitable for analysis",
        confidence="0%",
        risk_level="Not assessed - upload a clear skin or wound photo",
        ai_report=report_text,
        disclaimer="This system can only provide preliminary guidance from relevant skin or wound images. It cannot diagnose screenshots, documents, or unrelated photos.",
    )


def screen_obvious_non_medical_image(image: Image.Image) -> Optional[AnalysisResponse]:
    if is_likely_screenshot(image):
        return reject_non_medical_image(
            "The uploaded image looks like a screenshot, document, webpage, or app screen rather than a close-up medical photo."
        )

    return None


def image_to_data_url(image: Image.Image) -> str:
    prepared = image.copy()
    prepared.thumbnail((1024, 1024))

    buffer = io.BytesIO()
    prepared.save(buffer, format="JPEG", quality=88, optimize=True)
    encoded_image = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{encoded_image}"


def extract_json_object(raw_text: str) -> dict:
    text = raw_text.strip()

    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("The vision model did not return a JSON object.")

    return json.loads(text[start : end + 1])


def clean_confidence(value, fallback: float = 0.0) -> float:
    try:
        confidence = float(str(value).replace("%", "").strip())
    except (TypeError, ValueError):
        confidence = fallback

    return round(max(0.0, min(100.0, confidence)), 2)


def build_predictions(items) -> List[TopPrediction]:
    predictions = []

    if isinstance(items, list):
        for item in items[:3]:
            if not isinstance(item, dict):
                continue

            condition = str(item.get("condition", "")).strip()
            if not condition:
                continue

            predictions.append(
                TopPrediction(
                    condition=condition,
                    confidence=clean_confidence(item.get("confidence")),
                )
            )

    while len(predictions) < 3:
        predictions.append(
            TopPrediction(
                condition="No additional reliable finding",
                confidence=0.0,
            )
        )

    return predictions[:3]


def determine_risk_level(condition: str, confidence: float) -> str:
    condition_lower = condition.lower()

    if any(
        word in condition_lower
        for word in ["severe", "deep laceration", "stitches", "infected wound", "charring", "cellulitis"]
    ):
        if confidence >= 60:
            return "🔴 High Risk - Seek prompt medical attention"
        return "🟠 Medium-High Risk - Consult a healthcare provider urgently"

    if any(
        word in condition_lower
        for word in ["moderate", "burn", "infection", "inflammation", "rash"]
    ):
        if confidence >= 60:
            return "🟠 Medium Risk - Consult a healthcare provider"
        return "🟡 Low-Medium Risk - Monitor closely and consider medical advice"

    if "normal healthy skin" in condition_lower:
        return "🟢 Low Risk - No obvious issue detected by the screening model"

    return "🟢 Low Risk - Monitor and maintain proper hygiene"


def generate_emergency_warning(condition: str) -> str:
    critical_terms = ["severe burn", "deep laceration", "infected wound", "cellulitis", "charring"]

    if any(term in condition.lower() for term in critical_terms):
        return "🚨 URGENT: This may require immediate professional medical evaluation."

    return "No immediate emergency detected. Continue monitoring and consult a doctor if symptoms worsen."


def analyze_image_with_groq_vision(image: Image.Image) -> AnalysisResponse:
    data_url = image_to_data_url(image)

    analysis_prompt = """
You are DermaCare AI, a careful medical triage assistant. Analyze the uploaded image directly.

Return only valid JSON with this exact structure:
{
  "is_medical_skin_image": true,
  "rejection_reason": "",
  "top_3_predictions": [
    {"condition": "short visual finding, not a final diagnosis", "confidence": 0}
  ],
  "possible_condition": "best preliminary visual finding",
  "confidence": 0,
  "risk_level": "Low Risk, Medium Risk, or High Risk with short reason",
  "emergency_warning": "urgent warning or no immediate emergency detected",
  "ai_report": "patient-friendly report with: condition summary, observed signs, severity, safe general care, red flags, when to consult a doctor, and disclaimer"
}

Rules:
- Use the actual image content. Do not reuse a generic answer.
- If the image is not a clear close-up of human skin, a wound, a rash, acne, bruise, burn, or similar visible skin concern, set is_medical_skin_image to false and explain rejection_reason.
- Do not diagnose with certainty.
- Do not prescribe medicines, dosages, or treatment plans.
- Recommend a licensed healthcare professional when symptoms are significant, worsening, unclear, or concerning.
- Confidence must be a number from 0 to 100.
"""

    try:
        chat_completion = client.chat.completions.create(
            model=GROQ_VISION_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a safe medical image triage assistant. You provide preliminary visual guidance only.",
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": analysis_prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
            temperature=0.2,
            max_tokens=1400,
            response_format={"type": "json_object"},
        )

        result = extract_json_object(chat_completion.choices[0].message.content)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Groq vision analysis failed: {str(e)}",
        )

    if not result.get("is_medical_skin_image", False):
        reason = str(result.get("rejection_reason", "")).strip()
        if not reason:
            reason = "The uploaded image is not a reliable close-up skin or wound photo."
        return reject_non_medical_image(reason)

    top_3_predictions = build_predictions(result.get("top_3_predictions"))
    top_prediction = str(result.get("possible_condition", "")).strip()
    if not top_prediction:
        top_prediction = top_3_predictions[0].condition

    top_confidence = clean_confidence(result.get("confidence"), top_3_predictions[0].confidence)
    risk_assessment = str(result.get("risk_level", "")).strip()
    if not risk_assessment:
        risk_assessment = determine_risk_level(top_prediction, top_confidence)

    emergency_alert = str(result.get("emergency_warning", "")).strip()
    if not emergency_alert:
        emergency_alert = generate_emergency_warning(top_prediction)

    medical_report = str(result.get("ai_report", "")).strip()
    if not medical_report:
        medical_report = (
            "The image was reviewed for preliminary triage, but no detailed narrative report was returned. "
            "Please consult a licensed healthcare professional for proper evaluation."
        )

    return AnalysisResponse(
        top_prediction=top_prediction,
        top_3_predictions=top_3_predictions,
        emergency_warning=emergency_alert,
        possible_condition=top_prediction,
        confidence=f"{top_confidence}%",
        risk_level=risk_assessment,
        ai_report=medical_report,
        disclaimer="⚠️ MEDICAL DISCLAIMER: This is a preliminary AI-assisted triage assessment only and should NOT be considered a medical diagnosis. Always consult a licensed healthcare professional.",
    )


@app.get("/")
async def health_check():
    return {
        "message": "🏥 DermaCare AI Backend is running",
        "status": "operational",
        "mode": "groq-vision",
        "vision_model": GROQ_VISION_MODEL,
        "endpoints": {
            "health": "GET /",
            "analyze": "POST /analyze",
            "chat": "POST /chat",
        },
    }


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_image(file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()
        validate_image_upload(file, file_bytes)

        image = Image.open(io.BytesIO(file_bytes)).convert("RGB")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to process uploaded file: {str(e)}",
        )

    try:
        rejection_response = screen_obvious_non_medical_image(image)
        if rejection_response:
            return rejection_response

        return analyze_image_with_groq_vision(image)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Image analysis failed: {str(e)}",
        )


@app.post("/chat")
async def chat_with_assistant(request: ChatRequest):
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        context_section = ""
        if request.context and request.context.strip():
            context_section = f"\nPREVIOUS REPORT CONTEXT:\n{request.context}\n"

        chat_prompt = f"""
You are DermaCare AI, a safe medical triage chatbot.

{context_section}

USER QUESTION:
{request.question}

Answer safely and clearly.

Rules:
- Do NOT prescribe medicines or dosages.
- Do NOT give final diagnosis.
- Recommend a licensed healthcare professional when needed.
- Use simple language.
- Mention emergency symptoms if relevant.
"""

        chat_completion = client.chat.completions.create(
            model=GROQ_CHAT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are DermaCare AI, a safe and professional medical triage assistant.",
                },
                {
                    "role": "user",
                    "content": chat_prompt,
                },
            ],
            temperature=0.4,
            max_tokens=700,
        )

        return {
            "answer": chat_completion.choices[0].message.content,
            "safety_note": "This is general guidance only. Please consult a licensed healthcare professional.",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Chat processing failed: {str(e)}",
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
