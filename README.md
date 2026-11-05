# Agata GTK Theme

**v1.0.5**

Agata is a modern desktop theme for GTK 3 and GTK 4, with matching styles for GNOME Shell,
Cinnamon, XFCE and a growing set of other apps. It comes in two color editions, each with a Dark
and a Light variant:

| Edition | Character | Dark: background / accent | Light: background / accent |
|---|---|---|---|
| **Nord** | Muted blue accents and cool blue-gray surfaces, based on the [Nord](https://www.nordtheme.com/) palette | `#303744` / `#81A1C1` | `#ECEFF4` / `#81A1C1` |
| **Gruvbox** | Warm, earthy tones, based on the [Gruvbox](https://github.com/morhetz/gruvbox) palette | `#282828` / `#83A598` | `#F9F5D7` / `#458588` |

The four themes are installed as `Agata-Nord-Dark`, `Agata-Nord-Light`, `Agata-Gruvbox-Dark` and
`Agata-Gruvbox-Light`.

The theme files are ready to use, so there is nothing to compile. The installer needs only Bash
and installs for the current user, without `sudo`.

## What is included

Each theme directory in [`themes/`](themes) is complete and self-contained:

| Component | Directory | Notes |
|---|---|---|
| GTK 3 | `gtk-3.0/` | Also styles the XFCE panel and the Whisker menu. Defines the legacy `theme_*_color` names. |
| GTK 4 / libadwaita | `gtk-4.0/` | Optional integration for libadwaita apps. See [GTK 4 and libadwaita](#gtk-4-and-libadwaita). |
| GTK 2 | `gtk-2.0/` | For old apps. Uses the pixmap engine, plus murrine and adwaita for a few widgets if they are installed. |
| GNOME Shell | `gnome-shell/` | Needs the User Themes extension. Supports GNOME 47 and newer as well as older releases. |
| Cinnamon | `cinnamon/` | Panel, menus, applets and dialogs. |
| XFWM4 and Metacity | `xfwm4/`, `metacity-1/` | Window decorations for XFCE and Metacity-based desktops. |
| Plank | `plank/` | Dock theme. |

Also in the repository:

- [`wallpapers/`](wallpapers): matching wallpapers for all four variants.
- [`extras/`](extras): color schemes for other apps. See [Other apps](#other-apps).
- [`tools/`](tools): maintenance scripts. See [Development](#development).

## Requirements

- A desktop that uses GTK themes: GNOME, Cinnamon or XFCE. Other GTK desktops work too, but are
  not tested.
- **GNOME Shell** needs the **User Themes** extension to load a Shell theme. It ships in the
  `gnome-shell-extensions` package on Arch, Debian and Ubuntu, and in
  `gnome-shell-extension-user-theme` on Fedora. Enable it in the Extensions app, or run
  `gnome-extensions enable user-theme@gnome-shell-extensions.gcampax.github.com`. On Wayland a
  newly installed extension appears only after you log out and back in.
- **GTK 2 apps (optional):** install `gtk-engine-murrine` if your distribution packages it. The
  theme works without it.

## Installation

Clone the repository or download a release, then run the installer from the repository
directory:

```bash
./install.sh
```

The interactive installer asks three questions:

1. Which color edition: Nord or Gruvbox.
2. Which variant: Dark, Light or Both.
3. Whether to enable the optional GTK 4/libadwaita integration.

You can also pass the choices on the command line:

```bash
./install.sh install nord both                     # edition: nord | gruvbox, variant: dark | light | both
./install.sh install gruvbox dark --libadwaita     # also link the theme into ~/.config/gtk-4.0
./install.sh install nord both --dest /path/to/themes   # install somewhere else
./install.sh --help                                # all commands
```

The themes are copied to `~/.local/share/themes/`. Running the installer again replaces an
installed theme completely, so it also updates it.

### Applying the theme

**GNOME**: select the theme in GNOME Tweaks under *Appearance*, or run:

```bash
gsettings set org.gnome.desktop.interface gtk-theme 'Agata-Nord-Dark'
gsettings set org.gnome.desktop.interface color-scheme 'prefer-dark'      # 'default' for Light variants
gsettings set org.gnome.shell.extensions.user-theme name 'Agata-Nord-Dark'
```

**Cinnamon**: open *System Settings → Themes* and set *Applications*, *Desktop* and *Window
borders* to the Agata theme.

**XFCE**: select the theme in *Settings → Appearance → Style* and in *Settings → Window
Manager → Style*.

Already running GTK 3 apps switch at once. GTK 4 apps need a restart, and the GNOME Shell theme
reloads when you switch it.

### GTK 4 and libadwaita

libadwaita apps do not load GTK themes by themselves. With `--libadwaita` (or the matching
answer in the interactive installer), the installer replaces `~/.config/gtk-4.0` with a link to
the theme's `gtk-4.0` directory. If you install both variants, it asks which one to link. An
existing configuration that does not come from Agata is first moved to
`~/.config/gtk-4.0.backup-<timestamp>`.

The theme also sets libadwaita's named colors (`window_bg_color`, `accent_bg_color` and the
rest). Widgets the base theme does not style, such as newer dialogs, toggle groups and spinners,
get Agata colors this way too. This covers libadwaita 1.0 through 1.10.

Some libadwaita apps may still ignore parts of a third-party theme, depending on the app and the
libadwaita version.

### Uninstallation

```bash
./install.sh remove nord both        # or: remove gruvbox dark, ...
./install.sh remove all              # every Agata theme
./install.sh remove-libadwaita       # remove the ~/.config/gtk-4.0 link and restore the newest backup
```

## Other apps

[`extras/`](extras) holds color schemes that match the four variants, so terminals and editors
blend in with the desktop:

| App | Folder | Notes |
|---|---|---|
| Alacritty | [`extras/alacritty`](extras/alacritty) | Import one file from `alacritty.toml`. |
| Ghostty | [`extras/ghostty`](extras/ghostty) | Can follow the system light/dark preference. |
| Midnight Commander | [`extras/mc`](extras/mc) | True-color skins. Needs mc built with S-Lang. |
| Neovim | [`extras/neovim`](extras/neovim) | Color schemes with lualine themes. `agata-nord` and `agata-gruvbox` follow `'background'`. |
| Visual Studio Code | [`extras/vscode`](extras/vscode) | One extension with all four themes. Pack it with `tools/pack-vscode-theme.py`. |

Each folder has its own installation steps. All the schemes are generated from one file,
[`extras/palette.json`](extras/palette.json). It holds every color of each variant (the UI
colors, 16 ANSI colors and editor syntax colors), so you can also use it to theme apps that have
no scheme yet. See [`extras/README.md`](extras/README.md).

## Icons, cursors and wallpapers

Agata does not include an icon or cursor theme; `index.theme` defaults to Adwaita. Icon themes
with a Nord-colored folder variant work well with the Nord edition, for example
`Newaita-reborn-nord` / `Newaita-reborn-nord-dark`, whose folder colors are exactly Agata Nord's
`#5E81AC` and `#81A1C1`.

Matching wallpapers are in [`wallpapers/`](wallpapers). The Nord ones are
`Agata-Wallpaper-Dark.jpg` and `Agata-Wallpaper-Light.jpg`; the Gruvbox ones are
`Agata-Wallpaper-Gruvbox-Dark.jpg` and `Agata-Wallpaper-Gruvbox-Light.jpg`.

## Compatibility

The themes were tested on:

- Zorin OS 18.1
- Linux Mint Cinnamon 22.3
- Linux Mint XFCE 22.3
- Xubuntu 26.10
- Fedora 44 and 45, XFCE
- Fedora 44 and 45, GNOME

GNOME Shell support:

- GNOME 47 and newer get a compatibility layer at the top of each `gnome-shell.css`. It is
  generated from the GNOME Shell 51 default theme and recolored to the Agata palette, so newer
  widgets such as quick-settings menus, notification groups and toggle switches match the theme.
- Selectors used by older GNOME releases are kept, so the same files work there too.

The look can still vary with the desktop, the GTK version, the compositor and the installed
extensions.

## Development

There is no build step: the files in `themes/` are the source. Edit the shipped `.css`,
`themerc` and `.xml` files directly, then reinstall the theme to try a change.

- **Changes usually go into all four themes.** Nord and Gruvbox of the same variant are
  identical line by line except for colors. Dark and Light differ more, so a fix has to be redone
  with each variant's colors.
- **Agata's own overrides go at the end of `gtk.css`.** In `gtk-3.0/gtk.css` and
  `gtk-4.0/gtk.css`, the hand-written overrides follow the compiled base, each block starting
  with a `/* Agata ... */` comment. `gtk-dark.css` gets no overrides.
- **Generated parts are not edited by hand.** This applies to the GNOME Shell compatibility layer
  (between the `BEGIN`/`END` markers) and to everything in `extras/<app>/`. Change their
  generators and run them again.

The scripts in [`tools/`](tools) check and regenerate these parts. They need a Linux system with
GNOME, GTK 3 and 4 and PyGObject; see [`tools/README.md`](tools/README.md).

| Command | Purpose |
|---|---|
| `tools/check-gtk-css.py` | Parses all GTK 3/4 stylesheets with the installed GTK. It must report 0 problems. |
| `tools/check-parity.sh` | Checks that Nord and Gruvbox differ only in colors. |
| `tools/regenerate-shell-layer.sh [--check]` | Rebuilds the GNOME Shell 47+ compatibility layer. |
| `tools/add-libadwaita-palette.py` | Rewrites the libadwaita named-color block in `gtk-4.0/gtk.css`. |
| `tools/gen-app-themes.py [--check]` | Regenerates `extras/` from `palette.json` and checks it against the GTK colors and the contrast targets. |
| `tools/pack-vscode-theme.py` | Packs the VS Code extension into a VSIX file. |
| `tools/st-probe.sh` | Shows the computed GNOME Shell style of a widget without a running Shell. |

To change a color used by the other apps, change the GTK theme first, then `extras/palette.json`,
then run `tools/gen-app-themes.py`.

## Credits and license

Agata was created by Deivid Schlosser Onório and is based on the
[Jasper GTK theme](https://github.com/vinceliuice/Jasper-gtk-theme) by vinceliuice. The color
editions follow the [Nord](https://www.nordtheme.com/) and
[Gruvbox](https://github.com/morhetz/gruvbox) palettes.

Released under the MIT License; see [`LICENSE`](LICENSE).
