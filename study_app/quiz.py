import asyncio
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, Query

from study_app.models import (
    GenerateQuizRequest,
    QuizResponse,
    SubmitAnswerRequest,
    AnswerFeedback,
    QuizQuestionResponse
)
from study_app.quizservices import QuizService

router = APIRouter(tags=["Quiz & Rewards"])

def get_quiz_service() -> QuizService:
    return QuizService()

@router.post("/api/quiz/generate", response_model=QuizResponse)
async def generate_quiz(
    req: GenerateQuizRequest,
    svc: QuizService = Depends(get_quiz_service),
):
    """
    Generate quiz questions from a content session.
    Uses the simplified text if available, otherwise normalised text.
    """
    try:
        # We run this in an executor because the AI generation can be blocking
        return await asyncio.get_event_loop().run_in_executor(
            None, svc.generate_quiz, req
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

@router.get("/api/quiz/{session_id}", response_model=QuizResponse)
def get_quiz(
    session_id: UUID,
    user_id: UUID = Query(..., description="User ID to filter questions"),
    svc: QuizService = Depends(get_quiz_service),
):
    """Fetch all questions for a session (correct answers not included)."""
    try:
        # Fetching directly from the service which handles Supabase logic
        rows = svc.db.table("quiz_questions").select("*").eq("session_id", str(session_id)).execute().data
        
        questions = [
            QuizQuestionResponse(
                id=r["id"],
                session_id=r["session_id"],
                question_type=r["question_type"],
                question_text=r["question_text"],
                options=r.get("options"),
                difficulty=r.get("difficulty"),
                created_at=r["created_at"],
            )
            for r in rows
        ]
        return QuizResponse(session_id=session_id, questions=questions, total=len(questions))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/quiz/{session_id}/next", response_model=QuizResponse)
def get_next_questions(
    session_id: UUID,
    user_id: UUID = Query(...),
    svc: QuizService = Depends(get_quiz_service),
):
    """Return only questions the user hasn't answered yet."""
    return svc.get_unanswered(str(session_id), str(user_id))

@router.post("/api/quiz/answer", response_model=AnswerFeedback)
async def submit_answer(
    req: SubmitAnswerRequest,
    consecutive_correct: int = Query(
        default=0, ge=0, description="Current correct answer streak"),
    svc: QuizService = Depends(get_quiz_service),
):
    """Submit a user answer and get immediate AI feedback."""
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None, svc.submit_answer, req, consecutive_correct
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))