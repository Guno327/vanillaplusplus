#!/usr/bin/env python3
"""Generate the Adventurer skill-tree background canvas (issue #116 rework).

The first #116 pass used the tiled vanilla `end.png` advancement background
behind a 198:1 vertical ribbon of nodes. The rework lays the tree out as a
centered radial web (see scripts/gen_skill_tree.py's layout_polar()), so the
background is now a single full-canvas image (puffish `position: fill`) with
four labelled quadrant regions - one per class - matching the four angular
sectors the nodes fan into. This is a PLACEHOLDER: procedurally generated,
clean and legible, deliberately not final commissioned art (the custom skill
mod tracked as #163 is where real art lands). It reads as an intentional
4-sector web backdrop, not a ribbon.

Wedge directions match layout_polar()'s class_order angles in puffish's
screen space (y increases downward, angle 0 = +x = right, measured
clockwise): Warrior=right (0deg), Ranger=down (90deg), Mystic=left (180deg),
Artisan=up (270deg). SECTOR_FILL / sector-half math is kept in sync with
gen_skill_tree.py so the coloured wedges line up with where nodes actually
sit.

Output: pack/kubejs/assets/vanillaplusplus/textures/gui/skills/adventurer_bg.png
(referenced from category.json as
"vanillaplusplus:textures/gui/skills/adventurer_bg.png"). KubeJS serves
kubejs/assets/ as a resource-pack root, so no extra wiring is needed.
"""
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Kept in sync by hand with gen_skill_tree.py (SECTOR_FILL and CLASS_SPECS
# order). Directions are in screen space (y down), clockwise from +x.
SIZE = 1024
SECTOR_FILL = 0.82
# (label, wedge-center-angle-degrees, RGB) - order == gen_skill_tree.py's
# CLASS_SPECS order (warrior, ranger, mystic, artisan) at i*90deg.
CLASSES = [
    ("WARRIOR", 0, (150, 52, 46)),
    ("RANGER", 90, (52, 120, 52)),
    ("MYSTIC", 180, (84, 70, 150)),
    ("ARTISAN", 270, (168, 124, 42)),
]

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = (REPO_ROOT / "pack" / "kubejs" / "assets" / "vanillaplusplus"
       / "textures" / "gui" / "skills" / "adventurer_bg.png")


def _font(size):
    for name in ("DejaVuSans-Bold.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def generate():
    cx = cy = SIZE / 2
    max_r = SIZE / 2
    bg_deep = (14, 16, 24)
    bg_edge = (8, 9, 14)
    img = Image.new("RGB", (SIZE, SIZE), bg_deep)
    px = img.load()

    sector_half = (90 / 2) * SECTOR_FILL  # degrees, matches layout_polar()

    def wedge_color(angle_deg):
        for _label, center, rgb in CLASSES:
            d = abs((angle_deg - center + 180) % 360 - 180)
            if d <= sector_half:
                return rgb
        return None

    # Radial paint: dark vignette + faint per-class wedge tint that fades out
    # toward the rim, so the four sectors read without hiding the nodes.
    for y in range(SIZE):
        for x in range(SIZE):
            dx, dy = x - cx, y - cy
            r = math.hypot(dx, dy)
            t = min(r / max_r, 1.0)
            base = _lerp(bg_deep, bg_edge, t)
            ang = math.degrees(math.atan2(dy, dx)) % 360
            wc = wedge_color(ang)
            if wc is not None:
                # strongest around the mid-radius band, fading at center + rim
                band = math.sin(min(t, 1.0) * math.pi)  # 0 at center/rim, 1 mid
                tint = 0.16 * band
                base = _lerp(base, wc, tint)
            px[x, y] = base

    draw = ImageDraw.Draw(img, "RGBA")

    # Concentric depth rings (radius = graph depth in the tree) - 7 rings.
    for depth in range(1, 8):
        rr = max_r * depth / 8.0
        draw.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                     outline=(120, 130, 150, 40), width=2)

    # Sector gutter spokes (the empty gaps between class wedges, at
    # center +- sector_half).
    for _label, center, _rgb in CLASSES:
        for edge in (center - sector_half, center + sector_half):
            a = math.radians(edge)
            draw.line([cx, cy, cx + max_r * math.cos(a), cy + max_r * math.sin(a)],
                      fill=(0, 0, 0, 70), width=3)

    # Center origin glow.
    for rr, alpha in ((70, 60), (46, 90), (26, 150)):
        draw.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=(230, 232, 240, alpha))

    # Class labels, placed mid-wedge, oriented outward.
    label_font = _font(52)
    for label, center, rgb in CLASSES:
        a = math.radians(center)
        lr = max_r * 0.60
        lx, ly = cx + lr * math.cos(a), cy + lr * math.sin(a)
        light = _lerp(rgb, (255, 255, 255), 0.55)
        tw = draw.textlength(label, font=label_font)
        draw.text((lx - tw / 2, ly - 26), label, font=label_font,
                  fill=(*light, 235), stroke_width=3, stroke_fill=(0, 0, 0, 200))

    title_font = _font(30)
    title = "ADVENTURER"
    tw = draw.textlength(title, font=title_font)
    draw.text((cx - tw / 2, cy - 92), title, font=title_font,
              fill=(210, 214, 226, 210), stroke_width=2, stroke_fill=(0, 0, 0, 190))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT)
    print(f"wrote {OUT} ({SIZE}x{SIZE})")


if __name__ == "__main__":
    generate()
