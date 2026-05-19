import os

os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("SCAD_BINARY", "/usr/bin/openscad")

from gts_service import settings  # pyright: ignore[reportUnusedImport]  # noqa: F401
