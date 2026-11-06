"""Compatibility imports for repository tools; applications use globalsim."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
from globalsim.replay_protocol import (
    HEADER, MAGIC, FIELDS, Replay, read_exact, read_wire, decode, read_reply,
)
