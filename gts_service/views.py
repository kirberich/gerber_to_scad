from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from gts_service.api import get_version
from gts_service.forms import ConvertGerberForm


def main(request: HttpRequest) -> HttpResponse:
    return render(
        request, "main.html", {"form": ConvertGerberForm(), "version": get_version()}
    )
