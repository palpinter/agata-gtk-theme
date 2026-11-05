# Agata for Visual Studio Code

One extension with four color themes: Agata Nord Dark, Agata Nord Light, Agata Gruvbox Dark and
Agata Gruvbox Light. Tested with VS Code 1.144; it needs 1.70 or newer, and works in VSCodium and
Code - OSS as well.

## Installation

VS Code only loads extensions installed through `--install-extension` (or the Marketplace), so
pack the folder into a VSIX first. The script needs only Python, no npm:

```bash
tools/pack-vscode-theme.py /tmp/agata-theme.vsix
code --install-extension /tmp/agata-theme.vsix      # codium --install-extension ... for VSCodium
```

Then pick the theme with **Preferences: Color Theme** (<kbd>Ctrl</kbd>+<kbd>K</kbd> <kbd>Ctrl</kbd>+<kbd>T</kbd>),
or in `settings.json`:

```json
"workbench.colorTheme": "Agata Nord Dark"
```

To follow the system light/dark preference:

```json
"window.autoDetectColorScheme": true,
"workbench.preferredDarkColorTheme": "Agata Nord Dark",
"workbench.preferredLightColorTheme": "Agata Nord Light"
```

After regenerating the themes, pack again and install with `--install-extension ... --force`,
which replaces an installed copy of the same version.

## Design

The colors match the Neovim schemes in [`../neovim`](../neovim), so both editors look alike:

- The editor, side bar, panel and terminal use the terminal background. The status bar and the
  tab strip use the GTK view color, like Neovim's status and tab lines.
- Find, hover and suggestion widgets and the command palette use the view color, like Neovim
  floats. Menus use the GTK popover color.
- Selections in lists, menus and the suggestion widget are accent bars, as in Neovim and the
  Midnight Commander skins. Active tabs and views have an accent border.
- Syntax colors are the palette's `syntax` roles, for TextMate scopes and semantic tokens alike:
  nord-vim conventions for Nord, gruvbox for Gruvbox.
- The integrated terminal uses the variant's 16 ANSI colors.

Files: `package.json` and `themes/*-color-theme.json`. They are generated from
[`../palette.json`](../palette.json), so do not edit them by hand. To change a color, override it
with `workbench.colorCustomizations` or `editor.tokenColorCustomizations` in your settings.
