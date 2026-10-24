"""Opt-in integration checks against a real Linux Docker daemon."""

import os
import subprocess
from pathlib import Path

import pytest

from evaluation.swebench_container import (
    SwebenchContainerExecutor,
    SwebenchTaskContainer,
)


IMAGE = os.environ.get("ARIA_DOCKER_TEST_IMAGE", "alpine:3.20")


@pytest.fixture(scope="module", autouse=True)
def require_linux_docker_image() -> None:
    if os.environ.get("ARIA_DOCKER_INTEGRATION") != "1":
        pytest.skip("set ARIA_DOCKER_INTEGRATION=1 to run Docker integration tests")
    info = subprocess.run(
        ["docker", "info", "--format", "{{.OSType}}"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if info.returncode != 0 or info.stdout.strip() != "linux":
        pytest.skip("a running Linux Docker engine is required")
    image = subprocess.run(
        ["docker", "image", "inspect", IMAGE],
        capture_output=True,
        check=False,
    )
    if image.returncode != 0:
        pytest.skip(f"Docker image is not available locally: {IMAGE}")


@pytest.mark.asyncio
async def test_linux_container_binds_windows_workspace_and_writes_back(
    tmp_path: Path,
) -> None:
    (tmp_path / "input.txt").write_text("mounted from Windows", encoding="utf-8")
    container = SwebenchTaskContainer(IMAGE, tmp_path)
    executor = SwebenchContainerExecutor(container)

    async with container.running():
        result = await executor.execute(
            "test \"$(cat input.txt)\" = 'mounted from Windows' "
            "&& printf 'written by Linux container' > result.txt "
            "&& pwd",
            tmp_path,
            30,
        )

    assert result.returncode == 0, result.stderr.decode(errors="replace")
    assert result.stdout.decode().strip() == "/testbed"
    assert (tmp_path / "result.txt").read_text(encoding="utf-8") == (
        "written by Linux container"
    )
    assert container.container_id is None


@pytest.mark.asyncio
async def test_timed_out_linux_command_removes_container(tmp_path: Path) -> None:
    container = SwebenchTaskContainer(IMAGE, tmp_path)
    executor = SwebenchContainerExecutor(container)
    await container.start()

    with pytest.raises(TimeoutError):
        await executor.execute("sleep 30", tmp_path, 0.5)

    assert container.container_id is None
