"""Extract the Suzanne mesh from ``monkey.glb`` into a compact binary asset.

Run from the repository root:

    uv run python scripts/extract_monkey.py

The output is a unit-sized mesh: its largest bounding-box dimension is 1, it is
centered on X/Z, and its lowest point is at Y=0.  The runtime scales it by the
requested ``--size``.
"""

from __future__ import annotations

import math
import struct
from pathlib import Path

from tileset_testbed.glb import read_glb_json

COMPONENT_FORMATS = {
    5120: "b",
    5121: "B",
    5122: "h",
    5123: "H",
    5125: "I",
    5126: "f",
}
TYPE_COMPONENTS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "monkey.glb"
TARGET = ROOT / "src" / "tileset_testbed" / "data" / "monkey.bin"


def read_accessor(
    gltf: dict, binary: bytes, accessor_index: int
) -> list[tuple[float, ...]]:
    accessor = gltf["accessors"][accessor_index]
    if "bufferView" not in accessor:
        raise ValueError("sparse accessors are not supported")

    view = gltf["bufferViews"][accessor["bufferView"]]
    component_type = accessor["componentType"]
    components = TYPE_COMPONENTS[accessor["type"]]
    fmt = COMPONENT_FORMATS[component_type]
    item_size = struct.calcsize(fmt) * components
    stride = view.get("byteStride", item_size)
    start = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)

    return [
        struct.unpack_from(f"<{components}{fmt}", binary, start + index * stride)
        for index in range(accessor["count"])
    ]


def normalize(vector: tuple[float, ...]) -> tuple[float, float, float]:
    length = math.sqrt(sum(component * component for component in vector))
    if length == 0.0:
        return (0.0, 1.0, 0.0)
    return tuple(component / length for component in vector)  # type: ignore[return-value]


def main() -> None:
    gltf, binary = read_glb_json(SOURCE)

    nodes_with_mesh = [node for node in gltf["nodes"] if "mesh" in node]
    if not nodes_with_mesh:
        raise SystemExit(f"{SOURCE} has no mesh nodes")

    for node in nodes_with_mesh:
        if any(key in node for key in ("matrix", "translation", "rotation", "scale")):
            raise SystemExit(
                "monkey node has a transform; extend the extractor before using it"
            )

    positions: list[tuple[float, ...]] = []
    normals: list[tuple[float, ...]] = []
    indices: list[int] = []

    for node in nodes_with_mesh:
        mesh = gltf["meshes"][node["mesh"]]
        for primitive in mesh["primitives"]:
            attributes = primitive["attributes"]
            if "NORMAL" not in attributes or "indices" not in primitive:
                raise SystemExit("monkey primitive needs NORMAL and indices")

            primitive_positions = read_accessor(gltf, binary, attributes["POSITION"])
            primitive_normals = read_accessor(gltf, binary, attributes["NORMAL"])
            primitive_indices = read_accessor(gltf, binary, primitive["indices"])

            base = len(positions)
            positions.extend(primitive_positions)
            normals.extend(primitive_normals)
            indices.extend(base + value[0] for value in primitive_indices)

    min_x = min(position[0] for position in positions)
    max_x = max(position[0] for position in positions)
    min_y = min(position[1] for position in positions)
    max_y = max(position[1] for position in positions)
    min_z = min(position[2] for position in positions)
    max_z = max(position[2] for position in positions)

    center_x = (min_x + max_x) / 2.0
    center_z = (min_z + max_z) / 2.0
    extent = max(max_x - min_x, max_y - min_y, max_z - min_z)
    scale = 1.0 / extent

    unit_positions = [
        (
            (position[0] - center_x) * scale,
            (position[1] - min_y) * scale,
            (position[2] - center_z) * scale,
        )
        for position in positions
    ]
    unit_normals = [normalize(normal) for normal in normals]

    flat_positions = [
        component for position in unit_positions for component in position
    ]
    flat_normals = [component for normal in unit_normals for component in normal]

    payload = bytearray()
    payload += b"SHP1"
    payload += struct.pack("<II", len(unit_positions), len(indices))
    payload += struct.pack(f"<{len(flat_positions)}f", *flat_positions)
    payload += struct.pack(f"<{len(flat_normals)}f", *flat_normals)
    payload += struct.pack(f"<{len(indices)}I", *indices)

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_bytes(payload)

    print(f"source: {SOURCE} ({SOURCE.stat().st_size} bytes)")
    print(f"target: {TARGET} ({TARGET.stat().st_size} bytes)")
    print(
        f"vertices: {len(unit_positions)}, triangles: {len(indices) // 3}, "
        f"scale: {scale:.6f}"
    )
    print(
        "unit bounds: "
        f"x [{min(position[0] for position in unit_positions):.6f}, "
        f"{max(position[0] for position in unit_positions):.6f}], "
        f"y [{min(position[1] for position in unit_positions):.6f}, "
        f"{max(position[1] for position in unit_positions):.6f}], "
        f"z [{min(position[2] for position in unit_positions):.6f}, "
        f"{max(position[2] for position in unit_positions):.6f}]"
    )


if __name__ == "__main__":
    main()
