from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from uuid import UUID
from .gemini import get_gemini_client
from .database import get_db

router = APIRouter(prefix="/api/study", tags=["Explanations"])


class SummaryRequest(BaseModel):
    session_id: UUID
    target_level: str = "easy"


@router.post("/explain")
async def explain_content(req: SummaryRequest):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "SELECT content FROM study_sessions WHERE id = %s",
                (str(req.session_id),),
            )
            row = cur.fetchone()
    finally:
        db.close()

    if not row:
        raise HTTPException(status_code=404, detail="Session not found")

    content = row[0]
    model = get_gemini_client()

    prompt = f"""
    You are an expert academic tutor. 
    Explain the following text in a way that is {req.target_level} to understand.
    Break down complex jargon into simple analogies. 
    Use clear headings and formatting.
    
    TEXT TO EXPLAIN:
    {content}
    """

    try:
        response = model.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return {"explanation": response.text, "target_level": req.target_level}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
