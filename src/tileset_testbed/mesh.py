"""A tiny immutable triangle mesh type shared by the shape generators."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

Point = tuple[float, float, float]


@dataclass(frozen=True)
class Mesh:
    positions: tuple[Point, ...]
    normals: tuple[Point, ...]
    indices: tuple[int, ...]

    def __post_init__(self) -> None:
        if len(self.positions) != len(self.normals):
            raise ValueError("positions and normals must have the same length")
        if len(self.indices) % 3 != 0:
            raise ValueError("indices must form whole triangles")
        vertex_count = len(self.positions)
        if any(index < 0 or index >= vertex_count for index in self.indices):
            raise ValueError("index out of range")

    def bounds(self) -> tuple[Point, Point]:
        if not self.positions:
            raise ValueError("mesh has no vertices")
        minimum = tuple(
            min(position[axis] for position in self.positions) for axis in range(3)
        )
        maximum = tuple(
            max(position[axis] for position in self.positions) for axis in range(3)
        )
        return minimum, maximum  # type: ignore[return-value]

    def max_extent(self) -> float:
        minimum, maximum = self.bounds()
        return max(maximum[axis] - minimum[axis] for axis in range(3))

    def scaled(self, factor: float) -> Mesh:
        return Mesh(
            positions=tuple(
                (x * factor, y * factor, z * factor) for x, y, z in self.positions
            ),
            normals=self.normals,
            indices=self.indices,
        )

    def translated_x(self, offsets: Sequence[float]) -> Mesh:
        return self.translated_xyz([(offset, 0.0, 0.0) for offset in offsets])

    def translated_xyz(self, offsets: Sequence[Point]) -> Mesh:
        positions: list[Point] = []
        normals: list[Point] = []
        indices: list[int] = []
        base = 0
        for offset_x, offset_y, offset_z in offsets:
            positions.extend(
                (x + offset_x, y + offset_y, z + offset_z) for x, y, z in self.positions
            )
            normals.extend(self.normals)
            indices.extend(base + index for index in self.indices)
            base += len(self.positions)
        return Mesh(tuple(positions), tuple(normals), tuple(indices))
