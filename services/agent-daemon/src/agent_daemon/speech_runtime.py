"""Local speech runtime helpers for STT and TTS."""

from __future__ import annotations

from dataclasses import dataclass
import tempfile
from pathlib import Path


@dataclass(frozen=True)
class SpeechTranscription:
    is_success: bool
    transcript: str
    provider_id: str
    model_id: str
    detail: str


@dataclass(frozen=True)
class SpeechSynthesis:
    is_success: bool
    audio_wav: bytes
    audio_mime_type: str
    provider_id: str
    model_id: str
    detail: str


class LocalSpeechRuntime:
    """Speech runtime that uses optional local Python dependencies when available."""

    def __init__(self) -> None:
        self._whisper_model = None

    def transcribe_audio_wav(self, audio_wav: bytes) -> SpeechTranscription:
        if not audio_wav:
            return SpeechTranscription(False, "", "local-whisper", "base", "No audio was received.")

        try:
            import whisper  # type: ignore
        except ImportError:
            return SpeechTranscription(
                False,
                "",
                "local-whisper",
                "base",
                (
                    "Local speech-to-text is not installed yet. "
                    "Install it with: pip install openai-whisper"
                ),
            )

        try:
            model = self._whisper_model
            if model is None:
                model = whisper.load_model("base")
                self._whisper_model = model

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
                temp_audio.write(audio_wav)
                temp_audio_path = Path(temp_audio.name)

            try:
                result = model.transcribe(str(temp_audio_path), fp16=False)
            finally:
                temp_audio_path.unlink(missing_ok=True)

            transcript = str(result.get("text", "")).strip()
            if not transcript:
                return SpeechTranscription(
                    False,
                    "",
                    "local-whisper",
                    "base",
                    "I could not hear clear speech. Please try again in a quieter room.",
                )

            return SpeechTranscription(True, transcript, "local-whisper", "base", "Transcription completed.")
        except Exception as exc:  # noqa: BLE001
            return SpeechTranscription(
                False,
                "",
                "local-whisper",
                "base",
                f"Local speech-to-text failed: {exc}",
            )

    def synthesize_speech(self, text: str, voice_id: str = "") -> SpeechSynthesis:
        text = text.strip()
        if not text:
            return SpeechSynthesis(False, b"", "audio/wav", "local-pyttsx3", "default", "No text to speak.")

        try:
            import pyttsx3  # type: ignore
        except ImportError:
            return SpeechSynthesis(
                False,
                b"",
                "audio/wav",
                "local-pyttsx3",
                "default",
                "Local text-to-speech is not installed yet. Install it with: pip install pyttsx3",
            )

        try:
            engine = pyttsx3.init()
            if voice_id:
                engine.setProperty("voice", voice_id)

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
                temp_audio_path = Path(temp_audio.name)

            try:
                engine.save_to_file(text, str(temp_audio_path))
                engine.runAndWait()
                audio = temp_audio_path.read_bytes()
            finally:
                temp_audio_path.unlink(missing_ok=True)

            if not audio:
                return SpeechSynthesis(
                    False,
                    b"",
                    "audio/wav",
                    "local-pyttsx3",
                    "default",
                    "Speech synthesis returned empty audio.",
                )

            return SpeechSynthesis(
                True,
                audio,
                "audio/wav",
                "local-pyttsx3",
                "default",
                "Speech synthesis completed.",
            )
        except Exception as exc:  # noqa: BLE001
            return SpeechSynthesis(
                False,
                b"",
                "audio/wav",
                "local-pyttsx3",
                "default",
                f"Local text-to-speech failed: {exc}",
            )
