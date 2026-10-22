from __future__ import annotations

import struct
from pathlib import Path

import pytest

from tileset_testbed.generate import generate
from tileset_testbed.glb import (
    FLOAT,
    UNSIGNED_INT,
    UNSIGNED_SHORT,
    pack_indices,
    read_glb_json,
)
from tileset_testbed.layouts import (
    Layout,
    grid2d,
    grid3d,
    halton,
    helix,
    lattice,
    sphere,
)
from tileset_testbed.shapes import Shape


def _paths(tmp_path: Path) -> dict[str, Path]:
    layout = grid2d(colors=3, columns=2, size=1.0, gap=0.5)
    return generate(layout, Shape.cube, 1.0, 0.5, tmp_path / "out")


def _small_layout(name: str) -> Layout:
    colors = 2
    per_color = 2
    if name == "grid2d":
        return grid2d(colors, per_color, 1.0, 0.5)
    if name == "grid3d":
        return grid3d(colors, 1, 2, 1.0, 0.5)
    if name == "lattice":
        return lattice(colors, per_color, 1.0, 0.5)
    if name == "sphere":
        return sphere(colors, per_color, 1.0, 0.5)
    if name == "halton":
        return halton(colors, per_color, 1.0, 0.5)
    if name == "helix":
        return helix(colors, per_color, 1.0, 0.5)
    raise AssertionError(name)


def _accessor_values(
    gltf: dict, binary: bytes, accessor_index: int, components: int
) -> list[tuple[float, ...]]:
    accessor = gltf["accessors"][accessor_index]
    view = gltf["bufferViews"][accessor["bufferView"]]
    start = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    values = struct.unpack_from(
        f"<{accessor['count'] * components}f", binary, start
    )
    return [
        tuple(values[index : index + components])
        for index in range(0, len(values), components)
    ]


def test_original_tileset_is_per_color_instanced(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    gltf, binary = read_glb_json(paths["original"].with_name("content.glb"))

    assert len(gltf["meshes"]) == 3
    assert len(gltf["materials"]) == 3
    assert len(gltf["nodes"]) == 3
    assert gltf["extensionsUsed"] == ["EXT_mesh_gpu_instancing"]

    # One node per color, each instancing all shapes of that color.
    for color, node in enumerate(gltf["nodes"]):
        assert node["name"] == f"color_{color}"
        assert node["mesh"] == color
        assert "translation" not in node
        attributes = node["extensions"]["EXT_mesh_gpu_instancing"]["attributes"]
        assert set(attributes) == {"TRANSLATION", "ROTATION", "SCALE"}
        assert gltf["accessors"][attributes["TRANSLATION"]]["count"] == 2

    # Color 0 has two cubes at x = -0.75 and 0.75, z = -1.5.
    attributes = gltf["nodes"][0]["extensions"]["EXT_mesh_gpu_instancing"][
        "attributes"
    ]
    translations = _accessor_values(gltf, binary, attributes["TRANSLATION"], 3)
    assert translations[0] == pytest.approx((-0.75, 0.0, -1.5))
    assert translations[1] == pytest.approx((0.75, 0.0, -1.5))

    # All three meshes share the same single-shape geometry accessors.
    accessors = gltf["meshes"][0]["primitives"][0]["attributes"]
    for mesh in gltf["meshes"]:
        assert mesh["primitives"][0]["attributes"] == accessors

    position = gltf["accessors"][accessors["POSITION"]]
    assert position["type"] == "VEC3"
    assert position["componentType"] == FLOAT
    assert position["count"] == 24
    assert position["min"] == [-0.5, 0.0, -0.5]
    assert position["max"] == [0.5, 1.0, 0.5]

    indices = gltf["accessors"][gltf["meshes"][0]["primitives"][0]["indices"]]
    assert indices["componentType"] == UNSIGNED_SHORT
    assert indices["count"] == 36


def test_optimized_tileset_is_one_instanced_node(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    gltf, _ = read_glb_json(paths["optimized"].with_name("content.glb"))

    assert len(gltf["meshes"]) == 1
    assert len(gltf["materials"]) == 1
    assert len(gltf["nodes"]) == 1
    assert set(gltf["extensionsUsed"]) == {
        "EXT_mesh_gpu_instancing",
        "EXT_instance_features",
        "EXT_structural_metadata",
    }

    node = gltf["nodes"][0]
    attributes = node["extensions"]["EXT_mesh_gpu_instancing"]["attributes"]
    assert set(attributes) == {
        "TRANSLATION",
        "ROTATION",
        "SCALE",
        "_FEATURE_ID_0",
    }

    features = node["extensions"]["EXT_instance_features"]["featureIds"][0]
    assert features["featureCount"] == 3
    assert features["attribute"] == 0
    assert features["propertyTable"] == 0
    assert features["label"] == "instanceColor"

    feature_accessor = gltf["accessors"][attributes["_FEATURE_ID_0"]]
    assert feature_accessor["componentType"] == UNSIGNED_SHORT
    assert feature_accessor["count"] == 3 * 2

    metadata = gltf["extensions"]["EXT_structural_metadata"]
    table = metadata["propertyTables"][0]
    assert table["name"] == "instanceColorTable"
    assert table["class"] == "instanceColor"
    assert table["count"] == 3

    color_accessor = gltf["accessors"][table["properties"]["baseColor"]["values"]]
    assert color_accessor["type"] == "VEC4"
    assert color_accessor["componentType"] == FLOAT
    assert color_accessor["count"] == 3


def test_both_tilesets_use_the_same_bounds(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    original, _ = read_glb_json(paths["original"].with_name("content.glb"))
    optimized, _ = read_glb_json(paths["optimized"].with_name("content.glb"))

    original_position = original["accessors"][0]
    optimized_position = optimized["accessors"][0]

    # Both use the same single-shape geometry; GPU instance transforms place
    # the copies, so the mesh bounds stay instance-local.
    assert original_position["min"] == [-0.5, 0.0, -0.5]
    assert original_position["max"] == [0.5, 1.0, 0.5]
    assert optimized_position["min"] == [-0.5, 0.0, -0.5]
    assert optimized_position["max"] == [0.5, 1.0, 0.5]


def test_pack_indices_switches_to_uint32() -> None:
    component, data = pack_indices([0, 65535])
    assert component == UNSIGNED_SHORT
    assert len(data) == 4

    component, data = pack_indices([0, 65536])
    assert component == UNSIGNED_INT
    assert len(data) == 8


def test_360_colors_use_uint16_feature_ids(tmp_path: Path) -> None:
    layout = grid2d(colors=360, columns=1, size=1.0, gap=0.0)
    paths = generate(layout, Shape.cube, 1.0, 0.0, tmp_path / "out")
    gltf, _ = read_glb_json(paths["optimized"].with_name("content.glb"))
    attributes = gltf["nodes"][0]["extensions"]["EXT_mesh_gpu_instancing"]["attributes"]
    feature_accessor = gltf["accessors"][attributes["_FEATURE_ID_0"]]
    assert feature_accessor["componentType"] == UNSIGNED_SHORT
    assert feature_accessor["count"] == 360

    table = gltf["extensions"]["EXT_structural_metadata"]["propertyTables"][0]
    assert table["count"] == 360


@pytest.mark.parametrize("shape", list(Shape))
def test_all_shapes_generate(tmp_path: Path, shape: Shape) -> None:
    layout = grid2d(colors=2, columns=1, size=1.0, gap=0.5)
    paths = generate(layout, shape, 1.0, 0.5, tmp_path / shape.value)
    original, _ = read_glb_json(paths["original"].with_name("content.glb"))
    optimized, _ = read_glb_json(paths["optimized"].with_name("content.glb"))

    assert len(original["meshes"]) == 2
    assert len(optimized["meshes"]) == 1
    assert original["accessors"][0]["count"] > 0
    assert optimized["accessors"][0]["count"] > 0


@pytest.mark.parametrize(
    "layout_name",
    ["grid2d", "grid3d", "lattice", "sphere", "halton", "helix"],
)
def test_all_layouts_generate(tmp_path: Path, layout_name: str) -> None:
    layout = _small_layout(layout_name)
    paths = generate(layout, Shape.cube, 1.0, 0.5, tmp_path / layout_name)
    original, _ = read_glb_json(paths["original"].with_name("content.glb"))
    optimized, _ = read_glb_json(paths["optimized"].with_name("content.glb"))

    assert len(original["materials"]) == layout.colors
    assert len(optimized["meshes"]) == 1
    assert len(optimized["nodes"]) == 1

    # The original is always one instanced node per color, regardless of layout.
    assert original["extensionsUsed"] == ["EXT_mesh_gpu_instancing"]
    assert len(original["meshes"]) == layout.colors
    assert len(original["nodes"]) == layout.colors
    for color, node in enumerate(original["nodes"]):
        assert node["mesh"] == color
        attributes = node["extensions"]["EXT_mesh_gpu_instancing"]["attributes"]
        assert set(attributes) == {"TRANSLATION", "ROTATION", "SCALE"}
        translation_accessor = original["accessors"][attributes["TRANSLATION"]]
        assert translation_accessor["count"] == len(layout.positions_by_color[color])

    attributes = optimized["nodes"][0]["extensions"]["EXT_mesh_gpu_instancing"][
        "attributes"
    ]
    translation_accessor = optimized["accessors"][attributes["TRANSLATION"]]
    assert translation_accessor["count"] == layout.total
