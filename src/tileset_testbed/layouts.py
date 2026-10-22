"""Layout generators for the original and instanced tilesets.

A layout produces one list of anchor points per color.  The anchor point is the
shape's bottom (``Anchor.bottom``) or center (``Anchor.center``); the caller
resolves ``Anchor.auto`` and shifts the whole scene so its lowest point is at
``Y = 0``.

For grid layouts every color has the same relative pattern, so the original
tileset can share one group mesh and translate it by the color's Z row.  For
the other layouts the per-color positions differ, so the original tileset uses
one single-shape mesh per color plus one node per shape.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from .mesh import Mesh, Point


class Anchor(str, Enum):
    auto = "auto"
    bottom = "bottom"
    center = "center"


class ColorOrder(str, Enum):
    block = "block"
    interleaved = "interleaved"


class HelixStyle(str, Enum):
    filled = "filled"
    outline = "outline"


@dataclass(frozen=True)
class Layout:
    name: str
    colors: int
    positions_by_color: tuple[tuple[Point, ...], ...]
    origins: tuple[Point, ...]
    default_anchor: Anchor
    grouped: bool
    params: tuple[tuple[str, object], ...]

    @property
    def total(self) -> int:
        return sum(len(positions) for positions in self.positions_by_color)

    def instances(self) -> list[tuple[int, Point]]:
        return [
            (color, position)
            for color, positions in enumerate(self.positions_by_color)
            for position in positions
        ]

    def relative_by_color(self) -> tuple[tuple[Point, ...], ...]:
        return tuple(
            tuple(
                (
                    position[0] - origin[0],
                    position[1] - origin[1],
                    position[2] - origin[2],
                )
                for position in positions
            )
            for positions, origin in zip(self.positions_by_color, self.origins)
        )

    def translated(self, offset: Point) -> Layout:
        dx, dy, dz = offset
        return Layout(
            name=self.name,
            colors=self.colors,
            positions_by_color=tuple(
                tuple(
                    (position[0] + dx, position[1] + dy, position[2] + dz)
                    for position in positions
                )
                for positions in self.positions_by_color
            ),
            origins=self.origins,
            default_anchor=self.default_anchor,
            grouped=self.grouped,
            params=self.params,
        )

    def bounds(self, shape: Mesh) -> tuple[Point, Point]:
        shape_min, shape_max = shape.bounds()
        xs = [
            position[0]
            for positions in self.positions_by_color
            for position in positions
        ]
        ys = [
            position[1]
            for positions in self.positions_by_color
            for position in positions
        ]
        zs = [
            position[2]
            for positions in self.positions_by_color
            for position in positions
        ]
        if not xs:
            raise ValueError("layout has no positions")

        return (
            (min(xs) + shape_min[0], min(ys) + shape_min[1], min(zs) + shape_min[2]),
            (max(xs) + shape_max[0], max(ys) + shape_max[1], max(zs) + shape_max[2]),
        )


def _spacing(size: float, gap: float) -> float:
    return size + gap


def _color_z(color: int, colors: int, spacing: float) -> float:
    return (color - (colors - 1) / 2.0) * spacing


def _assign_colors(
    positions: list[Point],
    colors: int,
    per_color: int,
    order: ColorOrder,
) -> tuple[tuple[Point, ...], ...]:
    if len(positions) != colors * per_color:
        raise ValueError("position count does not match colors * per_color")

    buckets: list[list[Point]] = [[] for _ in range(colors)]
    for index, position in enumerate(positions):
        color = index // per_color if order is ColorOrder.block else index % colors
        buckets[color].append(position)
    return tuple(tuple(bucket) for bucket in buckets)


def grid2d(
    colors: int,
    columns: int,
    size: float,
    gap: float,
) -> Layout:
    if colors < 1 or columns < 1:
        raise ValueError("colors and columns must be >= 1")
    spacing = _spacing(size, gap)
    origins = tuple(
        (0.0, 0.0, _color_z(color, colors, spacing)) for color in range(colors)
    )
    positions = tuple(
        tuple(
            (
                (column - (columns - 1) / 2.0) * spacing,
                0.0,
                origins[color][2],
            )
            for column in range(columns)
        )
        for color in range(colors)
    )
    return Layout(
        name="grid2d",
        colors=colors,
        positions_by_color=positions,
        origins=origins,
        default_anchor=Anchor.bottom,
        grouped=True,
        params=(("columns", columns),),
    )


def grid3d(
    colors: int,
    columns: int,
    layers: int,
    size: float,
    gap: float,
    stagger: bool = False,
) -> Layout:
    if colors < 1 or columns < 1 or layers < 1:
        raise ValueError("colors, columns and layers must be >= 1")
    spacing = _spacing(size, gap)
    origins = tuple(
        (0.0, 0.0, _color_z(color, colors, spacing)) for color in range(colors)
    )
    positions: list[tuple[Point, ...]] = []
    for color in range(colors):
        row: list[Point] = []
        for layer in range(layers):
            offset = spacing / 2.0 if stagger and layer % 2 == 1 else 0.0
            for column in range(columns):
                row.append(
                    (
                        (column - (columns - 1) / 2.0) * spacing + offset,
                        layer * spacing,
                        origins[color][2] + offset,
                    )
                )
        positions.append(tuple(row))
    return Layout(
        name="grid3d",
        colors=colors,
        positions_by_color=tuple(positions),
        origins=origins,
        default_anchor=Anchor.bottom,
        grouped=True,
        params=(
            ("columns", columns),
            ("layers", layers),
            ("stagger", stagger),
        ),
    )


def lattice(
    colors: int,
    per_color: int,
    size: float,
    gap: float,
    stagger: bool = False,
    color_order: ColorOrder = ColorOrder.block,
) -> Layout:
    if colors < 1 or per_color < 1:
        raise ValueError("colors and per_color must be >= 1")
    total = colors * per_color
    side = math.ceil(total ** (1.0 / 3.0))
    nx = side
    nz = side
    ny = math.ceil(total / (nx * nz))
    spacing = _spacing(size, gap)

    positions: list[Point] = []
    for index in range(total):
        layer = index // (nx * nz)
        remainder = index % (nx * nz)
        row = remainder // nx
        column = remainder % nx
        offset = spacing / 2.0 if stagger and layer % 2 == 1 else 0.0
        positions.append(
            (
                (column - (nx - 1) / 2.0) * spacing + offset,
                layer * spacing,
                (row - (nz - 1) / 2.0) * spacing + offset,
            )
        )

    return Layout(
        name="lattice",
        colors=colors,
        positions_by_color=_assign_colors(positions, colors, per_color, color_order),
        origins=tuple((0.0, 0.0, 0.0) for _ in range(colors)),
        default_anchor=Anchor.bottom,
        grouped=False,
        params=(
            ("per_color", per_color),
            ("grid", f"{nx}x{ny}x{nz}"),
            ("stagger", stagger),
            ("color_order", color_order.value),
        ),
    )


def sphere(
    colors: int,
    per_color: int,
    size: float,
    gap: float,
    radius: float | None = None,
    color_order: ColorOrder = ColorOrder.block,
) -> Layout:
    if colors < 1 or per_color < 1:
        raise ValueError("colors and per_color must be >= 1")
    total = colors * per_color
    spacing = _spacing(size, gap)
    if radius is None or radius <= 0.0:
        radius = math.sqrt(total * spacing**2 / (4.0 * math.pi))
    radius = max(radius, size / 2.0)

    golden_angle = math.pi * (3.0 - math.sqrt(5.0))
    positions: list[Point] = []
    for index in range(total):
        y = 1.0 - (index + 0.5) * 2.0 / total
        ring = math.sqrt(max(0.0, 1.0 - y * y))
        theta = golden_angle * index
        positions.append(
            (
                radius * ring * math.cos(theta),
                radius * y,
                radius * ring * math.sin(theta),
            )
        )

    return Layout(
        name="sphere",
        colors=colors,
        positions_by_color=_assign_colors(positions, colors, per_color, color_order),
        origins=tuple((0.0, 0.0, 0.0) for _ in range(colors)),
        default_anchor=Anchor.center,
        grouped=False,
        params=(
            ("per_color", per_color),
            ("radius", radius),
            ("color_order", color_order.value),
        ),
    )


def _halton(index: int, base: int) -> float:
    fraction = 1.0
    result = 0.0
    current = index
    while current > 0:
        fraction /= base
        result += fraction * (current % base)
        current //= base
    return result


def halton(
    colors: int,
    per_color: int,
    size: float,
    gap: float,
    extent: float | None = None,
    color_order: ColorOrder = ColorOrder.block,
) -> Layout:
    if colors < 1 or per_color < 1:
        raise ValueError("colors and per_color must be >= 1")
    total = colors * per_color
    spacing = _spacing(size, gap)
    if extent is None or extent <= 0.0:
        extent = total ** (1.0 / 3.0) * spacing
    extent = max(extent, size)

    positions: list[Point] = []
    for index in range(total):
        sample = index + 1
        positions.append(
            (
                (_halton(sample, 2) - 0.5) * extent,
                _halton(sample, 3) * extent,
                (_halton(sample, 5) - 0.5) * extent,
            )
        )

    return Layout(
        name="halton",
        colors=colors,
        positions_by_color=_assign_colors(positions, colors, per_color, color_order),
        origins=tuple((0.0, 0.0, 0.0) for _ in range(colors)),
        default_anchor=Anchor.center,
        grouped=False,
        params=(
            ("per_color", per_color),
            ("extent", extent),
            ("color_order", color_order.value),
        ),
    )


def helix(
    colors: int,
    per_color: int,
    size: float,
    gap: float,
    turns: float = 3.0,
    radius: float | None = None,
    color_order: ColorOrder = ColorOrder.block,
    style: HelixStyle = HelixStyle.filled,
    per_layer: int | None = None,
) -> Layout:
    if colors < 1 or per_color < 1:
        raise ValueError("colors and per_color must be >= 1")
    if turns <= 0.0:
        raise ValueError("turns must be > 0")
    total = colors * per_color
    spacing = _spacing(size, gap)

    if style is HelixStyle.outline:
        if radius is None or radius <= 0.0:
            shapes_per_turn = max(1.0, total / turns)
            radius = max(size, shapes_per_turn * spacing / (2.0 * math.pi))

        positions: list[Point] = []
        for index in range(total):
            angle = 2.0 * math.pi * turns * index / total
            positions.append(
                (
                    radius * math.cos(angle),
                    index * spacing,
                    radius * math.sin(angle),
                )
            )

        return Layout(
            name="helix",
            colors=colors,
            positions_by_color=_assign_colors(
                positions, colors, per_color, color_order
            ),
            origins=tuple((0.0, 0.0, 0.0) for _ in range(colors)),
            default_anchor=Anchor.center,
            grouped=False,
            params=(
                ("per_color", per_color),
                ("style", style.value),
                ("turns", turns),
                ("radius", radius),
                ("color_order", color_order.value),
            ),
        )

    if per_layer is not None and radius is not None:
        raise ValueError("specify per_layer or radius, not both")

    if per_layer is None:
        if radius is None:
            per_layer = max(1, round(total ** (2.0 / 3.0)))
        else:
            per_layer = max(1, round(math.pi * (radius / spacing) ** 2))
    per_layer = min(per_layer, total)
    layers = math.ceil(total / per_layer)

    if radius is None or radius <= 0.0:
        radius = spacing * math.sqrt(per_layer / math.pi) * 1.05

    golden_angle = math.pi * (3.0 - math.sqrt(5.0))
    positions = []
    for layer in range(layers):
        start = layer * per_layer
        layer_count = min(per_layer, total - start)
        phase = 2.0 * math.pi * turns * layer / layers if layers > 1 else 0.0
        y = layer * spacing
        for index in range(layer_count):
            r = radius * math.sqrt((index + 0.5) / layer_count)
            angle = index * golden_angle + phase
            positions.append((r * math.cos(angle), y, r * math.sin(angle)))

    return Layout(
        name="helix",
        colors=colors,
        positions_by_color=_assign_colors(positions, colors, per_color, color_order),
        origins=tuple((0.0, 0.0, 0.0) for _ in range(colors)),
        default_anchor=Anchor.center,
        grouped=False,
        params=(
            ("per_color", per_color),
            ("style", style.value),
            ("per_layer", per_layer),
            ("layers", layers),
            ("radius", radius),
            ("turns", turns),
            ("color_order", color_order.value),
        ),
    )


LAYOUT_NAMES = ("grid2d", "grid3d", "lattice", "sphere", "halton", "helix")
