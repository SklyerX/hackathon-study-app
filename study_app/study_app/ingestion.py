from fastapi import APIRouter, UploadFile, File, HTTPException
from .models import IngestionResult, IngestionStatus, InputType, TextPayload
from .upload import FileProcessor
from .database import get_db

router = APIRouter(tags=["Ingestion"])

HARDCODED_USER_ID = "00000000-0000-0000-0000-000000000000"


@router.post("/api/ingestion/upload", response_model=IngestionResult)
async def upload_file(file: UploadFile = File(...)):
    processor = FileProcessor()
    try:
        file_bytes = await file.read()
        result = await processor.process(file_bytes, file.filename, file.content_type)

        db = get_db()
        try:
            with db.cursor() as cur:
                cur.execute(
                    """INSERT INTO study_sessions (filename, content, input_type, user_id)
                       VALUES (%s, %s, %s, %s) RETURNING id""",
                    (
                        result.filename,
                        result.normalised_text,
                        result.input_type.value,
                        HARDCODED_USER_ID,
                    ),
                )
                row = cur.fetchone()
                result.session_id = row[0]
                result.status = IngestionStatus.success
        finally:
            db.close()

        return result

    except Exception as e:
        return IngestionResult(
            session_id=None,
            status=IngestionStatus.failed,
            input_type=InputType.text,
            filename=file.filename,
            normalised_text="",
            character_count=0,
            word_count=0,
            error=str(e),
        )


@router.post("/api/ingestion/text", response_model=IngestionResult)
async def submit_text(payload: TextPayload):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """INSERT INTO study_sessions (filename, content, input_type, user_id)
                   VALUES (%s, %s, %s, %s) RETURNING id""",
                ("manual_input.txt", payload.content, "text", HARDCODED_USER_ID),
            )
            row = cur.fetchone()
            session_id = row[0]
    finally:
        db.close()

    return IngestionResult(
        status=IngestionStatus.success,
        input_type=InputType.text,
        filename="manual_input.txt",
        session_id=session_id,
        normalised_text=payload.content,
        character_count=len(payload.content),
        word_count=len(payload.content.split()),
    )
