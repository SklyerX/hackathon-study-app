import re
import mimetypes
import io
import PyPDF2
from PIL import Image
from .gemini import get_gemini_client
from .config import get_settings
from .models import IngestionResult, IngestionStatus, InputType

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

PDF_MIME_TYPES = {"application/pdf"}


def _count_words(text: str) -> int:
    return len(text.split())


def _clean_text(text: str) -> str:
    """Remove excessive whitespace / control characters."""
    text = re.sub(r"[\r\n]+", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _detect_input_type(filename: str, provided_type: InputType | None) -> InputType:
    if provided_type:
        return provided_type
    mime, _ = mimetypes.guess_type(filename)
    if mime in AUDIO_MIME_TYPES:
        return InputType.audio
    if mime in IMAGE_MIME_TYPES:
        return InputType.image
    return InputType.text  # Default for PDFs and text


class FileProcessor:
    def __init__(self):
        self.client = get_gemini_client()
        self.settings = get_settings()

    async def process(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str | None = None,
        input_type: InputType | None = None,
    ) -> IngestionResult:
        detected_type = _detect_input_type(filename, input_type)

        try:
            if detected_type == InputType.audio:
                normalised = await self._process_audio(file_bytes, filename)
            elif detected_type == InputType.image:
                normalised = await self._process_image(file_bytes)
            else:
                # Handle PDF or Text
                mime, _ = mimetypes.guess_type(filename)
                if mime == "application/pdf":
                    normalised = await self._process_pdf(file_bytes)
                else:
                    normalised = await self._process_text(file_bytes)

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

    async def _process_text(self, file_bytes: bytes) -> str:
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return file_bytes.decode("latin-1")

    async def _process_audio(self, file_bytes: bytes, filename: str) -> str:
        mime, _ = mimetypes.guess_type(filename)
        mime = mime or "audio/mpeg"

        prompt = (
            "Transcribe this audio recording accurately. Return ONLY the transcript."
        )
        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt, {"mime_type": mime, "data": file_bytes}],
        )
        return response.text

    async def _process_image(self, file_bytes: bytes) -> str:
        image = Image.open(io.BytesIO(file_bytes))
        prompt = (
            "Extract ALL text visible in this image. Return ONLY the extracted text."
        )

        response = self.client.models.generate_content(
            model="gemini-2.5-flash", contents=[prompt, image]
        )
        return response.text

    async def _process_pdf(self, file_bytes: bytes) -> str:
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        text = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(text)
