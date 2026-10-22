"""Procedural and asset-backed shape meshes.

Every shape is normalized to a bounding box whose largest dimension equals
``size``, centered on the X/Z axes with its lowest point at ``Y = 0``.  That
keeps the grid layout and the tileset bounds identical for every shape.
"""

from __future__ import annotations

import math
import struct
from enum import Enum
from functools import lru_cache
from importlib import resources

from .mesh import Mesh, Point


class Shape(str, Enum):
    cube = "cube"
    sphere = "sphere"
    monkey = "monkey"
    cylinder = "cylinder"
    cone = "cone"
    torus = "torus"


MONKEY_MAGIC = b"SHP1"


def make_shape(shape: Shape | str, size: float) -> Mesh:
    if size <= 0.0:
        raise ValueError("size must be > 0")
    if not isinstance(shape, Shape):
        shape = Shape(shape)

    builders = {
        Shape.cube: cube_mesh,
        Shape.sphere: sphere_mesh,
        Shape.monkey: monkey_mesh,
        Shape.cylinder: cylinder_mesh,
        Shape.cone: cone_mesh,
        Shape.torus: torus_mesh,
    }
    return builders[shape](size)


def _mesh_from_faces(faces: list[tuple[Point, list[Point]]]) -> Mesh:
    positions: list[Point] = []
    normals: list[Point] = []
    indices: list[int] = []
    for normal, quad in faces:
        base = len(positions)
        positions.extend(quad)
        normals.extend([normal, normal, normal, normal])
        indices.extend((base, base + 1, base + 2, base, base + 2, base + 3))
    return Mesh(tuple(positions), tuple(normals), tuple(indices))


def cube_mesh(size: float) -> Mesh:
    half = size / 2.0
    y0, y1 = 0.0, size
    x0, x1 = -half, half
    z0, z1 = -half, half

    p000 = (x0, y0, z0)
    p001 = (x0, y0, z1)
    p010 = (x0, y1, z0)
    p011 = (x0, y1, z1)
    p100 = (x1, y0, z0)
    p101 = (x1, y0, z1)
    p110 = (x1, y1, z0)
    p111 = (x1, y1, z1)

    return _mesh_from_faces(
        [
            ((1.0, 0.0, 0.0), [p100, p110, p111, p101]),
            ((-1.0, 0.0, 0.0), [p000, p001, p011, p010]),
            ((0.0, 1.0, 0.0), [p010, p011, p111, p110]),
            ((0.0, -1.0, 0.0), [p000, p100, p101, p001]),
            ((0.0, 0.0, 1.0), [p001, p101, p111, p011]),
            ((0.0, 0.0, -1.0), [p000, p010, p110, p100]),
        ]
    )


def sphere_mesh(size: float, segments: int = 32, rings: int = 16) -> Mesh:
    if segments < 3:
        raise ValueError("segments must be >= 3")
    if rings < 2:
        raise ValueError("rings must be >= 2")

    radius = size / 2.0
    center_y = size / 2.0

    positions: list[Point] = [(0.0, size, 0.0)]
    normals: list[Point] = [(0.0, 1.0, 0.0)]

    for ring in range(1, rings):
        phi = math.pi * ring / rings
        sin_phi = math.sin(phi)
        cos_phi = math.cos(phi)
        y = center_y + radius * cos_phi
        ring_radius = radius * sin_phi
        for segment in range(segments):
            theta = 2.0 * math.pi * segment / segments
            cos_theta = math.cos(theta)
            sin_theta = math.sin(theta)
            positions.append((ring_radius * cos_theta, y, ring_radius * sin_theta))
            normals.append((sin_phi * cos_theta, cos_phi, sin_phi * sin_theta))

    bottom = len(positions)
    positions.append((0.0, 0.0, 0.0))
    normals.append((0.0, -1.0, 0.0))

    indices: list[int] = []
    top = 0
    first_ring = 1

    for segment in range(segments):
        current = first_ring + segment
        following = first_ring + (segment + 1) % segments
        indices.extend((top, following, current))

    for ring in range(rings - 2):
        upper = first_ring + ring * segments
        lower = first_ring + (ring + 1) * segments
        for segment in range(segments):
            a = upper + segment
            d = upper + (segment + 1) % segments
            b = lower + segment
            c = lower + (segment + 1) % segments
            indices.extend((a, c, b, a, d, c))

    last_ring = first_ring + (rings - 2) * segments
    for segment in range(segments):
        current = last_ring + segment
        following = last_ring + (segment + 1) % segments
        indices.extend((bottom, current, following))

    return Mesh(tuple(positions), tuple(normals), tuple(indices))


def cylinder_mesh(size: float, segments: int = 32) -> Mesh:
    if segments < 3:
        raise ValueError("segments must be >= 3")

    radius = size / 2.0
    positions: list[Point] = []
    normals: list[Point] = []

    for segment in range(segments):
        theta = 2.0 * math.pi * segment / segments
        cos_theta = math.cos(theta)
        sin_theta = math.sin(theta)
        positions.append((radius * cos_theta, 0.0, radius * sin_theta))
        normals.append((cos_theta, 0.0, sin_theta))

    for segment in range(segments):
        theta = 2.0 * math.pi * segment / segments
        cos_theta = math.cos(theta)
        sin_theta = math.sin(theta)
        positions.append((radius * cos_theta, size, radius * sin_theta))
        normals.append((cos_theta, 0.0, sin_theta))

    for segment in range(segments):
        theta = 2.0 * math.pi * segment / segments
        positions.append((radius * math.cos(theta), 0.0, radius * math.sin(theta)))
        normals.append((0.0, -1.0, 0.0))

    for segment in range(segments):
        theta = 2.0 * math.pi * segment / segments
        positions.append((radius * math.cos(theta), size, radius * math.sin(theta)))
        normals.append((0.0, 1.0, 0.0))

    bottom_center = len(positions)
    positions.append((0.0, 0.0, 0.0))
    normals.append((0.0, -1.0, 0.0))
    top_center = len(positions)
    positions.append((0.0, size, 0.0))
    normals.append((0.0, 1.0, 0.0))

    indices: list[int] = []
    top_side = segments
    bottom_cap = 2 * segments
    top_cap = 3 * segments

    for segment in range(segments):
        following = (segment + 1) % segments
        a = segment
        b = following
        d = top_side + segment
        c = top_side + following
        indices.extend((a, c, b, a, d, c))

    for segment in range(segments):
        following = (segment + 1) % segments
        a = bottom_cap + segment
        b = bottom_cap + following
        indices.extend((bottom_center, a, b))

    for segment in range(segments):
        following = (segment + 1) % segments
        a = top_cap + segment
        b = top_cap + following
        indices.extend((top_center, b, a))

    return Mesh(tuple(positions), tuple(normals), tuple(indices))


def cone_mesh(size: float, segments: int = 32) -> Mesh:
    if segments < 3:
        raise ValueError("segments must be >= 3")

    radius = size / 2.0
    height = size
    normal_length = math.hypot(height, radius)

    positions: list[Point] = []
    normals: list[Point] = []

    for segment in range(segments):
        theta = 2.0 * math.pi * segment / segments
        cos_theta = math.cos(theta)
        sin_theta = math.sin(theta)
        positions.append((radius * cos_theta, 0.0, radius * sin_theta))
        normals.append(
            (
                height * cos_theta / normal_length,
                radius / normal_length,
                height * sin_theta / normal_length,
            )
        )

    for segment in range(segments):
        theta = 2.0 * math.pi * (segment + 0.5) / segments
        cos_theta = math.cos(theta)
        sin_theta = math.sin(theta)
        positions.append((0.0, height, 0.0))
        normals.append(
            (
                height * cos_theta / normal_length,
                radius / normal_length,
                height * sin_theta / normal_length,
            )
        )

    for segment in range(segments):
        theta = 2.0 * math.pi * segment / segments
        positions.append((radius * math.cos(theta), 0.0, radius * math.sin(theta)))
        normals.append((0.0, -1.0, 0.0))

    base_center = len(positions)
    positions.append((0.0, 0.0, 0.0))
    normals.append((0.0, -1.0, 0.0))

    indices: list[int] = []
    apex = segments
    base_cap = 2 * segments

    for segment in range(segments):
        following = (segment + 1) % segments
        a = segment
        b = following
        t = apex + segment
        indices.extend((a, t, b))

    for segment in range(segments):
        following = (segment + 1) % segments
        a = base_cap + segment
        b = base_cap + following
        indices.extend((base_center, a, b))

    return Mesh(tuple(positions), tuple(normals), tuple(indices))


def torus_mesh(size: float, major_segments: int = 48, minor_segments: int = 16) -> Mesh:
    if major_segments < 3 or minor_segments < 3:
        raise ValueError("torus segment counts must be >= 3")

    tube = size / 8.0
    major = size / 2.0 - tube
    center_y = tube

    positions: list[Point] = []
    normals: list[Point] = []
    for major_index in range(major_segments):
        u = 2.0 * math.pi * major_index / major_segments
        cos_u = math.cos(u)
        sin_u = math.sin(u)
        for minor_index in range(minor_segments):
            v = 2.0 * math.pi * minor_index / minor_segments
            cos_v = math.cos(v)
            sin_v = math.sin(v)
            ring_radius = major + tube * cos_v
            positions.append(
                (ring_radius * cos_u, center_y + tube * sin_v, ring_radius * sin_u)
            )
            normals.append((cos_v * cos_u, sin_v, cos_v * sin_u))

    indices: list[int] = []
    for major_index in range(major_segments):
        next_major = (major_index + 1) % major_segments
        for minor_index in range(minor_segments):
            next_minor = (minor_index + 1) % minor_segments
            a = major_index * minor_segments + minor_index
            b = next_major * minor_segments + minor_index
            c = next_major * minor_segments + next_minor
            d = major_index * minor_segments + next_minor
            indices.extend((a, c, b, a, d, c))

    return Mesh(tuple(positions), tuple(normals), tuple(indices))


def monkey_mesh(size: float) -> Mesh:
    return _load_unit_monkey().scaled(size)


@lru_cache(maxsize=1)
def _load_unit_monkey() -> Mesh:
    path = resources.files("tileset_testbed").joinpath("data", "monkey.bin")
    if not path.is_file():
        raise FileNotFoundError(
            "monkey.bin is missing; run `uv run python scripts/extract_monkey.py`"
        )

    data = path.read_bytes()
    magic, vertex_count, index_count = struct.unpack_from("<4sII", data, 0)
    if magic != MONKEY_MAGIC:
        raise ValueError("monkey.bin has an unknown format")

    offset = 12
    float_count = vertex_count * 3
    positions_flat = struct.unpack_from(f"<{float_count}f", data, offset)
    offset += float_count * 4
    normals_flat = struct.unpack_from(f"<{float_count}f", data, offset)
    offset += float_count * 4
    indices = struct.unpack_from(f"<{index_count}I", data, offset)

    positions = tuple(
        (positions_flat[i], positions_flat[i + 1], positions_flat[i + 2])
        for i in range(0, float_count, 3)
    )
    normals = tuple(
        (normals_flat[i], normals_flat[i + 1], normals_flat[i + 2])
        for i in range(0, float_count, 3)
    )
    return Mesh(positions, normals, indices)


def shape_choices() -> tuple[str, ...]:
    return tuple(shape.value for shape in Shape)
