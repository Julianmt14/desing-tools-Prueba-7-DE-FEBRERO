#!/usr/bin/env python
"""Punto de entrada para los comandos CLI del proyecto."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from app.cli import cli  # noqa: E402  (importación diferida hasta ajustar sys.path)


if __name__ == "__main__":
    cli()
