# Basic vector maths class
import math


class V(object):
    def __init__(self, x: float = 0, y: float = 0):
        self.x = float(x)
        self.y = float(y)

    def __unicode__(self):
        return "(%s, %s)" % (self.x, self.y)

    __repr__ = __unicode__

    @classmethod
    def from_tuple(cls, coordinates):
        x, y = coordinates
        return V(x, y)

    def as_tuple(self):
        return (self.x, self.y)

    def __getitem__(self, index):
        if index == 0:
            return self.x
        if index == 1:
            return self.y
        raise IndexError("Vectors are two-dimensional!")

    @classmethod
    def intersection(cls, o1, d1, o2, d2):
        """Find intersection of two vectors, if any"""
        try:
            l2 = ((o2.x - o1.x) * d1.y / d1.x - o2.y + o1.y) / (
                d2.y - d2.x * d1.y / d1.x
            )
            return o2 + d2 * l2
        except ZeroDivisionError:
            return None

    @classmethod
    def point_line_projection(cls, v1, v2, p, limit_to_segment=False):
        """Returns the projection of the point p on the line defined
        by the two endpoints v1 and v2
        """
        d = v2 - v1
        l2 = d.abs_sq()

        # If v1 and v2 are equal, simply return v1 (the line direction is undefined)
        if l2 == 0:
            return v1

        # Get the projection factor
        a = ((p - v1) * d) / l2

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

    def consume_tuple(self, other):
        if isinstance(other, tuple) or isinstance(other, list):
            return V(other[0], other[1])
        return other

    def cross(self, other):
        """cross product"""
        return V(self.x * other.y - other.x * self.y)

    def rotate(self, theta, as_degrees=False):
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

    def __cmp__(self, other):
        other = self.consume_tuple(other)
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

    def __add__(self, other):
        other = self.consume_tuple(other)
        return V(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        other = self.consume_tuple(other)
        return V(self.x - other.x, self.y - other.y)

    def __mul__(self, other):
        other = self.consume_tuple(other)
        if isinstance(other, V):
            return self.x * other.x + self.y * other.y
        return V(other * self.x, other * self.y)

    def __div__(self, other):
        if not other:
            raise Exception("Division by zero")
        other = float(other)
        return V(self.x / other, self.y / other)

    def __eq__(self, other: "V") -> bool:
        return self.x == other.x and self.y == other.y

    __truediv__ = __div__
