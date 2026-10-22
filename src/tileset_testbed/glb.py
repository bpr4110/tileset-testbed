"""Minimal glTF/GLB writer for the generated tilesets.

The GLB files are written by hand so the custom ``EXT_*`` extensions can be
emitted exactly as intended without depending on a large glTF library.
"""

from __future__ import annotations

import json
import struct
from pathlib import Path
from typing import Any

from .colors import RGBA
from .layouts import Layout
from .mesh import Mesh, Point

FLOAT = 5126
UNSIGNED_SHORT = 5123
UNSIGNED_INT = 5125

ARRAY_BUFFER = 34962
ELEMENT_ARRAY_BUFFER = 34963
MODE_TRIANGLES = 4


# ---------------------------------------------------------------------------
# Binary helpers
# ---------------------------------------------------------------------------


class BinaryBuilder:
    def __init__(self) -> None:
        self._data = bytearray()

    @property
    def data(self) -> bytes:
        return bytes(self._data)

    def add(self, data: bytes, alignment: int = 4) -> tuple[int, int]:
        padding = (-len(self._data)) % alignment
        if padding:
            self._data.extend(b"\x00" * padding)
        offset = len(self._data)
        self._data.extend(data)
        return offset, len(data)


def pack_vec3(values: list[Point]) -> bytes:
    flat = [component for value in values for component in value]
    return struct.pack(f"<{len(flat)}f", *flat)


def pack_vec4(values: list[tuple[float, float, float, float]]) -> bytes:
    flat = [component for value in values for component in value]
    return struct.pack(f"<{len(flat)}f", *flat)


def pack_indices(indices: list[int]) -> tuple[int, bytes]:
    if max(indices, default=0) <= 0xFFFF:
        return UNSIGNED_SHORT, struct.pack(f"<{len(indices)}H", *indices)
    return UNSIGNED_INT, struct.pack(f"<{len(indices)}I", *indices)


def minmax_vec3(values: list[Point]) -> tuple[list[float], list[float]]:
    minimum = [min(value[index] for value in values) for index in range(3)]
    maximum = [max(value[index] for value in values) for index in range(3)]
    return minimum, maximum


# ---------------------------------------------------------------------------
# glTF document helpers
# ---------------------------------------------------------------------------


def empty_gltf() -> dict[str, Any]:
    return {
        "asset": {"version": "2.0", "generator": "tileset-testbed 0.1.0"},
        "scene": 0,
        "scenes": [{"nodes": []}],
        "nodes": [],
        "meshes": [],
        "materials": [],
        "accessors": [],
        "bufferViews": [],
        "buffers": [{"byteLength": 0}],
    }


def add_buffer_view(
    gltf: dict[str, Any],
    builder: BinaryBuilder,
    data: bytes,
    target: int | None = None,
) -> int:
    offset, length = builder.add(data)
    view: dict[str, Any] = {
        "buffer": 0,
        "byteOffset": offset,
        "byteLength": length,
    }
    if target is not None:
        view["target"] = target
    gltf["bufferViews"].append(view)
    return len(gltf["bufferViews"]) - 1


def add_accessor(
    gltf: dict[str, Any],
    view_index: int,
    component_type: int,
    count: int,
    type_: str,
    minmax: tuple[list[float], list[float]] | None = None,
) -> int:
    accessor: dict[str, Any] = {
        "bufferView": view_index,
        "componentType": component_type,
        "count": count,
        "type": type_,
    }
    if minmax is not None:
        accessor["min"], accessor["max"] = minmax
    gltf["accessors"].append(accessor)
    return len(gltf["accessors"]) - 1


def make_material(name: str, color: RGBA) -> dict[str, Any]:
    return {
        "name": name,
        "pbrMetallicRoughness": {
            "baseColorFactor": list(color),
            "metallicFactor": 0.0,
            "roughnessFactor": 1.0,
        },
        "alphaMode": "OPAQUE",
    }


def make_primitive(
    position_accessor: int,
    normal_accessor: int,
    index_accessor: int,
    material: int,
) -> dict[str, Any]:
    return {
        "attributes": {
            "POSITION": position_accessor,
            "NORMAL": normal_accessor,
        },
        "indices": index_accessor,
        "material": material,
        "mode": MODE_TRIANGLES,
    }


def add_mesh_accessors(
    gltf: dict[str, Any], builder: BinaryBuilder, mesh: Mesh
) -> tuple[int, int, int]:
    positions = list(mesh.positions)
    normals = list(mesh.normals)
    indices = list(mesh.indices)

    position_view = add_buffer_view(gltf, builder, pack_vec3(positions), ARRAY_BUFFER)
    normal_view = add_buffer_view(gltf, builder, pack_vec3(normals), ARRAY_BUFFER)
    index_component, index_data = pack_indices(indices)
    index_view = add_buffer_view(gltf, builder, index_data, ELEMENT_ARRAY_BUFFER)

    position_accessor = add_accessor(
        gltf, position_view, FLOAT, len(positions), "VEC3", minmax_vec3(positions)
    )
    normal_accessor = add_accessor(gltf, normal_view, FLOAT, len(normals), "VEC3")
    index_accessor = add_accessor(
        gltf, index_view, index_component, len(indices), "SCALAR"
    )
    return position_accessor, normal_accessor, index_accessor


# ---------------------------------------------------------------------------
# GLB construction
# ---------------------------------------------------------------------------


def build_original_glb(
    layout: Layout, palette: list[RGBA], mesh: Mesh
) -> tuple[dict[str, Any], bytes]:
    """Build the non-instanced baseline tileset.

    Grid layouts share one group mesh per color and place it with one node per
    color.  Other layouts use one single-shape mesh per color and one node per
    shape, which keeps the GLB small even for thousands of shapes per color.
    """
    gltf = empty_gltf()
    builder = BinaryBuilder()

    if layout.grouped:
        relatives = layout.relative_by_color()
        group_mesh = mesh.translated_xyz(relatives[0])
        position_accessor, normal_accessor, index_accessor = add_mesh_accessors(
            gltf, builder, group_mesh
        )

        for color_index, color in enumerate(palette):
            gltf["materials"].append(make_material(f"color_{color_index}", color))
            gltf["meshes"].append(
                {
                    "name": f"shape_group_{color_index}",
                    "primitives": [
                        make_primitive(
                            position_accessor,
                            normal_accessor,
                            index_accessor,
                            color_index,
                        )
                    ],
                }
            )
            gltf["nodes"].append(
                {
                    "name": f"color_{color_index}",
                    "mesh": color_index,
                    "translation": list(layout.origins[color_index]),
                }
            )

        gltf["scenes"][0]["nodes"] = list(range(layout.colors))
        return gltf, builder.data

    position_accessor, normal_accessor, index_accessor = add_mesh_accessors(
        gltf, builder, mesh
    )

    for color_index, color in enumerate(palette):
        gltf["materials"].append(make_material(f"color_{color_index}", color))
        gltf["meshes"].append(
            {
                "name": f"shape_{color_index}",
                "primitives": [
                    make_primitive(
                        position_accessor,
                        normal_accessor,
                        index_accessor,
                        color_index,
                    )
                ],
            }
        )

    nodes: list[int] = []
    for color_index, positions in enumerate(layout.positions_by_color):
        for instance_index, position in enumerate(positions):
            nodes.append(len(gltf["nodes"]))
            gltf["nodes"].append(
                {
                    "name": f"color_{color_index}_{instance_index}",
                    "mesh": color_index,
                    "translation": [position[0], position[1], position[2]],
                }
            )

    gltf["scenes"][0]["nodes"] = nodes
    return gltf, builder.data


def build_optimized_glb(
    layout: Layout, palette: list[RGBA], mesh: Mesh
) -> tuple[dict[str, Any], bytes]:
    """One instanced node with per-instance color feature IDs."""
    gltf = empty_gltf()
    builder = BinaryBuilder()
    position_accessor, normal_accessor, index_accessor = add_mesh_accessors(
        gltf, builder, mesh
    )

    instances = layout.instances()
    translations = [position for _, position in instances]
    rotations = [(0.0, 0.0, 0.0, 1.0) for _ in instances]
    scales = [(1.0, 1.0, 1.0) for _ in instances]
    feature_ids = [color for color, _ in instances]

    translation_view = add_buffer_view(
        gltf, builder, pack_vec3(translations), ARRAY_BUFFER
    )
    rotation_view = add_buffer_view(gltf, builder, pack_vec4(rotations), ARRAY_BUFFER)
    scale_view = add_buffer_view(gltf, builder, pack_vec3(scales), ARRAY_BUFFER)
    feature_view = add_buffer_view(
        gltf,
        builder,
        struct.pack(f"<{len(feature_ids)}H", *feature_ids),
        ARRAY_BUFFER,
    )
    color_view = add_buffer_view(gltf, builder, pack_vec4(palette), ARRAY_BUFFER)

    translation_accessor = add_accessor(
        gltf, translation_view, FLOAT, len(translations), "VEC3"
    )
    rotation_accessor = add_accessor(gltf, rotation_view, FLOAT, len(rotations), "VEC4")
    scale_accessor = add_accessor(gltf, scale_view, FLOAT, len(scales), "VEC3")
    feature_accessor = add_accessor(
        gltf, feature_view, UNSIGNED_SHORT, len(feature_ids), "SCALAR"
    )
    color_accessor = add_accessor(gltf, color_view, FLOAT, len(palette), "VEC4")

    gltf["materials"].append(make_material("shared_white", (1.0, 1.0, 1.0, 1.0)))
    gltf["meshes"].append(
        {
            "name": "shape",
            "primitives": [
                make_primitive(
                    position_accessor,
                    normal_accessor,
                    index_accessor,
                    0,
                )
            ],
        }
    )
    gltf["nodes"].append(
        {
            "name": "instanced_shapes",
            "mesh": 0,
            "extensions": {
                "EXT_mesh_gpu_instancing": {
                    "attributes": {
                        "TRANSLATION": translation_accessor,
                        "ROTATION": rotation_accessor,
                        "SCALE": scale_accessor,
                        "_FEATURE_ID_0": feature_accessor,
                    }
                },
                "EXT_instance_features": {
                    "featureIds": [
                        {
                            "featureCount": layout.colors,
                            "attribute": 0,
                            "propertyTable": 0,
                            "label": "instanceColor",
                        }
                    ]
                },
            },
        }
    )
    gltf["scenes"][0]["nodes"] = [0]
    gltf["extensionsUsed"] = [
        "EXT_mesh_gpu_instancing",
        "EXT_instance_features",
        "EXT_structural_metadata",
    ]
    gltf["extensions"] = {
        "EXT_structural_metadata": {
            "schema": {
                "classes": {
                    "instanceColor": {
                        "properties": {
                            "baseColor": {
                                "type": "VEC4",
                                "componentType": "FLOAT32",
                            }
                        }
                    }
                }
            },
            "propertyTables": [
                {
                    "name": "instanceColorTable",
                    "class": "instanceColor",
                    "count": layout.colors,
                    "properties": {"baseColor": {"values": color_accessor}},
                }
            ],
        }
    }
    return gltf, builder.data


# ---------------------------------------------------------------------------
# GLB I/O
# ---------------------------------------------------------------------------


def write_glb(path: Path, gltf: dict[str, Any], binary: bytes) -> None:
    document = dict(gltf)
    document["buffers"] = [{"byteLength": len(binary)}]

    json_bytes = json.dumps(document, separators=(",", ":")).encode("utf-8")
    json_bytes += b" " * ((-len(json_bytes)) % 4)

    binary_bytes = binary + b"\x00" * ((-len(binary)) % 4)
    total_length = 12 + 8 + len(json_bytes) + 8 + len(binary_bytes)

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as file:
        file.write(struct.pack("<III", 0x46546C67, 2, total_length))
        file.write(struct.pack("<II", len(json_bytes), 0x4E4F534A))
        file.write(json_bytes)
        file.write(struct.pack("<II", len(binary_bytes), 0x004E4942))
        file.write(binary_bytes)


def read_glb_json(path: Path) -> tuple[dict[str, Any], bytes]:
    """Read the JSON chunk and BIN chunk of a GLB (used by the tests)."""
    data = path.read_bytes()
    magic, version, _ = struct.unpack_from("<III", data, 0)
    if magic != 0x46546C67 or version != 2:
        raise ValueError(f"{path} is not a GLB 2.0 file")

    json_length, json_type = struct.unpack_from("<II", data, 12)
    if json_type != 0x4E4F534A:
        raise ValueError(f"{path} has no JSON chunk")

    json_start = 20
    json_bytes = data[json_start : json_start + json_length]
    bin_header = json_start + json_length
    bin_length, bin_type = struct.unpack_from("<II", data, bin_header)
    if bin_type != 0x004E4942:
        raise ValueError(f"{path} has no BIN chunk")

    bin_start = bin_header + 8
    return json.loads(json_bytes.decode("utf-8")), data[
        bin_start : bin_start + bin_length
    ]
