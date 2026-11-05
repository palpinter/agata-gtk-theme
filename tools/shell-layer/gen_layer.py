#!/usr/bin/env python3
"""Generate the "GNOME Shell 47+ compatibility layer" at the top of each gnome-shell.css.

Usage (normally via tools/regenerate-shell-layer.sh):
  gen_layer.py --stock STOCK_DARK_CSS --themes THEMES_DIR --gaps-dir DIR --shell-version N [--write | --check]

The layer is the stock GNOME Shell dark theme recolored to each Agata palette:
  (A) stock rules for style classes Agata does not style at all,
  (B) stock !important color declarations (they beat Agata's normal ones, because St
      sorts by origin + importance before specificity),
  (D) stock colors on elements Agata styles but where it leaves the property unset;
      the (selector, property) list is gaps-<theme>.json from find_gaps.py,
  (C) hand-mapped successors of renamed widgets using Agata's own declarations,
      plus targeted fixes (toggle-switch knob, opaque stacked notifications, ...).
Light themes use an inverted mapping (stock dark bg -> Agata bg, white -> Agata fg).
st-mix()/-st-accent-color are precomputed, so the output also parses on older St.
"""
import argparse, colorsys, json, pathlib, re, sys, tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from shellcss import parse, split_top, to_rgba, fmt, mix, lighten, darken, transparentize, num, COLOR_RE  # noqa: E402

BEGIN = "/* BEGIN Agata GNOME Shell 47+ compatibility layer"
END = "/* END Agata GNOME Shell 47+ compatibility layer */"

SKIP_CLASS = re.compile(r"^(lg-|evaluator-results$|LookingGlass)")
SKIP_SEL = re.compile(r"\.toggle-switch|#LookingGlass|\.lg-|\.qr-code|screen-recording-indicator|screen-sharing-indicator|privacy-indicator")
COLOR_PROPS = {"color", "background-color", "border-color", "box-shadow", "text-shadow", "-arrow-background-color",
               "-arrow-border-color", "caret-color", "selection-background-color", "selected-color", "outline-color",
               "-barlevel-background-color", "-barlevel-active-background-color", "-barlevel-overdrive-color",
               "-slider-handle-border-color", "-arrow-box-shadow"}
# Stock effects that must keep their literal colors (screenshot flash, dimming, shield).
KEEP_LITERAL = re.compile(r"^(stage|\.flashspot|\.lightbox|\.screen-shield-background|\.screenshot-ui-(area|screen)-)")


def classes_of(sel):
    return set(re.findall(r"\.([A-Za-z_][\w-]*)", sel)) | {"#" + x for x in re.findall(r"#([A-Za-z_][\w-]*)", sel)}


def theme_palette(rules):
    pal = {}
    for key, sel, prop in [("fg", "stage", "color"), ("bg", "#lockDialogGroup", "background-color"),
                           ("popup", ".modal-dialog", "background-color"), ("accent", ".quick-toggle:checked", "background-color"),
                           ("accent_fg", ".quick-toggle:checked", "color"), ("warning", ".login-dialog-message-warning", "color")]:
        v = None
        for sels, decls in rules:
            if sel in sels:
                for k, vv, _ in decls:
                    if k == prop:
                        v = vv
        if v is None:
            raise SystemExit(f"palette anchor not found in Agata stylesheet: {sel} {{ {prop} }}")
        pal[key] = to_rgba(v)
    return pal


def lightness(c):
    return colorsys.rgb_to_hls(c[0] / 255, c[1] / 255, c[2] / 255)[1]


def is_neutral(c):
    return max(c[:3]) - min(c[:3]) <= 14


def make_mapper(pal):
    # Anchors in the stock (dark) color space -> Agata colors.
    anchors = sorted([(lightness(to_rgba("#222226")), pal["bg"]),
                      (lightness(to_rgba("#36363a")), pal["popup"]),
                      (1.0, pal["fg"])], key=lambda a: a[0])
    inverted = lightness(pal["bg"]) > lightness(pal["fg"])

    def ramp(c):
        L = lightness(c)
        if L >= 0.95:                     # GNOME near-whites (#fafafb, ...) are its foreground
            L = 1.0
        if L <= anchors[0][0]:
            out = anchors[0][1]
        else:
            out = anchors[-1][1]
            for (l0, c0), (l1, c1) in zip(anchors, anchors[1:]):
                if l0 <= L <= l1:
                    t = (L - l0) / (l1 - l0)
                    out = tuple(c0[i] + (c1[i] - c0[i]) * t for i in range(3)) + (1.0,)
                    break
        return (out[0], out[1], out[2], c[3])

    def leaf(tok):
        if tok == "-st-accent-color":
            return pal["accent"]
        if tok == "-st-accent-fg-color":
            return (pal["accent_fg"][0], pal["accent_fg"][1], pal["accent_fg"][2], 1.0)
        c = to_rgba(tok)
        if c is None:
            raise ValueError(tok)
        if c[3] < 1.0 and max(c[:3]) < 40:      # translucent black: shadows, scrims
            return c
        if c[3] == 0.0:
            return c
        if is_neutral(c):
            return ramp(c)
        if abs(c[0] - 0xcd) + abs(c[1] - 0x93) + abs(c[2] - 0x09) < 30:   # stock warning yellow
            return pal["warning"][:3] + (c[3],)
        return c                                   # other status colors stay as GNOME defines them

    def evaluate(expr):
        expr = expr.strip()
        m = re.match(r"^(st-mix|st-lighten|st-darken|st-transparentize)\((.*)\)$", expr)
        if m:
            args = split_top(m.group(2))
            f = m.group(1)
            if f == "st-mix":
                return mix(evaluate(args[0]), evaluate(args[1]), num(args[2]))
            c, a = evaluate(args[0]), num(args[1])
            if f == "st-transparentize":
                return transparentize(c, a)
            if inverted:                               # light themes: "lighter" means "further from the background"
                f = "st-darken" if f == "st-lighten" else "st-lighten"
            return (lighten if f == "st-lighten" else darken)(c, a)
        return leaf(expr)

    expr_re = re.compile(r"st-(?:mix|lighten|darken|transparentize)\(|" + COLOR_RE)

    def map_value(v):
        out, i = [], 0
        while i < len(v):
            m = expr_re.search(v, i)
            if not m:
                out.append(v[i:])
                break
            out.append(v[i:m.start()])
            if m.group(0).endswith("("):            # function: find the matching paren
                depth, j = 0, m.end() - 1
                while j < len(v):
                    depth += v[j] == "("
                    depth -= v[j] == ")"
                    j += 1
                    if depth == 0:
                        break
                tok = v[m.start():j]
                i = j
            else:
                tok = m.group(0)
                i = m.end()
            out.append(fmt(evaluate(tok)))
        return "".join(out)

    return map_value


def color_decls(decls, map_value):
    out = []
    for k, v, imp in decls:
        if k == "background":
            if "url(" in v:
                continue
            k = "background-color"
        elif k == "border":
            m = re.search(COLOR_RE + r"|st-\w+\(.*\)", v)
            if not m:
                continue
            k, v = "border-color", m.group(0)
        if k not in COLOR_PROPS:
            continue
        if not re.search(COLOR_RE + r"|st-\w+\(", v):
            continue
        out.append((k, map_value(v), imp))
    return out


def normalize(v):
    """Spell plain color tokens the way fmt() does, so unchanged values compare equal."""
    return re.sub(r"#[0-9A-Fa-f]{3,8}\b|rgba?\([^()]*\)|\b(?:white|black|transparent)\b",
                  lambda m: fmt(to_rgba(m.group(0))), v)


def agata_decls(rules, sel, props=("color", "background-color", "box-shadow")):
    out = []
    for sels, decls in rules:
        if sel in sels:
            out += [(k, v, imp) for k, v, imp in decls if k in props]
    return out


def render(sels, decls):
    body = "".join(f"\n  {k}: {v}{' !important' if imp else ''};" for k, v, imp in decls)
    return ",\n".join(sels) + " {" + body + "\n}\n"


def strip_layer(text):
    if BEGIN in text:
        text = text[text.index(END) + len(END):].lstrip("\n")
    return text


def parse_text(text):
    with tempfile.NamedTemporaryFile("w", suffix=".css", encoding="utf-8", delete=False) as tmp:
        tmp.write(text)
    try:
        return parse(tmp.name)
    finally:
        pathlib.Path(tmp.name).unlink()


def build(theme_dir, stock, gaps_dir, shell_version):
    path = theme_dir / "gnome-shell" / "gnome-shell.css"
    text = strip_layer(path.read_text(encoding="utf-8"))
    agata = parse_text(text)
    pal = theme_palette(agata)
    map_value = make_mapper(pal)
    agata_classes = set()
    agata_sel_props = {}
    for sels, decls in agata:
        for s in sels:
            agata_classes |= classes_of(s)
            agata_sel_props.setdefault(s, {}).update({k: imp for k, v, imp in decls})
    missing = {c for c in set().union(*(classes_of(s) for sels, _ in stock for s in sels)) - agata_classes
               if not SKIP_CLASS.match(c.lstrip("#"))}

    # (A) and (B)
    out_a, out_b = [], []
    for sels, decls in stock:
        keep = [s for s in sels if classes_of(s) & missing and not SKIP_SEL.search(s)]
        if keep:
            cd = color_decls(decls, map_value)
            if cd:
                out_a.append(render(keep, cd))
        shared = [s for s in sels if not (classes_of(s) & missing) and not SKIP_SEL.search(s)]
        imp_decls = [(k, v, imp) for k, v, imp in decls if imp]
        if shared and imp_decls:
            cd = color_decls(imp_decls, map_value)
            # Only where Agata does not already set the same property as !important on that selector.
            for s in shared:
                own = agata_sel_props.get(s, {})
                cds = [d for d in cd if not own.get(d[0])]
                if cds:
                    out_b.append(render([s], cds))

    # (D) Stock colors on elements Agata styles but leaves this property unset (St-verified list).
    out_d = []
    gaps_file = gaps_dir / f"gaps-{theme_dir.name}.json"
    if not gaps_file.exists():
        raise SystemExit(f"missing {gaps_file}; run find_gaps.py first (regenerate-shell-layer.sh does)")
    last = {}
    for sels, decls in stock:
        for s in sels:
            for k, v, imp in decls:
                if not imp:
                    last[(s, k)] = v
    by_sel = {}
    for s, k in json.loads(gaps_file.read_text()):
        if KEEP_LITERAL.search(s) or (s, k) not in last:
            continue
        for kk, vv, _ in color_decls([(k, last[(s, k)], False)], map_value):
            orig = color_decls([(k, last[(s, k)], False)], normalize)
            if not orig or orig[0][1] != vv:
                by_sel.setdefault(s, []).append((kk, vv, False))
    out_d = [render([s], d) for s, d in by_sel.items()]

    # (C) Renamed widgets and targeted fixes, using Agata's own declarations.
    alias = []
    # Quick toggles with a menu: GNOME 47+ renamed .quick-menu-toggle/.quick-toggle-arrow. Port every
    # Agata rule for the old structure, layout included: Agata's plain `.quick-toggle { min-width:
    # 12em; border-radius: 10px }` would otherwise beat GNOME's stock `.quick-toggle-has-menu
    # .quick-toggle { min-width: auto }` (origin wins over specificity) and push the arrow out.
    # The menu button is also an .icon-button; the extra class out-ranks `.quick-settings .icon-button`.
    for sels, decls in agata:
        new = [s.replace(".quick-menu-toggle", ".quick-toggle-has-menu").replace(".quick-toggle-arrow", ".quick-toggle-menu-button.icon-button")
                .replace(":rtr", ":rtl") for s in sels if ".quick-menu-toggle" in s]
        if new:
            alias.append(render(new, decls))
    # Collapsed notification groups (GNOME 46+) stack later messages *behind* the first one, so the
    # cards must be opaque. Agata's menu cards are translucent overlays (`.popup-menu .message`), so
    # flatten each state onto Agata's menu background: same look, but the stack no longer shows through.
    menu_bg = to_rgba(agata_decls(agata, ".popup-menu .popup-menu-content", ("background-color",))[-1][1])
    for state in ("", ":hover", ":focus", ":active"):
        d = agata_decls(agata, f".popup-menu .message{state}", ("background-color",))
        if d:
            c = to_rgba(d[-1][1])
            flat = tuple(c[i] * c[3] + menu_bg[i] * (1 - c[3]) for i in range(3)) + (1.0,)
            alias.append(render([f".popup-menu .message-notification-group .message{state}"],
                                [("background-color", fmt(flat), False)]))
    # Screen recording/sharing pills are red/orange in every theme: keep white text on them
    # (Agata's #panel .panel-button color would otherwise win, giving dark text in Light).
    pills = [f"{p} .panel-button.{ind}{st}" for p in ("#panel", "#panel:overview", "#panel.unlock-screen", "#panel.login-screen")
             for ind in ("screen-recording-indicator", "screen-sharing-indicator")
             for st in ("", ":hover", ":focus", ":active", ":checked")]
    alias.append(render(pills, [("color", "#fafafb", False)]))
    for sels, decls in stock:                        # and keep GNOME's own pill colors in every state
        keep = [s for s in sels if re.search(r"screen-(recording|sharing)-indicator", s)]
        cd = [d for d in color_decls(decls, lambda v: v) if d[0] in ("box-shadow", "background-color")] if keep else []
        if cd:
            alias.append(render(keep, cd))
    # Scrollbar handles: StButton#vhandle (old) -> .vhandle (GNOME 46+).
    for state in ["", ":hover", ":active"]:
        d = agata_decls(agata, f"StScrollBar StButton#vhandle{state}", ("background-color",))
        if d:
            alias.append(render([f"StScrollBar > .vhandle{state}", f"StScrollBar > .hhandle{state}"], d))
    for state in ["", ":hover", ":active"]:
        d = agata_decls(agata, f"#unlockDialogNotifications StButton#vhandle{state}", ("background-color",))
        if d:
            alias.append(render([f"#unlockDialogNotifications > .vhandle{state}", f"#unlockDialogNotifications > .hhandle{state}"], d))
    # Toggle switches: GNOME 47+ draws the track in CSS and adds a .handle knob. Agata keeps its
    # SVG switch images, so hide the extra knob and the stock track color behind them.
    alias.append(render([".toggle-switch", ".toggle-switch:hover", ".toggle-switch:checked", ".toggle-switch:checked:hover"],
                        [("background-color", "transparent", False)]))
    alias.append(render([".toggle-switch .handle", ".toggle-switch:checked .handle"],
                        [("background-color", "transparent", False), ("box-shadow", "none", False)]))

    header = (f"{BEGIN}\n   Generated from the GNOME Shell {shell_version} default theme, recolored to {theme_dir.name}.\n"
              "   Covers widgets added or renamed since the Jasper base (quick toggles with menus,\n"
              "   notification groups, toggle-switch knobs, scrollbar handles, lock-screen auth, ...)\n"
              "   and stock !important accent colors. Precomputed colors: works without st-mix().\n"
              "   Kept first in the file so Agata's own rules below win ties. */\n\n")
    block = header + "/* (A) GNOME 47+ widgets Agata does not style */\n" + "\n".join(out_a) + \
        "\n/* (B) Stock !important colors that would override Agata */\n" + "\n".join(out_b) + \
        "\n/* (D) Stock colors on styled elements where Agata leaves the property unset */\n" + "\n".join(out_d) + \
        "\n/* (C) Renamed widgets mapped to Agata's own colors */\n" + "\n".join(alias) + END + "\n\n"
    return path, block + text, (len(out_a), len(out_b), len(out_d), len(alias), len(missing))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stock", required=True, help="stock GNOME Shell gnome-shell-dark.css")
    ap.add_argument("--themes", required=True, type=pathlib.Path, help="the repo's themes/ directory")
    ap.add_argument("--gaps-dir", required=True, type=pathlib.Path, help="directory with gaps-<theme>.json")
    ap.add_argument("--shell-version", required=True, help="GNOME Shell major version, for the header")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="rewrite gnome-shell.css files")
    mode.add_argument("--check", action="store_true", help="exit 1 if any file would change")
    args = ap.parse_args()

    stock = parse(args.stock)
    changed = []
    for theme_dir in sorted(args.themes.glob("Agata-*")):
        path, new, (a, b, d, c, n_missing) = build(theme_dir, stock, args.gaps_dir, args.shell_version)
        same = path.read_text(encoding="utf-8") == new
        print(f"{theme_dir.name}: (A) {a}, (B) {b}, (D) {d}, (C) {c} rules; {n_missing} unstyled stock classes"
              f"{'' if same else ' [changed]'}")
        if not same:
            changed.append(path)
            if args.write:
                path.write_text(new, encoding="utf-8")
    if args.check and changed:
        sys.exit(1)


if __name__ == "__main__":
    main()
