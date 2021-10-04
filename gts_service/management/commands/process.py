from django.core.management.base import BaseCommand
from pathlib import Path
from gts_service import gerber_to_scad
import gerber


class Command(BaseCommand):
    help = "Process files on the command line"

    def add_arguments(self, parser):
        parser.add_argument("outline_file", type=Path)
        parser.add_argument("paste_file", type=Path)
        parser.add_argument("output_file", type=Path)
        parser.add_argument("--thickness", type=float, default=0.2)
        parser.add_argument("--no-ledge", action="store_true")

    def handle(self, *args, **options):

        with open(options["outline_file"], "r") as outline_file:
            outline = gerber.loads(outline_file.read())

        with open(options["paste_file"], "r") as paste_file:
            paste = gerber.loads(paste_file.read())

        output = gerber_to_scad.process(
            outline,
            paste,
            options["thickness"],
            not options["no_ledge"],
            # form.cleaned_data['ledge_height'],
            # form.cleaned_data['ledge_gap'],
            # form.cleaned_data['increase_hole_size_by'],
            # form.cleaned_data['simplify_regions']
        )

        with open(options["output_file"], "w") as scad_file:
            scad_file.write(output)
