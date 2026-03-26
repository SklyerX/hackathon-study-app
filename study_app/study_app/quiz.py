import asyncio
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends

from .models import (
    GenerateQuizRequest,
    QuizResponse,
    SubmitAnswerRequest,
    AnswerFeedback,
)
from .quizservices import QuizService

router = APIRouter(tags=["Quiz & Rewards"])


def get_quiz_service() -> QuizService:
    return QuizService()


@router.post("/api/quiz/generate", response_model=QuizResponse)
async def generate_quiz(
    req: GenerateQuizRequest,
    svc: QuizService = Depends(get_quiz_service),
):
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None, svc.generate_quiz, req
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/api/quiz/answer", response_model=AnswerFeedback)
async def submit_answer(
    req: SubmitAnswerRequest,
    svc: QuizService = Depends(get_quiz_service),
):
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None, svc.submit_answer, req
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
