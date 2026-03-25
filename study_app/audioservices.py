from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from elevenlabs.client import ElevenLabs
from study_app.config import get_settings, Settings
from study_app.ingestion import TextPayload

router = APIRouter(prefix="/api/audio", tags=["Audio"])


@router.post("/read-premium")
async def read_with_elevenlabs(
    payload: TextPayload,
    settings: Settings = Depends(get_settings)
):
    client = ElevenLabs(api_key=settings.elevenlabs_api_key)

    audio_generator = client.generate(
        text=payload.content,
        voice=settings.elevenlabs_voice_id,
        model="eleven_multilingual_v2"
    )

    return StreamingResponse(audio_generator, media_type="audio/mpeg")
