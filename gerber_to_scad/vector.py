# Basic vector maths class
from __future__ import annotations

import math

from typing_extensions import override


class V(object):
    def __init__(self, x: float = 0, y: float = 0):
        self.x = float(x)
        self.y = float(y)

    def __unicode__(self):
        return "(%s, %s)" % (self.x, self.y)

    __repr__ = __unicode__

    @classmethod
    def from_tuple(cls, coordinates: tuple[float, float]):
        x, y = coordinates
        return V(x, y)

    def as_tuple(self):
        return (self.x, self.y)

    def __getitem__(self, index: int):
        if index == 0:
            return self.x
        if index == 1:
            return self.y
        raise IndexError("Vectors are two-dimensional!")

    @classmethod
    def intersection(cls, o1: V, d1: V, o2: V, d2: V):
        """Find intersection of two vectors, if any"""
        try:
            l2 = ((o2.x - o1.x) * d1.y / d1.x - o2.y + o1.y) / (
                d2.y - d2.x * d1.y / d1.x
            )
            return o2 + d2 * l2
        except ZeroDivisionError:
            return None

    @classmethod
    def point_line_projection(cls, v1: V, v2: V, p: V, limit_to_segment: bool = False):
        """Returns the projection of the point p on the line defined
        by the two endpoints v1 and v2
        """
        d = v2 - v1
        l2 = d.abs_sq()

        # If v1 and v2 are equal, simply return v1 (the line direction is undefined)
        if l2 == 0:
            return v1

        # Get the projection factor
        a = ((p - v1).dot(d)) / l2

        # Limit the projection to be limited to stay between v1 and v2, if requested
        if limit_to_segment:
            if a < 0:
                return v1
            if a > 1:
                return v2

        return v1 + d * a

    def abs_sq(self):
        """Square of absolute value of vector self"""
        return abs(self.x * self.x + self.y * self.y)

    def dot(self, other: V):
        return self.x * other.x + self.y * other.y

    def cross(self, other: V):
        """cross product"""
        return V(self.x * other.y - other.x * self.y)

    def rotate(self, theta: float, as_degrees: bool = False):
        """Adapted from https://gist.github.com/mcleonard/5351452.
        Rotate this vector by theta in degrees.
        """
        if as_degrees:
            theta = math.radians(theta)

        dc, ds = math.cos(theta), math.sin(theta)
        x, y = dc * self.x - ds * self.y, ds * self.x + dc * self.y
        return V(x, y)

    def __abs__(self):
        return math.sqrt(self.abs_sq())

    def __cmp__(self, other: object):
        if not isinstance(other, V):
            return False
        if self.x == other.x and self.y == other.y:
            return 0
        if abs(self) < abs(other):
            return -1
        return 1

    def __nonzero__(self):
        if self.x or self.y:
            return True
        return False

    def __neg__(self):
        return V(-self.x, -self.y)

    def __add__(self, other: V):
        return V(self.x + other.x, self.y + other.y)

    def __sub__(self, other: V):
        return V(self.x - other.x, self.y - other.y)

    def __mul__(self, other: float) -> V:
        """Dot product"""
        return V(other * self.x, other * self.y)

    def __div__(self, other: float):
        return V(self.x / other, self.y / other)

    @override
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, "V"):
            return False
        return self.x == other.x and self.y == other.y

    __truediv__ = __div__
