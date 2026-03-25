from pydantic import BaseModel
from enum import Enum
from typing import Optional
from uuid import UUID


class InputType(str, Enum):
    pdf = "pdf"
    text = "text"
    audio = "audio"
    image = "image"


class IngestionStatus(str, Enum):
    success = "success"
    failed = "failed"


class IngestionResult(BaseModel):
    """
    Returned to the client after any upload.
    `normalised_text` is the single source of truth that all
    downstream AI services (simplifier, chunker, quiz) consume.
    """
    status: IngestionStatus
    input_type: InputType
    filename: str
    session_id: UUID
    normalised_text: str
    character_count: int
    word_count: int
    error: Optional[str] = None


class TextPayload(BaseModel):
    """Direct text submission (no file upload needed)."""
    content: str
