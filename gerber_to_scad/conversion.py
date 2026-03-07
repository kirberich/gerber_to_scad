from pygerber.gerberx3.parser2.commands2.arc2 import Arc2, CCArc2
from pygerber.gerberx3.parser2.commands2.flash2 import Flash2
from pygerber.gerberx3.parser2.commands2.line2 import Line2
from pygerber.gerberx3.parser2.commands2.region2 import Region2
from solid import (
    OpenSCADObject,
    linear_extrude,
    mirror,
    offset,
    polygon,
    rotate,
    scad_render,
    translate,
    union,
    utils,
)

from gerber_to_scad.types import Frame, Ledge, Stencil

from . import geometry
from .vector import V


def convert(stencil: Stencil) -> str:
    """Converts a parsed gerber outline and solderpaste files into an OpenSCAD stencil."""
    outline_shape = _outline_shape(stencil)
    cutout_polygon = _create_cutouts(stencil)

    if stencil.gap:
        outline_shape = geometry.offset_shape(outline_shape, stencil.gap)

    # Move the polygons to be centered around the origin
    outline_polygon = polygon([v.as_tuple() for v in outline_shape])

    outline_bounds = geometry.bounding_box(outline_shape)
    outline_offset = outline_bounds[0] + (outline_bounds[2] - outline_bounds[0]) / 2
    centered_outline_polygon = translate((-outline_offset[0], -outline_offset[1], 0))(
        outline_polygon
    )
    cutout_polygon = translate((-outline_offset[0], -outline_offset[1], 0))(
        cutout_polygon
    )

    if stencil.flip_stencil:
        mirror_normal = (-1, 0, 0)
        centered_outline_polygon = mirror(mirror_normal)(centered_outline_polygon)
        cutout_polygon = mirror(mirror_normal)(cutout_polygon)

    scad_stencil = linear_extrude(height=stencil.thickness)(
        centered_outline_polygon - cutout_polygon
    )

    match stencil.alignment_aid:
        case Ledge():
            ledge_polygon = _create_ledge(stencil, outline_shape)
            scad_ledge = translate((-outline_offset[0], -outline_offset[1], 0))(
                utils.down(stencil.alignment_aid.thickness - stencil.thickness)(
                    linear_extrude(height=stencil.alignment_aid.thickness)(
                        ledge_polygon
                    )
                )
            )
            scad_stencil = scad_ledge + scad_stencil
        case Frame():
            frame_shape = geometry.bounding_box(
                outline_shape,
                width=stencil.alignment_aid.width,
                height=stencil.alignment_aid.height,
            )
            frame_polygon = (
                translate((-outline_offset[0], -outline_offset[1], 0))(
                    polygon([v.as_tuple() for v in frame_shape])
                )
                - centered_outline_polygon
            )
            scad_frame = utils.down(
                stencil.alignment_aid.thickness - stencil.thickness
            )(linear_extrude(height=stencil.alignment_aid.thickness)(frame_polygon))
            scad_stencil = scad_frame + scad_stencil
        case None:
            pass

    # Rotate the stencil to make it printable
    scad_stencil = rotate(a=180, v=(1, 0, 0))(scad_stencil)

    return scad_render(scad_stencil)


def _outline_shape(stencil: Stencil) -> list[V]:
    """Extract board outline shape from the parsed outline gerber file.

    Returns the convex hull of all outline points.
    """
    points: list[V] = []

    for command in stencil.outline_file._command_buffer:  # pyright: ignore[reportPrivateUsage]
        if isinstance(command, Line2):
            points.extend(geometry.vertices_from_line_stroke(command))
        elif isinstance(command, (Arc2, CCArc2)):
            points.extend(geometry.vertices_from_arc(command))

    if not points:
        return _outline_shape_from_bounds(stencil)

    return geometry.convex_hull(points)


def _outline_shape_from_bounds(stencil: Stencil) -> list[V]:
    """Fallback: create outline from file bounding box when no line/arc commands exist."""
    bbox = stencil.outline_file._command_buffer.get_bounding_box()  # pyright: ignore[reportPrivateUsage]
    return geometry.vertices_from_bounding_box(bbox)


def _create_cutouts(stencil: Stencil) -> OpenSCADObject:
    """Create cutout polygons from the parsed solderpaste gerber file."""
    polygons: list[OpenSCADObject] = []

    for command in stencil.solderpaste_file._command_buffer:  # pyright: ignore[reportPrivateUsage]
        if isinstance(command, Flash2):
            vertices = geometry.vertices_from_flash(command)
        elif isinstance(command, Line2):
            width = float(command.aperture.get_stroke_width().as_millimeters())
            if width > 0:
                vertices = geometry.vertices_from_line_stroke(command)
            else:
                continue
        elif isinstance(command, Region2):
            vertices = geometry.vertices_from_region(command)
        else:
            continue

        if len(vertices) < 3:
            continue

        shape_polygon = polygon([(v.x, v.y) for v in vertices])
        if stencil.increase_hole_size_by:
            shape_polygon = offset(delta=stencil.increase_hole_size_by)(shape_polygon)
        polygons.append(shape_polygon)

    return union()(*polygons)


def _create_ledge(stencil: Stencil, outline_shape: geometry.Shape) -> OpenSCADObject:
    """Create a polygon for the ledge around the board outline.

    Used to align the stencil with the PCB.
    """
    assert isinstance(stencil.alignment_aid, Ledge)
    # Create an offset version of the outline - this is the outer edge of the ledge
    offset_outline_shape = geometry.offset_shape(list(outline_shape), 1.2)
    offset_outline_polygon = polygon([v.as_tuple() for v in offset_outline_shape])

    # A polygon of the board outline itself - cut out to leave just the ledge
    outline_polygon = polygon([v.as_tuple() for v in outline_shape])

    full_ledge_polygon = offset_outline_polygon - outline_polygon

    if stencil.alignment_aid.is_full_ledge:
        return full_ledge_polygon

    # Cut the ledge in half by taking the bounding box of the outline, cutting it in half
    # and removing the resulting shape from the ledge shape.
    # We always leave the longer side of the ledge intact.
    cutter = geometry.bounding_box(offset_outline_shape)
    height = abs(cutter[1][1] - cutter[0][1])
    width = abs(cutter[0][0] - cutter[3][0])

    if width > height:
        cutter[1].y -= height / 2
        cutter[2].y -= height / 2
    else:
        cutter[2].x -= width / 2
        cutter[3].x -= width / 2

    return full_ledge_polygon - polygon([v.as_tuple() for v in cutter])
