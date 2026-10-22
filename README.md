# tileset-testbed

Generate two minimal 3D Tiles 1.1 tilesets from the same layout and shape
parameters:

- **original** — the non-instanced baseline.
- **optimized** — one shape mesh plus one
  `EXT_mesh_gpu_instancing` node, with per-instance colors stored as
  `EXT_instance_features` feature IDs and an `EXT_structural_metadata`
  property table.

The optimized tileset is meant for testing the Cesium for Unreal
feature/metadata material pipeline.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

## Layout commands

Each layout is its own subcommand, so `--help` only shows relevant options.

```text
tileset-testbed grid2d   --columns N      --colors C
tileset-testbed grid3d   --columns X --layers Y --colors C [--stagger]
tileset-testbed lattice  --per-color N    --colors C [--stagger]
tileset-testbed sphere   --per-color N    --colors C [--radius R]
tileset-testbed halton   --per-color N    --colors C [--extent E]
tileset-testbed helix    --per-color N    --colors C [--turns T] [--style filled|outline] [--per-layer L | --radius R]
```

| layout | positions | total shapes |
| --- | --- | --- |
| `grid2d` | columns along X, one row per color along Z | `colors * columns` |
| `grid3d` | columns x layers per color, colors along Z | `colors * columns * layers` |
| `lattice` | compact near-cubic lattice | `colors * per_color` |
| `sphere` | Fibonacci sphere surface | `colors * per_color` |
| `halton` | deterministic 3D Halton volume | `colors * per_color` |
| `helix` | filled spiral column (default) or thin outline helix | `colors * per_color` |

Common options for every command:

| option | meaning |
| --- | --- |
| `--shape` | `cube`, `sphere`, `monkey`, `cylinder`, `cone`, `torus` |
| `--colors`, `-c` | number of HSV hues, 1..360 |
| `--size`, `-s` | largest bounding-box dimension of each shape |
| `--gap`, `-g` | target surface gap between neighbouring shapes |
| `--output`, `-o` | output directory (required) |
| `--anchor` | `auto`, `bottom`, or `center` |
| `--force`, `-f` | overwrite existing generated files |

Non-grid layouts also accept:

| option | meaning |
| --- | --- |
| `--color-order` | `block` (default) or `interleaved` |
| `--radius` | explicit sphere radius, or helix disc/outline radius |
| `--extent` | cubic volume extent for `halton`; auto when omitted |
| `--turns` | helix turn count (default `3`) |
| `--style` | helix style: `filled` (default) or `outline` |
| `--per-layer` | shapes per disc for the filled helix; auto when omitted |

## Examples

```powershell
# Current 2D grid
tileset-testbed grid2d --shape cube --colors 3 --columns 10 `
    --size 1 --gap 0.5 -o out

# 3D grid: 6 colors, 4 columns, 3 layers
tileset-testbed grid3d --shape monkey --colors 6 --columns 4 --layers 3 `
    --size 1 --gap 0.5 --stagger -o out

# Compact lattice
tileset-testbed lattice --shape sphere --colors 12 --per-color 10 `
    --size 0.5 --gap 0.25 -o out

# Sphere surface
tileset-testbed sphere --shape cube --colors 8 --per-color 12 `
    --size 0.5 --gap 0.25 -o out

# Deterministic irregular volume
tileset-testbed halton --shape monkey --colors 10 --per-color 20 `
    --size 1 --gap 0.5 --extent 10 -o out

# Filled spiral column (default): many shapes per disc, discs rotated as they stack
tileset-testbed helix --shape cone --colors 4 --per-color 20 `
    --size 0.5 --turns 3 -o out

# Wider and shorter: ten shapes per disc
tileset-testbed helix --shape cone --colors 4 --per-color 20 `
    --size 0.5 --per-layer 10 -o out

# Old thin-outline helix for comparison
tileset-testbed helix --shape cone --colors 4 --per-color 20 `
    --size 0.5 --style outline --radius 4 -o out
```

## Semantics

- `size` is the largest bounding-box dimension of the shape. Every shape is
  normalized to that size, centered on X/Z, with its lowest point at `Y = 0`
  before anchoring.
- `gap` is exact spacing (`size + gap`) for grid and lattice layouts. For
  `sphere`, `halton`, and the filled `helix`, it is a target used to derive the
  radius, extent, or disc radius; actual neighbour distances are approximate.
- The filled helix stacks horizontal discs. Each disc contains `per_layer`
  shapes; each disc is rotated slightly compared with the one below it, so the
  outside reads as a spiral and the inside is full. The default `per_layer` is
  `round(total ** (2/3))`, which balances height and width. A larger
  `per_layer` makes the column shorter and wider; a smaller one makes it taller
  and narrower. `--radius` is an alternative way to choose the disc radius.
- `--style outline` keeps the old one-shape-per-step thin helix; it is useful
  for comparison but is much taller.
- `--anchor auto` picks `bottom` for grid/lattice layouts and `center` for
  `sphere`/`halton`/`helix`.
- After layout, the whole scene is shifted so its lowest point touches `Y = 0`,
  and the tileset bounding box is computed from the actual instances.
- Colors are assigned to the Z rows in grid layouts. For the other layouts,
  `block` gives each color a contiguous set of positions; `interleaved` cycles
  colors through the layout.

### Original tileset behavior

- `grid2d` / `grid3d`: one group mesh per color, shared geometry, and one node
  per color. This matches the previous baseline.
- `lattice` / `sphere` / `halton` / `helix`: one single-shape mesh per color and
  one node per shape. This keeps the GLB compact instead of duplicating a
  per-color position set a hundred times.

The optimized tileset always uses one shape mesh and one instanced node.

## Shapes

| shape | source |
| --- | --- |
| `cube` | procedural |
| `sphere` | procedural UV sphere |
| `monkey` | `monkey.glb` in the repo root, packed into `src/tileset_testbed/data/monkey.bin` |
| `cylinder` | procedural, capped |
| `cone` | procedural, capped base |
| `torus` | procedural |

Regenerate the monkey data after changing `monkey.glb`:

```powershell
uv run python scripts/extract_monkey.py
```

## Output

```text
out/
├── README.md
├── original/
│   ├── tileset.json
│   └── content.glb
└── optimized/
    ├── tileset.json
    └── content.glb
```

The generated `out/README.md` records the layout, shape, and all layout
parameters, and contains the Cesium for Unreal material setup.

## Variant matrix

Generate every layout x shape combination with 100 colors and 1000 shapes per
color:

```powershell
uv run python scripts/generate_variants.py --colors 100 --per-color 1000 `
    --size 1 --gap 0.5 --output tilesets --clean
```

The script writes `tilesets/README.md` with the directory table and file sizes.
Use `--layouts` / `--shapes` to run a subset, for example:

```powershell
uv run python scripts/generate_variants.py --layouts grid3d,sphere `
    --shapes monkey --colors 100 --per-color 1000 --output tilesets
```

## Cesium for Unreal

The optimized tileset renders with a shared white material until you set up the
metadata-aware material:

1. Add `Cesium Features Metadata` to the `Cesium3DTileset` actor.
2. Auto Fill.
3. Keep the instance feature set (`instanceColor` /
   `_FEATURE_INSTANCE_ID_0`) and the `instanceColorTable` / `baseColor`
   property.
4. Set the property encoding to **Vec4 / Float / Coerce**.
5. Generate Material.
6. Duplicate or derive a Material from `M_CesiumBaseMaterial`, add the generated
   layer to that Material's layer stack, rename the layer to exactly
   `FeaturesMetadata`, and create a Material Instance from that Material.
7. In the generated layer, wire the `baseColor` output into Base Color.
8. Assign the Material Instance to the tileset's `Material` slot and refresh
   the tileset.

A generic glTF viewer will show the optimized mesh white; that is expected.

No georeferencing transform is written: `root.transform` is identity.

## Development

```powershell
uv sync
uv run pytest
uv run ruff check .
uv run tileset-testbed --help
```

## License

MIT © John But. See [LICENSE](LICENSE).
