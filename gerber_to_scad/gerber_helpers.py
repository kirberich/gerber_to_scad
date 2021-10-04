"""Helpers for dealing with gerber files."""


def get_aperture_size(aperture):
    diameter = getattr(aperture, "diameter", 0)
    width = getattr(aperture, "width", 0)
    height = getattr(aperture, "height", 0)

    return diameter or width or height


def has_wide_aperture(aperture):
    """Returns True if an aperture has a non-zero size, False otherwise."""
    if get_aperture_size(aperture):
        return True
    return False
