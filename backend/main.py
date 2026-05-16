from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image
from dotenv import load_dotenv
from groq import Groq
from transformers import CLIPProcessor, CLIPModel
import io
import os
from typing import Optional, List

# ============================================
# Configuration & Environment Setup
# ============================================

# Load environment variables from .env file
load_dotenv(dotenv_path=".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("❌ GROQ_API_KEY not found in .env file")

# Initialize Groq client for LLM
client = Groq(api_key=GROQ_API_KEY)

# Image validation configuration
MAX_IMAGE_SIZE_MB = 8  # 8 MB file size limit
MAX_IMAGE_SIZE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

# ============================================
# Load CLIP Vision Model
# ============================================

print("⏳ Loading OpenAI CLIP vision model...")
try:
    model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
    processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    print("✅ CLIP vision model loaded successfully")
except Exception as e:
    print(f"❌ Failed to load CLIP model: {str(e)}")
    raise

# ============================================
# Improved Medical Condition Labels
# ============================================

# Enhanced CLIP labels for better skin and wound classification
# Organized from severe to mild conditions
MEDICAL_CONDITION_LABELS = [
    # Severe conditions
    "severe burn wound with blistering and charring",
    "deep laceration or cut requiring stitches",
    "infected wound with pus or purulent discharge",
    "severe skin infection or cellulitis",
    
    # Moderate conditions
    "moderate burn with redness and swelling",
    "moderate laceration or deep cut",
    "infected acne with pustules and inflammation",
    "severe skin rash with spreading inflammation",
    "infected or inflamed bruise",
    
    # Mild to moderate conditions
    "minor burn or thermal injury",
    "minor cut or abrasion",
    "mild acne or pimple",
    "light skin rash or dermatitis",
    "bruise or contusion injury",
    "eczema or dry skin condition",
    
    # Normal conditions
    "normal healthy skin with no visible issues",
]

# ============================================
# FastAPI Application Setup
# ============================================

app = FastAPI(
    title="DermaCare AI Backend",
    description="Advanced AI-powered skin and wound triage system",
    version="2.0"
)

# Configure CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow requests from any origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# Pydantic Models for Request/Response
# ============================================

class ChatRequest(BaseModel):
    """Request model for the /chat endpoint"""
    question: str
    context: Optional[str] = ""


class TopPrediction(BaseModel):
    """Model for individual top prediction"""
    condition: str
    confidence: float


class AnalysisResponse(BaseModel):
    """Structured response model for image analysis endpoint"""
    # New fields
    top_prediction: str
    top_3_predictions: List[TopPrediction]
    emergency_warning: str
    
    # Legacy fields for frontend compatibility
    possible_condition: str
    confidence: str
    risk_level: str
    ai_report: str
    disclaimer: str


# ============================================
# Helper Functions
# ============================================

def validate_image_upload(file: UploadFile, file_bytes: bytes) -> bool:
    """
    Validate that uploaded file is a valid image with proper type and size.
    
    Args:
        file: UploadFile object with file metadata
        file_bytes: Raw file bytes
        
    Returns:
        bool: True if file passes validation
        
    Raises:
        HTTPException: If file fails any validation check
    """
    
    # Check 1: Verify file size does not exceed limit
    if len(file_bytes) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds {MAX_IMAGE_SIZE_MB}MB size limit. Size: {len(file_bytes) / (1024*1024):.1f}MB"
        )
    
    # Check 2: Verify MIME type is allowed image format
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Allowed types: JPEG, PNG, WebP, GIF"
        )
    
    # Check 3: Verify file can be opened and is not corrupted
    try:
        image = Image.open(io.BytesIO(file_bytes))
        image.verify()  # Verify image integrity
        # Note: verify() closes the image, so we'll re-open it in the analysis function
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Corrupted or invalid image file: {str(e)}"
        )
    
    return True


def get_top_3_predictions(labels: List[str], probabilities) -> List[TopPrediction]:
    """
    Extract top 3 predictions from CLIP model output.
    
    Args:
        labels: List of condition labels
        probabilities: Tensor of prediction probabilities for each label
        
    Returns:
        List[TopPrediction]: Top 3 predictions sorted by confidence score
    """
    
    # Create list of (label, confidence) tuples
    predictions = []
    for i, label in enumerate(labels):
        confidence_score = probabilities[i].item() * 100  # Convert to percentage
        predictions.append(TopPrediction(
            condition=label,
            confidence=round(confidence_score, 2)
        ))
    
    # Sort by confidence descending and return top 3
    predictions.sort(key=lambda x: x.confidence, reverse=True)
    return predictions[:3]


def determine_risk_level(condition: str, confidence: float) -> str:
    """
    Determine medical risk level based on detected condition and confidence.
    
    Args:
        condition: Detected condition description
        confidence: Confidence percentage from CLIP model
        
    Returns:
        str: Risk level classification with emoji indicator
    """
    
    # Define keyword indicators for each risk level
    high_risk_indicators = ["severe", "deep laceration", "stitches", "infected wound", "charring"]
    medium_risk_indicators = ["moderate", "burn", "infection", "cellulitis", "inflammation"]
    
    condition_lower = condition.lower()
    
    # High risk determination
    if any(indicator in condition_lower for indicator in high_risk_indicators):
        if confidence > 65:
            return "🔴 High Risk - Seek immediate medical attention"
        else:
            return "🟠 Medium-High Risk - Consult healthcare provider urgently"
    
    # Medium risk determination
    elif any(indicator in condition_lower for indicator in medium_risk_indicators):
        if confidence > 70:
            return "🟠 Medium Risk - Consult a healthcare provider"
        else:
            return "🟡 Low-Medium Risk - Monitor condition closely"
    
    # Low risk (normal or minor conditions)
    else:
        return "🟢 Low Risk - Monitor and maintain proper hygiene"


def generate_emergency_warning(condition: str) -> str:
    """
    Generate emergency warning alert if condition appears to be severe.
    
    Args:
        condition: Detected medical condition
        
    Returns:
        str: Emergency warning message or empty string
    """
    
    critical_conditions = [
        "severe burn",
        "deep laceration",
        "stitches",
        "infected wound",
        "cellulitis"
    ]
    
    condition_lower = condition.lower()
    
    if any(critical in condition_lower for critical in critical_conditions):
        return "🚨 URGENT: This condition may require immediate professional medical evaluation."
    
    return ""


def generate_ai_triage_report(condition: str, confidence: float, risk_level: str) -> str:
    """
    Generate comprehensive medical triage report using Groq LLM.
    
    Args:
        condition: Top predicted medical condition
        confidence: Confidence percentage from vision model
        risk_level: Risk level classification
        
    Returns:
        str: Professional medical triage report
    """
    
    # Build detailed prompt for LLM
    report_prompt = f"""
You are DermaCare AI, a professional medical triage assistant for skin and wound conditions.

VISION AI ANALYSIS RESULTS:
- Detected Condition: {condition}
- Confidence Level: {confidence}%
- Risk Classification: {risk_level}

Please generate a comprehensive, professional medical triage report that includes:

📋 REPORT STRUCTURE:
1. **Condition Summary**: Brief, clear explanation of the detected condition
2. **Typical Symptoms**: What patients with this condition commonly experience
3. **Severity Assessment**: Analysis of the risk level and what it means
4. **Preliminary Care Guidance**: Safe, general care recommendations (not prescriptions)
5. **When to Seek Professional Help**: Clear warning signs that require doctor consultation
6. **Home Management Tips**: General, safe recommendations if applicable
7. **Important Warnings**: Safety information on what NOT to do

⚠️ CRITICAL SAFETY GUIDELINES:
✓ ALWAYS use clear, non-technical language for general readers
✓ NEVER prescribe specific medications or dosages
✓ NEVER claim this is a final medical diagnosis
✓ ALWAYS emphasize consulting a licensed healthcare professional
✓ ALWAYS recommend professional evaluation for concerning symptoms
✓ ALWAYS prioritize patient safety in all recommendations

Format the response clearly with headers and bullet points for easy reading by patients.
"""
    
    try:
        # Call Groq LLM to generate report
        chat_completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": "You are a compassionate, safe, and professional medical triage assistant. Your role is to provide preliminary guidance only and never replace professional medical advice."
                },
                {
                    "role": "user",
                    "content": report_prompt
                }
            ],
            temperature=0.3,  # Low temperature for consistency
            max_tokens=900
        )
        
        return chat_completion.choices[0].message.content
        
    except Exception as e:
        return f"Report generation encountered an issue: {str(e)}\n\nPlease consult a healthcare professional for evaluation."


# ============================================
# API Endpoints
# ============================================

@app.get("/")
async def health_check():
    """
    Health check endpoint to verify backend is running.
    
    Returns:
        dict: Status information and available endpoints
    """
    return {
        "message": "🏥 DermaCare AI Backend v2.0 - Running",
        "status": "operational",
        "endpoints": {
            "health": "GET /",
            "analyze": "POST /analyze",
            "chat": "POST /chat"
        }
    }


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_image(file: UploadFile = File(...)):
    """
    Analyze uploaded medical image and generate triage report.
    
    This endpoint:
    - Validates uploaded image file (type, size, integrity)
    - Uses CLIP vision model to detect skin/wound conditions
    - Returns top 3 predictions with confidence scores
    - Generates professional medical report using Groq LLM
    - Includes emergency warnings for critical conditions
    
    Args:
        file: Medical image file (JPEG, PNG, WebP, or GIF)
        
    Returns:
        AnalysisResponse: Structured JSON with predictions, risk assessment, and report
        
    Raises:
        HTTPException: If file validation fails or processing encounters errors
    """
    
    try:
        # Read uploaded file bytes
        file_bytes = await file.read()
        
        # Validate file is valid image within size limits
        validate_image_upload(file, file_bytes)
        
        # Open image and convert to RGB (standard format for CLIP)
        image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to process uploaded file: {str(e)}"
        )
    
    try:
        # ============================================
        # CLIP Vision Model Inference
        # ============================================
        
        # Process image and labels through CLIP model
        inputs = processor(
            text=MEDICAL_CONDITION_LABELS,
            images=image,
            return_tensors="pt",
            padding=True
        )
        
        # Get CLIP predictions
        outputs = model(**inputs)
        logits_per_image = outputs.logits_per_image
        probabilities = logits_per_image.softmax(dim=1)[0]
        
        # Extract top 3 predictions
        top_3_predictions = get_top_3_predictions(
            MEDICAL_CONDITION_LABELS,
            probabilities
        )
        
        # Get top (most likely) prediction
        top_prediction = top_3_predictions[0].condition
        top_confidence = top_3_predictions[0].confidence
        
        # ============================================
        # Risk Assessment & Emergency Alerts
        # ============================================
        
        risk_assessment = determine_risk_level(top_prediction, top_confidence)
        emergency_alert = generate_emergency_warning(top_prediction)
        
        # ============================================
        # Generate AI Medical Report
        # ============================================
        
        medical_report = generate_ai_triage_report(
            top_prediction,
            top_confidence,
            risk_assessment
        )
        
        # ============================================
        # Build Structured Response
        # ============================================
        
        # Format confidence for display
        confidence_display = f"{top_confidence}%"
        
        return AnalysisResponse(
            # New enhanced fields
            top_prediction=top_prediction,
            top_3_predictions=top_3_predictions,
            emergency_warning=emergency_alert if emergency_alert else "No immediate emergency detected. Continue monitoring.",
            
            # Legacy fields for frontend compatibility
            possible_condition=top_prediction,
            confidence=confidence_display,
            risk_level=risk_assessment,
            ai_report=medical_report,
            disclaimer="⚠️ MEDICAL DISCLAIMER: This is a preliminary AI-assisted triage assessment only and should NOT be considered a medical diagnosis. Always consult a licensed healthcare professional for proper evaluation, diagnosis, and treatment."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Image analysis failed: {str(e)}"
        )


@app.post("/chat")
async def chat_with_assistant(request: ChatRequest):
    """
    Chat endpoint for follow-up questions about medical analysis.
    
    This endpoint:
    - Maintains conversation context from previous analysis
    - Answers user follow-up questions about detected conditions
    - Enforces medical safety throughout all responses
    - Recommends professional consultation when needed
    
    Args:
        request: ChatRequest with user question and optional context
        
    Returns:
        dict: Assistant response with safety note
        
    Raises:
        HTTPException: If question is empty or processing fails
    """
    
    # Validate user question is not empty
    if not request.question or not request.question.strip():
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty"
        )
    
    try:
        # ============================================
        # Build Context-Aware Chat Prompt
        # ============================================
        
        # Include previous analysis context if provided
        context_section = ""
        if request.context and request.context.strip():
            context_section = f"\nPREVIOUS ANALYSIS CONTEXT:\n{request.context}\n"
        
        # Build comprehensive chat prompt with safety guidelines embedded
        chat_prompt = f"""
You are DermaCare AI, a safe and professional medical triage chatbot specializing in skin and wound conditions.

{context_section}

USER QUESTION:
{request.question}

Please respond with helpful, accurate, and safe medical guidance.

🛡️ MANDATORY SAFETY REQUIREMENTS:
✓ NEVER prescribe medications or specific treatment regimens
✓ NEVER provide a final medical diagnosis
✓ NEVER contradict the importance of professional medical consultation
✓ ALWAYS recommend professional evaluation for:
  - Spreading or worsening conditions
  - Signs of infection (pus, warmth, redness)
  - Wounds that won't heal or show no improvement
  - Persistent pain or concerning symptoms
✓ ALWAYS communicate in simple, patient-friendly language
✓ ALWAYS provide only preliminary general health information
✓ ALWAYS include medical disclaimers when discussing treatments or care

Answer the user's specific question clearly while maintaining these safety standards.
"""
        
        # ============================================
        # Call Groq LLM for Response
        # ============================================
        
        chat_completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": "You are DermaCare AI, a compassionate and medically-informed triage assistant. Prioritize patient safety and always recommend professional medical consultation when appropriate."
                },
                {
                    "role": "user",
                    "content": chat_prompt
                }
            ],
            temperature=0.4,  # Balanced temperature for helpful responses
            max_tokens=700
        )
        
        response_text = chat_completion.choices[0].message.content
        
        return {
            "answer": response_text,
            "safety_note": "💡 Remember: This is general guidance only. Please consult a licensed healthcare professional for medical advice."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Chat processing failed: {str(e)}"
        )


# ============================================
# Main Entry Point
# ============================================

if __name__ == "__main__":
    import uvicorn
    
    # Run FastAPI server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
