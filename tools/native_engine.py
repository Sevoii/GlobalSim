"""Compatibility import for repository tools; applications use globalsim."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
from globalsim.native_engine import NativeRace
