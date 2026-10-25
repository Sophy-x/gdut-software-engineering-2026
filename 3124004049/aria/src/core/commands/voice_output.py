"""实现 /voice 命令：切换助手回复的语音输出。"""

from .registry import CommandContext, SlashCommand
from ..voice import WindowsSpeech


async def voice_output_command(context: CommandContext) -> None:
    """显示或切换语音输出状态。"""

    if not WindowsSpeech.available():
        context.screen.add_entry(
            "tool", "Voice output is available on Windows with System.Speech configured."
        )
        return

    option = context.arguments.casefold()
    if option in {"on", "enable", "enabled"}:
        context.screen.set_voice_output_enabled(True)
        context.screen.add_entry("tool", "Voice output enabled.")
    elif option in {"off", "disable", "disabled"}:
        context.screen.set_voice_output_enabled(False)
        context.screen.add_entry("tool", "Voice output disabled.")
    elif not option:
        state = "enabled" if context.screen.voice_output_enabled else "disabled"
        context.screen.add_entry("tool", f"Voice output is {state}.")
    else:
        context.screen.add_entry("tool", "Usage: /voice on|off")


voice_output_command_slash = SlashCommand(
    name="voice",
    description="Enable, disable, or inspect spoken assistant replies",
    handler=voice_output_command,
)
