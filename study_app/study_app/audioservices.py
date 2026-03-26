import uuid
import struct
from pathlib import Path
from fastapi import APIRouter, Depends
from .config import get_settings, Settings
from .models import TextPayload
from .gemini import get_gemini_client

router = APIRouter(prefix="/api/audio", tags=["Audio"])

AUDIO_DIR = Path("audio_files")
AUDIO_DIR.mkdir(exist_ok=True)


def add_wav_header(
    pcm_data: bytes,
    sample_rate: int = 24000,
    channels: int = 1,
    bits_per_sample: int = 16,
) -> bytes:
    data_size = len(pcm_data)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,  # chunk size
        1,  # PCM format
        channels,
        sample_rate,
        sample_rate * channels * bits_per_sample // 8,  # byte rate
        channels * bits_per_sample // 8,  # block align
        bits_per_sample,
        b"data",
        data_size,
    )
    return header + pcm_data


@router.post("/read-premium")
async def read_with_gemini_tts(
    payload: TextPayload, settings: Settings = Depends(get_settings)
):
    client = get_gemini_client()

    response = client.models.generate_content(
        model="gemini-2.5-flash-preview-tts",
        contents=payload.content,
        config={
            "response_modalities": ["AUDIO"],
            "speech_config": {
                "voice_config": {"prebuilt_voice_config": {"voice_name": "Charon"}}
            },
        },
    )

    audio_data = response.candidates[0].content.parts[0].inline_data.data
    wav_data = add_wav_header(audio_data)

    filename = f"{uuid.uuid4()}.wav"
    filepath = AUDIO_DIR / filename

    with open(filepath, "wb") as f:
        f.write(wav_data)

    return {"url": f"/audio_files/{filename}"}
