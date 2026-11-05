#!/usr/bin/env python3
"""Generate the Agata app color schemes in extras/<app>/ from extras/palette.json.

  tools/gen-app-themes.py           write every extras/<app>/ scheme
  tools/gen-app-themes.py --check   exit 1 if any generated file would change

extras/palette.json is the single source of truth. For every variant it holds:
  ui        colors shared with the GTK theme (background, foreground, surface, elevated,
            accent, accent_foreground, accent_text); they are checked against the libadwaita
            palette block in themes/<variant>/gtk-4.0/gtk.css, so they cannot drift
  terminal  terminal-specific roles (text, cursor, selection, status bar, search matches)
  ansi      the 16 ANSI colors (normal, bright, optional dim)
  syntax    editor syntax roles (SYNTAX_ROLES: comment, keyword, function, type, string, ...),
            following the edition's own conventions (nord-vim for Nord, gruvbox for Gruvbox)
Where a variant declares min_contrast (e.g. {"normal": 4.5, "bright": 3.0, "syntax": 4.5,
"comment": 3.0}), the script also checks that those colors reach it on the background:
"normal" and "bright" for the ANSI groups, "syntax" for every syntax role except the comment,
"comment" for syntax.comment.

Adding an app: write a `render_<app>(name, v)` function that returns {output path: file text}
for a variant, register it in APPS, and add extras/<app>/README.md with install steps. Files that
several variants share (e.g. a dispatcher for an edition) may be returned by each of them, as long
as the text is identical.
"""
import json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXTRAS = ROOT / "extras"
PALETTE = EXTRAS / "palette.json"
ORDER = ["black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"]
CHROMATIC = ORDER[1:7]
SYNTAX_ROLES = ["comment", "keyword", "operator", "punctuation", "function", "function_builtin", "type",
                "type_builtin", "string", "escape", "number", "boolean", "constant", "constant_builtin", "variable",
                "variable_builtin", "parameter", "property", "module", "preproc", "decorator", "tag", "tag_attribute"]
GTK_NAMES = {"background": "window_bg_color", "foreground": "window_fg_color", "surface": "view_bg_color",
             "elevated": "card_bg_color", "accent": "accent_bg_color", "accent_foreground": "accent_fg_color",
             "accent_text": "accent_color"}


# ---------------------------------------------------------------- checks
def luminance(h):
    c = [int(h.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def mix(a, b, t):
    """a with t (0..1) of b mixed in, in sRGB."""
    pa, pb = ([int(h[i:i + 2], 16) for i in (1, 3, 5)] for h in (a, b))
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(pa, pb))


def readable_on(bg, *candidates):
    return max(candidates, key=lambda c: contrast(c, bg))


def check_variant(name, v):
    problems = []
    css = (ROOT / "themes" / name / "gtk-4.0" / "gtk.css").read_text(encoding="utf-8")
    for role, gtk_name in GTK_NAMES.items():
        m = re.search(rf"@define-color {gtk_name} (#[0-9A-Fa-f]{{6}});", css)
        if not m:
            problems.append(f"@define-color {gtk_name} missing in GTK theme (run tools/add-libadwaita-palette.py)")
        elif m.group(1).lower() != v["ui"][role].lower():
            problems.append(f"ui.{role} {v['ui'][role]} != GTK {gtk_name} {m.group(1)}")
    if list(v.get("syntax", {})) != SYNTAX_ROLES:
        problems.append(f"syntax roles must be exactly, in order: {', '.join(SYNTAX_ROLES)}")
        return problems
    bg = v["ui"]["background"]
    for group, target in v.get("min_contrast", {}).items():
        if group in ("normal", "bright"):
            colors = {f"ansi.{group}.{k}": v["ansi"][group][k] for k in CHROMATIC}
        elif group == "syntax":
            colors = {f"syntax.{k}": c for k, c in v["syntax"].items() if k != "comment"}
        elif group == "comment":
            colors = {"syntax.comment": v["syntax"]["comment"]}
        else:
            problems.append(f"unknown min_contrast group {group!r}")
            continue
        for label, color in colors.items():
            c = contrast(color, bg)
            if c < target - 0.005:
                problems.append(f"{label} {color} only {c:.2f}:1 (want {target}:1)")
    return problems


# ---------------------------------------------------------------- renderers
def accent_bar(v):
    """(bar color, text color) for selection bars: the accent shade (accent or accent_text) and
    text color (background or terminal foreground) with the highest contrast."""
    ui, t = v["ui"], v["terminal"]
    return max(((s, c) for s in (ui["accent"], ui["accent_text"]) for c in (ui["background"], t["foreground"])),
               key=lambda p: contrast(p[1], p[0]))


def header(prefix, name, v):
    lines = [f"{v['title']} color scheme, generated by tools/gen-app-themes.py from extras/palette.json.",
             f"Matches the {name} GTK / GNOME Shell theme ({PAL['homepage']})."]
    return "".join(f"{prefix} {l}\n" for l in lines)


def render_alacritty(name, v):
    ui, t, a = v["ui"], v["terminal"], v["ansi"]
    sec = lambda title, d: f"\n[{title}]\n" + "".join(f'{k} = "{val}"\n' for k, val in d.items())
    out = header("#", name, v)
    out += sec("colors.primary", dict(background=ui["background"], foreground=t["foreground"],
                                      dim_foreground=t["foreground_dim"], bright_foreground=t["foreground_bright"]))
    out += sec("colors.cursor", dict(text=ui["background"], cursor=t["cursor"]))
    out += sec("colors.vi_mode_cursor", dict(text=ui["background"], cursor=t["match"]))
    out += sec("colors.selection", dict(text="CellForeground", background=t["selection"]))
    out += sec("colors.search.matches", dict(foreground="CellBackground", background=t["match"]))
    out += sec("colors.search.focused_match", dict(foreground="CellBackground", background=t["match_focused"]))
    out += sec("colors.hints.start", dict(foreground=ui["background"], background=t["match_focused"]))
    out += sec("colors.hints.end", dict(foreground=ui["background"], background=t["match"]))
    out += sec("colors.footer_bar", dict(foreground=t["foreground"], background=t["bar"]))
    for group in ("normal", "bright", "dim"):
        if group in a:
            out += sec(f"colors.{group}", {k: a[group][k] for k in ORDER})
    return out


def render_ghostty(name, v):
    ui, t, a = v["ui"], v["terminal"], v["ansi"]
    out = header("#", name, v)
    out += "".join(f"palette = {i}={a['normal'][k]}\n" for i, k in enumerate(ORDER))
    out += "".join(f"palette = {i + 8}={a['bright'][k]}\n" for i, k in enumerate(ORDER))
    out += (f"background = {ui['background']}\nforeground = {t['foreground']}\n"
            f"cursor-color = {t['cursor']}\ncursor-text = {ui['background']}\n"
            f"selection-background = {t['selection']}\nselection-foreground = {t['foreground']}\n")
    return out


MC_LINES = dict(horiz="─", vert="│", lefttop="╭", righttop="╮", leftbottom="╰", rightbottom="╯",
                topmiddle="┬", bottommiddle="┴", leftmiddle="├", rightmiddle="┤", cross="┼")


def render_mc(name, v):
    """Midnight Commander true-color skin.

    Panels, command line, editor and viewer use the terminal background, so mc blends in with the
    Agata terminal schemes. Dialogs and menus sit on the GTK view color (surface), like Agata's own
    dialogs. The cursor bar is an accent bar whose shade and text color are picked per variant for
    the best contrast; hotkeys are accent-colored and underlined like GTK mnemonics. File types
    use the variant's readable ANSI colors (bright on dark, normal on light), following ls. Error
    dialogs sit on the normal ANSI red, which is calmer than Gruvbox's bright red.
    """
    ui, t, a = v["ui"], v["terminal"], v["ansi"]
    bg, dark = ui["background"], v["appearance"] == "dark"
    hue = a["bright" if dark else "normal"]
    text = (bg, t["foreground"])
    cursor, cursor_text = accent_bar(v)
    aliases = {
        "Background": bg, "Surface": ui["surface"], "Elevated": ui["elevated"],
        "Shade": mix(bg, "#000000", 0.25 if dark else 0.12), "Selection": t["selection"],
        "Text": t["foreground"], "TextBright": t["foreground_bright"], "TextDim": t["foreground_dim"],
        "Faint": a["bright"]["black"], "Accent": ui["accent_text"],
        "Cursor": cursor, "CursorText": cursor_text,
        **{f"Ansi{k.title()}": hue[k] for k in CHROMATIC},
        "MarkedText": readable_on(hue["yellow"], *text),
        "Match": t["match"], "MatchText": readable_on(t["match"], *text), "MatchFocused": t["match_focused"],
        "Error": a["normal"]["red"], "ErrorText": readable_on(a["normal"]["red"], bg, t["foreground_bright"]),
        "DiffAdded": mix(bg, hue["green"], 0.25), "DiffRemoved": mix(bg, hue["red"], 0.25),
        "DiffChanged": mix(bg, hue["blue"], 0.25), "DiffChangedNew": mix(bg, hue["yellow"], 0.3),
    }
    sections = {
        "core": dict(
            _default_="Text;Background", selected="CursorText;Cursor", marked="AnsiYellow;;bold",
            markselect="MarkedText;AnsiYellow;bold", gauge="CursorText;Cursor", input="Text;Background",
            inputunchanged="TextDim;Background", inputmark="Text;Selection", disabled="TextDim;Surface",
            reverse="CursorText;Cursor", commandlinemark="Text;Selection", header="Accent;;bold",
            inputhistory="", commandhistory="", shadow="Faint;Shade"),
        "dialog": dict(
            _default_="Text;Surface", dfocus="CursorText;Cursor", dhotnormal="Accent;;underline",
            dhotfocus="CursorText;Cursor;underline", dtitle="Accent;;bold"),
        "error": dict(
            _default_="ErrorText;Error", errdfocus="Error;ErrorText", errdhotnormal=";;underline",
            errdhotfocus="Error;ErrorText;underline", errdtitle=";;bold"),
        "filehighlight": dict(
            directory="AnsiBlue;;bold", executable="AnsiGreen;;bold", symlink="AnsiCyan;;bold", hardlink="",
            stalelink="AnsiRed;;bold+underline", device="AnsiYellow;;bold", special="AnsiYellow",
            core="AnsiRed", temp="TextDim", archive="AnsiRed", doc="AnsiYellow", source="AnsiCyan",
            media="AnsiMagenta", graph="AnsiMagenta;;bold", database="AnsiGreen"),
        "menu": dict(
            _default_="Text;Surface", menusel="CursorText;Cursor", menuhot="Accent;;underline",
            menuhotsel="CursorText;Cursor;underline", menuinactive="Text;Surface"),
        "popupmenu": dict(_default_="Text;Surface", menusel="CursorText;Cursor", menutitle="Accent;;bold"),
        "buttonbar": dict(hotkey="Accent;Background", button="Text;Surface"),
        "statusbar": dict(_default_="Text;Surface"),
        "help": dict(
            _default_="Text;Surface", helpitalic="AnsiGreen;;italic", helpbold="TextBright;;bold",
            helplink="Accent;;underline", helpslink="CursorText;Cursor", helptitle="Accent;;bold"),
        "editor": dict(
            _default_="Text;Background", editbold="AnsiYellow;;bold", editmarked="Text;Selection",
            editwhitespace="Faint;Background", editnonprintable=";Shade", editlinestate="TextDim;Surface",
            bookmark="Text;Elevated", bookmarkfound="MatchText;Match", editrightmargin=";Surface",
            editbg=";Surface", editframe="TextDim", editframeactive="Accent", editframedrag="MatchFocused"),
        "viewer": dict(
            _default_="Text;Background", viewbold="TextBright;;bold", viewunderline="Accent;;underline",
            viewselected="MatchText;Match"),
        "diffviewer": dict(
            added="Text;DiffAdded", changedline="Text;DiffChanged", changednew="Text;DiffChangedNew;bold",
            changed="Text;DiffChanged", removed="Text;DiffRemoved", error="ErrorText;Error"),
        "widget-panel": {"sort-up-char": "▴", "sort-down-char": "▾", "hiddenfiles-show-char": "•",
                         "hiddenfiles-hide-char": "○", "history-prev-item-char": "◂",
                         "history-next-item-char": "▸", "history-show-list-char": "▾",
                         "filename-scroll-left-char": "◂", "filename-scroll-right-char": "▸"},
        "widget-scrollbar": {"first-vert-char": "▴", "last-vert-char": "▾", "first-horiz-char": "◂",
                             "last-horiz-char": "▸", "current-char": "■", "background-char": "░"},
        "widget-editor": {"window-state-char": "↕", "window-close-char": "✕"},
    }
    lines = {**MC_LINES, **{"d" + k: c for k, c in MC_LINES.items() if k not in ("cross",)}}
    sec = lambda title, d: f"\n[{title}]\n" + "".join(f"    {k} = {val}\n".replace(" \n", "\n") for k, val in d.items())
    out = header("#", name, v)
    out += "# Needs a true-color terminal (COLORTERM=truecolor) and mc built with S-Lang; see extras/mc/README.md.\n"
    out += sec("skin", dict(description=v["title"], truecolors="true"))
    out += sec("Lines", lines)
    out += sec("aliases", aliases)
    for title, d in sections.items():
        out += sec(title, d)
    return out


def nvim_palette(v):
    """UI colors of the Neovim scheme (the Lua table `c`); syntax colors come from v["syntax"] (`s`)."""
    ui, t, a = v["ui"], v["terminal"], v["ansi"]
    bg, dark = ui["background"], v["appearance"] == "dark"
    hue = a["bright" if dark else "normal"]
    bar, bar_text = accent_bar(v)
    on = lambda color: readable_on(color, bg, t["foreground_bright"])
    c = {"bg": bg, "surface": ui["surface"], "elevated": ui["elevated"], "selection": t["selection"],
         "fg": t["foreground"], "fg_bright": t["foreground_bright"], "fg_dim": t["foreground_dim"],
         "faint": a["bright"]["black"], "accent": ui["accent_text"], "cursor": t["cursor"],
         "bar": bar, "bar_fg": bar_text, "match": t["match"], "match_fg": on(t["match"]),
         "match_focused": t["match_focused"], "match_focused_fg": on(t["match_focused"])}
    c.update({k: hue[k] for k in CHROMATIC})
    c.update({f"on_{k}": on(hue[k]) for k in CHROMATIC})
    c.update(diff_add=mix(bg, hue["green"], 0.2), diff_delete=mix(bg, hue["red"], 0.2),
             diff_change=mix(bg, hue["blue"], 0.15), diff_text=mix(bg, hue["blue"], 0.35))
    for level, k in (("error", "red"), ("warn", "yellow"), ("info", "blue"), ("hint", "cyan"), ("ok", "green")):
        c[f"{level}_bg"] = mix(bg, hue[k], 0.12)
    return c


def nvim_groups():
    """Highlight groups: {name: spec dict | "Target" (a link)}. Values "c.x"/"s.x" refer to the Lua tables."""
    h = lambda fg=None, bg=None, **kw: {k: val for k, val in dict(fg=fg, bg=bg, **kw).items() if val is not None}
    g = {
        # editor UI
        "Normal": h("c.fg", "c.bg"), "NormalFloat": h("c.fg", "c.surface"), "FloatBorder": h("c.faint", "c.surface"),
        "FloatTitle": h("c.accent", "c.surface", bold=True), "FloatFooter": h("c.fg_dim", "c.surface"),
        "Cursor": h("c.bg", "c.cursor"), "lCursor": "Cursor", "CursorIM": "Cursor", "TermCursor": "Cursor",
        "CursorLine": h(bg="c.surface"), "CursorColumn": h(bg="c.surface"), "ColorColumn": h(bg="c.surface"),
        "CursorLineNr": h("c.fg_bright", bold=True), "LineNr": h("c.faint"), "LineNrAbove": "LineNr",
        "LineNrBelow": "LineNr", "SignColumn": h("c.faint", "c.bg"), "FoldColumn": h("c.faint", "c.bg"),
        "Folded": h("c.fg_dim", "c.surface"), "WinSeparator": h("c.selection"), "VertSplit": "WinSeparator",
        "StatusLine": h("c.fg", "c.surface"), "StatusLineNC": h("c.fg_dim", "c.surface"),
        "StatusLineTerm": "StatusLine", "StatusLineTermNC": "StatusLineNC",
        "TabLine": h("c.fg_dim", "c.surface"), "TabLineFill": h(bg="c.surface"),
        "TabLineSel": h("c.bar_fg", "c.bar", bold=True), "WinBar": h("c.fg", "c.bg", bold=True),
        "WinBarNC": h("c.fg_dim", "c.bg"),
        "Pmenu": h("c.fg", "c.surface"), "PmenuSel": h("c.bar_fg", "c.bar"), "PmenuSbar": h(bg="c.elevated"),
        "PmenuThumb": h(bg="c.faint"), "PmenuKind": h("c.accent", "c.surface"), "PmenuKindSel": "PmenuSel",
        "PmenuExtra": h("c.fg_dim", "c.surface"), "PmenuExtraSel": "PmenuSel",
        "PmenuMatch": h("c.accent", "c.surface", bold=True), "PmenuMatchSel": h("c.bar_fg", "c.bar", bold=True),
        "WildMenu": "PmenuSel", "Visual": h(bg="c.selection"), "VisualNOS": "Visual",
        "Search": h("c.match_fg", "c.match"), "IncSearch": h("c.match_focused_fg", "c.match_focused"),
        "CurSearch": "IncSearch", "Substitute": h("c.on_red", "c.red"),
        "MatchParen": h("c.match_focused", "c.selection", bold=True),
        "NonText": h("c.selection"), "EndOfBuffer": h("c.selection"), "Whitespace": h("c.selection"),
        "SpecialKey": h("c.faint"), "Conceal": h("c.faint"), "Directory": h("c.blue"),
        "Title": h("c.accent", bold=True), "ErrorMsg": h("c.red", bold=True), "WarningMsg": h("c.yellow"),
        "MoreMsg": h("c.green"), "ModeMsg": h("c.fg", bold=True), "Question": h("c.green"),
        "QuickFixLine": h(bg="c.surface", bold=True),
        "SpellBad": h(sp="c.red", undercurl=True), "SpellCap": h(sp="c.yellow", undercurl=True),
        "SpellLocal": h(sp="c.cyan", undercurl=True), "SpellRare": h(sp="c.magenta", undercurl=True),
        "DiffAdd": h(bg="c.diff_add"), "DiffChange": h(bg="c.diff_change"),
        "DiffDelete": h("c.red", "c.diff_delete"), "DiffText": h(bg="c.diff_text"),
        "Added": h("c.green"), "Changed": h("c.yellow"), "Removed": h("c.red"),
        "diffAdded": "Added", "diffChanged": "Changed", "diffRemoved": "Removed",
        # diagnostics and LSP
        **{f"Diagnostic{lv}": h(f"c.{k}") for lv, k in (("Error", "red"), ("Warn", "yellow"), ("Info", "blue"),
                                                          ("Hint", "cyan"), ("Ok", "green"))},
        **{f"DiagnosticVirtualText{lv}": h(f"c.{k}", f"c.{lv.lower()}_bg")
           for lv, k in (("Error", "red"), ("Warn", "yellow"), ("Info", "blue"), ("Hint", "cyan"), ("Ok", "green"))},
        **{f"DiagnosticUnderline{lv}": h(sp=f"c.{k}", undercurl=True)
           for lv, k in (("Error", "red"), ("Warn", "yellow"), ("Info", "blue"), ("Hint", "cyan"), ("Ok", "green"))},
        "DiagnosticUnnecessary": h("c.faint"), "DiagnosticDeprecated": h(sp="c.faint", strikethrough=True),
        "LspReferenceText": h(bg="c.elevated"), "LspReferenceRead": h(bg="c.elevated"),
        "LspReferenceWrite": h(bg="c.elevated", underline=True), "LspInlayHint": h("c.faint", italic=True),
        "LspCodeLens": h("c.faint"), "LspSignatureActiveParameter": h(bg="c.elevated", bold=True),
        # syntax
        "Comment": h("s.comment", italic=True), "Constant": h("s.constant"), "String": h("s.string"),
        "Character": h("s.string"), "Number": h("s.number"), "Float": "Number", "Boolean": h("s.boolean"),
        "Identifier": h("s.variable"), "Function": h("s.function"),
        **{k: h("s.keyword") for k in ("Statement", "Conditional", "Repeat", "Label", "Keyword", "Exception",
                                       "StorageClass")},
        "Operator": h("s.operator"),
        **{k: h("s.preproc") for k in ("PreProc", "Include", "Define", "Macro", "PreCondit")},
        "Type": h("s.type"), "Structure": h("s.type"), "Typedef": h("s.type"),
        "Special": h("s.escape"), "SpecialChar": h("s.escape"), "Tag": h("s.tag"), "Delimiter": h("s.punctuation"),
        "SpecialComment": h("s.comment", bold=True), "Debug": h("c.red"), "Underlined": h(underline=True),
        "Ignore": h("c.faint"), "Error": h("c.red", bold=True), "Todo": h("c.yellow", bold=True),
        # treesitter
        "@variable": h("s.variable"), "@variable.builtin": h("s.variable_builtin"),
        "@variable.parameter": h("s.parameter"), "@variable.member": h("s.property"), "@property": h("s.property"),
        "@constant": h("s.constant"), "@constant.builtin": h("s.constant_builtin"), "@constant.macro": h("s.preproc"),
        "@module": h("s.module"), "@module.builtin": h("s.module"), "@label": h("s.keyword"),
        "@string": h("s.string"), "@string.regexp": h("s.escape"), "@string.escape": h("s.escape"),
        "@string.special": h("s.escape"), "@string.special.symbol": h("s.constant"),
        "@string.special.url": h("c.accent", underline=True), "@character": h("s.string"),
        "@character.special": h("s.escape"), "@boolean": h("s.boolean"), "@number": h("s.number"),
        "@number.float": "@number", "@type": h("s.type"), "@type.builtin": h("s.type_builtin"),
        "@type.definition": h("s.type"), "@attribute": h("s.decorator"), "@attribute.builtin": h("s.decorator"),
        "@function": h("s.function"), "@function.builtin": h("s.function_builtin"), "@function.call": "@function",
        "@function.macro": h("s.preproc"), "@function.method": "@function", "@function.method.call": "@function",
        "@constructor": h("s.type"), "@operator": h("s.operator"), "@keyword": h("s.keyword"),
        "@keyword.import": h("s.preproc"), "@keyword.directive": h("s.preproc"),
        "@punctuation.delimiter": h("s.punctuation"), "@punctuation.bracket": h("s.punctuation"),
        "@punctuation.special": h("s.escape"), "@comment": "Comment", "@comment.documentation": "Comment",
        "@comment.error": h("c.red", bold=True), "@comment.warning": h("c.yellow", bold=True),
        "@comment.todo": h("c.yellow", bold=True), "@comment.note": h("c.cyan", bold=True),
        "@tag": h("s.tag"), "@tag.builtin": h("s.tag"), "@tag.attribute": h("s.tag_attribute"),
        "@tag.delimiter": h("s.punctuation"),
        "@markup.strong": h(bold=True), "@markup.italic": h(italic=True),
        "@markup.strikethrough": h(strikethrough=True), "@markup.underline": h(underline=True),
        "@markup.heading": h("c.accent", bold=True), "@markup.quote": h("c.fg_dim", italic=True),
        "@markup.math": h("s.number"), "@markup.link": h("c.accent"), "@markup.link.label": h("s.type"),
        "@markup.link.url": h("c.accent", underline=True), "@markup.raw": h("s.string"),
        "@markup.list": h("s.keyword"), "@markup.list.checked": h("c.green"),
        "@markup.list.unchecked": h("c.faint"),
        "@diff.plus": "Added", "@diff.minus": "Removed", "@diff.delta": "Changed",
        "@lsp.type.namespace": "@module", "@lsp.type.parameter": "@variable.parameter",
        "@lsp.type.property": "@property", "@lsp.mod.deprecated": h(strikethrough=True),
        # plugins
        "GitSignsAdd": h("c.green"), "GitSignsChange": h("c.yellow"), "GitSignsDelete": h("c.red"),
        "TelescopeNormal": "NormalFloat", "TelescopeBorder": "FloatBorder", "TelescopeTitle": "FloatTitle",
        "TelescopePromptPrefix": h("c.accent"), "TelescopeSelection": h("c.fg_bright", "c.elevated"),
        "TelescopeSelectionCaret": h("c.accent", "c.elevated"), "TelescopeMatching": h("c.accent", bold=True),
        "TelescopeMultiSelection": h("c.yellow"),
        "NeoTreeNormal": h("c.fg", "c.bg"), "NeoTreeNormalNC": "NeoTreeNormal", "NeoTreeDirectoryName": h("c.blue"),
        "NeoTreeDirectoryIcon": h("c.blue"), "NeoTreeRootName": h("c.accent", bold=True),
        "NeoTreeIndentMarker": h("c.selection"), "NeoTreeExpander": h("c.faint"), "NeoTreeDotfile": h("c.faint"),
        "NeoTreeFileNameOpened": h("c.fg_bright", bold=True), "NeoTreeGitAdded": h("c.green"),
        "NeoTreeGitModified": h("c.yellow"), "NeoTreeGitDeleted": h("c.red"), "NeoTreeGitUntracked": h("c.magenta"),
        "NeoTreeGitConflict": h("c.red", bold=True), "NeoTreeGitIgnored": h("c.faint"),
        "NeoTreeTitleBar": h("c.bar_fg", "c.bar"), "NeoTreeFloatBorder": "FloatBorder",
        "NeoTreeWinSeparator": h("c.selection", "c.bg"), "NeoTreeCursorLine": "CursorLine",
        "WhichKey": h("c.accent"), "WhichKeyGroup": h("s.function"), "WhichKeyDesc": h("c.fg"),
        "WhichKeySeparator": h("c.faint"), "WhichKeyValue": h("c.fg_dim"), "WhichKeyNormal": "NormalFloat",
        "WhichKeyFloat": "NormalFloat", "WhichKeyBorder": "FloatBorder",
        "NoiceCmdlinePopupBorder": h("c.accent"), "NoiceCmdlinePopupTitle": h("c.accent"),
        "NoiceCmdlineIcon": h("c.accent"), "NoiceCmdlinePopupBorderSearch": h("c.yellow"),
        "NoiceCmdlineIconSearch": h("c.yellow"), "NoiceConfirmBorder": h("c.accent"),
        "NotifyBackground": h(bg="c.bg"),
        **{f"Notify{lv}{part}": h(f"c.{k}") for lv, k in (("ERROR", "red"), ("WARN", "yellow"), ("INFO", "blue"),
                                                          ("DEBUG", "faint"), ("TRACE", "magenta"))
           for part in ("Border", "Icon", "Title")},
        "IblIndent": h("c.selection", nocombine=True), "IblWhitespace": h("c.selection", nocombine=True),
        "IblScope": h("c.faint", nocombine=True),
        "FlashBackdrop": h("c.faint"), "FlashMatch": h("c.match_fg", "c.match"), "FlashCurrent": "IncSearch",
        "FlashLabel": h("c.on_magenta", "c.magenta", bold=True),
        "CmpItemAbbr": h("c.fg"), "CmpItemAbbrMatch": h("c.accent", bold=True),
        "CmpItemAbbrMatchFuzzy": h("c.accent"), "CmpItemAbbrDeprecated": h("c.faint", strikethrough=True),
        "CmpItemMenu": h("c.fg_dim"), "CmpItemKind": h("c.accent"),
        "CmpItemKindFunction": "@function", "CmpItemKindMethod": "@function", "CmpItemKindConstructor": "@constructor",
        "CmpItemKindVariable": "@variable", "CmpItemKindField": "@property", "CmpItemKindProperty": "@property",
        "CmpItemKindClass": "@type", "CmpItemKindInterface": "@type", "CmpItemKindStruct": "@type",
        "CmpItemKindEnum": "@type", "CmpItemKindModule": "@module", "CmpItemKindKeyword": "@keyword",
        "CmpItemKindConstant": "@constant", "CmpItemKindSnippet": h("c.green"), "CmpItemKindText": h("c.fg_dim"),
        "BlinkCmpLabelMatch": h("c.accent", bold=True), "BlinkCmpKind": h("c.accent"),
        "DashboardHeader": h("c.accent"), "DashboardFooter": h("c.faint", italic=True), "DashboardDesc": h("c.fg"),
        "DashboardKey": h("c.yellow"), "DashboardIcon": h("c.cyan"), "DashboardShortCut": h("c.cyan"),
        "MasonHeader": h("c.bar_fg", "c.bar", bold=True), "MasonHighlight": h("c.accent"),
        "MasonHighlightBlockBold": h("c.bar_fg", "c.bar", bold=True), "MasonMutedBlock": h("c.fg", "c.elevated"),
        **{f"MiniIcons{n}": h(f"c.{k}") for n, k in (("Azure", "accent"), ("Blue", "blue"), ("Cyan", "cyan"),
                                                      ("Green", "green"), ("Grey", "fg_dim"), ("Orange", "yellow"),
                                                      ("Purple", "magenta"), ("Red", "red"), ("Yellow", "yellow"))},
    }
    return g


LUA_KEYWORDS = set("and break do else elseif end false for function goto if in local nil not or repeat "
                   "return then true until while".split())


def lua_table(d, links=False, indent="  "):
    """Lua table body from {key: hex | "c.x"/"s.x" reference | bool | spec dict | link name (links=True)}."""
    name_ok = lambda k: re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", k) and k not in LUA_KEYWORDS
    key = lambda k: k if name_ok(k) else f'["{k}"]'

    def val(x):
        if isinstance(x, bool):
            return "true" if x else "false"
        m = re.fullmatch(r"([cs])\.(\w+)", str(x))
        if m:
            return f"{m[1]}.{m[2]}" if name_ok(m[2]) else f'{m[1]}["{m[2]}"]'
        return f'"{x}"'
    out = []
    for k, spec in d.items():
        if isinstance(spec, dict):
            inner = ", ".join(f"{a} = {val(b)}" for a, b in spec.items())
            out.append(f"{indent}{key(k)} = {{ {inner} }},")
        elif links:
            out.append(f'{indent}{key(k)} = {{ link = "{spec}" }},')
        else:
            out.append(f"{indent}{key(k)} = {val(spec)},")
    return "\n".join(out)


NVIM_GROUPS = nvim_groups()


def render_neovim(name, v):
    """Neovim color scheme (colors/<name>.lua), a lualine theme for it, and per-edition dispatchers
    (colors/agata-<edition>.lua) that pick Dark or Light from 'background'."""
    scheme, edition = name.lower(), f"agata-{v['edition']}"
    c, a = nvim_palette(v), v["ansi"]
    term = [a["normal"][k] for k in ORDER] + [a["bright"][k] for k in ORDER]
    out = header("--", name, v)
    out += (f"-- Install: see extras/neovim/README.md. Load with :colorscheme {scheme}, or :colorscheme {edition}\n"
            f"-- to follow 'background'.\n\n")
    out += "local c = {\n" + lua_table(c) + "\n}\n\n"
    out += "local s = {\n" + lua_table(v["syntax"]) + "\n}\n\n"
    out += ('vim.cmd("highlight clear")\nif vim.fn.exists("syntax_on") == 1 then\n  vim.cmd("syntax reset")\nend\n'
            f'vim.o.background = "{v["appearance"]}"\nvim.g.colors_name = "{scheme}"\n\n')
    out += "local groups = {\n" + lua_table(NVIM_GROUPS, links=True) + "\n}\n\n"
    out += "for group, spec in pairs(groups) do\n  vim.api.nvim_set_hl(0, group, spec)\nend\n\n"
    out += "for i, color in ipairs({\n" + "".join(f'  "{x}",\n' for x in term) + "}) do\n"
    out += '  vim.g["terminal_color_" .. (i - 1)] = color\nend\n'

    mode = lambda k: f'{{ a = {{ fg = c.on_{k}, bg = c.{k}, gui = "bold" }} }}'
    lualine = header("--", name, v) + f"-- lualine theme for the {scheme} color scheme (lualine picks it up with theme = \"auto\").\n\n"
    lualine += "local c = {\n" + lua_table(c) + "\n}\n\n"
    lualine += ("return {\n"
                '  normal = {\n    a = { fg = c.bar_fg, bg = c.bar, gui = "bold" },\n'
                "    b = { fg = c.fg, bg = c.elevated },\n    c = { fg = c.fg, bg = c.surface },\n  },\n"
                f"  insert = {mode('green')},\n  visual = {mode('magenta')},\n  replace = {mode('red')},\n"
                f"  command = {mode('yellow')},\n  terminal = {mode('cyan')},\n"
                "  inactive = {\n    a = { fg = c.fg_dim, bg = c.surface },\n    b = { fg = c.fg_dim, bg = c.surface },\n"
                "    c = { fg = c.fg_dim, bg = c.surface },\n  },\n}\n")

    title = f"Agata {v['edition'].title()}"
    pick = 'vim.o.background == "light" and "light" or "dark"'
    dispatch_head = (f"-- {title} color scheme: Dark or Light according to 'background', which Neovim sets from the\n"
                     "-- terminal background at start-up. Generated by tools/gen-app-themes.py from extras/palette.json.\n\n")
    colors_dispatch = (dispatch_head + f"local variant = {pick}\n"
                       f'vim.cmd.runtime("colors/{edition}-" .. variant .. ".lua")\nvim.g.colors_name = "{edition}"\n')
    lualine_dispatch = (dispatch_head.replace("color scheme", "lualine theme") + f"local variant = {pick}\n"
                        f'return dofile(vim.api.nvim_get_runtime_file("lua/lualine/themes/{edition}-" .. variant .. ".lua", false)[1])\n')
    base = EXTRAS / "neovim"
    return {base / "colors" / f"{scheme}.lua": out,
            base / "lua" / "lualine" / "themes" / f"{scheme}.lua": lualine,
            base / "colors" / f"{edition}.lua": colors_dispatch,
            base / "lua" / "lualine" / "themes" / f"{edition}.lua": lualine_dispatch}


VSCODE_SCOPES = [
    # (TextMate scopes, syntax role or "c.x" UI color, fontStyle); later entries win on equal specificity
    (["comment", "punctuation.definition.comment", "string.comment"], "s.comment", "italic"),
    (["keyword", "storage", "storage.modifier", "keyword.control"], "s.keyword", None),
    (["keyword.operator", "punctuation.accessor", "punctuation.separator.key-value"],
     "s.operator", None),
    (["keyword.operator.expression", "keyword.operator.logical.python", "keyword.operator.new"], "s.keyword", None),
    (["punctuation", "meta.brace", "punctuation.definition.string", "punctuation.definition.parameters",
      "punctuation.definition.block"], "s.punctuation", None),
    (["entity.name.function", "meta.function-call.generic", "support.function", "entity.name.method"],
     "s.function", None),
    (["support.function.builtin", "support.function.std", "support.function.misc"], "s.function_builtin", None),
    (["entity.name.type", "entity.name.class", "entity.name.struct", "entity.name.enum", "entity.name.interface",
      "entity.other.inherited-class", "support.class", "support.type", "entity.name.type.class"], "s.type", None),
    (["storage.type", "support.type.primitive", "support.type.builtin", "keyword.type"], "s.type_builtin", None),
    (["string", "string.quoted", "string.template"], "s.string", None),
    (["constant.character.escape", "string.regexp", "constant.other.placeholder",
      "punctuation.definition.template-expression", "punctuation.section.embedded"], "s.escape", None),
    (["constant.numeric"], "s.number", None),
    (["constant.language.boolean"], "s.boolean", None),
    (["constant.language", "support.constant"], "s.constant_builtin", None),
    (["constant.other", "variable.other.constant", "variable.other.enummember", "constant.other.symbol"],
     "s.constant", None),
    (["variable", "meta.definition.variable.name", "support.variable"], "s.variable", None),
    (["variable.language", "variable.language.this", "variable.language.self", "variable.language.super"],
     "s.variable_builtin", None),
    (["variable.parameter", "meta.function.parameters variable"], "s.parameter", None),
    (["variable.other.property", "variable.other.object.property", "support.variable.property",
      "meta.object-literal.key", "entity.name.variable.field", "variable.other.member"], "s.property", None),
    (["entity.name.namespace", "entity.name.module", "entity.name.package", "entity.name.type.module",
      "support.other.namespace"], "s.module", None),
    (["meta.preprocessor", "keyword.control.import", "keyword.control.export", "keyword.control.from",
      "keyword.control.directive", "keyword.other.import", "keyword.other.package", "entity.name.function.preprocessor",
      "entity.name.function.macro"], "s.preproc", None),
    (["meta.decorator", "entity.name.function.decorator", "punctuation.decorator", "storage.type.annotation",
      "meta.attribute", "entity.other.attribute"], "s.decorator", None),
    (["entity.name.tag", "support.class.component"], "s.tag", None),
    (["entity.other.attribute-name"], "s.tag_attribute", None),
    (["punctuation.definition.tag"], "s.punctuation", None),
    (["markup.heading", "entity.name.section", "punctuation.definition.heading"], "c.accent", "bold"),
    (["markup.bold"], None, "bold"), (["markup.italic"], None, "italic"),
    (["markup.strikethrough"], None, "strikethrough"), (["markup.underline"], None, "underline"),
    (["markup.underline.link", "string.other.link", "markup.link"], "c.accent", None),
    (["markup.inline.raw", "markup.fenced_code", "markup.raw"], "s.string", None),
    (["markup.quote"], "c.fg_dim", "italic"),
    (["markup.list", "punctuation.definition.list"], "s.keyword", None),
    (["markup.inserted", "punctuation.definition.inserted"], "c.green", None),
    (["markup.deleted", "punctuation.definition.deleted"], "c.red", None),
    (["markup.changed", "punctuation.definition.changed"], "c.yellow", None),
    (["invalid", "invalid.illegal"], "c.red", None),
    (["invalid.deprecated"], "c.faint", "strikethrough"),
]

VSCODE_SEMANTIC = {
    "namespace": "s.module", "class": "s.type", "struct": "s.type", "interface": "s.type", "enum": "s.type",
    "type": "s.type", "typeParameter": "s.type", "enumMember": "s.constant", "parameter": "s.parameter",
    "property": "s.property", "variable": "s.variable", "variable.readonly": "s.constant",
    "variable.defaultLibrary": "s.variable_builtin", "function": "s.function", "method": "s.function",
    "function.defaultLibrary": "s.function_builtin", "type.defaultLibrary": "s.type_builtin",
    "class.defaultLibrary": "s.type_builtin", "macro": "s.preproc", "decorator": "s.decorator",
    "keyword": "s.keyword", "operator": "s.operator", "number": "s.number", "string": "s.string",
    "regexp": "s.escape", "comment": "s.comment", "selfKeyword": "s.variable_builtin",
    "builtinType": "s.type_builtin", "*.deprecated": {"strikethrough": True},
}


def vscode_package():
    """extras/vscode/package.json, shared by all variants: one extension that contributes every theme."""
    version = re.search(r"\*\*v(\d+\.\d+\.\d+)\*\*", (ROOT / "README.md").read_text(encoding="utf-8"))
    themes = [{"label": v["title"], "uiTheme": "vs-dark" if v["appearance"] == "dark" else "vs",
               "path": f"./themes/{name.lower()}-color-theme.json"} for name, v in PAL["variants"].items()]
    pkg = {"name": "agata-theme", "displayName": "Agata", "publisher": "palpinter",
           "description": "Color themes matching the Agata GTK / GNOME Shell theme (Nord and Gruvbox, Dark and Light). "
                          "Generated by tools/gen-app-themes.py from extras/palette.json.",
           "version": version[1] if version else "0.0.0", "license": "GPL-3.0-or-later",
           "repository": {"type": "git", "url": PAL["homepage"]}, "engines": {"vscode": "^1.70.0"},
           "categories": ["Themes"], "contributes": {"themes": themes}}
    return json.dumps(pkg, indent=2, ensure_ascii=False) + "\n"


def render_vscode(name, v):
    """VS Code color theme (themes/<name>-color-theme.json) plus the shared extension manifest.

    The UI follows the Neovim scheme (nvim_palette): editor, side bar, panel and terminal on the
    terminal background, status bar and tab strip on the GTK view color (surface), widgets (find,
    hover, suggest, quick input) on surface like Neovim floats, menus on the GTK popover color
    (elevated), selections as accent bars. Syntax colors are the palette's syntax roles, for
    TextMate scopes and semantic tokens alike.
    """
    c, s, a, t = nvim_palette(v), v["syntax"], v["ansi"], v["terminal"]
    dark = v["appearance"] == "dark"
    ref = lambda x: (c if x[0] == "c" else s)[x[2:]]
    alpha = lambda color, f: color + f"{round(f * 255):02x}"
    shadow = "#00000066" if dark else "#00000029"
    border = c["selection"]
    col = {
        # base
        "foreground": c["fg"], "descriptionForeground": c["fg_dim"], "disabledForeground": c["faint"],
        "errorForeground": c["red"], "icon.foreground": c["fg"], "focusBorder": c["accent"],
        "contrastBorder": None, "widget.shadow": shadow, "widget.border": c["elevated"],
        "selection.background": alpha(c["accent"], 0.4), "sash.hoverBorder": c["accent"],
        "textLink.foreground": c["accent"], "textLink.activeForeground": c["accent"],
        "textPreformat.foreground": s["string"], "textPreformat.background": c["surface"],
        "textCodeBlock.background": c["surface"], "textBlockQuote.background": c["surface"],
        "textBlockQuote.border": c["accent"], "textSeparator.foreground": border,
        "toolbar.hoverBackground": c["elevated"], "toolbar.activeBackground": c["selection"],
        # buttons and inputs
        "button.background": c["bar"], "button.foreground": c["bar_fg"],
        "button.hoverBackground": mix(c["bar"], c["fg_bright"] if dark else c["bg"], 0.15),
        "button.secondaryBackground": c["elevated"], "button.secondaryForeground": c["fg"],
        "button.secondaryHoverBackground": c["selection"], "button.separator": alpha(c["bar_fg"], 0.4),
        "button.border": None,
        "dropdown.background": c["surface"], "dropdown.listBackground": c["surface"],
        "dropdown.border": c["elevated"], "dropdown.foreground": c["fg"],
        "input.background": c["surface"], "input.border": c["elevated"], "input.foreground": c["fg"],
        "input.placeholderForeground": c["faint"], "inputOption.activeBackground": alpha(c["accent"], 0.3),
        "inputOption.activeBorder": c["accent"], "inputOption.activeForeground": c["fg_bright"],
        "inputOption.hoverBackground": c["elevated"],
        "inputValidation.errorBackground": c["error_bg"], "inputValidation.errorBorder": c["red"],
        "inputValidation.warningBackground": c["warn_bg"], "inputValidation.warningBorder": c["yellow"],
        "inputValidation.infoBackground": c["info_bg"], "inputValidation.infoBorder": c["blue"],
        "checkbox.background": c["surface"], "checkbox.border": c["elevated"], "checkbox.foreground": c["fg"],
        "checkbox.selectBackground": c["surface"], "checkbox.selectBorder": c["accent"],
        "radio.activeBackground": c["bar"], "radio.activeForeground": c["bar_fg"], "radio.activeBorder": c["bar"],
        "radio.inactiveBackground": c["surface"], "radio.inactiveForeground": c["fg"],
        "radio.inactiveBorder": c["elevated"],
        "badge.background": c["bar"], "badge.foreground": c["bar_fg"], "progressBar.background": c["accent"],
        "scrollbar.shadow": shadow, "scrollbarSlider.background": alpha(c["faint"], 0.3),
        "scrollbarSlider.hoverBackground": alpha(c["faint"], 0.5),
        "scrollbarSlider.activeBackground": alpha(c["faint"], 0.7),
        "keybindingLabel.background": c["surface"], "keybindingLabel.foreground": c["fg"],
        "keybindingLabel.border": c["elevated"], "keybindingLabel.bottomBorder": c["elevated"],
        # lists and trees
        "list.activeSelectionBackground": c["bar"], "list.activeSelectionForeground": c["bar_fg"],
        "list.activeSelectionIconForeground": c["bar_fg"], "list.inactiveSelectionBackground": c["elevated"],
        "list.inactiveSelectionForeground": c["fg_bright"], "list.hoverBackground": c["surface"],
        "list.hoverForeground": c["fg_bright"], "list.focusOutline": c["accent"],
        "list.focusAndSelectionOutline": c["bar"], "list.inactiveFocusOutline": c["elevated"],
        "list.highlightForeground": c["accent"], "list.focusHighlightForeground": c["bar_fg"],
        "list.dropBackground": alpha(c["accent"], 0.25), "list.errorForeground": c["red"],
        "list.warningForeground": c["yellow"], "list.invalidItemForeground": c["red"],
        "list.deemphasizedForeground": c["faint"], "listFilterWidget.background": c["surface"],
        "listFilterWidget.outline": c["accent"], "listFilterWidget.noMatchesOutline": c["red"],
        "tree.indentGuidesStroke": c["selection"], "tree.inactiveIndentGuidesStroke": alpha(c["selection"], 0.6),
        # workbench parts
        "titleBar.activeBackground": c["bg"], "titleBar.activeForeground": c["fg"],
        "titleBar.inactiveBackground": c["bg"], "titleBar.inactiveForeground": c["fg_dim"], "titleBar.border": border,
        "commandCenter.background": c["surface"], "commandCenter.foreground": c["fg"],
        "commandCenter.activeBackground": c["elevated"], "commandCenter.border": c["elevated"],
        "commandCenter.inactiveBorder": c["surface"],
        "menubar.selectionBackground": c["elevated"], "menubar.selectionForeground": c["fg_bright"],
        "menu.background": c["elevated"], "menu.foreground": c["fg"], "menu.border": c["selection"],
        "menu.selectionBackground": c["bar"], "menu.selectionForeground": c["bar_fg"],
        "menu.separatorBackground": c["selection"],
        "activityBar.background": c["bg"], "activityBar.foreground": c["fg"],
        "activityBar.inactiveForeground": c["fg_dim"], "activityBar.activeBorder": c["accent"],
        "activityBar.activeBackground": c["surface"], "activityBar.border": border,
        "activityBarBadge.background": c["bar"], "activityBarBadge.foreground": c["bar_fg"],
        "activityBarTop.foreground": c["fg"], "activityBarTop.inactiveForeground": c["fg_dim"],
        "activityBarTop.activeBorder": c["accent"],
        "sideBar.background": c["bg"], "sideBar.foreground": c["fg"], "sideBar.border": border,
        "sideBarTitle.foreground": c["fg"], "sideBarSectionHeader.background": c["bg"],
        "sideBarSectionHeader.foreground": c["fg"], "sideBarSectionHeader.border": border,
        "sideBar.dropBackground": alpha(c["accent"], 0.2),
        "editorGroup.border": border, "editorGroup.dropBackground": alpha(c["accent"], 0.2),
        "editorGroupHeader.tabsBackground": c["surface"], "editorGroupHeader.tabsBorder": border,
        "editorGroupHeader.noTabsBackground": c["bg"],
        "tab.activeBackground": c["bg"], "tab.activeForeground": c["fg_bright"], "tab.activeBorderTop": c["accent"],
        "tab.inactiveBackground": c["surface"], "tab.inactiveForeground": c["fg_dim"], "tab.border": border,
        "tab.hoverBackground": c["bg"], "tab.hoverForeground": c["fg"],
        "tab.unfocusedActiveBackground": c["bg"], "tab.unfocusedActiveForeground": c["fg"],
        "tab.unfocusedActiveBorderTop": c["faint"], "tab.unfocusedInactiveBackground": c["surface"],
        "tab.unfocusedInactiveForeground": c["faint"], "tab.lastPinnedBorder": c["selection"],
        "tab.activeModifiedBorder": c["yellow"], "tab.inactiveModifiedBorder": alpha(c["yellow"], 0.6),
        "breadcrumb.background": c["bg"], "breadcrumb.foreground": c["fg_dim"],
        "breadcrumb.focusForeground": c["fg"], "breadcrumb.activeSelectionForeground": c["accent"],
        "breadcrumbPicker.background": c["surface"],
        "panel.background": c["bg"], "panel.border": border, "panel.dropBorder": c["accent"],
        "panelTitle.activeForeground": c["fg"], "panelTitle.activeBorder": c["accent"],
        "panelTitle.inactiveForeground": c["fg_dim"], "panelInput.border": c["elevated"],
        "panelSection.border": border, "panelSectionHeader.background": c["surface"],
        "outputView.background": c["bg"],
        "statusBar.background": c["surface"], "statusBar.foreground": c["fg"], "statusBar.border": border,
        "statusBar.noFolderBackground": c["surface"], "statusBar.noFolderForeground": c["fg"],
        "statusBar.debuggingBackground": c["yellow"], "statusBar.debuggingForeground": c["on_yellow"],
        "statusBar.debuggingBorder": c["yellow"], "statusBar.focusBorder": c["accent"],
        "statusBarItem.hoverBackground": c["elevated"], "statusBarItem.activeBackground": c["selection"],
        "statusBarItem.remoteBackground": c["bar"], "statusBarItem.remoteForeground": c["bar_fg"],
        "statusBarItem.prominentBackground": c["bar"], "statusBarItem.prominentForeground": c["bar_fg"],
        "statusBarItem.errorBackground": c["red"], "statusBarItem.errorForeground": c["on_red"],
        "statusBarItem.warningBackground": c["yellow"], "statusBarItem.warningForeground": c["on_yellow"],
        "statusBarItem.focusBorder": c["accent"],
        "quickInput.background": c["surface"], "quickInput.foreground": c["fg"],
        "quickInputTitle.background": c["elevated"], "quickInputList.focusBackground": c["bar"],
        "quickInputList.focusForeground": c["bar_fg"], "quickInputList.focusIconForeground": c["bar_fg"],
        "pickerGroup.foreground": c["accent"], "pickerGroup.border": c["selection"],
        "notifications.background": c["surface"], "notifications.foreground": c["fg"],
        "notifications.border": c["elevated"], "notificationCenterHeader.background": c["elevated"],
        "notificationCenterHeader.foreground": c["fg"], "notificationToast.border": c["elevated"],
        "notificationLink.foreground": c["accent"], "notificationsErrorIcon.foreground": c["red"],
        "notificationsWarningIcon.foreground": c["yellow"], "notificationsInfoIcon.foreground": c["blue"],
        "banner.background": c["elevated"], "banner.foreground": c["fg"], "banner.iconForeground": c["accent"],
        "debugToolBar.background": c["elevated"], "debugToolBar.border": c["selection"],
        "settings.headerForeground": c["accent"], "settings.modifiedItemIndicator": c["yellow"],
        "settings.focusedRowBackground": c["surface"], "settings.rowHoverBackground": c["surface"],
        "settings.focusedRowBorder": c["accent"],
        "welcomePage.tileBackground": c["surface"], "welcomePage.tileHoverBackground": c["elevated"],
        "welcomePage.tileBorder": c["elevated"], "walkThrough.embeddedEditorBackground": c["surface"],
        "extensionButton.prominentBackground": c["bar"], "extensionButton.prominentForeground": c["bar_fg"],
        "extensionButton.prominentHoverBackground": mix(c["bar"], c["fg_bright"] if dark else c["bg"], 0.15),
        "extensionBadge.remoteBackground": c["bar"], "extensionBadge.remoteForeground": c["bar_fg"],
        "extensionIcon.starForeground": c["yellow"],
        # editor
        "editor.background": c["bg"], "editor.foreground": c["fg"], "editorCursor.foreground": c["cursor"],
        "editorCursor.background": c["bg"], "editor.lineHighlightBackground": c["surface"],
        "editor.lineHighlightBorder": c["surface"], "editorLineNumber.foreground": c["faint"],
        "editorLineNumber.activeForeground": c["fg_bright"], "editorLineNumber.dimmedForeground": c["selection"],
        "editor.selectionBackground": c["selection"], "editor.inactiveSelectionBackground": alpha(c["selection"], 0.6),
        "editor.selectionHighlightBackground": alpha(c["accent"], 0.2),
        "editor.wordHighlightBackground": alpha(c["elevated"], 0.8),
        "editor.wordHighlightStrongBackground": alpha(c["elevated"], 0.8),
        "editor.wordHighlightStrongBorder": c["faint"],
        "editor.findMatchBackground": alpha(c["match_focused"], 0.4), "editor.findMatchBorder": c["match_focused"],
        "editor.findMatchHighlightBackground": alpha(c["match"], 0.3),
        "editor.findRangeHighlightBackground": alpha(c["surface"], 0.8),
        "editor.rangeHighlightBackground": alpha(c["elevated"], 0.5),
        "editor.hoverHighlightBackground": alpha(c["elevated"], 0.6),
        "editor.foldBackground": alpha(c["surface"], 0.7), "editor.foldPlaceholderForeground": c["fg_dim"],
        "editorLink.activeForeground": c["accent"],
        "editorWhitespace.foreground": c["selection"], "editorIndentGuide.background1": c["selection"],
        "editorIndentGuide.activeBackground1": c["faint"], "editorRuler.foreground": c["selection"],
        "editorCodeLens.foreground": c["faint"], "editorInlayHint.foreground": c["faint"],
        "editorInlayHint.background": alpha(c["surface"], 0.8), "editorGhostText.foreground": c["faint"],
        "editorBracketMatch.background": c["selection"], "editorBracketMatch.border": c["match_focused"],
        "editorBracketHighlight.foreground1": c["yellow"], "editorBracketHighlight.foreground2": c["magenta"],
        "editorBracketHighlight.foreground3": c["blue"], "editorBracketHighlight.foreground4": c["green"],
        "editorBracketHighlight.foreground5": c["cyan"], "editorBracketHighlight.foreground6": c["red"],
        "editorBracketHighlight.unexpectedBracket.foreground": c["red"],
        "editorUnnecessaryCode.opacity": "#000000a0",
        "editorError.foreground": c["red"], "editorWarning.foreground": c["yellow"],
        "editorInfo.foreground": c["blue"], "editorHint.foreground": c["cyan"],
        "problemsErrorIcon.foreground": c["red"], "problemsWarningIcon.foreground": c["yellow"],
        "problemsInfoIcon.foreground": c["blue"],
        "editorLightBulb.foreground": c["yellow"], "editorLightBulbAutoFix.foreground": c["accent"],
        "editorGutter.background": c["bg"], "editorGutter.addedBackground": c["green"],
        "editorGutter.modifiedBackground": c["yellow"], "editorGutter.deletedBackground": c["red"],
        "editorGutter.foldingControlForeground": c["fg_dim"],
        "editorOverviewRuler.border": border, "editorOverviewRuler.addedForeground": alpha(c["green"], 0.6),
        "editorOverviewRuler.modifiedForeground": alpha(c["yellow"], 0.6),
        "editorOverviewRuler.deletedForeground": alpha(c["red"], 0.6),
        "editorOverviewRuler.errorForeground": c["red"], "editorOverviewRuler.warningForeground": c["yellow"],
        "editorOverviewRuler.infoForeground": c["blue"],
        "editorOverviewRuler.findMatchForeground": alpha(c["match_focused"], 0.8),
        "editorOverviewRuler.selectionHighlightForeground": alpha(c["accent"], 0.6),
        "minimap.background": c["bg"], "minimap.selectionHighlight": c["selection"],
        "minimap.findMatchHighlight": c["match_focused"], "minimap.errorHighlight": c["red"],
        "minimap.warningHighlight": c["yellow"], "minimapGutter.addedBackground": c["green"],
        "minimapGutter.modifiedBackground": c["yellow"], "minimapGutter.deletedBackground": c["red"],
        "minimapSlider.background": alpha(c["faint"], 0.2), "minimapSlider.hoverBackground": alpha(c["faint"], 0.35),
        "minimapSlider.activeBackground": alpha(c["faint"], 0.5),
        "editorStickyScroll.background": c["bg"], "editorStickyScroll.shadow": shadow,
        "editorStickyScrollHover.background": c["surface"],
        # editor widgets (Neovim floats)
        "editorWidget.background": c["surface"], "editorWidget.foreground": c["fg"],
        "editorWidget.border": c["elevated"], "editorWidget.resizeBorder": c["accent"],
        "editorHoverWidget.background": c["surface"], "editorHoverWidget.foreground": c["fg"],
        "editorHoverWidget.border": c["elevated"], "editorHoverWidget.highlightForeground": c["accent"],
        "editorHoverWidget.statusBarBackground": c["elevated"],
        "editorSuggestWidget.background": c["surface"], "editorSuggestWidget.foreground": c["fg"],
        "editorSuggestWidget.border": c["elevated"], "editorSuggestWidget.selectedBackground": c["bar"],
        "editorSuggestWidget.selectedForeground": c["bar_fg"], "editorSuggestWidget.selectedIconForeground": c["bar_fg"],
        "editorSuggestWidget.highlightForeground": c["accent"],
        "editorSuggestWidget.focusHighlightForeground": c["bar_fg"],
        "editorSuggestWidgetStatus.foreground": c["fg_dim"],
        "editorMarkerNavigation.background": c["surface"], "editorMarkerNavigationError.background": c["red"],
        "editorMarkerNavigationWarning.background": c["yellow"], "editorMarkerNavigationInfo.background": c["blue"],
        "peekView.border": c["accent"], "peekViewEditor.background": c["surface"],
        "peekViewEditorGutter.background": c["surface"], "peekViewEditor.matchHighlightBackground": alpha(c["match_focused"], 0.4),
        "peekViewResult.background": c["surface"], "peekViewResult.fileForeground": c["fg_bright"],
        "peekViewResult.lineForeground": c["fg"], "peekViewResult.matchHighlightBackground": alpha(c["match_focused"], 0.4),
        "peekViewResult.selectionBackground": c["bar"], "peekViewResult.selectionForeground": c["bar_fg"],
        "peekViewTitle.background": c["elevated"], "peekViewTitleLabel.foreground": c["fg_bright"],
        "peekViewTitleDescription.foreground": c["fg_dim"],
        # diff, merge, git
        "diffEditor.insertedTextBackground": alpha(c["green"], 0.25),
        "diffEditor.removedTextBackground": alpha(c["red"], 0.25),
        "diffEditor.insertedLineBackground": alpha(c["green"], 0.12),
        "diffEditor.removedLineBackground": alpha(c["red"], 0.12),
        "diffEditor.diagonalFill": c["selection"], "diffEditor.border": border,
        "diffEditorGutter.insertedLineBackground": alpha(c["green"], 0.25),
        "diffEditorGutter.removedLineBackground": alpha(c["red"], 0.25),
        "diffEditor.unchangedRegionBackground": c["surface"],
        "merge.currentHeaderBackground": alpha(c["green"], 0.5), "merge.currentContentBackground": alpha(c["green"], 0.15),
        "merge.incomingHeaderBackground": alpha(c["blue"], 0.5), "merge.incomingContentBackground": alpha(c["blue"], 0.15),
        "merge.commonHeaderBackground": alpha(c["faint"], 0.5), "merge.commonContentBackground": alpha(c["faint"], 0.15),
        "gitDecoration.addedResourceForeground": c["green"], "gitDecoration.modifiedResourceForeground": c["yellow"],
        "gitDecoration.deletedResourceForeground": c["red"], "gitDecoration.renamedResourceForeground": c["cyan"],
        "gitDecoration.untrackedResourceForeground": c["magenta"], "gitDecoration.ignoredResourceForeground": c["faint"],
        "gitDecoration.conflictingResourceForeground": c["red"], "gitDecoration.submoduleResourceForeground": c["cyan"],
        "gitDecoration.stageModifiedResourceForeground": c["yellow"],
        "gitDecoration.stageDeletedResourceForeground": c["red"],
        "scmGraph.historyItemRefColor": c["accent"], "scmGraph.foreground1": c["blue"],
        "scmGraph.foreground2": c["green"], "scmGraph.foreground3": c["magenta"],
        "scmGraph.foreground4": c["yellow"], "scmGraph.foreground5": c["cyan"],
        # terminal
        "terminal.background": c["bg"], "terminal.foreground": t["foreground"], "terminal.border": border,
        "terminalCursor.foreground": t["cursor"], "terminalCursor.background": c["bg"],
        "terminal.selectionBackground": t["selection"], "terminal.findMatchBackground": alpha(t["match_focused"], 0.4),
        "terminal.findMatchHighlightBackground": alpha(t["match"], 0.3),
        **{f"terminal.ansi{'Bright' if g == 'bright' else ''}{k.title()}": a[g][k]
           for g in ("normal", "bright") for k in ORDER},
        "terminalCommandDecoration.defaultBackground": c["faint"],
        "terminalCommandDecoration.successBackground": c["green"],
        "terminalCommandDecoration.errorBackground": c["red"],
        # charts, testing, debugging
        "charts.foreground": c["fg"], "charts.lines": c["faint"], "charts.red": c["red"], "charts.blue": c["blue"],
        "charts.yellow": c["yellow"], "charts.orange": s["decorator"], "charts.green": c["green"],
        "charts.purple": c["magenta"],
        "testing.iconPassed": c["green"], "testing.iconFailed": c["red"], "testing.iconErrored": c["red"],
        "testing.iconQueued": c["yellow"], "testing.iconSkipped": c["faint"], "testing.runAction": c["green"],
        "debugIcon.breakpointForeground": c["red"], "debugIcon.startForeground": c["green"],
        "debugIcon.stopForeground": c["red"], "debugIcon.continueForeground": c["accent"],
        "debugIcon.pauseForeground": c["yellow"], "debugIcon.restartForeground": c["green"],
        "editor.stackFrameHighlightBackground": alpha(c["yellow"], 0.2),
        "editor.focusedStackFrameHighlightBackground": alpha(c["green"], 0.2),
        "debugTokenExpression.name": s["property"], "debugTokenExpression.value": c["fg"],
        "debugTokenExpression.string": s["string"], "debugTokenExpression.number": s["number"],
        "debugTokenExpression.boolean": s["boolean"], "debugTokenExpression.error": c["red"],
    }
    col = {k: val for k, val in col.items() if val is not None}
    rules = []
    for scopes, color, style in VSCODE_SCOPES:
        settings = {}
        if color:
            settings["foreground"] = ref(color)
        if style:
            settings["fontStyle"] = style
        rules.append({"scope": scopes, "settings": settings})
    semantic = {k: (ref(x) if isinstance(x, str) else x) for k, x in VSCODE_SEMANTIC.items()}
    theme = {"$schema": "vscode://schemas/color-theme", "name": v["title"],
             "type": v["appearance"], "semanticHighlighting": True, "colors": col,
             "tokenColors": rules, "semanticTokenColors": semantic}
    base = EXTRAS / "vscode"
    return {base / "themes" / f"{name.lower()}-color-theme.json": json.dumps(theme, indent=2) + "\n",
            base / "package.json": vscode_package()}


# app -> renderer returning {output path: text} for a variant
APPS = {
    "alacritty": lambda name, v: {EXTRAS / "alacritty" / f"{name.lower()}.toml": render_alacritty(name, v)},
    "ghostty": lambda name, v: {EXTRAS / "ghostty" / name: render_ghostty(name, v)},
    "mc": lambda name, v: {EXTRAS / "mc" / f"{name.lower()}.ini": render_mc(name, v)},
    "neovim": render_neovim,
    "vscode": render_vscode,
}


def main():
    global PAL
    check = "--check" in sys.argv[1:]
    PAL = json.loads(PALETTE.read_text(encoding="utf-8"))
    failed, changed = False, []
    for name, v in PAL["variants"].items():          # validate everything before writing anything
        problems = check_variant(name, v)
        for p in problems:
            print(f"{name}: {p}")
        failed |= bool(problems)
        low = min(contrast(v["ansi"]["normal"][k], v["ui"]["background"]) for k in CHROMATIC)
        print(f"{name}: lowest normal ANSI contrast {low:.2f}:1, "
              f"text {contrast(v['terminal']['foreground'], v['ui']['background']):.2f}:1")
    if failed:
        sys.exit("palette check failed; no files were written")
    outputs = {}
    for name, v in PAL["variants"].items():
        for app, render in APPS.items():
            for path, text in render(name, v).items():
                if outputs.setdefault(path, text) != text:
                    sys.exit(f"{app}: variants disagree on the shared file {path.relative_to(ROOT)}")
    for path, text in outputs.items():
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            changed.append(path)
            if not check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
    for p in changed:
        print(("would change: " if check else "wrote: ") + str(p.relative_to(ROOT)))
    if check and changed:
        sys.exit(1)


if __name__ == "__main__":
    main()
