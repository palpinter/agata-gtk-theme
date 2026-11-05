#!/usr/bin/env python3
"""Generate the Agata terminal color schemes in extras/terminal/ (Alacritty and Ghostty).

  tools/gen-terminal-themes.py           write extras/terminal/{alacritty,ghostty}/*
  tools/gen-terminal-themes.py --check   exit 1 if any generated file would change

Background, foreground and accent come from each GTK theme (the libadwaita palette block at the
end of themes/*/gtk-4.0/gtk.css), and the script checks that they match. The ANSI colors are:
  Nord Dark      the standard Nord palette, bright black lifted to Nord's comment gray #616e88
  Gruvbox Dark   the standard Gruvbox palette, black lifted off the background to #3c3836
  Gruvbox Light  Gruvbox colors in light-theme order: dark black, light white, the readable
                 "faded" Gruvbox colors as normal and the neutral ones as bright
  Nord Light     Nord hues darkened to at least 4.5:1 (normal) and 3:1 (bright) contrast
                 on the light background, because the plain Nord colors reach only about 2:1
"""
import colorsys, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "extras" / "terminal"


# ---------------------------------------------------------------- color helpers
def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def hexc(c):
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(x))) for x in c)


def luminance(h):
    c = [x / 255 for x in rgb(h)]
    c = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def darken_to(color, bg, target):
    """Lower HSL lightness (keeping hue and saturation) until `color` reaches `target` contrast on `bg`."""
    r, g, b = (x / 255 for x in rgb(color))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    while contrast(color, bg) < target and l > 0:
        l = max(0.0, l - 0.005)
        color = hexc(tuple(x * 255 for x in colorsys.hls_to_rgb(h, l, s)))
    return color


# ---------------------------------------------------------------- palettes
NORD = dict(red="#bf616a", green="#a3be8c", yellow="#ebcb8b", blue="#81a1c1", magenta="#b48ead",
            cyan="#88c0d0", frost_dark="#5e81ac", frost_teal="#8fbcbb")
ORDER = ["black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"]


def nord_light(bg):
    base = dict(red=NORD["red"], green=NORD["green"], yellow=NORD["yellow"], blue=NORD["frost_dark"],
                magenta=NORD["magenta"], cyan=NORD["cyan"])
    normal = {k: darken_to(v, bg, 4.5) for k, v in base.items()}
    bright = {k: darken_to(v, bg, 3.0) for k, v in base.items()}
    normal.update(black="#3b4252", white="#d8dee9")
    bright.update(black="#616e88", white="#e5e9f0")
    return normal, bright


def schemes():
    nl_normal, nl_bright = nord_light("#eceff4")
    return {
        "Agata-Nord-Dark": dict(
            title="Agata Nord Dark", bg="#303744", fg="#d8dee9", bright_fg="#eceff4", dim_fg="#a5abb6",
            accent="#81a1c1", cursor="#81a1c1", selection="#4c566a", bar="#394253",
            match="#88c0d0", focused="#ebcb8b",
            normal=dict(black="#3b4252", red=NORD["red"], green=NORD["green"], yellow=NORD["yellow"], blue=NORD["blue"],
                        magenta=NORD["magenta"], cyan=NORD["cyan"], white="#e5e9f0"),
            bright=dict(black="#616e88", red=NORD["red"], green=NORD["green"], yellow=NORD["yellow"], blue=NORD["blue"],
                        magenta=NORD["magenta"], cyan=NORD["frost_teal"], white="#eceff4"),
            dim=dict(black="#373e4d", red="#94545d", green="#809575", yellow="#b29e75", blue="#68809a",
                     magenta="#8c738c", cyan="#6d96a5", white="#aeb3bb")),
        "Agata-Nord-Light": dict(
            title="Agata Nord Light", bg="#eceff4", fg="#2e3440", bright_fg="#2e3440", dim_fg="#4c566a",
            accent="#81a1c1", cursor="#5e81ac", selection="#c5ccd8", bar="#e5e9f0",
            match=nl_normal["cyan"], focused=nl_normal["yellow"], normal=nl_normal, bright=nl_bright),
        "Agata-Gruvbox-Dark": dict(
            title="Agata Gruvbox Dark", bg="#282828", fg="#ebdbb2", bright_fg="#fbf1c7", dim_fg="#a89984",
            accent="#83a598", cursor="#83a598", selection="#504945", bar="#3c3836",
            match="#8ec07c", focused="#fabd2f",
            normal=dict(black="#3c3836", red="#cc241d", green="#98971a", yellow="#d79921", blue="#458588",
                        magenta="#b16286", cyan="#689d6a", white="#a89984"),
            bright=dict(black="#928374", red="#fb4934", green="#b8bb26", yellow="#fabd2f", blue="#83a598",
                        magenta="#d3869b", cyan="#8ec07c", white="#ebdbb2")),
        "Agata-Gruvbox-Light": dict(
            title="Agata Gruvbox Light", bg="#f9f5d7", fg="#3c3836", bright_fg="#282828", dim_fg="#7c6f64",
            accent="#458588", cursor="#458588", selection="#d5c4a1", bar="#ebdbb2",
            match="#427b58", focused="#b57614",
            normal=dict(black="#3c3836", red="#9d0006", green="#79740e", yellow="#b57614", blue="#076678",
                        magenta="#8f3f71", cyan="#427b58", white="#d5c4a1"),
            bright=dict(black="#7c6f64", red="#cc241d", green="#98971a", yellow="#d79921", blue="#458588",
                        magenta="#b16286", cyan="#689d6a", white="#ebdbb2")),
    }


# ---------------------------------------------------------------- consistency with the GTK themes
def check_against_gtk(name, s):
    css = (ROOT / "themes" / name / "gtk-4.0" / "gtk.css").read_text(encoding="utf-8")

    def named(color):
        m = re.search(rf"@define-color {color} (#[0-9A-Fa-f]{{6}});", css)
        if not m:
            sys.exit(f"{name}: @define-color {color} not found (run tools/add-libadwaita-palette.py)")
        return m.group(1).lower()

    for key, color in (("bg", "window_bg_color"), ("accent", "accent_bg_color")):
        if s[key] != named(color):
            sys.exit(f"{name}: terminal {key} {s[key]} != GTK {color} {named(color)}")
    if s["fg"] != named("window_fg_color") and name.endswith("Light"):
        sys.exit(f"{name}: terminal fg {s['fg']} != GTK window_fg_color {named('window_fg_color')}")


# ---------------------------------------------------------------- writers
HEADER = ("{title} terminal colors, generated by tools/gen-terminal-themes.py.\n"
          "Matches the {name} GTK / GNOME Shell theme (https://github.com/palpinter/agata-gtk-theme).")


def alacritty(name, s):
    head = "\n".join("# " + l for l in HEADER.format(name=name, title=s["title"]).splitlines())
    sec = lambda t, d: f"\n[{t}]\n" + "".join(f'{k} = "{v}"\n' for k, v in d.items())
    out = head + "\n"
    out += sec("colors.primary", dict(background=s["bg"], foreground=s["fg"], dim_foreground=s["dim_fg"],
                                      bright_foreground=s["bright_fg"]))
    out += sec("colors.cursor", dict(text=s["bg"], cursor=s["cursor"]))
    out += sec("colors.vi_mode_cursor", dict(text=s["bg"], cursor=s["match"]))
    out += sec("colors.selection", dict(text="CellForeground", background=s["selection"]))
    out += sec("colors.search.matches", dict(foreground="CellBackground", background=s["match"]))
    out += sec("colors.search.focused_match", dict(foreground="CellBackground", background=s["focused"]))
    out += sec("colors.hints.start", dict(foreground=s["bg"], background=s["focused"]))
    out += sec("colors.hints.end", dict(foreground=s["bg"], background=s["match"]))
    out += sec("colors.footer_bar", dict(foreground=s["fg"], background=s["bar"]))
    out += sec("colors.normal", {k: s["normal"][k] for k in ORDER})
    out += sec("colors.bright", {k: s["bright"][k] for k in ORDER})
    if "dim" in s:
        out += sec("colors.dim", {k: s["dim"][k] for k in ORDER})
    return out


def ghostty(name, s):
    out = "\n".join("# " + l for l in HEADER.format(name=name, title=s["title"]).splitlines()) + "\n"
    out += "".join(f"palette = {i}={s['normal'][k]}\n" for i, k in enumerate(ORDER))
    out += "".join(f"palette = {i + 8}={s['bright'][k]}\n" for i, k in enumerate(ORDER))
    out += (f"background = {s['bg']}\nforeground = {s['fg']}\n"
            f"cursor-color = {s['cursor']}\ncursor-text = {s['bg']}\n"
            f"selection-background = {s['selection']}\nselection-foreground = {s['fg']}\n")
    return out


def main():
    check = "--check" in sys.argv[1:]
    changed = []
    for name, s in schemes().items():
        check_against_gtk(name, s)
        files = {OUT / "alacritty" / f"{name.lower()}.toml": alacritty(name, s),
                 OUT / "ghostty" / name: ghostty(name, s)}
        for path, text in files.items():
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                changed.append(path)
                if not check:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(text, encoding="utf-8")
        low = min(contrast(s["normal"][k], s["bg"]) for k in ORDER[1:7])
        print(f"{name}: lowest normal-color contrast {low:.2f}:1, fg {contrast(s['fg'], s['bg']):.2f}:1")
    for p in changed:
        print(("would change: " if check else "wrote: ") + str(p.relative_to(ROOT)))
    if check and changed:
        sys.exit(1)


if __name__ == "__main__":
    main()
