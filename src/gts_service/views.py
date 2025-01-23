from __future__ import annotations

import logging
import os
import subprocess
from random import randint

import gerber
from django.conf import settings
from django.http.request import HttpRequest
from django.http.response import HttpResponse
from django.shortcuts import render

from gerber_to_scad import (
    process_gerber,
)
from gts_service.forms import UploadForm


def _get_version() -> str:
    with open("version") as f:
        return f.read()


def main(request: HttpRequest) -> HttpResponse:
    form = UploadForm(request.POST or None, files=request.FILES or None)
    version = _get_version()
    if form.is_valid():
        outline_file = form.cleaned_data["outline_file"]
        solderpaste_file = request.FILES["solderpaste_file"]
        outline = None

        if outline_file:
            try:
                outline = gerber.loads(outline_file.read().decode("utf-8"))
            except Exception as e:
                logging.exception(e)
                outline = None
                form.errors["outline_file"] = [
                    "Invalid format, is this a valid gerber file?"
                ]

        try:
            solder_paste = gerber.loads(solderpaste_file.read().decode("utf-8"))
        except Exception as e:
            logging.exception(e)
            solder_paste = None
            form.errors["solderpaste_file"] = [
                "Invalid format, is this a valid gerber file?"
            ]

        if not form.errors:
            output = process_gerber(
                outline_file=outline,
                solderpaste_file=solder_paste,
                stencil_thickness=form.cleaned_data["stencil_thickness"],
                include_ledge=form.cleaned_data["include_ledge"],
                ledge_thickness=form.cleaned_data["ledge_thickness"],
                gap=form.cleaned_data["gap"],
                include_frame=form.cleaned_data["include_frame"],
                frame_width=form.cleaned_data["frame_width"],
                frame_height=form.cleaned_data["frame_height"],
                frame_thickness=form.cleaned_data["frame_thickness"],
                increase_hole_size_by=form.cleaned_data["increase_hole_size_by"],
                simplify_regions=form.cleaned_data["simplify_regions"],
                flip_stencil=form.cleaned_data["flip_stencil"],
                stencil_width=form.cleaned_data["stencil_width"],
                stencil_height=form.cleaned_data["stencil_height"],
                stencil_margin=form.cleaned_data["stencil_margin"],
            )

            file_id = randint(1000000000, 9999999999)
            scad_filename = f"/tmp/gts-{file_id}.scad"
            stl_filename = f"/tmp/gts-{file_id}.stl"

            with open(scad_filename, "w") as scad_file:
                scad_file.write(output)

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
                form.errors["__all__"] = ["Failed to create an STL file from inputs"]
            else:
                with open(stl_filename) as stl_file:
                    stl_data = stl_file.read()
                os.remove(stl_filename)

            # Clean up temporary files
            os.remove(scad_filename)

        if form.errors:
            return render(request, "main.html", {"form": form, "version": version})

        response = HttpResponse(stl_data, content_type="application/zip")
        response["Content-Disposition"] = (
            "attachment; filename=%s" % stl_filename.rsplit("/")[-1]
        )
        return response

    return render(request, "main.html", {"form": form, "version": version})
