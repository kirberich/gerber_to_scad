"""CLI entry point for gerber_to_scad."""

import subprocess
import tempfile
import zipfile
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Literal

import click
from pygerber.gerberx3.api.v2 import GerberFile, ParsedFile

from .conversion import Frame, Ledge, Stencil, convert

# File extension sets and name patterns for auto-detecting gerber layers in zips
OUTLINE_SUFFIXES = {".gko", ".gm1", ".gm2"}
OUTLINE_PATTERNS = {
    "edge.cuts",
    "edge_cuts",
    "boardoutline",
    "board_outline",
    "outline",
}

TOP_PASTE_SUFFIXES = {".gtp"}
TOP_PASTE_PATTERNS = {
    "f.paste",
    "f_paste",
    "toppaste",
    "top_paste",
    "top-paste",
    "top_paste_mask",
    "toppastemask",
}

BOTTOM_PASTE_SUFFIXES = {".gbp"}
BOTTOM_PASTE_PATTERNS = {
    "b.paste",
    "b_paste",
    "bottompaste",
    "bottom_paste",
    "bottom-paste",
    "bottom_paste_mask",
    "bottompastemask",
}


def _find_in_zip(
    names: list[str], suffixes: set[str], patterns: set[str]
) -> str | None:
    """Find a file in a zip namelist by extension, falling back to name pattern matching."""
    for name in names:
        if Path(name).suffix.lower() in suffixes:
            return name
    for name in names:
        stem = Path(name).stem.lower()
        if any(p in stem for p in patterns):
            return name
    return None


def _parse_gerbers_from_zip(zip_path: Path, side: str) -> tuple[ParsedFile, ParsedFile]:
    """Extract gerber files from a zip and return parsed outline and paste files."""
    paste_suffixes = TOP_PASTE_SUFFIXES if side == "top" else BOTTOM_PASTE_SUFFIXES
    paste_patterns = TOP_PASTE_PATTERNS if side == "top" else BOTTOM_PASTE_PATTERNS

    with zipfile.ZipFile(zip_path) as zf:
        names = [n for n in zf.namelist() if not n.endswith("/")]

        outline_name = _find_in_zip(names, OUTLINE_SUFFIXES, OUTLINE_PATTERNS)
        paste_name = _find_in_zip(names, paste_suffixes, paste_patterns)

        if not outline_name:
            raise click.ClickException("Could not find an outline file in the zip.")
        if not paste_name:
            raise click.ClickException(
                f"Could not find a {side} paste file in the zip."
            )

        with tempfile.TemporaryDirectory() as tmp_dir:
            outline_path = Path(tmp_dir) / Path(outline_name).name
            paste_path = Path(tmp_dir) / Path(paste_name).name

            outline_path.write_bytes(zf.read(outline_name))
            paste_path.write_bytes(zf.read(paste_name))

            outline_parsed = GerberFile.from_file(str(outline_path)).parse()
            paste_parsed = GerberFile.from_file(str(paste_path)).parse()

    return outline_parsed, paste_parsed


def _write_output(scad_content: str, output_file: Path, openscad_binary: str) -> None:
    if output_file.suffix.lower() == ".stl":
        with tempfile.NamedTemporaryFile(suffix=".scad", mode="w", delete=False) as tmp:
            tmp.write(scad_content)
            tmp_path = tmp.name
        subprocess.run([openscad_binary, "-o", output_file, tmp_path], check=True)
        Path(tmp_path).unlink()
        return

    with open(output_file, "w") as f:
        f.write(scad_content)


def stencil_options(f: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator that adds common stencil options to a command."""

    @click.option(
        "-t",
        "--thickness",
        default=0.2,
        show_default=True,
        help="Stencil thickness in mm. Should be a multiple of your layer height.",
    )
    @click.option(
        "-a",
        "--alignment-aid",
        type=click.Choice(["ledge", "frame", "none"]),
        default="ledge",
        show_default=True,
        help="Alignment aid to include with the stencil.",
    )
    @click.option(
        "-f",
        "--full-ledge",
        is_flag=True,
        default=False,
        help="[ledge] Extend the ledge all the way around the board (default is half ledge).",
    )
    @click.option(
        "-L",
        "--ledge-thickness",
        default=1.2,
        show_default=True,
        help="[ledge] Ledge thickness in mm. Should be less than the PCB thickness.",
    )
    @click.option(
        "--frame-width",
        default=155.0,
        show_default=True,
        help="[frame] Width of the frame in mm.",
    )
    @click.option(
        "--frame-height",
        default=155.0,
        show_default=True,
        help="[frame] Height of the frame in mm.",
    )
    @click.option(
        "--frame-thickness",
        default=1.2,
        show_default=True,
        help="[frame] Thickness of the frame in mm.",
    )
    @click.option(
        "-g",
        "--gap",
        default=0.0,
        show_default=True,
        help="Gap in mm between board and ledge. Increase if fit is too tight.",
    )
    @click.option(
        "-i",
        "--increase-hole-size",
        default=0.0,
        show_default=True,
        help="Increase all hole sizes by this amount in mm.",
    )
    @click.option(
        "--flip",
        is_flag=True,
        default=False,
        help="Flip the stencil (use for bottom layer stencils).",
    )
    @click.option(
        "--openscad-binary",
        default="openscad",
        show_default=True,
        metavar="PATH",
        help="Path to the OpenSCAD binary. Only used when output ends in .stl.",
    )
    @wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return f(*args, **kwargs)

    return wrapper


def _alignment_aid(
    alignment_aid: Literal["ledge", "frame", "none"],
    full_ledge: bool,
    ledge_thickness: float,
    frame_width: float,
    frame_height: float,
    frame_thickness: float,
) -> Ledge | Frame | None:
    if alignment_aid == "ledge":
        return Ledge(is_full_ledge=full_ledge, thickness=ledge_thickness)
    if alignment_aid == "frame":
        return Frame(width=frame_width, height=frame_height, thickness=frame_thickness)
    return None


@click.group()
def cli() -> None:
    """Convert gerber files to a 3d-printable OpenSCAD solder stencil."""


@cli.command()
@click.option(
    "--outline",
    help="File containing the outline layer",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--paste",
    help="File containing the solderpaste layer (top or bottom)",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--output",
    help="Output file",
    required=True,
    type=click.Path(dir_okay=False, path_type=Path),
)
@stencil_options
def from_files(
    outline: Path,
    paste: Path,
    output: Path,
    thickness: float,
    alignment_aid: Literal["ledge", "frame", "none"],
    full_ledge: bool,
    ledge_thickness: float,
    frame_width: float,
    frame_height: float,
    frame_thickness: float,
    gap: float,
    increase_hole_size: float,
    flip: bool,
    openscad_binary: str,
) -> None:
    """Generate a stencil from an outline and paste gerber file."""
    outline_parsed = GerberFile.from_file(outline).parse()
    paste_parsed = GerberFile.from_file(paste).parse()

    _run_conversion(
        outline_parsed,
        paste_parsed,
        output,
        thickness,
        _alignment_aid(
            alignment_aid,
            full_ledge,
            ledge_thickness,
            frame_width,
            frame_height,
            frame_thickness,
        ),
        gap,
        increase_hole_size,
        flip,
        openscad_binary,
    )


@cli.command()
@click.option(
    "--input",
    type=click.Path(exists=True, path_type=Path, dir_okay=False),
    required=True,
)
@click.option(
    "--output", required=True, type=click.Path(path_type=Path, dir_okay=False)
)
@click.option(
    "--side",
    required=True,
    type=click.Choice(["top", "bottom"]),
    help="Side of the PCB to generate the stencil for. Note that for bottom stencils, you will likely want to use --flip as well",
)
@stencil_options
def from_zip_cmd(
    input: Path,
    output: Path,
    side: str,
    thickness: float,
    alignment_aid: Literal["ledge", "frame", "none"],
    full_ledge: bool,
    ledge_thickness: float,
    frame_width: float,
    frame_height: float,
    frame_thickness: float,
    gap: float,
    increase_hole_size: float,
    flip: bool,
    openscad_binary: str,
) -> None:
    """Generate a stencil from a zip file containing gerber files."""
    outline_parsed, paste_parsed = _parse_gerbers_from_zip(input, side)

    _run_conversion(
        outline_parsed,
        paste_parsed,
        output,
        thickness,
        _alignment_aid(
            alignment_aid,
            full_ledge,
            ledge_thickness,
            frame_width,
            frame_height,
            frame_thickness,
        ),
        gap,
        increase_hole_size,
        flip,
        openscad_binary,
    )


def _run_conversion(
    outline_parsed: ParsedFile,
    paste_parsed: ParsedFile,
    output_file: Path,
    thickness: float,
    alignment_aid: Ledge | Frame | None,
    gap: float,
    increase_hole_size: float,
    flip: bool,
    openscad_binary: str,
) -> None:
    stencil = Stencil(
        outline_file=outline_parsed,
        solderpaste_file=paste_parsed,
        alignment_aid=alignment_aid,
        thickness=thickness,
        gap=gap,
        increase_hole_size_by=increase_hole_size,
        flip_stencil=flip,
    )
    _write_output(convert(stencil), output_file, openscad_binary)


def gerber_to_scad_cli() -> None:
    cli()


if __name__ == "__main__":
    cli()
