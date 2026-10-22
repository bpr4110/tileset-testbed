from pathlib import Path

import pytest
from typer.testing import CliRunner

from tileset_testbed.cli import app

runner = CliRunner()


@pytest.mark.parametrize(
    "layout_args",
    [
        ["grid2d", "--columns", "2"],
        ["grid3d", "--columns", "2", "--layers", "2"],
        ["lattice", "--per-color", "2"],
        ["sphere", "--per-color", "2"],
        ["halton", "--per-color", "2"],
        ["helix", "--per-color", "2"],
    ],
)
def test_cli_generates_each_layout(tmp_path: Path, layout_args: list[str]) -> None:
    output = tmp_path / layout_args[0]
    result = runner.invoke(
        app,
        [
            *layout_args,
            "--colors",
            "2",
            "--size",
            "1",
            "--gap",
            "0.5",
            "--output",
            str(output),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (output / "original" / "tileset.json").is_file()
    assert (output / "original" / "content.glb").is_file()
    assert (output / "optimized" / "tileset.json").is_file()
    assert (output / "optimized" / "content.glb").is_file()
    assert (output / "README.md").is_file()


def test_cli_supports_shapes(tmp_path: Path) -> None:
    output = tmp_path / "monkey"
    result = runner.invoke(
        app,
        [
            "grid2d",
            "--columns",
            "1",
            "--shape",
            "monkey",
            "--colors",
            "2",
            "--output",
            str(output),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (output / "original" / "content.glb").is_file()
    assert (output / "optimized" / "content.glb").is_file()
    assert "| `shape` | `monkey` |" in (output / "README.md").read_text(
        encoding="utf-8"
    )


def test_cli_rejects_zero_size(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["grid2d", "--size", "0", "--output", str(tmp_path / "out")],
    )
    assert result.exit_code != 0


def test_cli_rejects_out_of_range_colors(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["grid2d", "--colors", "0", "--output", str(tmp_path / "out")],
    )
    assert result.exit_code != 0


def test_cli_rejects_unknown_shape(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["grid2d", "--shape", "bogus", "--output", str(tmp_path / "out")],
    )
    assert result.exit_code != 0


def test_cli_requires_force_to_overwrite(tmp_path: Path) -> None:
    output = tmp_path / "out"
    args = ["grid2d", "--columns", "2", "--colors", "2", "--output", str(output)]

    assert runner.invoke(app, args).exit_code == 0

    second = runner.invoke(app, args)
    assert second.exit_code == 1
    assert "already contains generated files" in second.output

    forced = runner.invoke(app, [*args, "--force"])
    assert forced.exit_code == 0, forced.output
