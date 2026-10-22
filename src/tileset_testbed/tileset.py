"""3D Tiles 1.1 tileset JSON generation."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

Point = tuple[float, float, float]


def bounds_to_box(minimum: Point, maximum: Point) -> tuple[list[float], float]:
    """Convert a glTF Y-up AABB to a 3D Tiles Z-up box and radius."""
    # glTF (x, y, z) -> tile (x, -z, y)
    tile_min = (minimum[0], -maximum[2], minimum[1])
    tile_max = (maximum[0], -minimum[2], maximum[1])

    center = tuple((tile_min[i] + tile_max[i]) / 2.0 for i in range(3))
    half = tuple((tile_max[i] - tile_min[i]) / 2.0 for i in range(3))

    box = [
        center[0],
        center[1],
        center[2],
        half[0],
        0.0,
        0.0,
        0.0,
        half[1],
        0.0,
        0.0,
        0.0,
        half[2],
    ]
    radius = math.sqrt(half[0] ** 2 + half[1] ** 2 + half[2] ** 2)
    return box, radius


def make_tileset(box: list[float], radius: float) -> dict[str, Any]:
    return {
        "asset": {"version": "1.1", "generator": "tileset-testbed 0.1.0"},
        # The tileset contains a single root tile, so the root is a leaf (0)
        # and the tileset error is its bounding-sphere radius.
        "geometricError": radius,
        "root": {
            "boundingVolume": {"box": box},
            "geometricError": 0.0,
            "refine": "ADD",
            "content": {"uri": "content.glb"},
        },
    }


def write_tileset(path: Path, box: list[float], radius: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(make_tileset(box, radius), indent=2) + "\n"
    path.write_text(text, encoding="utf-8")
