# Agata for Ghostty

Copy the schemes to Ghostty's theme directory:

```bash
mkdir -p ~/.config/ghostty/themes
cp extras/ghostty/Agata-* ~/.config/ghostty/themes/
```

Then set the theme in `~/.config/ghostty/config.ghostty`. Use a fixed theme:

```
theme = Agata-Nord-Dark
```

Or follow the system light/dark preference:

```
theme = light:Agata-Nord-Light,dark:Agata-Nord-Dark
```

Reload the configuration (default keybinding: <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>,</kbd>) or open a
new window. `ghostty +validate-config` reports any problem.

Files: `Agata-Nord-Dark`, `Agata-Nord-Light`, `Agata-Gruvbox-Dark`, `Agata-Gruvbox-Light`. They
are generated from [`../palette.json`](../palette.json), so do not edit them by hand.
