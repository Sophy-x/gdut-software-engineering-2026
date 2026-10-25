"""实现 /listen 命令：将识别到的语音放入可编辑输入框。"""

from .registry import CommandContext, SlashCommand
from ..voice import VoiceError, WindowsSpeech


async def listen_command(context: CommandContext) -> None:
    """监听一次语音并将识别文本填入输入草稿。"""

    if not WindowsSpeech.available():
        context.screen.add_entry(
            "tool", "Voice input is available on Windows with speech recognition configured."
        )
        return

    context.screen.set_status_message("Listening for speech...")
    try:
        transcript = await WindowsSpeech().recognize()
    except VoiceError as exc:
        context.screen.add_entry("tool", f"Voice input failed: {exc}")
    else:
        if transcript:
            context.screen.set_input_text(transcript)
            context.screen.add_entry("tool", "Speech recognized. Review the draft and press Enter.")
        else:
            context.screen.add_entry("tool", "No clear speech detected.")
    finally:
        context.screen.set_status_message("")


voice_input_command_slash = SlashCommand(
    name="listen",
    description="Recognize one spoken prompt and add it to the input draft",
    handler=listen_command,
)
