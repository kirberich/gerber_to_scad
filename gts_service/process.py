import os
import subprocess
import uuid

from django.conf import settings
from pygerber.gerberx3.api.v2 import ParsedFile

from gerber_to_scad.conversion import GerberConverter


class ConversionError(Exception):
    pass


def create_stl(
    *,
    outline: ParsedFile,
    solder_paste: ParsedFile,
    stencil_thickness: float,
    include_ledge: bool,
    full_ledge: bool,
    ledge_thickness: float,
    gap: float,
    increase_hole_size_by: float,
    flip_stencil: bool,
    include_frame: bool,
    frame_width: float,
    frame_height: float,
    frame_thickness: float,
):
    converter = GerberConverter(
        outline_file=outline,
        solderpaste_file=solder_paste,
        stencil_thickness=stencil_thickness,
        include_ledge=include_ledge,
        full_ledge=full_ledge,
        ledge_thickness=ledge_thickness,
        gap=gap,
        increase_hole_size_by=increase_hole_size_by,
        flip_stencil=flip_stencil,
        include_frame=include_frame,
        frame_width=frame_width,
        frame_height=frame_height,
        frame_thickness=frame_thickness,
    )

    file_id = uuid.uuid4()
    scad_filename = f"/tmp/gts-{file_id}.scad"
    stl_filename = f"/tmp/gts-{file_id}.stl"

    with open(scad_filename, "w") as scad_file:
        scad_file.write(converter.convert())

    p = subprocess.Popen(
        [
            settings.OPENSCAD_BIN,
            "-o",
            stl_filename,
            scad_filename,
        ]
    )
    p.wait()

    if p.returncode:
        raise ConversionError("Failed to create an STL file from inputs")

    with open(stl_filename, "rb") as stl_file:
        stl_data = stl_file.read()
    os.remove(stl_filename)

    # Clean up temporary files
    os.remove(scad_filename)

    return stl_data, stl_filename
