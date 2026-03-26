from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from study_app.models import IngestionResult, IngestionStatus, InputType, TextPayload
from study_app.upload import FileProcessor 
from study_app.database import get_supabase
from study_app.config import get_settings

# We name this 'router' so it can be easily imported by fastapi.py
router = APIRouter(tags=["Ingestion"])

@router.post("/api/ingestion/upload", response_model=IngestionResult)
async def upload_file(
    file: UploadFile = File(...),
    db = Depends(get_supabase)
):
    """Handles PDF, Image, and Audio uploads via Gemini Flash."""
    processor = FileProcessor()
    try:
        # 1. Process the file using the logic in your upload.py
        file_bytes = await file.read()
        result = await processor.process(file_bytes, file.filename, file.content_type)
        
        # 2. Save to Supabase 'study_sessions' table
        db_data = {
            "filename": result.filename,
            "content": result.normalised_text,
            "input_type": result.input_type.value
        }
        db_res = db.table("study_sessions").insert(db_data).execute()
        
        # 3. Attach the new database ID to the result
        if db_res.data:
            result.session_id = db_res.data[0]["id"]
            result.status = IngestionStatus.success
            
        return result

    except Exception as e:
        return IngestionResult(
            status=IngestionStatus.failed,
            input_type=InputType.text,
            filename=file.filename,
            normalised_text="",
            character_count=0,
            word_count=0,
            error=str(e)
        )

@router.post("/api/ingestion/text", response_model=IngestionResult)
async def submit_text(payload: TextPayload, db = Depends(get_supabase)):
    """Handles direct copy-pasted text."""
    try:
        db_data = {
            "filename": "manual_input.txt",
            "content": payload.content,
            "input_type": "text"
        }
        db_res = db.table("study_sessions").insert(db_data).execute()
        
        return IngestionResult(
            status=IngestionStatus.success,
            input_type=InputType.text,
            filename="manual_input.txt",
            session_id=db_res.data[0]["id"],
            normalised_text=payload.content,
            character_count=len(payload.content),
            word_count=len(payload.content.split())
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))