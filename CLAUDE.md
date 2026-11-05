# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Agata is a GTK 3/4 desktop theme (plus GNOME Shell, Cinnamon, XFWM4, Metacity, GTK 2 and Plank styling) shipped as **ready-made, pre-compiled theme files**. It is derived from the [Jasper GTK theme](https://github.com/vinceliuice/Jasper-gtk-theme), but the SASS sources and asset-render scripts are **not** in this repo. There is no build step, no test suite, and no package manifest. You edit the shipped `.css`/`themerc`/`.xml` files directly.

## Commands

```bash
./install.sh                                  # interactive installer
./install.sh install nord both                # edition: nord|gruvbox, variant: dark|light|both
./install.sh install gruvbox dark --libadwaita   # also symlink ~/.config/gtk-4.0 -> <theme>/gtk-4.0
./install.sh remove all                       # or: remove <edition> <variant>
./install.sh remove-libadwaita                # drop the gtk-4.0 link, restore newest backup
./install.sh install nord both --dest /tmp/agata-test   # install somewhere other than ~/.local/share/themes
bash -n install.sh                            # syntax-check the installer

# Maintenance tools (tools/README.md has details)
tools/check-gtk-css.py                        # parse all 16 gtk*.css with the installed GTK 3 and 4; must report 0 problems
tools/check-parity.sh                         # Nord vs Gruvbox must differ only in colors
tools/regenerate-shell-layer.sh [--check]     # rebuild the GNOME Shell compatibility layer from the installed GNOME
tools/add-libadwaita-palette.py               # rewrite the libadwaita palette block in gtk-4.0/gtk.css
tools/gen-terminal-themes.py [--check]        # regenerate extras/terminal/ (Alacritty, Ghostty); never hand-edit those files
tools/st-probe.sh [--light] themes/Agata-Nord-Dark '#panel > StButton.panel-button:hover'   # computed St style
```

The theme itself still ships pre-compiled; the tools are only for maintenance. To try a stylesheet change, reinstall the theme and reload it. For GTK 3 that means re-selecting the theme or running an app with `GTK_THEME=Agata-Nord-Dark <app>`. Install overwrites the target directory completely: it copies to a temp directory and then `mv`s it into place.

## Layout and how the four themes relate

`themes/` holds four complete, self-contained theme directories: `Agata-{Nord,Gruvbox}-{Dark,Light}`. Each has `index.theme`, `gtk-2.0/`, `gtk-3.0/`, `gtk-4.0/`, `gnome-shell/`, `cinnamon/`, `metacity-1/`, `xfwm4/` and `plank/`. `wallpapers/` holds the matching JPGs. `extras/terminal/` holds the generated Alacritty and Ghostty color schemes. Their bg and accent colors are asserted against each theme's libadwaita palette block, so change the GTK colors first, then regenerate them. Nothing is shared between the theme dirs, so **a fix usually has to be applied to all four**.

- **Nord vs Gruvbox (same variant):** the text files are line-for-line identical except for hex/rgba color values (and the theme name in comments and `index.theme`). To port a Nord change to Gruvbox, make the same edit at the same line and translate the colors. The mapping is mostly consistent, but it is not a perfect 1:1 `sed`: a few Nord colors map to different Gruvbox colors depending on context. Check the surrounding rules in the Gruvbox file. Main roles:
  - Dark: fg `#ECEFF4→#ebdbb2`, accent `#81A1C1→#83a598`, base `#394253→#3c3836`, bg `#303744→#282828`, `#454F63→#504945`, `#5E81AC→#458588`, `#252A34→#1d2021`
  - Light: fg `#2E3440→#3c3836`, accent `#81A1C1→#458588`, `#E5E9F0→#ebdbb2`, `#ECEFF4→#f9f5d7`, `#D8DEE9→#d5c4a1`, `#5E81AC→#076678`, `#F8FAFC→#fbf1c7`
- **Dark vs Light:** these differ in hundreds of lines, so a fix has to be redone for each variant with that variant's colors.
- **Binary assets:** the PNG/SVG assets in `gtk-3.0/assets/scalable`, `gtk-4.0/assets/scalable`, `cinnamon/assets`, `gnome-shell/assets`, `metacity-1/assets` and the `xfwm4/*.png` button and border images are recolored per edition. There are no source files for regenerating them. `gtk-2.0/` and its assets are identical across editions.

## Stylesheet structure (`gtk-3.0`, `gtk-4.0`)

- `gtk.css` and `gtk-dark.css` are large compiled Jasper outputs (~8k lines each). Near the end of `gtk-3.0/gtk.css` there is an `@define-color` block (`theme_bg_color`, `theme_selected_bg_color`, etc.) used by legacy apps and XFCE.
- **Hand-written Agata overrides are appended to the bottom of `gtk.css` only**, never to `gtk-dark.css`. Each block starts with a `/* Agata ... */` comment. Examples: the XFCE Whisker menu border and opaque surface fixes, panel icon contrast, and the tooltip contrast fix in Light. Put new desktop-specific tweaks there in the same way, so they stay separate from the compiled base, and repeat them in all four themes.
- The `gtk-4.0/gtk.css` overrides are a smaller subset of the GTK 3 ones (Whisker itself uses GTK 3).
- The last block of `gtk-4.0/gtk.css` (`/* Agata libadwaita palette ... */`) sets libadwaita's named colors (`@define-color window_bg_color`, `accent_bg_color`, ...) from that theme's own colors. This is how widgets the compiled base does not know (`AdwDialog`, `AdwToggleGroup`, `AdwSpinner`, ...) get Agata colors when the theme is linked into `~/.config/gtk-4.0`. libadwaita 1.6+ defines its `--*-color` variables in terms of these named colors, so named colors cover libadwaita 1.0 through 1.10. The trailing `:root { --standalone-color-oklab: ... }` rule makes libadwaita derive accent and status text colors for the theme's brightness instead of the system color scheme. It needs GTK 4.16+, and older GTK drops the rule.
- GTK 4 has no `gtkmix()`, and its `mix(a, b, f)` takes `f` as the share of `b`. Sass-style `gtkmix(A, B, 30%)` (30% of A) has to be written as `mix(B, A, 0.3)`.

## GNOME Shell stylesheet (`gnome-shell/gnome-shell.css`)

- The User Themes extension loads it as the *application* stylesheet on top of GNOME's own default theme. St sorts by origin and importance first, then by specificity:
  - Any property Agata sets beats the stock theme, whatever the stock selector's specificity.
  - Properties Agata never sets on an element show GNOME's stock colors, including the system accent color.
  - Stock `!important` declarations beat Agata's normal ones.
- The compiled Agata base predates GNOME 47. The top of each file holds a generated **GNOME Shell 47+ compatibility layer** between `/* BEGIN Agata GNOME Shell 47+ compatibility layer` and `/* END ... */`. It is the GNOME Shell 51 default theme recolored to the theme's palette, with colors precomputed instead of `st-mix()`/`-st-accent-color`:
  - (A) widgets with classes Agata does not style;
  - (B) stock `!important` colors;
  - (D) stock colors on styled elements where Agata leaves a property unset (checked by evaluating St with and without Agata);
  - (C) hand-mapped successors of renamed widgets, e.g. `.quick-menu-toggle .quick-toggle-arrow` → `.quick-toggle-has-menu .quick-toggle-menu-button.icon-button`, `StButton#vhandle` → `.vhandle`, plus the toggle-switch fix. GNOME 47+ adds a CSS `.handle` knob, which is hidden so Agata's SVG switches stay. (C) also flattens Agata's translucent `.popup-menu .message` overlays onto the menu background for `.popup-menu .message-notification-group .message`. Collapsed notification groups stack messages behind the first one, so translucent cards show the text underneath.
  
  Layout needs the same care as colors. Agata's generic layout rules beat GNOME's stock layout for the new structure, unless the stock rule is `!important`. For example, `.quick-toggle { min-width: 12em; border-radius: 10px }` overrode the stock `.quick-toggle-has-menu .quick-toggle { min-width: auto }` and pushed quick-settings menu arrows out of their tiles. That is why (C) ports *all* of Agata's `.quick-menu-toggle` rules, layout included. The menu button also has `.icon-button`, so the extra class is needed to out-rank `.quick-settings .icon-button`. The St probe cannot resolve `em` lengths without a Clutter backend (they read as -1), but `px` values work.
  
  It sits first so that Agata's own rules win ties. **Never hand-edit the layer.** Change the generator (`tools/shell-layer/gen_layer.py`) and run `tools/regenerate-shell-layer.sh`. On the GNOME release the committed layer came from (see its header), `--check` must report no changes. Agata design changes belong below the END marker. The layer is generated from the dark stock theme for all four themes: Light themes get an inverted mapping (stock dark bg → Agata bg, white → Agata fg), matching Agata Light's light lock screen and OSD. Status colors (recording and sharing pills, privacy indicator), the QR code, the screenshot flash and dimming keep GNOME's values.
- Do not remove "dead" pre-GNOME-47 selectors (`.quick-menu-toggle`, `.message-list-section`, `#vhandle`, ...). Older GNOME releases on the tested distros still use them.

## Checking changes without switching themes

- GTK CSS: `tools/check-gtk-css.py` loads each stylesheet with `Gtk.CssProvider` and collects its `parsing-error` signals. All 16 `gtk*.css` files currently parse with zero errors on GTK 3.24 and 4.24.
- Shell CSS: `tools/st-probe.sh` evaluates widget chains with real St, without a running shell. It layers the stock theme (extracted from `/usr/share/gnome-shell/gnome-shell-theme.gresource`) under an Agata stylesheet, the same way the User Themes extension does. `tools/shell-layer/st-env.sh` locates the St/mutter typelibs (`/usr/lib`, `/usr/lib64` or a Debian multiarch dir).
- To check the live desktop after editing, reinstall and set the User Themes `name` to `''` and back to reload the Shell theme. libadwaita apps only pick up CSS changes when restarted.

## Installer (`install.sh`)

- Bash with `set -Eeuo pipefail`. Installs per-user only, to `~/.local/share/themes` by default; it needs no sudo.
- Before copying, it checks that `index.theme`, `gtk-3.0/gtk.css` and `gtk-4.0/gtk.css` exist in each theme.
- libadwaita integration replaces `~/.config/gtk-4.0` with a symlink to the installed theme's `gtk-4.0`. A non-Agata config is moved to `gtk-4.0.backup-<timestamp>`. An existing Agata link is detected by matching the resolved path against the four theme names (`is_agata_theme`).
- The edition and theme names are hardcoded in several places: `is_agata_theme`, `theme_name`, the edition validation in argument parsing, the interactive menus, `usage`, and the `remove all` list. Adding or renaming an edition means updating all of them, plus `README.md`.

## Release metadata

`README.md` carries the version string (`**v1.0.5**`) and the list of distros the theme was tested on. Update both when cutting a release or after testing on a new distro or desktop.
