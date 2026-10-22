import math

import pytest

from tileset_testbed.tileset import bounds_to_box, make_tileset


def test_bounds_to_box_maps_y_up_to_z_up() -> None:
    box, radius = bounds_to_box((-1.0, 0.0, -2.0), (3.0, 4.0, 2.0))

    assert box == pytest.approx(
        [1.0, 0.0, 2.0, 2.0, 0.0, 0.0, 0.0, 2.0, 0.0, 0.0, 0.0, 2.0]
    )
    assert radius == pytest.approx(math.sqrt(12.0))


def test_tileset_json() -> None:
    box = [0.0, 0.0, 0.5, 1.25, 0.0, 0.0, 0.0, 2.0, 0.0, 0.0, 0.0, 0.5]
    tileset = make_tileset(box, 2.0)

    assert tileset["asset"]["version"] == "1.1"
    assert tileset["root"]["content"]["uri"] == "content.glb"
    assert tileset["root"]["refine"] == "ADD"
    assert tileset["root"]["geometricError"] == pytest.approx(0.0)
    assert tileset["root"]["boundingVolume"]["box"] == box
    assert tileset["geometricError"] == pytest.approx(2.0)
