from __future__ import annotations

import math

import pytest

from tileset_testbed.layouts import (
    Anchor,
    ColorOrder,
    HelixStyle,
    grid2d,
    grid3d,
    halton,
    helix,
    lattice,
    sphere,
)
from tileset_testbed.shapes import Shape, make_shape


def test_grid2d() -> None:
    layout = grid2d(colors=2, columns=3, size=1.0, gap=0.5)

    assert layout.total == 6
    assert [len(positions) for positions in layout.positions_by_color] == [3, 3]
    assert layout.grouped is True
    assert layout.default_anchor is Anchor.bottom
    assert layout.origins[0] == (0.0, 0.0, -0.75)
    assert layout.origins[1] == (0.0, 0.0, 0.75)
    assert layout.positions_by_color[0][0] == (-1.5, 0.0, -0.75)
    assert layout.positions_by_color[1][2] == (1.5, 0.0, 0.75)


def test_grid3d() -> None:
    layout = grid3d(colors=2, columns=2, layers=3, size=1.0, gap=0.5)

    assert layout.total == 12
    assert [len(positions) for positions in layout.positions_by_color] == [6, 6]
    assert layout.grouped is True
    assert layout.default_anchor is Anchor.bottom

    ys = [position[1] for position in layout.positions_by_color[0]]
    assert sorted(set(ys)) == [0.0, 1.5, 3.0]


def test_grid3d_stagger() -> None:
    plain = grid3d(2, 2, 2, 1.0, 0.5, stagger=False)
    staggered = grid3d(2, 2, 2, 1.0, 0.5, stagger=True)

    assert plain.positions_by_color[0][0][0] == pytest.approx(-0.75)
    assert staggered.positions_by_color[0][2][0] == pytest.approx(0.0)
    assert staggered.positions_by_color[0][2][2] == pytest.approx(
        plain.positions_by_color[0][2][2] + 0.75
    )


def test_lattice() -> None:
    layout = lattice(colors=3, per_color=4, size=1.0, gap=0.5)

    assert layout.total == 12
    assert [len(positions) for positions in layout.positions_by_color] == [4, 4, 4]
    assert layout.grouped is False
    assert layout.default_anchor is Anchor.bottom
    assert layout.origins == ((0.0, 0.0, 0.0),) * 3


def test_lattice_interleaved() -> None:
    layout = lattice(
        colors=3,
        per_color=2,
        size=1.0,
        gap=0.0,
        color_order=ColorOrder.interleaved,
    )

    assert [len(positions) for positions in layout.positions_by_color] == [2, 2, 2]
    assert layout.positions_by_color[0][0] != layout.positions_by_color[0][1]


def test_sphere() -> None:
    layout = sphere(colors=2, per_color=5, size=1.0, gap=0.5, radius=5.0)

    assert layout.total == 10
    assert [len(positions) for positions in layout.positions_by_color] == [5, 5]
    assert layout.grouped is False
    assert layout.default_anchor is Anchor.center
    for positions in layout.positions_by_color:
        for position in positions:
            assert math.dist(position, (0.0, 0.0, 0.0)) == pytest.approx(5.0)


def test_halton() -> None:
    layout = halton(colors=2, per_color=4, size=1.0, gap=0.5, extent=10.0)

    assert layout.total == 8
    assert [len(positions) for positions in layout.positions_by_color] == [4, 4]
    assert layout.grouped is False
    assert layout.default_anchor is Anchor.center
    for positions in layout.positions_by_color:
        for x, y, z in positions:
            assert -5.0 <= x <= 5.0
            assert 0.0 <= y <= 10.0
            assert -5.0 <= z <= 5.0


def test_helix_outline() -> None:
    layout = helix(
        colors=2,
        per_color=5,
        size=1.0,
        gap=0.5,
        turns=2.0,
        radius=4.0,
        style=HelixStyle.outline,
    )

    assert layout.total == 10
    assert [len(positions) for positions in layout.positions_by_color] == [5, 5]
    assert layout.grouped is False
    assert layout.default_anchor is Anchor.center
    assert dict(layout.params)["style"] == "outline"

    ys = [position[1] for position in layout.positions_by_color[0]]
    assert ys == pytest.approx([0.0, 1.5, 3.0, 4.5, 6.0])
    for positions in layout.positions_by_color:
        for x, _, z in positions:
            assert math.hypot(x, z) == pytest.approx(4.0)


def test_helix_filled_is_compact() -> None:
    layout = helix(colors=2, per_color=50, size=1.0, gap=0.5)

    assert layout.total == 100
    assert [len(positions) for positions in layout.positions_by_color] == [50, 50]
    assert layout.grouped is False
    assert layout.default_anchor is Anchor.center

    params = dict(layout.params)
    assert params["style"] == "filled"
    assert params["per_layer"] == 22
    assert params["layers"] == 5

    ys = {
        round(position[1], 6)
        for positions in layout.positions_by_color
        for position in positions
    }
    assert ys == {0.0, 1.5, 3.0, 4.5, 6.0}

    shape = make_shape(Shape.cube, 1.0)
    minimum, maximum = layout.bounds(shape)
    assert maximum[1] - minimum[1] == pytest.approx(7.0)
    assert maximum[1] - minimum[1] < 10.0

    for positions in layout.positions_by_color:
        for x, _, z in positions:
            assert math.hypot(x, z) <= params["radius"] + 1e-6


def test_helix_filled_per_layer() -> None:
    layout = helix(colors=2, per_color=10, size=1.0, gap=0.5, per_layer=10)
    params = dict(layout.params)

    assert layout.total == 20
    assert params["per_layer"] == 10
    assert params["layers"] == 2
    assert [len(positions) for positions in layout.positions_by_color] == [10, 10]


def test_helix_filled_radius() -> None:
    layout = helix(colors=2, per_color=100, size=1.0, gap=0.5, radius=10.0)
    params = dict(layout.params)

    assert params["per_layer"] == 140
    assert params["layers"] == 2
    assert params["radius"] == 10.0
    for positions in layout.positions_by_color:
        for x, _, z in positions:
            assert math.hypot(x, z) <= 10.0 + 1e-6


def test_helix_rejects_per_layer_and_radius() -> None:
    with pytest.raises(ValueError):
        helix(colors=2, per_color=10, size=1.0, gap=0.5, per_layer=5, radius=10.0)


def test_layout_bounds_and_translation() -> None:
    layout = grid2d(colors=2, columns=2, size=1.0, gap=0.0)
    shape = make_shape(Shape.cube, 1.0)

    minimum, maximum = layout.bounds(shape)
    assert minimum == pytest.approx((-1.0, 0.0, -1.0))
    assert maximum == pytest.approx((1.0, 1.0, 1.0))

    translated = layout.translated((0.0, 2.0, 0.0))
    minimum, maximum = translated.bounds(shape)
    assert minimum == pytest.approx((-1.0, 2.0, -1.0))
    assert maximum == pytest.approx((1.0, 3.0, 1.0))
    assert translated.origins == layout.origins


def test_relative_by_color_for_grid() -> None:
    layout = grid2d(colors=2, columns=2, size=1.0, gap=0.0)
    relatives = layout.relative_by_color()

    assert relatives[0] == relatives[1]
    assert relatives[0] == (
        (-0.5, 0.0, 0.0),
        (0.5, 0.0, 0.0),
    )
