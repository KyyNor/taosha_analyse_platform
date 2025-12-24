
from __future__ import annotations

import abc
import json
import os
import shutil
import subprocess
import sys
import typing
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from langchain.agents.middleware._execution import BaseExecutionPolicy

try:  # pragma: no cover - optional dependency on POSIX platforms
    import resource
except ImportError:  # pragma: no cover - non-POSIX systems
    resource = None  # type: ignore[assignment]


SHELL_TEMP_PREFIX = "langchain-shell-"

def _launch_subprocess(
    command: Sequence[str],
    *,
    env: Mapping[str, str],
    cwd: Path,
    preexec_fn: typing.Callable[[], None] | None,
    start_new_session: bool,
) -> subprocess.Popen[str]:
    return subprocess.Popen(  # noqa: S603
        list(command),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        env=env,
        preexec_fn=preexec_fn,  # noqa: PLW1509
        start_new_session=start_new_session,
    )

@dataclass
class CustomDockerExecutionPolicy(BaseExecutionPolicy):
    """Run the shell inside a dedicated Docker container.

    Choose this policy when commands originate from untrusted users or you require
    strong isolation between sessions. By default the workspace is bind-mounted only
    when it refers to an existing non-temporary directory; ephemeral sessions run
    without a mount to minimise host exposure. The container's network namespace is
    disabled by default (`--network none`) and you can enable further hardening via
    `read_only_rootfs` and `user`.

    The security guarantees depend on your Docker daemon configuration. Run the agent on
    a host where Docker is locked down (rootless mode, AppArmor/SELinux, etc.) and
    review any additional volumes or capabilities passed through ``extra_run_args``. The
    default image is `python:3.12-alpine3.19`; supply a custom image if you need
    preinstalled tooling.
    """

    binary: str = "docker"
    image: str = "python:3.12-alpine3.19"
    remove_container_on_exit: bool = True
    network_enabled: bool = False
    extra_run_args: Sequence[str] | None = None
    memory_bytes: int | None = None
    cpu_time_seconds: typing.Any | None = None
    cpus: str | None = None
    read_only_rootfs: bool = False
    user: str | None = None
    target_workspace: Path | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.memory_bytes is not None and self.memory_bytes <= 0:
            msg = "memory_bytes must be positive if provided."
            raise ValueError(msg)
        if self.cpu_time_seconds is not None:
            msg = (
                "DockerExecutionPolicy does not support cpu_time_seconds; configure CPU limits "
                "using Docker run options such as '--cpus'."
            )
            raise RuntimeError(msg)
        if self.cpus is not None and not self.cpus.strip():
            msg = "cpus must be a non-empty string when provided."
            raise ValueError(msg)
        if self.user is not None and not self.user.strip():
            msg = "user must be a non-empty string when provided."
            raise ValueError(msg)
        self.extra_run_args = tuple(self.extra_run_args or ())

    def spawn(
        self,
        *,
        workspace: Path,
        env: Mapping[str, str],
        command: Sequence[str],
    ) -> subprocess.Popen[str]:
        full_command = self._build_command(workspace, env, command)
        host_env = os.environ.copy()
        return _launch_subprocess(
            full_command,
            env=host_env,
            cwd=workspace,
            preexec_fn=None,
            start_new_session=False,
        )

    def _build_command(
        self,
        workspace: Path,
        env: Mapping[str, str],
        command: Sequence[str],
    ) -> list[str]:
        binary = self._resolve_binary()
        full_command: list[str] = [binary, "run", "-i"]
        if self.remove_container_on_exit:
            full_command.append("--rm")
        if not self.network_enabled:
            full_command.extend(["--network", "none"])
        if self.memory_bytes is not None:
            full_command.extend(["--memory", str(self.memory_bytes)])
        if self._should_mount_workspace(workspace):
            host_path = str(workspace)
            if self.target_workspace:
                target_host_path = str(self.target_workspace)
            else:
                target_host_path = str(workspace)
            full_command.extend(["-v", f"{host_path}:{target_host_path}"])
            full_command.extend(["-w", target_host_path])
        else:
            full_command.extend(["-w", "/"])
        if self.read_only_rootfs:
            full_command.append("--read-only")
        for key, value in env.items():
            full_command.extend(["-e", f"{key}={value}"])
        if self.cpus is not None:
            full_command.extend(["--cpus", self.cpus])
        if self.user is not None:
            full_command.extend(["--user", self.user])
        if self.extra_run_args:
            full_command.extend(self.extra_run_args)
        full_command.append(self.image)
        full_command.extend(command)
        return full_command

    @staticmethod
    def _should_mount_workspace(workspace: Path) -> bool:
        return not workspace.name.startswith(SHELL_TEMP_PREFIX)

    def _resolve_binary(self) -> str:
        path = shutil.which(self.binary)
        if path is None:
            msg = (
                "Docker execution policy requires the '%s' CLI to be installed"
                " and available on PATH."
            )
            raise RuntimeError(msg % self.binary)
        return path

