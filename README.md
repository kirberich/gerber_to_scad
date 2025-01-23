# gerber_to_scad
Simple python script for converting gerber files into a 3d printable solder stencil scad file

## Installation
gerber to scad requires >=python3.10

* Make sure you have (poetry)[https://python-poetry.org/docs/] installed. Easiest way: `curl -sSL https://install.python-poetry.org | python3 -`
* Run `poetry install`
* or add via poetry `add git+ssh://git@github.com:kirberich/gerber_to_scad.git` to your poetry based project

Note: on M1 macs, scipy doesn't install correctly out of the box. If you're getting installation errors, try this:

```bash
brew install openblas
export OPENBLAS="$(brew --prefix openblas)"
poetry install
```
## Usage

* To activate the poetry virtualenv, run `poetry shell`.

You should now be able to run the script. You'll get some information on available options if you run it with the -h argument:

```bash
(env) $ python main.py -h
usage: main.py [-h] [-t THICKNESS] [-n] [-L LEDGE_THICKNESS] [-g GAP]
                         [-i INCREASE_HOLE_SIZE]
                         outline_file solderpaste_file output_file

Convert gerber files to an scad 3d printable solder stencil.

positional arguments:
  outline_file          Outline file
  solderpaste_file      Solderpaste file
  output_file           Output file

optional arguments:
  -h, --help            show this help message and exit
  -t THICKNESS, --thickness THICKNESS
                        Thickness (in mm) of the stencil. Make sure this is a
                        multiple of the layer height you use for printing
                        (default: 0.2)
  -n, --no-ledge        By default, a ledge around half the outline of the
                        board is included, to allow aligning the stencil
                        easily. Pass this to exclude this ledge.
  -L LEDGE_THICKNESS, --ledge-thickness LEDGE_THICKNESS
                        Thickness of the stencil ledge. This should be less than
                        the thickness of the PCB (default: 1.2)
  -g GAP, --gap GAP     Gap (in mm) between board and stencil ledge. Increase
                        this if the fit of the stencil is too tight (default:
                        0.0)
  -i INCREASE_HOLE_SIZE, --increase-hole-size INCREASE_HOLE_SIZE
                        Increase the size of all holes in the stencil by this
                        amount (in mm). Use this if you find holes get printed
                        smaller than they should (default: 0.0)
```

For basic usage, simply run the script with input files for the gerber outline and solderpaste files and specify an output:

```bash
python main.py outline_file.gko toppaste_file.gtp output.scad
```
