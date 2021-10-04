import os
from random import randint
import subprocess

from django.conf import settings
from django.http.response import HttpResponse
from django.shortcuts import render

import gerber
from gerber_to_scad import (
    process_gerber,
)
from gts_service.forms import UploadForm
import logging


def _get_version():
    with open("version", "r") as f:
        return f.read()


def main(request):
    form = UploadForm(request.POST or None, files=request.FILES or None)
    version = _get_version()
    if form.is_valid():
        outline_file = form.cleaned_data["outline_file"]
        solderpaste_file = request.FILES["solderpaste_file"]

        try:
            outline = gerber.loads(outline_file.read().decode("utf-8"))
        except Exception as e:
            logging.error(e)
            outline = None
            form.errors["outline_file"] = [
                "Invalid format, is this a valid gerber file?"
            ]

        try:
            solder_paste = gerber.loads(solderpaste_file.read().decode("utf-8"))
        except Exception as e:
            logging.error(e)
            solder_paste = None
            form.errors["solderpaste_file"] = [
                "Invalid format, is this a valid gerber file?"
            ]

        if outline and solder_paste:
            output = process_gerber(
                outline,
                solder_paste,
                form.cleaned_data["stencil_thickness"],
                form.cleaned_data["include_ledge"],
                form.cleaned_data["ledge_height"],
                form.cleaned_data["ledge_gap"],
                form.cleaned_data["increase_hole_size_by"],
                form.cleaned_data["simplify_regions"],
            )

            file_id = randint(1000000000, 9999999999)
            scad_filename = "/tmp/gts-{}.scad".format(file_id)
            stl_filename = "/tmp/gts-{}.stl".format(file_id)

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
                with open(stl_filename, "r") as stl_file:
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
