import re
import mimetypes
from pathlib import Path

import io
import PyPDF2

import google.generativeai as genai

from study_app.gemini import get_gemini_client
from study_app.config import get_settings
from study_app.ingestion import IngestionResult, IngestionStatus, InputType


AUDIO_MIME_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/ogg",
    "audio/webm",
    "audio/m4a",
    "audio/mp4",
}

IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/bmp",
    "image/tiff",
}

PDF_MIME_TYPES = {
    "application/pdf",
}


def _count_words(text: str) -> int:
    return len(text.split())


def _clean_text(text: str) -> str:
    """Remove excessive whitespace / control characters."""
    text = re.sub(r"[\r\n]+", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _detect_input_type(filename: str, provided_type: InputType | None) -> InputType:
    """
    If the caller already told us the type, trust them.
    Otherwise sniff from the file extension.
    """
    if provided_type:
        return provided_type

    mime, _ = mimetypes.guess_type(filename)
    if mime in AUDIO_MIME_TYPES:
        return InputType.audio
    if mime in IMAGE_MIME_TYPES:
        return InputType.image
    if mime in PDF_MIME_TYPES:
        return InputType.text
    return InputType.text


# ── Main service ──────────────────────────────────────────────────────────────

class IngestionService:

    def __init__(self):
        self.model: genai.GenerativeModel = get_gemini_client()
        self.settings = get_settings()

    # ── Public entry point ────────────────────────────────────────────────────

    async def ingest(
        self,
        file_bytes: bytes,
        filename: str,
        input_type: InputType | None = None,
    ) -> IngestionResult:
        """
        Main entry point.  Accepts raw bytes + filename and returns
        a normalised IngestionResult regardless of input type.
        """
        detected_type = _detect_input_type(filename, input_type)

        try:
            if detected_type == InputType.text:
                normalised = await self._process_text(file_bytes)
            elif detected_type == InputType.audio:
                normalised = await self._process_audio(file_bytes, filename)
            elif detected_type == InputType.image:
                normalised = await self._process_image(file_bytes, filename)
            elif detected_type == InputType.pdf:
                normalised = await self._process_pdf(file_bytes)
            else:
                raise ValueError(f"Unsupported input type: {detected_type}")

            normalised = _clean_text(normalised)

            return IngestionResult(
                status=IngestionStatus.success,
                input_type=detected_type,
                filename=filename,
                normalised_text=normalised,
                character_count=len(normalised),
                word_count=_count_words(normalised),
            )

        except Exception as exc:
            return IngestionResult(
                status=IngestionStatus.failed,
                input_type=detected_type,
                filename=filename,
                normalised_text="",
                character_count=0,
                word_count=0,
                error=str(exc),
            )

    # ── Also accept plain text strings (no file upload) ──────────────────────

    async def ingest_raw_text(self, content: str, filename: str = "direct_input.txt") -> IngestionResult:
        normalised = _clean_text(content)
        return IngestionResult(
            status=IngestionStatus.success,
            input_type=InputType.text,
            filename=filename,
            normalised_text=normalised,
            character_count=len(normalised),
            word_count=_count_words(normalised),
        )

    # ── Private processors ────────────────────────────────────────────────────

    async def _process_text(self, file_bytes: bytes) -> str:
        """
        Decode text file. Try UTF-8 first, fall back to latin-1.
        """
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return file_bytes.decode("latin-1")

    async def _process_audio(self, file_bytes: bytes, filename: str) -> str:
        """
        Send audio to Gemini 1.5 Flash for transcription.
        Gemini natively understands audio — no Whisper needed.
        """
        mime, _ = mimetypes.guess_type(filename)
        mime = mime or "audio/mpeg"

        prompt = (
            "Transcribe this audio recording accurately. "
            "Preserve all technical and academic vocabulary exactly as spoken. "
            "Format the output as clean paragraphs — no timestamps, no speaker labels "
            "unless the content is clearly a dialogue. "
            "Return ONLY the transcript, nothing else."
        )

        audio_part = {
            "mime_type": mime,
            "data": file_bytes,
        }

        response = self.model.generate_content([prompt, audio_part])
        return response.text

    async def _process_image(self, file_bytes: bytes, filename: str) -> str:
        """
        Send image (photo of notes, textbook page, whiteboard) to Gemini Vision.
        Extracts and structures all readable text from the image.
        """
        import PIL.Image
        import io

        image = PIL.Image.open(io.BytesIO(file_bytes))

        prompt = (
            "You are an expert academic OCR assistant. "
            "Extract ALL text visible in this image — including handwritten notes, "
            "printed text, diagrams with labels, equations, tables, and bullet points. "
            "Preserve the logical structure (headings, sub-points, numbered lists). "
            "If there are diagrams, describe them briefly in [brackets] and include their labels. "
            "Return ONLY the extracted and structured text — no commentary, no preamble."
        )

        response = self.model.generate_content([prompt, image])
        return response.text

    async def _process_pdf(self, file_bytes: bytes) -> str:
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        text = []
        for page in reader.pages:
            text.append(page.extract_text() or "")
        return "\n".join(text)
