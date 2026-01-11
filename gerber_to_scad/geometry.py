"""Geometry helpers for gerber_to_scad _shapes_, as opposed to OpenSCAD objects.

Once a shape is turned into an openscad object, we cannot introspect the object anymore, so any operations that require
concrete numbers for size, convex hull etc, have to happen on shapes before turning them into openscad objects.

"""

from collections.abc import Sequence

from scipy.spatial import ConvexHull
from solid import utils

from .vector import V

Rect = tuple[V, V, V, V]
Shape = Sequence[V]


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

    # import matplotlib.pyplot as plt

    # print(hull.vertices)
    # x = [hull.points[pair[1]][0] for pair in hull.vertices]
    # y = [hull.points[pair[1]][1] for pair in hull.vertices]
    # plt.plot(x, y)
    # plt.show()
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
