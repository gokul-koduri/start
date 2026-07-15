"""Root-level launcher for the nvidia-nim proxy.

This module is intentionally thin: it re-execs ``uv`` in the nvidia-nim
project directory so ``uv run uvicorn server:app ...`` works from the
repository root without trying to import the Python 3.14 stack into the root
Python 3.12 environment.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
NVIDIA_NIM_DIR = ROOT_DIR / "nvidia-nim"


def _launch_nvidia_nim_server() -> None:
    uvicorn_args = list(sys.argv[1:])
    if not uvicorn_args or uvicorn_args[0].startswith("-"):
        uvicorn_args.insert(0, "server:app")

    os.chdir(NVIDIA_NIM_DIR)
    os.environ.pop("VIRTUAL_ENV", None)
    os.execvp("uv", ["uv", "run", "uvicorn", *uvicorn_args])


_launch_nvidia_nim_server()