"""Command-line entry point."""

from __future__ import annotations

from pathlib import Path

import typer

from . import layouts
from .generate import generate
from .layouts import Anchor, ColorOrder, HelixStyle
from .shapes import Shape, shape_choices

SHAPE_HELP = ", ".join(shape_choices())

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Generate minimal original and instanced 3D Tiles tilesets of colored shapes.",
)


def _shape_option() -> Shape:
    return typer.Option(Shape.cube, "--shape", help=f"Shape: {SHAPE_HELP}.")


def _colors_option() -> int:
    return typer.Option(
        3,
        "--colors",
        "-c",
        min=1,
        max=360,
        help="Number of HSV hues sampled at S=1, V=1.",
    )


def _size_option() -> float:
    return typer.Option(
        1.0,
        "--size",
        "-s",
        min=0.0,
        help="Largest bounding-box dimension of each shape.",
    )


def _gap_option() -> float:
    return typer.Option(
        0.5,
        "--gap",
        "-g",
        min=0.0,
        help="Target surface gap between neighbouring shapes.",
    )


def _output_option() -> Path:
    return typer.Option(
        ...,
        "--output",
        "-o",
        help="Directory to write the two tilesets to.",
    )


def _force_option() -> bool:
    return typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing generated files.",
    )


def _anchor_option() -> Anchor:
    return typer.Option(
        Anchor.auto,
        "--anchor",
        help="Shape anchor: auto, bottom or center.",
    )


def _color_order_option() -> ColorOrder:
    return typer.Option(
        ColorOrder.block,
        "--color-order",
        help="Color assignment: block or interleaved.",
    )


def _run(
    layout: layouts.Layout,
    shape: Shape,
    size: float,
    gap: float,
    output: Path,
    anchor: Anchor,
    force: bool,
) -> None:
    if size <= 0.0:
        raise typer.BadParameter("must be > 0", param_hint="--size")

    try:
        paths = generate(layout, shape, size, gap, output, anchor, force)
    except (ValueError, FileExistsError, OSError) as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(
        f"Generated {layout.total} {shape.value} shapes "
        f"with {layout.name} ({layout.colors} colors)"
    )
    typer.echo(f"  original:  {paths['original']}")
    typer.echo(f"  optimized: {paths['optimized']}")
    typer.echo(f"  readme:    {paths['readme']}")


@app.command("grid2d")
def grid2d(
    columns: int = typer.Option(
        1, "--columns", min=1, help="Shapes per color along X."
    ),
    colors: int = _colors_option(),
    shape: Shape = _shape_option(),
    size: float = _size_option(),
    gap: float = _gap_option(),
    output: Path = _output_option(),
    anchor: Anchor = _anchor_option(),
    force: bool = _force_option(),
) -> None:
    """A 2D grid: columns along X and one row per color along Z."""
    _run(
        layouts.grid2d(colors, columns, size, gap),
        shape,
        size,
        gap,
        output,
        anchor,
        force,
    )


@app.command("grid3d")
def grid3d(
    columns: int = typer.Option(
        1, "--columns", min=1, help="Shapes per color along X."
    ),
    layers: int = typer.Option(1, "--layers", min=1, help="Layers per color along Y."),
    stagger: bool = typer.Option(
        False, "--stagger", help="Offset alternate layers by half a cell."
    ),
    colors: int = _colors_option(),
    shape: Shape = _shape_option(),
    size: float = _size_option(),
    gap: float = _gap_option(),
    output: Path = _output_option(),
    anchor: Anchor = _anchor_option(),
    force: bool = _force_option(),
) -> None:
    """A 3D grid: columns x layers shapes per color, colors along Z."""
    _run(
        layouts.grid3d(colors, columns, layers, size, gap, stagger),
        shape,
        size,
        gap,
        output,
        anchor,
        force,
    )


@app.command("lattice")
def lattice(
    per_color: int = typer.Option(1, "--per-color", min=1, help="Shapes per color."),
    stagger: bool = typer.Option(
        False, "--stagger", help="Offset alternate layers by half a cell."
    ),
    color_order: ColorOrder = _color_order_option(),
    colors: int = _colors_option(),
    shape: Shape = _shape_option(),
    size: float = _size_option(),
    gap: float = _gap_option(),
    output: Path = _output_option(),
    anchor: Anchor = _anchor_option(),
    force: bool = _force_option(),
) -> None:
    """A compact near-cubic lattice of all shapes."""
    _run(
        layouts.lattice(colors, per_color, size, gap, stagger, color_order),
        shape,
        size,
        gap,
        output,
        anchor,
        force,
    )


@app.command("sphere")
def sphere(
    per_color: int = typer.Option(1, "--per-color", min=1, help="Shapes per color."),
    radius: float | None = typer.Option(
        None, "--radius", min=0.0, help="Sphere radius; auto when omitted."
    ),
    color_order: ColorOrder = _color_order_option(),
    colors: int = _colors_option(),
    shape: Shape = _shape_option(),
    size: float = _size_option(),
    gap: float = _gap_option(),
    output: Path = _output_option(),
    anchor: Anchor = _anchor_option(),
    force: bool = _force_option(),
) -> None:
    """Distribute shapes on a Fibonacci sphere surface."""
    _run(
        layouts.sphere(colors, per_color, size, gap, radius, color_order),
        shape,
        size,
        gap,
        output,
        anchor,
        force,
    )


@app.command("halton")
def halton(
    per_color: int = typer.Option(1, "--per-color", min=1, help="Shapes per color."),
    extent: float | None = typer.Option(
        None, "--extent", min=0.0, help="Cubic volume extent; auto when omitted."
    ),
    color_order: ColorOrder = _color_order_option(),
    colors: int = _colors_option(),
    shape: Shape = _shape_option(),
    size: float = _size_option(),
    gap: float = _gap_option(),
    output: Path = _output_option(),
    anchor: Anchor = _anchor_option(),
    force: bool = _force_option(),
) -> None:
    """Distribute shapes with a deterministic 3D Halton sequence."""
    _run(
        layouts.halton(colors, per_color, size, gap, extent, color_order),
        shape,
        size,
        gap,
        output,
        anchor,
        force,
    )


@app.command("helix")
def helix(
    per_color: int = typer.Option(1, "--per-color", min=1, help="Shapes per color."),
    turns: float = typer.Option(
        3.0, "--turns", min=0.1, help="Number of spiral turns."
    ),
    radius: float | None = typer.Option(
        None, "--radius", min=0.0, help="Disc/helix radius; auto when omitted."
    ),
    style: HelixStyle = typer.Option(
        HelixStyle.filled,
        "--style",
        help="filled (stacked discs) or outline (thin helix).",
    ),
    per_layer: int | None = typer.Option(
        None, "--per-layer", min=1, help="Shapes per disc; filled style only."
    ),
    color_order: ColorOrder = _color_order_option(),
    colors: int = _colors_option(),
    shape: Shape = _shape_option(),
    size: float = _size_option(),
    gap: float = _gap_option(),
    output: Path = _output_option(),
    anchor: Anchor = _anchor_option(),
    force: bool = _force_option(),
) -> None:
    """Stack shapes in a filled spiral column (or a thin outline helix)."""
    if per_layer is not None and radius is not None:
        raise typer.BadParameter(
            "use --per-layer or --radius, not both",
            param_hint="--per-layer/--radius",
        )
    if style is HelixStyle.outline and per_layer is not None:
        raise typer.BadParameter(
            "--per-layer only applies to the filled style",
            param_hint="--per-layer",
        )
    _run(
        layouts.helix(
            colors,
            per_color,
            size,
            gap,
            turns,
            radius,
            color_order,
            style,
            per_layer,
        ),
        shape,
        size,
        gap,
        output,
        anchor,
        force,
    )


if __name__ == "__main__":
    app()
