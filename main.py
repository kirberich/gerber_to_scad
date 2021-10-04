import argparse
from gerber_to_scad import process_gerber
import gerber

if __name__ == "__main__":
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
        "-L",
        "--ledge-height",
        type=float,
        default=1.2,
        help="Height of the stencil ledge. This should be less than the "
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

    args = parser.parse_args()

    outline_file = open(args.outline_file, "r")
    solderpaste_file = open(args.solderpaste_file, "r")

    outline = gerber.loads(outline_file.read())
    solder_paste = gerber.loads(solderpaste_file.read())
    with open(args.output_file, "w") as output_file:
        output_file.write(
            process_gerber(
                outline,
                solder_paste,
                args.thickness,
                args.include_ledge,
                args.ledge_height,
                args.gap,
                args.increase_hole_size,
            )
        )
