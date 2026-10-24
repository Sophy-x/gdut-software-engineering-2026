"""定义命令执行后端及默认的宿主实现。"""

import asyncio
import os
import signal
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class CommandExecution:
    """保存一次命令执行的原始结果。"""

    stdout: bytes
    stderr: bytes
    returncode: int


class CommandExecutor(Protocol):
    """定义命令执行后端需要提供的最小接口。"""

    async def execute(
        self,
        command: str,
        cwd: Path,
        timeout_seconds: float,
    ) -> CommandExecution:
        """执行命令并返回标准输出、错误输出和退出码。"""


class HostCommandExecutor:
    """在宿主进程中执行命令并负责进程组清理。"""

    async def execute(
        self,
        command: str,
        cwd: Path,
        timeout_seconds: float,
    ) -> CommandExecution:
        """执行宿主命令，并在超时或取消时回收进程组。"""

        process = await asyncio.create_subprocess_shell(
            command,
            cwd=cwd.resolve(),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            **process_group_options(),
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout_seconds,
            )
        except TimeoutError:
            await terminate_process_group(process)
            raise
        except asyncio.CancelledError:
            await terminate_process_group(process)
            raise
        return CommandExecution(stdout, stderr, process.returncode)


async def terminate_process_group(process: asyncio.subprocess.Process) -> None:
    """终止命令进程组并回收标准输出与错误管道。"""

    if process.returncode is None:
        if os.name == "nt":
            try:
                process.send_signal(signal.CTRL_BREAK_EVENT)
            except OSError:
                process.terminate()
        else:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        try:
            await asyncio.wait_for(process.wait(), timeout=1)
        except TimeoutError:
            if os.name == "nt":
                process.kill()
            else:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            await process.wait()
    await process.communicate()


def process_group_options() -> dict[str, int | bool]:
    """返回创建可单独终止子进程组所需的平台参数。"""

    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}
