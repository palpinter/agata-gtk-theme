#!/usr/bin/env python3
"""(Re)write the "Agata libadwaita palette" block at the end of each themes/*/gtk-4.0/gtk.css.

The block sets libadwaita's named colors from the theme's own colors, so libadwaita widgets the
compiled stylesheet does not know (AdwDialog, AdwToggleGroup, AdwSpinner, ...) use the Agata
palette when the theme is linked into ~/.config/gtk-4.0. Run it after changing the base colors.
"""
import pathlib, re, sys

MARK = "/* Agata libadwaita palette"
THEMES = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parent.parent / "themes"


def rules(text):
    t = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return [([s.strip() for s in m.group(1).split(",")], m.group(2)) for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", t)]


def prop(rs, sel, name):
    for sels, body in rs:
        if sel in sels:
            for d in body.split(";"):
                k, _, v = d.partition(":")
                if k.strip() == name:
                    return v.strip()
    raise SystemExit(f"missing {sel} {{ {name} }}")


def named(text, name):
    m = re.search(rf"@define-color {name} ([^;]+);", text)
    if not m:
        raise SystemExit(f"missing @define-color {name}")
    return m.group(1).strip()


for f in sorted(THEMES.glob("Agata-*/gtk-4.0/gtk.css")):
    text = f.read_text(encoding="utf-8")
    if MARK in text:
        text = text[:text.index(MARK)].rstrip("\n") + "\n"
    theme = f.parts[-3]
    rs = rules(text)
    win_bg, win_fg = prop(rs, ".background", "background-color"), prop(rs, ".background", "color")
    view_bg, view_fg = prop(rs, ".view", "background-color"), prop(rs, ".view", "color")
    card_bg = prop(rs, ".card", "background-color")
    pop_bg, pop_fg = prop(rs, "popover.background > contents", "background-color"), prop(rs, "popover.background > contents", "color")
    acc_bg, acc_fg = prop(rs, "button.suggested-action", "background-color"), prop(rs, "button.suggested-action", "color")
    link = prop(rs, "link", "color")
    borders = named(text, "borders")
    dark = theme.endswith("Dark")
    accent_text = acc_bg if dark else link
    standalone = "max(l, 0.85) a b" if dark else "min(l, 0.5) a b"
    toggle_bg = "rgba(255, 255, 255, 0.2)" if dark else "#ffffff"
    block = f"""

{MARK}: lets libadwaita widgets that this stylesheet does not
   style itself (AdwDialog, AdwBottomSheet, AdwToggleGroup, AdwSpinner, ...)
   pick up the {theme} colors instead of stock Adwaita and the system accent.
   libadwaita 1.6+ maps its --*-color variables to these named colors, and
   older releases read them directly. Status colors (success, warning, error,
   destructive) are left to libadwaita. */
@define-color accent_bg_color {acc_bg};
@define-color accent_fg_color {acc_fg};
@define-color accent_color {accent_text};
@define-color window_bg_color {win_bg};
@define-color window_fg_color {win_fg};
@define-color view_bg_color {view_bg};
@define-color view_fg_color {view_fg};
@define-color headerbar_bg_color {win_bg};
@define-color headerbar_fg_color {win_fg};
@define-color headerbar_backdrop_color {win_bg};
@define-color headerbar_border_color {win_fg};
@define-color sidebar_bg_color {win_bg};
@define-color sidebar_fg_color {win_fg};
@define-color sidebar_backdrop_color {win_bg};
@define-color sidebar_border_color {borders};
@define-color secondary_sidebar_bg_color {win_bg};
@define-color secondary_sidebar_fg_color {win_fg};
@define-color secondary_sidebar_backdrop_color {win_bg};
@define-color secondary_sidebar_border_color {borders};
@define-color card_bg_color {card_bg};
@define-color card_fg_color {win_fg};
@define-color dialog_bg_color {win_bg};
@define-color dialog_fg_color {win_fg};
@define-color popover_bg_color {pop_bg};
@define-color popover_fg_color {pop_fg};
@define-color thumbnail_bg_color {card_bg};
@define-color thumbnail_fg_color {win_fg};

/* libadwaita 1.6+ (GTK 4.16+): derive accent and status text colors for this
   theme's brightness rather than the system color scheme, so Light/Dark still
   read correctly when the theme and the system preference differ. Older GTK
   ignores this rule. */
:root {{
  --standalone-color-oklab: {standalone};
  --active-toggle-bg-color: {toggle_bg};
  --active-toggle-fg-color: {win_fg};
  --overview-bg-color: {win_bg};
  --overview-fg-color: {win_fg};
}}
"""
    new = text.rstrip("\n") + "\n" + block
    changed = new != f.read_text(encoding="utf-8")
    if changed:
        f.write_text(new, encoding="utf-8")
    print(f"{theme}: {'updated' if changed else 'unchanged'} "
          f"(window {win_bg}/{win_fg}, view {view_bg}, card {card_bg}, accent {acc_bg}, accent text {accent_text})")
