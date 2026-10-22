from __future__ import annotations

import pytest

from tileset_testbed.shapes import Shape, make_shape

Point = tuple[float, float, float]
SHAPES = list(Shape)


def _cross(a: Point, b: Point) -> Point:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _subtract(a: Point, b: Point) -> Point:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a: Point, b: Point) -> float:
    return sum(a[index] * b[index] for index in range(3))


@pytest.mark.parametrize("shape", SHAPES)
def test_shape_bounds_and_indices(shape: Shape) -> None:
    mesh = make_shape(shape, 1.0)
    minimum, maximum = mesh.bounds()

    assert minimum[1] == pytest.approx(0.0, abs=1e-6)
    assert (minimum[0] + maximum[0]) / 2.0 == pytest.approx(0.0, abs=1e-6)
    assert (minimum[2] + maximum[2]) / 2.0 == pytest.approx(0.0, abs=1e-6)
    assert mesh.max_extent() == pytest.approx(1.0, rel=1e-6)

    assert len(mesh.positions) == len(mesh.normals)
    assert len(mesh.indices) % 3 == 0
    assert all(0 <= index < len(mesh.positions) for index in mesh.indices)


@pytest.mark.parametrize("shape", SHAPES)
def test_shape_winding_faces_outward(shape: Shape) -> None:
    mesh = make_shape(shape, 1.0)

    for index in range(0, len(mesh.indices), 3):
        a = mesh.positions[mesh.indices[index]]
        b = mesh.positions[mesh.indices[index + 1]]
        c = mesh.positions[mesh.indices[index + 2]]
        geometric = _cross(_subtract(b, a), _subtract(c, a))
        normal = mesh.normals[mesh.indices[index]]
        assert _dot(geometric, normal) > 0.0, (
            f"{shape.value} triangle {index // 3} is wound inward"
        )


def test_scaling_preserves_normals() -> None:
    unit = make_shape(Shape.sphere, 1.0)
    scaled = make_shape(Shape.sphere, 2.0)

    assert scaled.max_extent() == pytest.approx(2.0)
    assert scaled.normals == unit.normals
    assert len(scaled.positions) == len(unit.positions)


def test_translated_x_repeats_the_mesh() -> None:
    mesh = make_shape(Shape.cube, 1.0)
    group = mesh.translated_x([-2.0, 2.0])

    assert len(group.positions) == 2 * len(mesh.positions)
    assert len(group.indices) == 2 * len(mesh.indices)

    minimum, maximum = group.bounds()
    assert minimum[0] == pytest.approx(-2.5)
    assert maximum[0] == pytest.approx(2.5)


def test_monkey_asset() -> None:
    mesh = make_shape(Shape.monkey, 1.0)
    assert len(mesh.positions) > 0
    assert len(mesh.indices) > 0


def test_invalid_shape() -> None:
    with pytest.raises(ValueError):
        make_shape("not-a-shape", 1.0)


def test_invalid_size() -> None:
    with pytest.raises(ValueError):
        make_shape(Shape.cube, 0.0)


def test_translated_xyz_repeats_the_mesh() -> None:
    mesh = make_shape(Shape.cube, 1.0)
    group = mesh.translated_xyz([(0.0, 1.0, 0.0), (2.0, 1.0, 0.0)])

    assert len(group.positions) == 2 * len(mesh.positions)
    assert len(group.indices) == 2 * len(mesh.indices)
    minimum, maximum = group.bounds()
    assert minimum == pytest.approx((-0.5, 1.0, -0.5))
    assert maximum == pytest.approx((2.5, 2.0, 0.5))
