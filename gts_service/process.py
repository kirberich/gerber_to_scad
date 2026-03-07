import os
import subprocess
import uuid

from django.conf import settings

from gerber_to_scad.conversion import Stencil, convert


class ConversionError(Exception):
    pass


def create_stl(stencil: Stencil):
    file_id = uuid.uuid4()
    scad_filename = f"/tmp/gts-{file_id}.scad"
    stl_filename = f"/tmp/gts-{file_id}.stl"

    with open(scad_filename, "w") as scad_file:
        scad_file.write(convert(stencil))

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
