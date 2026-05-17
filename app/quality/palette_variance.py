"""Dominant palette extraction + CIE76 drift vs StyleProfile palette (ADR-0009 §5)."""

from __future__ import annotations

import io
import math
import re
from collections import Counter

from PIL import Image

_HEX_RE = re.compile(r"^#([0-9A-Fa-f]{6})$")


def _clamp01(v: float) -> float:
    return min(max(float(v), 0.0), 1.0)


def _srgb_byte_to_lin(c: float) -> float:
    c = _clamp01(c)
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _hex_to_lab(hex_color: str) -> tuple[float, float, float]:
    m = _HEX_RE.match(hex_color.strip())
    if not m:
        raise ValueError(f"expected #RRGGBB hex color, got {hex_color!r}")
    rr, gg, bb = int(m.group(1)[0:2], 16), int(m.group(1)[2:4], 16), int(m.group(1)[4:6], 16)
    r_lin = _srgb_byte_to_lin(rr / 255.0)
    g_lin = _srgb_byte_to_lin(gg / 255.0)
    b_lin = _srgb_byte_to_lin(bb / 255.0)
    x = r_lin * 0.4124564 + g_lin * 0.3575761 + b_lin * 0.1804375
    y = r_lin * 0.2126729 + g_lin * 0.7151522 + b_lin * 0.0721750
    z = r_lin * 0.0193339 + g_lin * 0.1191920 + b_lin * 0.9503041
    xn, yn, zn = 0.95047, 1.00000, 1.08883
    x_, y_, z_ = x / xn, y / yn, z / zn

    def f(t: float) -> float:
        t = max(t, 1e-12)
        delta = (6 / 29) ** 3
        return math.pow(t, 1 / 3) if t > delta else ((29 / 6) ** 2 * t) / 3 + 4 / 29

    l = 116 * f(y_) - 16 if y_ > 1e-12 else 0.0
    a_lab = 500 * (f(x_) - f(y_))
    b_lab = 200 * (f(y_) - f(z_))
    return float(l), float(a_lab), float(b_lab)


def delta_e76(lab1: tuple[float, float, float], lab2: tuple[float, float, float]) -> float:
    return math.sqrt(
        (lab1[0] - lab2[0]) ** 2 + (lab1[1] - lab2[1]) ** 2 + (lab1[2] - lab2[2]) ** 2
    )


def _rgb_quantized_hexes(img: Image.Image) -> list[tuple[str, float]]:
    """Return up to eight (#RRGGBB, normalized weight) pairs from quantized colors."""
    q = img.convert("RGB").quantize(colors=8, method=Image.MEDIANCUT)
    pal_raw = q.getpalette()
    flat = list(q.get_flattened_data())
    counts = Counter(flat)
    total_pixels = len(flat)
    # PIL palette maps index -> RGB triples (sometimes padded to 256 entries).
    hex_weights: dict[str, float] = {}
    for idx, n in counts.most_common(8):
        if pal_raw is None:
            continue
        r, g, b = pal_raw[idx * 3], pal_raw[idx * 3 + 1], pal_raw[idx * 3 + 2]
        hx = f"#{int(r):02x}{int(g):02x}{int(b):02x}".upper()
        hex_weights[hx] = hex_weights.get(hx, 0.0) + float(n) / total_pixels
    ranked = sorted(hex_weights.items(), key=lambda kv: kv[1], reverse=True)
    return ranked


def check_palette_drift(
    image_bytes: bytes,
    style_palette: list[str],
    threshold: float,
) -> tuple[bool, list[str]]:
    """ΔE76 in LAB vs ``style_palette``; does not mutate storage."""
    palette_labs = [_hex_to_lab(h) for h in style_palette]
    img = Image.open(io.BytesIO(image_bytes))
    ranked = _rgb_quantized_hexes(img)
    if not ranked:
        return False, []
    deltas: list[float] = []
    weights: list[float] = []
    for hx, w in ranked:
        img_lab = _hex_to_lab(hx)
        min_d = min(delta_e76(img_lab, lab) for lab in palette_labs)
        deltas.append(min_d)
        weights.append(w)
    mean_delta = (
        sum(d * w for d, w in zip(deltas, weights, strict=True)) / sum(weights)
        if sum(weights) > 0
        else 0.0
    )
    extracted = [h for h, _ in ranked]
    return bool(mean_delta > float(threshold)), extracted
