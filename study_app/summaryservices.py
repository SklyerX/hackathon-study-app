from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from study_app.gemini import get_gemini_client
from study_app.config import get_settings, Settings

router = APIRouter(prefix="/api/study", tags=["Explanations"])


class SummaryRequest(BaseModel):
    content: str
    target_level: str = "easy"


@router.post("/explain")
async def explain_content(
    req: SummaryRequest,
    settings: Settings = Depends(get_settings)
):
    model = get_gemini_client()

    prompt = f"""
    You are an expert academic tutor. 
    Explain the following text in a way that is {req.target_level} to understand.
    Break down complex jargon into simple analogies. 
    Use clear headings and formatting.
    
    TEXT TO EXPLAIN:
    {req.content}
    """

    try:
        response = model.generate_content(prompt)
        return {
            "explanation": response.text,
            "target_level": req.target_level
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
