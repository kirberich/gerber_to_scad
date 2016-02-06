import sys
import logging
import argparse

import gerber
from gerber import primitives

from solid import (
    polygon,
    scad_render,
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


def make_v(v, decimal_places=2):
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
        v1 = make_v(p.lower_left)  # lower left
        v2 = make_v((v1[0], v1[1] + p.height))  # top left
        v3 = make_v((v2[0] + p.width, v2[1]))  # top right
        v4 = make_v((v1[0] + p.width, v1[1]))  # bottom right

        faces += [(v1, v2), (v2, v3), (v3, v4), (v4, v1)]
    elif type(p) == primitives.Region:
        for sub_primitive in p.primitives:
            # the primitives in regions aren't converted to metric when calling to_metric on the file,
            # so we call it explicitly here:
            sub_primitive.to_metric()
            faces += primitive_to_faces(sub_primitive)
    else:
        raise NotImplementedError("Unexpected primitive type {}".format(type(p)))
    return faces


def create_outline_shape(outline):
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
        biggest = None
        biggest_size = (0, 0)
        for shape in outline_shapes:
            x_coordinates = [c[0] for c in shape]
            y_coordinates = [c[1] for c in shape]
            x_size = max(x_coordinates) - min(x_coordinates)
            y_size = max(y_coordinates) - min(y_coordinates)
            if x_size > biggest_size[0] or y_size > biggest_size[1]:
                biggest = shape
                biggest_size = (x_size, y_size)
        outline_shape = biggest
    else:
        outline_shape = outline_shapes[0]

    outline_shape = [[x, y] for x, y in outline_shape]
    return outline_shape


def offset_shape(shape, offset, inside=False):
    """ Offset a shape by <offset> mm. """
    offset_3d_points = utils.offset_points(
        shape,
        offset,
        inside=inside
    )

    return [[x, y] for x, y, z in offset_3d_points]



def create_cutouts(solder_paste, increase_hole_size_by=0.0):
    solder_paste.to_metric()

    cutout_faces = []

    for p in solder_paste.primitives:
        cutout_faces += primitive_to_faces(p)

    cutout_shapes = combine_faces_into_shapes(cutout_faces)

    polygons = []
    for shape in cutout_shapes:
        if increase_hole_size_by:
            shape = offset_shape(shape, increase_hole_size_by)
        polygons.append(polygon([[x, y] for x, y in shape]))

    return union()(*polygons)


def bounding_box(shape):
    min_x = min(shape, key=lambda v: v[0])[0]
    max_x = max(shape, key=lambda v: v[0])[0]
    min_y = min(shape, key=lambda v: v[1])[1]
    max_y = max(shape, key=lambda v: v[1])[1]
    return [
        [min_x, min_y],
        [min_x, max_y],
        [max_x, max_y],
        [max_x, min_y]
    ]


def process(outline_file, solderpaste_file, stencil_thickness=0.2, include_ledge=True,
            ledge_height=1.2, ledge_gap=0.0, increase_hole_size_by=0.0):

    outline_shape = create_outline_shape(outline_file)
    cutout_polygon = create_cutouts(solderpaste_file, increase_hole_size_by=increase_hole_size_by)

    if ledge_gap:
        # Add a gap between the ledge and the stencil
        outline_shape = offset_shape(outline_shape, ledge_gap)
    outline_polygon = polygon(outline_shape)

    stencil = linear_extrude(height=stencil_thickness)(outline_polygon - cutout_polygon)

    if include_ledge:
        ledge_shape = offset_shape(outline_shape, 1.2)
        ledge_polygon = polygon(ledge_shape) - outline_polygon

        # Cut the ledge in half by taking the bounding box of the outline, cutting it in half
        # and removing the resulting shape from the ledge shape
        # We always leave the longer side of the ledge intact so we don't end up with a tiny ledge.
        cutter = bounding_box(ledge_shape)
        height = abs(cutter[1][1] - cutter[0][1])
        width = abs(cutter[0][0] - cutter[3][0])

        if width > height:
            cutter[1][1] -= height/2
            cutter[2][1] -= height/2
        else:
            cutter[2][0] -= width/2
            cutter[3][0] -= width/2

        ledge_polygon = ledge_polygon - polygon(cutter)

        ledge = utils.down(
            ledge_height - stencil_thickness
        )(
            linear_extrude(height=ledge_height)(ledge_polygon)
        )
        stencil = ledge + stencil

    # Rotate the stencil to make it printable
    stencil = rotate(a=180, v=[1, 0, 0])(stencil)

    return scad_render(stencil)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert gerber files to an scad 3d printable solder stencil.')
    parser.add_argument('outline_file', help='Outline file')
    parser.add_argument('solderpaste_file', help='Solderpaste file')
    parser.add_argument('output_file', help='Output file', default="output.scad")
    args = parser.parse_args()

    outline_file = open(args.outline_file, 'rU')
    solderpaste_file = open(args.solderpaste_file, 'rU')
    
    outline = gerber.loads(outline_file.read())
    solder_paste = gerber.loads(solderpaste_file.read())

    with open(args.output_file, 'w') as output_file:
        output_file.write(process(outline, solder_paste))
