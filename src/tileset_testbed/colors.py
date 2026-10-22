"""Color palette generation.

HSV hue values are converted to sRGB with full saturation/value, then to
linear RGB because glTF ``baseColorFactor`` and metadata colors are linear.
"""

from __future__ import annotations

import colorsys

RGBA = tuple[float, float, float, float]


def srgb_to_linear(value: float) -> float:
    """Convert one sRGB channel in [0, 1] to linear RGB."""
    if value <= 0.04045:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def hue_to_linear_rgba(hue: float) -> RGBA:
    """Convert an HSV hue (s=1, v=1) to a linear RGBA color."""
    red, green, blue = colorsys.hsv_to_rgb(hue % 1.0, 1.0, 1.0)
    return (
        srgb_to_linear(red),
        srgb_to_linear(green),
        srgb_to_linear(blue),
        1.0,
    )


def make_palette(colors: int) -> list[RGBA]:
    """Return ``colors`` evenly-spaced hues, starting at red (hue 0)."""
    if colors < 1:
        raise ValueError("colors must be >= 1")
    return [hue_to_linear_rgba(index / colors) for index in range(colors)]
