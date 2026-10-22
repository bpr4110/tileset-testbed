import pytest

from tileset_testbed.colors import hue_to_linear_rgba, make_palette, srgb_to_linear


def test_three_primary_hues() -> None:
    palette = make_palette(3)
    assert palette[0] == pytest.approx((1.0, 0.0, 0.0, 1.0))
    assert palette[1] == pytest.approx((0.0, 1.0, 0.0, 1.0))
    assert palette[2] == pytest.approx((0.0, 0.0, 1.0, 1.0))


def test_single_color_is_red() -> None:
    assert make_palette(1) == [pytest.approx((1.0, 0.0, 0.0, 1.0))]


def test_palette_size() -> None:
    assert len(make_palette(360)) == 360


def test_hue_wraps() -> None:
    assert hue_to_linear_rgba(1.0) == pytest.approx(hue_to_linear_rgba(0.0))


def test_srgb_to_linear() -> None:
    assert srgb_to_linear(0.0) == pytest.approx(0.0)
    assert srgb_to_linear(1.0) == pytest.approx(1.0)
    assert srgb_to_linear(0.5) == pytest.approx(0.21404114048223255)


def test_palette_rejects_zero() -> None:
    with pytest.raises(ValueError):
        make_palette(0)
