"""CLI entry point for gerber_to_scad."""

import argparse

from pygerber.gerberx3.api.v2 import GerberFile

from .conversion import GerberConverter


def gerber_to_scad_cli():
    parser = argparse.ArgumentParser(
        description="Convert gerber files to an scad 3d printable solder stencil."
    )
    parser.add_argument("outline_file", help="Outline file")
    parser.add_argument("solderpaste_file", help="Solderpaste file")
    parser.add_argument("output_file", help="Output file", default="output.scad")

    # Optional arguments
    parser.add_argument(
        "-t",
        "--thickness",
        type=float,
        default=0.2,
        help="Thickness (in mm) of the stencil. Make sure this is a multiple "
        "of the layer height you use for printing (default: %(default)0.1f)",
    )
    parser.add_argument(
        "-n",
        "--no-ledge",
        dest="include_ledge",
        action="store_false",
        help="By default, a ledge around half the outline of the board is included, to allow "
        "aligning the stencil easily. Pass this to exclude this ledge.",
    )
    parser.set_defaults(include_ledge=True)
    parser.add_argument(
        "-f",
        "--full-ledge",
        action="store_true",
        help="Include a full ledge around the entire board (default is half ledge).",
    )
    parser.add_argument(
        "-L",
        "--ledge-thickness",
        type=float,
        default=1.2,
        help="Thickness of the stencil ledge. This should be less than the "
        "thickness of the PCB (default: %(default)0.1f)",
    )
    parser.add_argument(
        "-g",
        "--gap",
        type=float,
        default=0,
        help="Gap (in mm) between board and stencil ledge. Increase this if "
        "the fit of the stencil is too tight (default: %(default)0.1f)",
    )
    parser.add_argument(
        "-i",
        "--increase-hole-size",
        type=float,
        default=0,
        help="Increase the size of all holes in the stencil by this amount (in "
        "mm). Use this if you find holes get printed smaller than they should "
        "(default: %(default)0.1f)",
    )
    parser.add_argument(
        "--flip",
        action="store_true",
        help="Flip the stencil. Use this for making stencils for the bottom layer.",
    )

    args = parser.parse_args()

    outline_parsed = GerberFile.from_file(args.outline_file).parse()
    paste_parsed = GerberFile.from_file(args.solderpaste_file).parse()

    converter = GerberConverter(
        outline_file=outline_parsed,
        solderpaste_file=paste_parsed,
        stencil_thickness=args.thickness,
        include_ledge=args.include_ledge,
        ledge_thickness=args.ledge_thickness,
        full_ledge=args.full_ledge,
        gap=args.gap,
        increase_hole_size_by=args.increase_hole_size,
        flip_stencil=args.flip,
    )

    with open(args.output_file, "w") as output_file:
        output_file.write(converter.convert())


if __name__ == "__main__":
    gerber_to_scad_cli()
