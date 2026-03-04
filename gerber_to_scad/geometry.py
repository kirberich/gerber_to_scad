"""Geometry helpers for gerber_to_scad _shapes_, as opposed to OpenSCAD objects.

Once a shape is turned into an openscad object, we cannot introspect the object anymore, so any operations that require
concrete numbers for size, convex hull etc, have to happen on shapes before turning them into openscad objects.

"""

import math
from collections.abc import Sequence

from pygerber.gerberx3.math.bounding_box import BoundingBox
from pygerber.gerberx3.parser2.apertures2.circle2 import Circle2
from pygerber.gerberx3.parser2.apertures2.macro2 import Macro2
from pygerber.gerberx3.parser2.apertures2.obround2 import Obround2
from pygerber.gerberx3.parser2.apertures2.polygon2 import Polygon2
from pygerber.gerberx3.parser2.apertures2.rectangle2 import Rectangle2
from pygerber.gerberx3.parser2.commands2.arc2 import Arc2, CCArc2
from pygerber.gerberx3.parser2.commands2.flash2 import Flash2
from pygerber.gerberx3.parser2.commands2.line2 import Line2
from pygerber.gerberx3.parser2.commands2.region2 import Region2
from scipy.spatial import ConvexHull
from solid import utils

from .vector import V

Rect = tuple[V, V, V, V]
Shape = Sequence[V]

MAX_SEGMENT_LENGTH = 0.2


def bounding_box(
    shape: Sequence[V], width: float = 0, height: float = 0, margin: float = 0
) -> Rect:
    min_x = min(shape, key=lambda v: v[0])[0]
    max_x = max(shape, key=lambda v: v[0])[0]
    min_y = min(shape, key=lambda v: v[1])[1]
    max_y = max(shape, key=lambda v: v[1])[1]
    if (float(width or 0) > 0 and float(height or 0) > 0) or float(margin or 0) > 0:
        if margin > 0:
            margin_x = margin
            margin_y = margin
        else:
            margin_x = (width - (max_x - min_x)) / 2
            margin_y = (height - (max_y - min_y)) / 2
        return (
            V(min_x - margin_x, min_y - margin_y),
            V(min_x - margin_x, max_y + margin_y),
            V(max_x + margin_x, max_y + margin_y),
            V(max_x + margin_x, min_y - margin_y),
        )
    return (V(min_x, min_y), V(min_x, max_y), V(max_x, max_y), V(max_x, min_y))


def convex_hull(points: list[V]) -> list[V]:
    hull = ConvexHull([v.as_tuple() for v in points])
    hull_points = [hull.points[vertex_index] for vertex_index in hull.vertices]
    return [V(float(x), float(y)) for x, y in hull_points]


def offset_shape(shape: Sequence[V], offset: float) -> list[V]:
    """Offset a shape by <offset> mm."""

    return [
        V(p[0], p[1])
        for p in utils.offset_points(
            [p.as_tuple() for p in shape],  # type: ignore
            abs(offset),
            internal=offset < 0,  # type: ignore
        )
    ]


def _vertices_from_circle(cx: float, cy: float, diameter: float) -> list[V]:
    """Rasterize a circle into polygon vertices."""
    circ = math.pi * diameter
    num_segments = max(8, int(round(circ / MAX_SEGMENT_LENGTH)))
    points: list[V] = []
    for i in range(num_segments):
        angle = i * (2 * math.pi / num_segments)
        x = cx + math.cos(angle) * diameter / 2
        y = cy + math.sin(angle) * diameter / 2
        points.append(V(round(x, 3), round(y, 3)))
    return points


def _vertices_from_rect(
    cx: float, cy: float, width: float, height: float, rotation_deg: float = 0
) -> list[V]:
    """Create rectangle vertices centered at (cx, cy) with optional rotation."""
    hw = width / 2
    hh = height / 2
    corners = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]

    if rotation_deg:
        angle = math.radians(rotation_deg)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        rotated = []
        for x, y in corners:
            rx = x * cos_a - y * sin_a
            ry = x * sin_a + y * cos_a
            rotated.append((rx, ry))
        corners = rotated

    return [V(round(cx + x, 3), round(cy + y, 3)) for x, y in corners]


def _vertices_from_obround(cx: float, cy: float, obround: Obround2) -> list[V]:
    """Create obround (stadium) vertices centered at (cx, cy).

    An obround is a rectangle with semicircular ends on the shorter sides.
    """
    width = float(obround.x_size.as_millimeters())
    height = float(obround.y_size.as_millimeters())
    rotation_deg = float(obround.rotation)

    points: list[tuple[float, float]] = []
    if width > height:
        # Semicircles on left and right
        r = height / 2
        rect_half_w = (width - height) / 2
        # Right semicircle
        num_arc = max(4, int(round(math.pi * r / MAX_SEGMENT_LENGTH)))
        for i in range(num_arc + 1):
            angle = -math.pi / 2 + i * math.pi / num_arc
            points.append((rect_half_w + r * math.cos(angle), r * math.sin(angle)))
        # Left semicircle
        for i in range(num_arc + 1):
            angle = math.pi / 2 + i * math.pi / num_arc
            points.append((-rect_half_w + r * math.cos(angle), r * math.sin(angle)))
    else:
        # Semicircles on top and bottom
        r = width / 2
        rect_half_h = (height - width) / 2
        # Top semicircle
        num_arc = max(4, int(round(math.pi * r / MAX_SEGMENT_LENGTH)))
        for i in range(num_arc + 1):
            angle = i * math.pi / num_arc
            points.append((r * math.cos(angle), rect_half_h + r * math.sin(angle)))
        # Bottom semicircle
        for i in range(num_arc + 1):
            angle = math.pi + i * math.pi / num_arc
            points.append((r * math.cos(angle), -rect_half_h + r * math.sin(angle)))

    if rotation_deg:
        angle = math.radians(rotation_deg)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        points = [(x * cos_a - y * sin_a, x * sin_a + y * cos_a) for x, y in points]

    return [V(round(cx + x, 3), round(cy + y, 3)) for x, y in points]


def _vertices_from_polygon(cx: float, cy: float, polygon: Polygon2) -> list[V]:
    """Create regular polygon vertices."""
    outer_diameter = float(polygon.outer_diameter.as_millimeters())
    num_vertices = polygon.number_vertices
    rotation_deg = float(polygon.rotation)

    r = outer_diameter / 2
    offset_angle = math.radians(rotation_deg)
    points: list[V] = []
    for i in range(num_vertices):
        angle = offset_angle + i * (2 * math.pi / num_vertices)
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        points.append(V(round(x, 3), round(y, 3)))
    return points


def vertices_from_line_stroke(line: Line2) -> list[V]:
    """Create a rectangle from a Line2 command using its aperture stroke width."""
    start_x = float(line.start_point.x.as_millimeters())
    start_y = float(line.start_point.y.as_millimeters())
    end_x = float(line.end_point.x.as_millimeters())
    end_y = float(line.end_point.y.as_millimeters())
    width = float(line.aperture.get_stroke_width().as_millimeters())

    start_v = V(start_x, start_y)
    end_v = V(end_x, end_y)
    dir_v = end_v - start_v
    abs_dir_v = abs(dir_v)
    if abs_dir_v:
        dir_v = dir_v / abs_dir_v
    else:
        dir_v = V(0, 0)

    half_w = width / 2
    perp = dir_v.rotate(90, as_degrees=True) * half_w

    return [
        V(round((start_v + perp).x, 3), round((start_v + perp).y, 3)),
        V(round((end_v + perp).x, 3), round((end_v + perp).y, 3)),
        V(round((end_v - perp).x, 3), round((end_v - perp).y, 3)),
        V(round((start_v - perp).x, 3), round((start_v - perp).y, 3)),
    ]


def vertices_from_bounding_box(bbox: BoundingBox):
    min_x = float(bbox.min_x.as_millimeters())
    min_y = float(bbox.min_y.as_millimeters())
    max_x = float(bbox.max_x.as_millimeters())
    max_y = float(bbox.max_y.as_millimeters())
    return [
        V(min_x, min_y),
        V(min_x, max_y),
        V(max_x, max_y),
        V(max_x, min_y),
    ]


def vertices_from_line(command: Line2) -> list[V]:
    """Extract start and end points from a Line2 command."""
    return [
        V(
            round(float(command.start_point.x.as_millimeters()), 3),
            round(float(command.start_point.y.as_millimeters()), 3),
        ),
        V(
            round(float(command.end_point.x.as_millimeters()), 3),
            round(float(command.end_point.y.as_millimeters()), 3),
        ),
    ]


def vertices_from_arc(command: Arc2 | CCArc2) -> list[V]:
    """Rasterize an Arc2/CCArc2 command into vertices."""

    start_x = float(command.start_point.x.as_millimeters())
    start_y = float(command.start_point.y.as_millimeters())
    end_x = float(command.end_point.x.as_millimeters())
    end_y = float(command.end_point.y.as_millimeters())
    center_x = float(command.center_point.x.as_millimeters())
    center_y = float(command.center_point.y.as_millimeters())
    clockwise = not isinstance(command, CCArc2)

    """Rasterize an arc into line segments."""
    radius = math.sqrt((start_x - center_x) ** 2 + (start_y - center_y) ** 2)
    if radius == 0:
        return []

    start_angle = math.atan2(start_y - center_y, start_x - center_x)
    end_angle = math.atan2(end_y - center_y, end_x - center_x)

    if clockwise:
        if end_angle >= start_angle:
            end_angle -= 2 * math.pi
        sweep = start_angle - end_angle
    else:
        if end_angle <= start_angle:
            end_angle += 2 * math.pi
        sweep = end_angle - start_angle

    arc_length = radius * abs(sweep)
    num_segments = max(1, int(round(arc_length / MAX_SEGMENT_LENGTH)))

    points: list[V] = []
    for i in range(num_segments + 1):
        t = i / num_segments
        if clockwise:
            angle = start_angle - t * sweep
        else:
            angle = start_angle + t * sweep
        x = center_x + math.cos(angle) * radius
        y = center_y + math.sin(angle) * radius
        points.append(V(round(x, 3), round(y, 3)))

    return points


def vertices_from_region(command: Region2) -> list[V]:
    """Extract all vertices from a Region2 command's sub-commands."""
    points: list[V] = []
    for sub_cmd in command.command_buffer:
        if isinstance(sub_cmd, Line2):
            points.append(
                V(
                    round(float(sub_cmd.start_point.x.as_millimeters()), 3),
                    round(float(sub_cmd.start_point.y.as_millimeters()), 3),
                )
            )
        elif isinstance(sub_cmd, (Arc2, CCArc2)):
            points.extend(vertices_from_arc(sub_cmd))
    return points


def vertices_from_flash(command: Flash2) -> list[V]:
    """Convert a Flash2 command to polygon vertices based on its aperture type."""
    x = float(command.flash_point.x.as_millimeters())
    y = float(command.flash_point.y.as_millimeters())
    aperture = command.aperture

    if isinstance(aperture, Circle2):
        return _vertices_from_circle(x, y, float(aperture.diameter.as_millimeters()))
    elif isinstance(aperture, Obround2):
        # Obround extends Rectangle2, so check it first
        return _vertices_from_obround(x, y, aperture)
    elif isinstance(aperture, Rectangle2):
        return _vertices_from_rect(
            x,
            y,
            float(aperture.x_size.as_millimeters()),
            float(aperture.y_size.as_millimeters()),
            float(aperture.rotation),
        )
    elif isinstance(aperture, Polygon2):
        return _vertices_from_polygon(x, y, aperture)
    elif isinstance(aperture, Macro2):
        # For macro apertures, get bounding box and use that as a rectangle
        bbox = command.get_bounding_box()
        min_x = float(bbox.min_x.as_millimeters())
        min_y = float(bbox.min_y.as_millimeters())
        max_x = float(bbox.max_x.as_millimeters())
        max_y = float(bbox.max_y.as_millimeters())
        return [
            V(round(min_x, 3), round(min_y, 3)),
            V(round(max_x, 3), round(min_y, 3)),
            V(round(max_x, 3), round(max_y, 3)),
            V(round(min_x, 3), round(max_y, 3)),
        ]
    else:
        print(f"Warning: unsupported aperture type {type(aperture).__name__}, skipping")
        return []
