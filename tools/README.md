# Maintenance tools

The theme ships ready to use, with nothing to compile. These scripts help maintain the files in
`themes/`. They need a Linux system with GNOME installed (GNOME Shell, mutter, gjs, PyGObject
with GTK 3 and 4, `gresource` from glib2). Run them from a graphical session, because GTK
initialization needs a display.

| Command | What it does |
|---|---|
| `tools/check-gtk-css.py` | Parses every `gtk-3.0`/`gtk-4.0` stylesheet with the installed GTK and lists parsing errors. It exits with status 1 if any are found. |
| `tools/check-parity.sh` | Checks that the Nord and Gruvbox editions differ only in colors and theme names. |
| `tools/regenerate-shell-layer.sh` | Rebuilds the generated *GNOME Shell 47+ compatibility layer* at the top of each `gnome-shell/gnome-shell.css`. It uses the GNOME Shell installed on this machine. With `--check`, it only reports, and exits with status 1 if any file would change. |
| `tools/add-libadwaita-palette.py` | Rewrites the libadwaita palette block at the end of each `gtk-4.0/gtk.css` from that theme's own colors. |
| `tools/gen-app-themes.py [--check]` | Generates the app color schemes in `extras/<app>/` from `extras/palette.json`. It checks that the shared UI colors still match the GTK themes and that the declared contrast targets are met (see `extras/README.md`). |
| `tools/pack-vscode-theme.py [OUT.vsix]` | Packs `extras/vscode/` into a VSIX without npm or vsce, for `code --install-extension`. VS Code ignores extension folders copied into `~/.vscode/extensions` by hand. |
| `tools/st-probe.sh [--light] THEME 'CHAIN'…` | Prints the computed St style (colors, padding, margin, radius) of a widget chain, with the stock theme underneath. Nothing on the desktop changes. |

## The GNOME Shell compatibility layer

Agata's Shell stylesheet predates GNOME 47. The User Themes extension loads it *on top of*
GNOME's stock theme, and St decides between the two by origin and importance before
specificity. This has three consequences:

- Every property Agata sets wins, even inside widget structures that GNOME has since changed.
- Widgets and properties Agata never mentions keep GNOME's stock colors, including the system
  accent color.
- Stock `!important` rules override Agata.

`regenerate-shell-layer.sh` deals with this as follows:

1. It extracts the stock dark theme and finds the St/mutter typelibs (`shell-layer/st-env.sh`).
2. For each theme, `shell-layer/find_gaps.py` evaluates every stock color rule with real St
   (`shell-layer/st_probe_json.js`), once with the stock theme alone and once with Agata on top.
   The rules Agata leaves untouched are the gaps.
3. `shell-layer/gen_layer.py` recolors the stock rules to the theme's palette, precomputing
   `st-mix()`/`-st-accent-color` so the output parses on older St as well. It adds
   hand-written mappings for renamed widgets (sections A, B, D and C, described in the
   generated header and in `CLAUDE.md`). Light themes use an inverted mapping.
4. `check-parity.sh` confirms that the four themes still match each other.

The output depends on the installed GNOME release. Never hand-edit the layer. Change
`gen_layer.py` and regenerate on the GNOME version you target. Agata's own design changes
belong below the layer's END marker.
