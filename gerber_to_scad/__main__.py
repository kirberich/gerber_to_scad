"""`__main__.py` file adds support for running like: `python -m gerber_to_scad -h`."""

from .cli import gerber_to_scad_cli

if __name__ == "__main__":
    gerber_to_scad_cli()
    