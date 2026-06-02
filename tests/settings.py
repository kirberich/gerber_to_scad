import os

os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("SCAD_BINARY", "/usr/bin/openscad")

from gts_service.settings import *  # pyright: ignore[reportUnusedImport]  # noqa: F401, F403
