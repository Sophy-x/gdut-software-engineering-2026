"""实现 /listen 命令：将识别到的语音放入可编辑输入框。"""

import asyncio

from .registry import CommandContext, SlashCommand
from ..voice import (
    NoSpeechDetected,
    SpeechRecognition,
    VoiceError,
    WhisperSpeech,
)


async def listen_command(context: CommandContext) -> None:
    """监听一次语音并将识别文本填入输入草稿。"""

    recognizer = WhisperSpeech()
    if not recognizer.available():
        context.screen.add_entry(
            "tool",
            "Whisper voice input is not installed. Run `uv sync --frozen` first.",
        )
        return

    def stop_recording() -> None:
        """停止采集但保留已经收到的音频，后续继续 Whisper 转写。"""

        recognizer.stop()
        context.screen.set_status_message("Transcribing recorded audio...")

    set_cancel_handler = getattr(context.screen, "set_cancel_handler", None)
    if set_cancel_handler is not None:
        set_cancel_handler(stop_recording)
    context.screen.set_status_message("Recording... Press Esc to stop")
    try:
        result = await recognizer.recognize()
    except asyncio.CancelledError:
        raise
    except NoSpeechDetected as exc:
        context.screen.add_entry("tool", f"No speech detected: {exc}")
    except VoiceError as exc:
        context.screen.add_entry("tool", f"Voice input failed: {exc}")
    else:
        if isinstance(result, str):
            result = SpeechRecognition(result, "unknown", 0.0)
        context.screen.set_input_text(result.text)
        context.screen.add_entry(
            "tool",
            f"Speech recognized ({result.language}, "
            f"language probability {result.language_probability:.2f}). "
            "Review the draft and press Enter.",
        )
    finally:
        if set_cancel_handler is not None:
            set_cancel_handler(None)
        context.screen.set_status_message("")


voice_input_command_slash = SlashCommand(
    name="listen",
    description="Recognize one spoken prompt and add it to the input draft",
    handler=listen_command,
)
