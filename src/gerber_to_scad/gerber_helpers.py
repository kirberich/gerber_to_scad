"""Helpers for dealing with gerber files."""

from __future__ import annotations


def get_aperture_size(aperture) -> int:
    diameter = getattr(aperture, "diameter", 0)
    width = getattr(aperture, "width", 0)
    height = getattr(aperture, "height", 0)

    return diameter or width or height


def has_wide_aperture(aperture, length) -> bool:
    """
    Returns True if an aperture is large compared to a given line length,

    or, if no line length is given, if it's non-zero.
    """
    aperture_size = get_aperture_size(aperture)

    # A zero-size aperture is never considered wide
    if not aperture_size:
        return False

    # If the aperture is more than a 10th of the length of the object, consider it wide
    if aperture_size and length:
        return aperture_size > length / 10

    return True
