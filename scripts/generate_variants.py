"""Generate the full layout x shape variant matrix.

Run from the repository root:

    uv run python scripts/generate_variants.py --colors 100 --per-color 1000 \
        --size 1 --gap 0.5 --output tilesets --clean
"""

from __future__ import annotations

import shutil
from pathlib import Path

import typer

from tileset_testbed import layouts
from tileset_testbed.generate import generate
from tileset_testbed.glb import read_glb_json
from tileset_testbed.layouts import Anchor, ColorOrder, Layout
from tileset_testbed.shapes import Shape

app = typer.Typer(add_completion=False)


def _layout_for(
    name: str, colors: int, per_color: int, size: float, gap: float
) -> Layout:
    if name == "grid2d":
        return layouts.grid2d(colors, per_color, size, gap)
    if name == "grid3d":
        layers = 10 if per_color % 10 == 0 else 1
        columns = per_color // layers
        return layouts.grid3d(colors, columns, layers, size, gap)
    if name == "lattice":
        return layouts.lattice(
            colors, per_color, size, gap, color_order=ColorOrder.block
        )
    if name == "sphere":
        return layouts.sphere(
            colors, per_color, size, gap, color_order=ColorOrder.block
        )
    if name == "halton":
        return layouts.halton(
            colors, per_color, size, gap, color_order=ColorOrder.block
        )
    if name == "helix":
        return layouts.helix(colors, per_color, size, gap, color_order=ColorOrder.block)
    raise ValueError(f"unknown layout: {name}")


@app.command()
def main(
    colors: int = typer.Option(100, "--colors", min=1, max=360),
    per_color: int = typer.Option(1000, "--per-color", min=1),
    size: float = typer.Option(1.0, "--size", min=0.0),
    gap: float = typer.Option(0.5, "--gap", min=0.0),
    output: Path = typer.Option(Path("tilesets"), "--output"),
    clean: bool = typer.Option(False, "--clean", help="Remove the output first."),
    layouts_filter: str = typer.Option(
        "", "--layouts", help="Comma-separated layout names; empty means all."
    ),
    shapes_filter: str = typer.Option(
        "", "--shapes", help="Comma-separated shape names; empty means all."
    ),
) -> None:
    layout_names = [
        name.strip()
        for name in (
            layouts_filter.split(",") if layouts_filter else layouts.LAYOUT_NAMES
        )
        if name.strip()
    ]
    shape_names = [
        name.strip()
        for name in (
            shapes_filter.split(",") if shapes_filter else [s.value for s in Shape]
        )
        if name.strip()
    ]

    unknown_layouts = [
        name for name in layout_names if name not in layouts.LAYOUT_NAMES
    ]
    if unknown_layouts:
        raise typer.BadParameter(
            f"unknown layouts: {unknown_layouts}", param_hint="--layouts"
        )
    try:
        shapes = [Shape(name) for name in shape_names]
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--shapes") from exc

    if size <= 0.0:
        raise typer.BadParameter("must be > 0", param_hint="--size")

    output = output.expanduser().resolve()
    if clean and output.exists():
        for child in output.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    output.mkdir(parents=True, exist_ok=True)

    generated = 0

    for layout_name in layout_names:
        for shape in shapes:
            layout = _layout_for(layout_name, colors, per_color, size, gap)
            name = f"c{colors}-n{per_color}-{layout_name}-{shape.value}"
            destination = output / name
            generated += 1
            typer.echo(f"[{generated}] {name} ({layout.total} shapes)")
            generate(
                layout,
                shape,
                size,
                gap,
                destination,
                Anchor.auto,
                force=True,
            )

    _write_manifest(output, colors, per_color, size, gap)
    typer.echo(
        f"Generated {generated} variants; manifest includes all variants in {output}"
    )


def _variant_total(optimized_path: Path) -> int:
    gltf, _ = read_glb_json(optimized_path)
    node = gltf["nodes"][0]
    attributes = node["extensions"]["EXT_mesh_gpu_instancing"]["attributes"]
    return gltf["accessors"][attributes["TRANSLATION"]]["count"]


def _write_manifest(
    output: Path,
    colors: int,
    per_color: int,
    size: float,
    gap: float,
) -> None:
    rows: list[tuple[str, str, str, int, int, int]] = []
    for variant in sorted(path for path in output.iterdir() if path.is_dir()):
        parts = variant.name.split("-")
        if len(parts) != 4:
            continue
        color_part, count_part, layout_name, shape_name = parts
        if not color_part.startswith("c") or not count_part.startswith("n"):
            continue
        try:
            variant_colors = int(color_part[1:])
            variant_count = int(count_part[1:])
        except ValueError:
            continue
        if variant_colors != colors or variant_count != per_color:
            continue

        original = variant / "original" / "content.glb"
        optimized = variant / "optimized" / "content.glb"
        if not (original.is_file() and optimized.is_file()):
            continue
        rows.append(
            (
                variant.name,
                layout_name,
                shape_name,
                _variant_total(optimized),
                original.stat().st_size,
                optimized.stat().st_size,
            )
        )

    lines = [
        "# Generated variants",
        "",
        f"- colors: `{colors}`",
        f"- shapes per color: `{per_color}`",
        f"- size: `{size}`",
        f"- gap: `{gap}`",
        "",
        "Both tilesets use `EXT_mesh_gpu_instancing`: the original groups instances",
        "by color (one node per color), the optimized uses one node in total.",
        "No georeferencing transform is written.",
        "Helix uses a filled disc stack by default; use `--per-layer` or `--radius`",
        "to trade height for width.",
        "",
        "| directory | layout | shape | total | original GLB | optimized GLB |",
        "| --- | --- | --- | ---: | ---: | ---: |",
    ]
    for name, layout_name, shape_name, total, original_size, optimized_size in rows:
        lines.append(
            f"| `{name}` | `{layout_name}` | `{shape_name}` | {total} | "
            f"{original_size / (1024 * 1024):.2f} MB | "
            f"{optimized_size / (1024 * 1024):.2f} MB |"
        )
    (output / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    app()
