"""Django Ninja API for gerber-to-stencil conversion."""

from django import forms
from django.forms.utils import ErrorList
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from ninja import NinjaAPI

from gts_service.forms import ConvertGerberForm, InvalidInput, stencil_from_form
from gts_service.process import ConversionError, create_stl

api = NinjaAPI()


def get_version() -> str:
    with open("version") as f:
        return f.read()


def _render_form(
    request: HttpRequest, form: forms.Form, status: int = 200
) -> HttpResponse:
    return render(
        request, "main.html", {"form": form, "version": get_version()}, status=status
    )


def _handle_form_errors(
    request: HttpRequest,
    form: forms.Form,
    errors: dict[str, ErrorList],
) -> HttpResponse:
    for key, value in errors.items():
        form.errors[key] = value
    return _render_form(request, form, status=422)


@api.get("/convert")
def convert_redirect(request: HttpRequest) -> HttpResponse:
    return HttpResponseRedirect("/")


@api.post("/convert")
def convert(request: HttpRequest) -> HttpResponse:
    form = ConvertGerberForm(request.POST, request.FILES)

    try:
        stencil = stencil_from_form(form)
        stl_data, stl_filename = create_stl(stencil)
    except (InvalidInput, ConversionError) as e:
        if isinstance(e, ConversionError):
            errors = {"__all__": ErrorList([str(e)])}
        else:
            errors = e.errors

        return _handle_form_errors(request, form, errors)

    response = HttpResponse(stl_data, content_type="application/zip")
    response["Content-Disposition"] = (
        f"attachment; filename={stl_filename.rsplit('/')[-1]}"
    )
    return response
