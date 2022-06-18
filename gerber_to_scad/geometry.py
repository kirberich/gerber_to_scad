"""Geometry helpers"""
from scipy.spatial import ConvexHull
from .vector import V
from typing import Tuple, List


def bounding_box(shape) -> Tuple[V, V, V, V]:
    min_x = min(shape, key=lambda v: v[0])[0]
    max_x = max(shape, key=lambda v: v[0])[0]
    min_y = min(shape, key=lambda v: v[1])[1]
    max_y = max(shape, key=lambda v: v[1])[1]
    return (V(min_x, min_y), V(min_x, max_y), V(max_x, max_y), V(max_x, min_y))


def convex_hull(points: List[V]) -> List[V]:
    hull = ConvexHull([v.as_tuple() for v in points])

    # import matplotlib.pyplot as plt

    # print(hull.vertices)
    # x = [hull.points[pair[1]][0] for pair in hull.vertices]
    # y = [hull.points[pair[1]][1] for pair in hull.vertices]
    # plt.plot(x, y)
    # plt.show()
    hull_points = [hull.points[vertex_index] for vertex_index in hull.vertices]

    return [V(float(x), float(y)) for x, y in hull_points]
