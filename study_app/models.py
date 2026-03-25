from pydantic import BaseModel
from enum import Enum
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class InputType(str, Enum):
    pdf = "pdf"
    text = "text"
    audio = "audio"
    image = "image"

class IngestionStatus(str, Enum):
    success = "success"
    failed = "failed"

class IngestionResult(BaseModel):
    status: IngestionStatus
    input_type: InputType
    filename: str
    session_id: UUID  
    normalised_text: str
    character_count: int
    word_count: int
    error: Optional[str] = None

class TextPayload(BaseModel):
    content: str

class QuestionType(str, Enum):
    mcq = "mcq"
    short_answer = "short_answer"
    true_false = "true_false"

class DifficultyLevel(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"

class GenerateQuizRequest(BaseModel):
    session_id: UUID
    num_questions: int = 5
    difficulty: DifficultyLevel = DifficultyLevel.medium
    question_types: List[QuestionType] = [QuestionType.mcq]

class QuizQuestionResponse(BaseModel):
    id: UUID
    session_id: UUID
    question_type: str
    question_text: str
    options: Optional[List[str]] = None
    difficulty: Optional[str] = None
    created_at: datetime

class QuizResponse(BaseModel):
    session_id: UUID
    questions: List[QuizQuestionResponse]
    total: int

class SubmitAnswerRequest(BaseModel):
    question_id: UUID
    user_id: UUID
    user_answer: str

class AnswerFeedback(BaseModel):
    is_correct: bool
    correct_answer: str
    explanation: str
    points_earned: int = 0