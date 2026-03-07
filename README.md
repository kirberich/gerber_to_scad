# gerber_to_scad
Simple python script for converting gerber files into a 3d printable solder stencil scad file

This repository has both a CLI tool, and a web app you can run locally or self-host. The tool used to run online at solder-stencil.me, but this is currently offline. If anyone misses it, let me know and I might bring it back!

## Installation

* To install just the library: `pip install gerber-to-scad`
* To install the library and the web service: `pip install "gerber-to-scad[service]"`

`gerber_to_scad` requires python3.10 or higher.

## Development setup

* Clone the repo
* Make sure you have [poetry](https://python-poetry.org/docs/) installed.
* Run `poetry install`.
* To activate the poetry virtualenv, run `poetry shell`.

Note: on M1 macs, scipy doesn't install correctly out of the box. If you're getting installation errors, try this:

```bash
brew install openblas
export OPENBLAS="$(brew --prefix openblas)"
poetry install
```

## Usage

You'll get some information on available options if you run it with the -h argument:

```bash
(env) $ gerber_to_scad from-files --help

Usage: gerber_to_scad from-files [OPTIONS]

  Generate a stencil from an outline and paste gerber file.

Options:
  --outline FILE                  File containing the outline layer
                                  [required]
  --paste FILE                    File containing the solderpaste layer (top
                                  or bottom)  [required]
  --output FILE                   Output file  [required]
  -t, --thickness FLOAT           Stencil thickness in mm. Should be a
                                  multiple of your layer height.  [default:
                                  0.2]
  -a, --alignment-aid [ledge|frame|none]
                                  Alignment aid to include with the stencil.
                                  [default: ledge]
  -f, --full-ledge                [ledge] Extend the ledge all the way around
                                  the board (default is half ledge).
  -L, --ledge-thickness FLOAT     [ledge] Ledge thickness in mm. Should be
                                  less than the PCB thickness.  [default: 1.2]
  --frame-width FLOAT             [frame] Width of the frame in mm.  [default:
                                  155.0]
  --frame-height FLOAT            [frame] Height of the frame in mm.
                                  [default: 155.0]
  --frame-thickness FLOAT         [frame] Thickness of the frame in mm.
                                  [default: 1.2]
  -g, --gap FLOAT                 Gap in mm between board and ledge. Increase
                                  if fit is too tight.  [default: 0.0]
  -i, --increase-hole-size FLOAT  Increase all hole sizes by this amount in
                                  mm.  [default: 0.0]
  --flip                          Flip the stencil (use for bottom layer
                                  stencils).
  --openscad-binary PATH          Path to the OpenSCAD binary. Only used when
                                  output ends in .stl.  [default: openscad]
  --help                          Show this message and exit.
```

For basic usage, simply run the script with input files for the gerber outline and solderpaste files and specify an output:

```bash
gerber_to_scad from-files --outline=outline_file.gko --paste=toppaste_file.gtp --output=output.scad
```

Specifying a .stl file as the output file will directly call OpenSCAD to create the STL - if OpenSCAD is not on the path, you can use `--openscad-binary=<path>` to specify it

## Contributing

Contributions are very welcome, I don't have a lot of time to spend on this project, but I try to review PRs as much as I can!

* Please use ruff to format your code - if you use VS code, you can open the `gerber_to_scad.code-workspace` file to get all the right automatic formatting in your editor, or you can just run `ruff format .` in the project root.
