import logging

from django.core.files.uploadedfile import UploadedFile
from django.forms import Form
from django.forms.utils import ErrorList
from django.http import HttpRequest
from django.http.response import HttpResponse
from django.shortcuts import render
from pygerber.gerberx3.api.v2 import GerberFile

from gts_service.forms import ConvertGerberForm
from gts_service.process import ConversionError, create_stl


def _get_version():
    with open("version", "r") as f:
        return f.read()


def _validate_gerber_file(raw_file: UploadedFile | list[object], form: Form):
    if isinstance(raw_file, list):
        raise RuntimeError(f"Expected single uploaded gerber file, got {raw_file}")

    try:
        return GerberFile.from_str(raw_file.read().decode("utf-8")).parse()
    except Exception as e:
        logging.error(e)
        form.errors["outline_file"] = ErrorList(
            ["Invalid format, is this a valid gerber file?"]
        )


def main(request: HttpRequest):
    form = ConvertGerberForm(request.POST or None, files=request.FILES or None)
    version = _get_version()
    stl_data = None

    if not form.is_valid():
        return render(request, "main.html", {"form": form, "version": version})

    outline = _validate_gerber_file(request.FILES["outline_file"], form)
    solder_paste = _validate_gerber_file(request.FILES["solderpaste_file"], form)

    if outline is None or solder_paste is None:
        return render(request, "main.html", {"form": form, "version": version})

    try:
        stl_data, stl_filename = create_stl(
            outline=outline,
            solder_paste=solder_paste,
            stencil_thickness=form.cleaned_data["stencil_thickness"],
            include_ledge=form.cleaned_data["include_ledge"],
            full_ledge=form.cleaned_data["full_ledge"],
            ledge_thickness=form.cleaned_data["ledge_thickness"],
            gap=form.cleaned_data["gap"],
            increase_hole_size_by=form.cleaned_data["increase_hole_size_by"],
            flip_stencil=form.cleaned_data["flip_stencil"],
            include_frame=form.cleaned_data["include_frame"],
            frame_width=form.cleaned_data["frame_width"],
            frame_height=form.cleaned_data["frame_height"],
            frame_thickness=form.cleaned_data["frame_thickness"],
        )

        response = HttpResponse(stl_data, content_type="application/zip")
        response["Content-Disposition"] = (
            f"attachment; filename={stl_filename.rsplit('/')[-1]}"
        )
        return response
    except ConversionError as e:
        form.errors["__all__"] = ErrorList([str(e)])
        return render(request, "main.html", {"form": form, "version": version})
