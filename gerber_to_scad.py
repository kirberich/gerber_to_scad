import sys
import logging
import argparse

import gerber
from gerber import primitives

from solid import (
    polygon,
    scad_render_to_file,
    union,
    linear_extrude,
    rotate,
)

from solid import utils


def combine_faces_into_shapes(faces):
    """ Takes a list of faces and combines them into continuous shapes. """
    shapes = []

    for face in faces:
        if len(face) != 2:
            raise Exception("face with more than two vertices")

        v1 = face[0]
        v2 = face[1]

        for shape in shapes:
            # Face is already in the shape
            if v1 in shape and v2 in shape:
                break
            elif v1 in shape:
                vertex_index = shape.index(v1)
                # insert after existing vertex
                shape.insert(vertex_index + 1, v2)
                break
            elif v2 in shape:
                vertex_index = shape.index(v2)
                # Insert before existing vertex
                shape.insert(vertex_index, v1)
                break
        else:
            # No existing vertex was found in any face
            shapes.append(list(face))

    return shapes


def make_v(v, decimal_places=4):
    """ Round vertex coordinates to some amount of decimal places. """
    return round(v[0], decimal_places), round(v[1], decimal_places)


def primitive_to_faces(p):
    """ Turns a gerber primitive into a list of faces.
        The faces and vertices in the faces are in drawing-order.
    """
    faces = []
    if type(p) == primitives.Line:
        v1 = make_v(p.start)
        v2 = make_v(p.end)

        faces.append((v1, v2))
    elif type(p) == primitives.Circle:
        raise NotImplementedError("Handling circle primitives is not handled yet.")
    elif type(p) == primitives.Rectangle:
        v1 = p.lower_left  # lower left
        v2 = (v1[0], v1[1] + p.height)  # top left
        v3 = (v2[0] + p.width, v2[1])  # top right
        v4 = (v1[0] + p.width, v1[1])  # bottom right
        faces += [(v1, v2), (v2, v3), (v3, v4), (v4, v1)]
    else:
        raise NotImplementedError("Unexpected primitive type {}".format(type(p)))
    return faces


def create_outline_shape(outline_file):
    outline = gerber.loads(outline_file.read())
    outline.to_metric()

    outline_faces = []

    for p in outline.primitives:
        outline_faces += primitive_to_faces(p)

    outline_shapes = combine_faces_into_shapes(outline_faces)

    if not outline_shapes:
        logging.error("No outline shape found, quitting.")
        sys.exit(1)

    if len(outline_shapes) > 1:
        logging.warning("More than one outline shape found, using the largest one.")
        outline_shape = sorted(outline_shapes, key=lambda s: len(s), reverse=True)[0]
    else:
        outline_shape = outline_shapes[0]

    outline_shape = [[x, y] for x, y in outline_shape]
    return outline_shape


def create_cutouts(solderpaste_file):
    solder_paste = gerber.loads(solderpaste_file.read())
    solder_paste.to_metric()

    cutout_faces = []

    for p in solder_paste.primitives:
        cutout_faces += primitive_to_faces(p)

    cutout_shapes = combine_faces_into_shapes(cutout_faces)

    polygons = []
    for shape in cutout_shapes:
        polygons.append(polygon([[x, y] for x, y in shape]))

    return union()(*polygons)


def process(outline_file, solderpaste_file, output_file):
    outline_shape = create_outline_shape(outline_file)
    outline_polygon = polygon(outline_shape)
    cutout_polygon = create_cutouts(solderpaste_file)

    offset_outline_3d_points = utils.offset_points(
        outline_shape,
        1.2,
        inside=False
    )

    offset_outline_polygon = polygon(
        [[x, y] for x, y, z in offset_outline_3d_points]
    )

    wall_polygon = offset_outline_polygon - outline_polygon
    wall = utils.down(0.8)(linear_extrude(height=1)(wall_polygon))

    board = linear_extrude(height=0.2)(outline_polygon - cutout_polygon)

    combined = wall + board

    # Rotate the board to make it printable
    combined = rotate(a=180, v=[1, 0, 0])(combined)

    scad_render_to_file(combined, args.output_file)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert gerber files to an scad 3d printable solder stencil.')
    parser.add_argument('outline_file', help='Outline file')
    parser.add_argument('solderpaste_file', help='Solderpaste file')
    parser.add_argument('output_file', help='Output file', default="output.scad")
    args = parser.parse_args()

    outline_file = open(args.outline_file, 'rU')
    solderpaste_file = open(args.solderpaste_file, 'rU')
    output_file = open(args.output_file, 'rU')

    process(outline_file, solderpaste_file, output_file)
