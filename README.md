# gerber_to_scad
Simple python script for converting gerber files into a 3d printable solder stencil scad file

## Installation

```bash
cd gerber_to_scad
virtualenv env # Only tested for python 2.7
source env/bin/activate
pip install -r requirements.txt
```

You should now be able to run the script. You'll get some information on available options if you run it with the -h argument:
```bash
(env) $ python gerber_to_scad.py -h
usage: gerber_to_scad.py [-h] [-t THICKNESS] [-n] [-L LEDGE_HEIGHT] [-g GAP]
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
  -L LEDGE_HEIGHT, --ledge-height LEDGE_HEIGHT
                        Height of the stencil ledge. This should be less than
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
python gerber_to_scad.py outline_file.gko toppaste_file.gtp output.stl
```
