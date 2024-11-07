import math
from copy import copy
from typing import List, Tuple, cast

from gerber import primitives
from gerber.am_statements import (
    AMOutlinePrimitive,
    AMCenterLinePrimitive,
    AMCirclePrimitive,
    AMPrimitive,
    AMCommentPrimitive,
    AMVectorLinePrimitive,
)

from solid import polygon, scad_render, union, linear_extrude, rotate, mirror, translate
from solid import utils
from .vector import V
from . import geometry
from . import gerber_helpers

MAX_SEGMENT_LENGTH = 0.1


def combine_faces_into_shapes(faces):
    """Takes a list of faces and combines them into continuous shapes."""
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


def make_v(v: Tuple[float, float], decimal_places=3) -> V:
    """Round vertex coordinates to some amount of decimal places."""
    return V(round(v[0], decimal_places), round(v[1], decimal_places))


def rect_from_line(line: primitives.Line):
    """Creates a rectangle from a line primitive by thickening it
    according to the primitive's aperture size.

    Treats rectangular apertures as square because otherwise the maths
    becomes too hard for my brain.
    """
    r: float = gerber_helpers.get_aperture_size(line.aperture) / 2.0

    start_v = V.from_tuple(line.start)
    end_v = V.from_tuple(line.end)

    dir_v = end_v - start_v
    # normalize direction vector
    abs_dir_v = abs(dir_v)
    if abs_dir_v:
        dir_v = dir_v / abs_dir_v
    else:
        dir_v = V(0, 0)

    # 45 degree angle means the vector pointing to the new rectangle edges has to be sqrt(2)*r long
    v_len = math.sqrt(2) * r

    # Give the direction vector the appropriate length
    dir_v = cast(V, dir_v * v_len)

    v1 = start_v + dir_v.rotate(135, as_degrees=True)
    v2 = start_v + dir_v.rotate(-135, as_degrees=True)
    v3 = end_v + dir_v.rotate(-45, as_degrees=True)
    v4 = end_v + dir_v.rotate(45, as_degrees=True)

    return [v1, v2, v3, v4]


def primitive_to_shape(p, in_region=False, simplify_regions=False) -> List[V]:
    """Turns a gerber primitive into an scad shape.

    If in_region is True, all shapes are assumed to be contours only, ignoring apertures.
    """
    # the primitives in sub-primitives sometimes aren't converted to metric when calling to_metric on the file,
    # so we call it explicitly here:
    if not isinstance(p, AMPrimitive) and p.units != "metric":
        p.to_metric()

    vertices: List[V] = []
    if isinstance(p, primitives.Line):
        # Lines are tricky: they're sometimes used to draw rounded rectangles by using a large aperture
        # or they're used to outline shapes. For now, we'll just use those two cases:
        # If a non-zero aperture size is set, we'll draw rectangles (treating circular apertures as square for now)
        # otherwise we'll just use the lines directly (they're later joined into shapes)

        length = math.sqrt((p.start[0] - p.end[0]) ** 2 + (p.start[1] - p.end[1]) ** 2)
        if not in_region and gerber_helpers.has_wide_aperture(
            p.aperture, length=length
        ):

            vertices = rect_from_line(p)
        else:
            v1 = make_v(p.start)
            v2 = make_v(p.end)
            vertices = [v1, v2]
    elif isinstance(p, (primitives.Circle, AMCirclePrimitive)):
        # Rasterize circle, aiming for a hopefully reasonable segment length of 0.1mm
        circ = math.pi * p.diameter
        num_segments = max(1, int(round(circ / MAX_SEGMENT_LENGTH)))

        # Generate vertexes for each segment around the circle
        for s in range(0, num_segments):
            angle = s * (2 * math.pi / num_segments)
            x = p.position[0] + math.cos(angle) * p.diameter / 2
            y = p.position[1] + math.sin(angle) * p.diameter / 2
            vertices.append(make_v((x, y)))
    elif isinstance(p, primitives.Rectangle):
        v1 = make_v(p.lower_left)  # lower left
        v2 = make_v((v1[0], v1[1] + p.height))  # top left
        v3 = make_v((v2[0] + p.width, v2[1]))  # top right
        v4 = make_v((v1[0] + p.width, v1[1]))  # bottom right
        vertices = [v1, v2, v3, v4]
    elif isinstance(p, AMCenterLinePrimitive):
        # Essentially a rotated rectangle
        print(f"Center line {p.rotation} deg")
        center = p.center
        angle_rad = p.rotation * math.pi / 180
        cos_angle = math.cos(angle_rad)
        sin_angle = math.sin(angle_rad)

        p1 = (center[0] - p.width / 2, center[1] - p.height / 2)
        p2 = (center[0] + p.width / 2, center[1] - p.height / 2)
        p3 = (center[0] + p.width / 2, center[1] + p.height / 2)
        p4 = (center[0] - p.width / 2, center[1] + p.height / 2)

        # Rotate point about origin
        # (x*cos(theta)-y*sin(theta), x*sin(theta)+y*cos(theta))
        vertices = [
            V(
                p1[0] * cos_angle - p1[1] * sin_angle,
                p1[0] * sin_angle + p1[1] * cos_angle,
            ),
            V(
                p2[0] * cos_angle - p2[1] * sin_angle,
                p2[0] * sin_angle + p2[1] * cos_angle,
            ),
            V(
                p3[0] * cos_angle - p3[1] * sin_angle,
                p3[0] * sin_angle + p3[1] * cos_angle,
            ),
            V(
                p4[0] * cos_angle - p4[1] * sin_angle,
                p4[0] * sin_angle + p4[1] * cos_angle,
            ),
        ]
    elif isinstance(p, primitives.Region):
        for sub_primitive in p.primitives:
            vertices += [
                vertex
                for vertex in primitive_to_shape(sub_primitive, in_region=True)
                if vertex not in vertices
            ]
        if simplify_regions:
            vertices = list(geometry.bounding_box(vertices))
    elif isinstance(p, primitives.Obround):
        # We don't care about vertex duplication here because we'll just create a convex hull for the whole thing
        for sub_primitive in p.subshapes.values():
            vertices += primitive_to_shape(sub_primitive)
        vertices = geometry.convex_hull(vertices)
    elif isinstance(p, primitives.Arc):
        if p.direction == "counterclockwise":
            if p.end_angle <= p.start_angle:
                sweep_angle = 360 - (p.start_angle - p.end_angle)
            else:
                sweep_angle = p.start_angle - p.end_angle
        else:
            if p.end_angle >= p.start_angle:
                sweep_angle = 360 - (p.end_angle - p.start_angle)
            else:
                sweep_angle = p.start_angle - p.end_angle

        arc_length = p.radius * sweep_angle
        num_segments = max(1, int(round(arc_length / MAX_SEGMENT_LENGTH)))
        angle_delta = sweep_angle / num_segments

        angle = p.start_angle

        for s in range(0, num_segments):
            x = p.center[0] + math.cos(angle) * p.radius
            y = p.center[1] + math.sin(angle) * p.radius
            vertices.append(make_v((x, y)))

            angle = (
                angle + angle_delta
                if p.direction == "counterclockwise"
                else angle - angle_delta
            )

    elif isinstance(p, AMOutlinePrimitive):
        return [make_v(point) for point in p.points]
    elif isinstance(p, AMVectorLinePrimitive):
        # A vector line with a given thickness - we turn this into a rotated rectangle
        start_v = V.from_tuple(p.start)
        end_v = V.from_tuple(p.end)

        dir_v = end_v - start_v
        # normalize direction vector
        abs_dir_v = abs(dir_v)
        if abs_dir_v:
            dir_v = dir_v / abs_dir_v
        else:
            dir_v = V(0, 0)

        # Give the direction vector the appropriate length
        dir_v = cast(V, dir_v * p.width / 2)

        v1 = start_v + dir_v.rotate(90, as_degrees=True)
        v2 = start_v + dir_v.rotate(-90, as_degrees=True)
        v3 = end_v + dir_v.rotate(-90, as_degrees=True)
        v4 = end_v + dir_v.rotate(90, as_degrees=True)

        return [v1, v2, v3, v4]

    elif isinstance(p, AMCommentPrimitive):
        return []
    else:
        raise NotImplementedError("Unexpected primitive type {}".format(type(p)))
    return vertices


def create_outline_shape_rect(outline) -> List[V]:
    outline.to_metric()
    outline_vertices: List[V] = []

    # For some reason, some boards don't have any primitives but just some rectangular bounds
    # In that case, we just use those bounds as a rectangle defining the board
    # To make matters worse, the bounds aren't stored in the usual shape format but rather as
    # ((min_x, max_x), (min_y, max_y))

    bounds = outline.bounds
    min_x, max_x = bounds[0]
    min_y, max_y = bounds[1]

    outline_vertices += [
        V(min_x, min_y),
        V(min_x, max_y),
        V(max_x, max_y),
        V(max_x, min_y),
    ]

    return geometry.convex_hull(outline_vertices)


def outline_shape_from_file(outline) -> List[V]:
    outline.to_metric()
    outline_vertices: List[V] = []

    if outline.primitives:
        for p in outline.primitives:
            if type(p) == primitives.AMGroup:
                print(f"Ignoring AMGroup {p}")
                continue
            outline_vertices += primitive_to_shape(p)
        return geometry.convex_hull(outline_vertices)
    else:
        return create_outline_shape_rect(outline)


def offset_shape(shape: List[V], offset, inside=False) -> List[V]:
    """Offset a shape by <offset> mm."""

    return [
        V(p[0], p[1])
        for p in utils.offset_points(
            [v.as_tuple() for v in shape], offset, internal=inside  # type: ignore
        )
    ]


def find_line_closest_to_point(point, lines):
    """Finds the line from a list of lines that is closest to `point`.
    Returns a bunch of information about the closest line.
    """
    d = float("inf")
    closest_vertex = None
    far_vertex = None
    closest_line_index = None
    for line_index, line in enumerate(lines):
        for vertex_index, vertex in enumerate(line):
            point_d = (vertex[0] - point[0]) ** 2 + (vertex[1] - point[1]) ** 2
            if point_d < d and point_d < (0.001) ** 2:
                d = point_d
                closest_vertex = vertex
                far_vertex = line[vertex_index - 1]  # 0 or -1
                closest_line_index = line_index

    return {
        "closest_line_index": closest_line_index,
        "close_vertex": closest_vertex,
        "far_vertex": far_vertex,
    }


def lines_to_shapes(lines: List[List[V]]) -> List[List[V]]:
    """Takes a list of lines and joins them together into shapes.

    1) Starts the first shape with the first line
    2) Looks for other line segments that are close to its end points (first or last vertex)
    3) If it finds a close line it discards the close point and appends the second point to the shape
    4) The found line is removed from the list of lines.
    5) Repeats the process with the new shape, again looking for lines close to its (new) end points
    6) Once no more close shapes are found, the first shape is closed and the process starts over with the next remaining line
    """
    # lines = deepcopy(lines)
    if not lines:
        return []

    shapes: List[List[V]] = []
    shape = copy(lines[0])
    lines = lines[1:]

    while True:
        # Try to find a point close to the start of the shape
        start_point_info = find_line_closest_to_point(shape[0], lines)
        if start_point_info["closest_line_index"] is not None:
            shape.insert(0, start_point_info["far_vertex"])
            del lines[start_point_info["closest_line_index"]]
            continue

        # If no point close to the start was found, try to find a point close to the end of the shape
        end_point_info = find_line_closest_to_point(shape[-1], lines)
        if end_point_info["closest_line_index"] is not None:
            shape.append(end_point_info["far_vertex"])
            del lines[end_point_info["closest_line_index"]]
            continue

        # There is no close point to this shape, so it must be finished.
        shapes.append(shape)

        # While there are lines remaining, chose the next one as the start of the next shape
        if lines:
            shape = copy(lines[0])
            lines = lines[1:]
        else:
            break

    # shapes = [convex_hull(shape) for shape in shapes if len(shape) > 2]
    return shapes


def create_cutouts(solder_paste, increase_hole_size_by=0.0, simplify_regions=False):
    solder_paste.to_metric()

    cutout_shapes: List[List[V]] = []
    cutout_lines: List[List[V]] = []

    apertures = {}
    # Aperture macros are saved as a list of shapes
    aperture_macros = {}
    current_aperture = None
    current_x = 0
    current_y = 0
    for statement in solder_paste.statements:
        if statement.type == "PARAM":
            if statement.param == "AD":
                # define aperture
                apertures[statement.d] = {
                    "shape": statement.shape,
                    "modifiers": statement.modifiers,
                }
            elif statement.param == "AM":
                # Aperture macro
                aperture_macros[statement.name] = []
                for primitive in statement.primitives:
                    aperture_macros[statement.name].append(
                        primitive_to_shape(primitive)
                    )

        elif statement.type == "APERTURE":
            current_aperture = statement.d
        elif statement.type == "COORD" and statement.op in ["D02", "D2"]:
            # Move coordinates
            if statement.x is not None:
                current_x = statement.x
            if statement.y is not None:
                current_y = statement.y
        elif statement.type == "COORD" and statement.op in [
            "D03",
            "D3",
        ]:  # flash object coordinates
            if not current_aperture:
                raise Exception("No aperture set on flash object coordinates!")

            aperture = apertures[current_aperture]
            current_x = statement.x if statement.x is not None else current_x
            current_y = statement.y if statement.y is not None else current_y
            if aperture["shape"] == "C":  # circle
                cutout_shapes.append(
                    primitive_to_shape(
                        primitives.Circle(
                            diameter=aperture["modifiers"][0][0],
                            position=[current_x, current_y],
                        )
                    )
                )
            elif aperture["shape"] == "R":  # rectangle
                width, height = aperture["modifiers"][0]
                print(f"Rect X: {current_x} Y: {current_y}")
                cutout_shapes.append(
                    primitive_to_shape(
                        primitives.Rectangle(
                            position=[current_x, current_y],
                            width=width,
                            height=height,
                        )
                    )
                )
            elif aperture["shape"] == "O":  # obround
                width, height = aperture["modifiers"][0]
                print(f"Obround at {current_x},{current_y}")
                obround = primitives.Obround((0, 0), width, height)
                shape = primitive_to_shape(obround)
                positioned_shape = [
                    V(p[0] + current_x, p[1] + current_y) for p in shape
                ]
                cutout_shapes.append(positioned_shape)
            elif aperture["shape"] in aperture_macros:  # Aperture macro shape
                for macro_shape in aperture_macros[aperture["shape"]]:
                    # Offset all points in the macro and add the resulting shape
                    shape = [V(p[0] + current_x, p[1] + current_y) for p in macro_shape]
                    cutout_shapes.append(shape)
            else:
                raise NotImplementedError(
                    f"Unsupported flash aperture {aperture['shape']}"
                )
        else:
            pass

    for p in solder_paste.primitives:
        if type(p) == primitives.AMGroup:
            print(f"Ignoring AMGroup {p}")
            continue
        shape = primitive_to_shape(p, simplify_regions=simplify_regions)
        if len(shape) > 2:
            cutout_shapes.append(shape)
        else:
            cutout_lines.append(shape)

    # If the cutouts contain lines we try to first join them together into shapes
    cutout_shapes += lines_to_shapes(cutout_lines)
    polygons = []
    for shape in cutout_shapes:
        if increase_hole_size_by and len(shape) > 2:
            shape = offset_shape(shape, increase_hole_size_by)
        polygons.append(polygon([(x, y) for x, y in shape]))

    return union()(*polygons)


def process_gerber(
        *,
    outline_file,
    solderpaste_file,
    stencil_thickness: float,
    include_ledge: bool,
    ledge_thickness: float,
    gap: float,
    include_frame: bool,
    frame_width: float,
    frame_height: float,
    frame_thickness: float,
    increase_hole_size_by: float,
    simplify_regions: bool,
    flip_stencil: bool,
    stencil_width: float,
    stencil_height: float,
    stencil_margin: float,
):
    """Convert gerber outline and solderpaste files to an scad file."""
    if outline_file:
        outline_shape = outline_shape_from_file(outline_file)
    else:
        outline_shape_rect = create_outline_shape_rect(solderpaste_file)
        outline_shape = geometry.bounding_box(outline_shape_rect, width=stencil_width, height=stencil_height, margin=stencil_margin)

    cutout_polygon = create_cutouts(
        solderpaste_file,
        increase_hole_size_by=increase_hole_size_by,
        simplify_regions=simplify_regions,
    )

    # debugging!
    # return scad_render(linear_extrude(height=stencil_thickness)(polygon(outline_shape)))

    if gap:
        # Add a gap around the outline
        outline_shape = offset_shape(outline_shape, gap)
    outline_polygon = polygon([v.as_tuple() for v in outline_shape])

    # Move the polygons to be centered around the origin
    outline_bounds = geometry.bounding_box(outline_shape)
    outline_offset =  outline_bounds[0] + (outline_bounds[2] - outline_bounds[0])/2
    outline_polygon = translate((-outline_offset[0], -outline_offset[1], 0))(outline_polygon)
    cutout_polygon = translate((-outline_offset[0], -outline_offset[1], 0))(cutout_polygon)

    if flip_stencil:
        mirror_normal = (-1, 0, 0)

        outline_polygon = mirror(mirror_normal)(outline_polygon)
        cutout_polygon = mirror(mirror_normal)(cutout_polygon)

    stencil = linear_extrude(height=stencil_thickness)(outline_polygon - cutout_polygon)

    if include_ledge:
        ledge_shape = offset_shape(outline_shape, 1.2)
        ledge_polygon = translate((-outline_offset[0], -outline_offset[1], 0))(polygon([v.as_tuple() for v in ledge_shape]))- outline_polygon

        # Cut the ledge in half by taking the bounding box of the outline, cutting it in half
        # and removing the resulting shape from the ledge shape
        # We always leave the longer side of the ledge intact so we don't end up with a tiny ledge.
        cutter = geometry.bounding_box(ledge_shape)
        height = abs(cutter[1][1] - cutter[0][1])
        width = abs(cutter[0][0] - cutter[3][0])

        if width > height:
            cutter[1].y -= height / 2
            cutter[2].y -= height / 2
        else:
            cutter[2].x -= width / 2
            cutter[3].x -= width / 2

        ledge_polygon = ledge_polygon - translate((-outline_offset[0], -outline_offset[1], 0))(polygon([v.as_tuple() for v in cutter]))

        ledge = utils.down(ledge_thickness - stencil_thickness)(
            linear_extrude(height=ledge_thickness)(ledge_polygon)
        )
        stencil = ledge + stencil
    elif include_frame:
        frame_shape = geometry.bounding_box(outline_shape, width=frame_width, height=frame_height)
        frame_polygon = translate((-outline_offset[0], -outline_offset[1], 0))(polygon([v.as_tuple() for v in frame_shape])) - outline_polygon

        frame = utils.down(frame_thickness - stencil_thickness)(
            linear_extrude(height=frame_thickness)(frame_polygon)
        )
        stencil = frame + stencil

    # Rotate the stencil to make it printable
    stencil = rotate(a=180, v=(1, 0, 0))(stencil)

    # for debugging, output just the cutout polygon (extruded)
    # return scad_render(linear_extrude(height=stencil_thickness)(cutout_polygon))

    return scad_render(stencil)
