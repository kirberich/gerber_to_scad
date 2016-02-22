#!/usr/bin/env python
import argparse
import math

from scipy.spatial import ConvexHull

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


def convex_hull(points):
    hull = ConvexHull(points)
    hull_points = [hull.points[vertex_index] for vertex_index in hull.vertices]
    return [(float(x), float(y)) for x, y in hull_points]


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


def make_v(v, decimal_places=3):
    """ Round vertex coordinates to some amount of decimal places. """
    return round(v[0], decimal_places), round(v[1], decimal_places)


def primitive_to_shape(p):
    """ Turns a gerber primitive into a shape. """
    # the primitives in sub-primitives sometimes aren't converted to metric when calling to_metric on the file,
    # so we call it explicitly here:
    p.to_metric()

    vertices = []
    if type(p) == primitives.Line:
        v1 = make_v(p.start)
        v2 = make_v(p.end)
        vertices = [v1, v2]
    elif type(p) == primitives.Circle:
        # Rasterize circle, aiming for a hopefully reasonable segment length of 0.1mm
        vertices = []
        circ = math.pi * p.diameter
        num_segments = int(round(circ / 0.1))

        # Generate vertexes for each segment around the circle
        for s in range(0, num_segments):
            angle = s * (2 * math.pi / num_segments)
            x = p.position[0] + math.cos(angle) * p.diameter / 2
            y = p.position[1] + math.sin(angle) * p.diameter / 2
            vertices.append(make_v((x, y)))
    elif type(p) == primitives.Rectangle:
        v1 = make_v(p.lower_left)  # lower left
        v2 = make_v((v1[0], v1[1] + p.height))  # top left
        v3 = make_v((v2[0] + p.width, v2[1]))  # top right
        v4 = make_v((v1[0] + p.width, v1[1]))  # bottom right
        vertices = [v1, v2, v3, v4]
    elif type(p) == primitives.Region:
        vertices = []
        for sub_primitive in p.primitives:
            vertices += [vertex for vertex in primitive_to_shape(sub_primitive) if vertex not in vertices]
    elif type(p) == primitives.Obround:
        # We don't care about vertex duplication here because we'll just convex_hull the whole thing
        vertices = []
        for sub_primitive in p.subshapes.values():
            vertices += primitive_to_shape(sub_primitive)
        vertices = convex_hull(vertices)
    elif type(p) == primitives.Arc:
        sweep_angle = p.sweep_angle
        arc_length = p.radius * sweep_angle
        num_segments = int(round(arc_length / 0.1))
        angle_delta = sweep_angle / num_segments

        angle = p.start_angle
        for s in range(0, num_segments):
            x = p.center[0] + math.cos(angle) * p.radius
            y = p.center[1] + math.sin(angle) * p.radius
            vertices.append(make_v((x, y)))

            angle = angle + angle_delta if p.direction == 'counterclockwise' else angle - angle_delta
    else:
        raise NotImplementedError("Unexpected primitive type {}".format(type(p)))
    return vertices


def create_outline_shape(outline):
    outline.to_metric()

    outline_vertices = []
    for p in outline.primitives:
        outline_vertices += primitive_to_shape(p)

    return convex_hull(outline_vertices)


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

    cutout_shapes = []

    for p in solder_paste.primitives:
        cutout_shapes.append(primitive_to_shape(p))

    polygons = []
    for shape in cutout_shapes:
        if increase_hole_size_by and len(shape) > 2:
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

    # Optional arguments
    parser.add_argument('-t', '--thickness', type=float, default=0.2,
        help='Thickness (in mm) of the stencil. Make sure this is a multiple '
        'of the layer height you use for printing (default: %(default)0.1f)')
    parser.add_argument('-n', '--no-ledge', dest='include_ledge', action='store_false',
        help='By default, a ledge around half the outline of the board is included, to allow '
        'aligning the stencil easily. Pass this to exclude this ledge.')
    parser.set_defaults(include_ledge=True)
    parser.add_argument('-L', '--ledge-height', type=float, default=1.2,
        help='Height of the stencil ledge. This should be less than the '
        'thickness of the PCB (default: %(default)0.1f)')
    parser.add_argument('-g', '--gap', type=float, default=0,
        help='Gap (in mm) between board and stencil ledge. Increase this if '
        'the fit of the stencil is too tight (default: %(default)0.1f)')
    parser.add_argument('-i', '--increase-hole-size', type=float, default=0,
        help='Increase the size of all holes in the stencil by this amount (in '
        'mm). Use this if you find holes get printed smaller than they should '
        '(default: %(default)0.1f)')

    args = parser.parse_args()

    outline_file = open(args.outline_file, 'rU')
    solderpaste_file = open(args.solderpaste_file, 'rU')

    outline = gerber.loads(outline_file.read())
    solder_paste = gerber.loads(solderpaste_file.read())
    with open(args.output_file, 'w') as output_file:
        output_file.write(
            process(
                outline,
                solder_paste,
                args.thickness,
                args.include_ledge,
                args.ledge_height,
                args.gap,
                args.increase_hole_size
            )
        )
