from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from django.test.client import Client

TESTS_DIR = Path(__file__).parent


def _mock_popen(args: Any, **kwargs: Any):
    """Fake OpenSCAD: write empty STL to the requested output path."""
    stl_path = args[2]  # [openscad_bin, "-o", stl_path, scad_path]
    Path(stl_path).write_bytes(b"fake stl data")
    proc = MagicMock()
    proc.returncode = 0
    return proc


def test_convert_endpoint(client: Client):
    with (
        open(TESTS_DIR / "test_board-toppaste.gtp", "rb") as paste_file,
        open(TESTS_DIR / "test_board-outline.gko", "rb") as outline_file,
        patch("gts_service.process.subprocess.Popen", side_effect=_mock_popen),
    ):
        response = client.post(
            "/convert",
            {
                "solderpaste_file": paste_file,
                "outline_file": outline_file,
                "thickness": "0.2",
                "gap": "0.0",
                "alignment_aid": "ledge",
                "ledge__thickness": "1.2",
                "frame__width": "155.0",
                "frame__height": "155.0",
                "frame__thickness": "1.2",
                "increase_hole_size_by": "0.0",
            },
        )

    assert response.status_code == 200
    assert response["Content-Disposition"].startswith("attachment")
