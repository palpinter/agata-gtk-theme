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


# app -> renderer returning {output path: text} for a variant
APPS = {
    "alacritty": lambda name, v: {EXTRAS / "alacritty" / f"{name.lower()}.toml": render_alacritty(name, v)},
    "ghostty": lambda name, v: {EXTRAS / "ghostty" / name: render_ghostty(name, v)},
    "mc": lambda name, v: {EXTRAS / "mc" / f"{name.lower()}.ini": render_mc(name, v)},
    "neovim": render_neovim,
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
