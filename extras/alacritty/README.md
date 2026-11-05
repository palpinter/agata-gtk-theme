# Agata for Alacritty

Copy the schemes:

```bash
mkdir -p ~/.config/alacritty/themes
cp extras/alacritty/*.toml ~/.config/alacritty/themes/
```

Import one of them in `~/.config/alacritty/alacritty.toml` (Alacritty 0.14 or newer):

```toml
[general]
import = ["~/.config/alacritty/themes/agata-nord-dark.toml"]
```

Remove any `[colors]` sections from `alacritty.toml` itself. Settings in the main file take
precedence over imported ones. Running windows pick up the change automatically.

Files: `agata-nord-dark.toml`, `agata-nord-light.toml`, `agata-gruvbox-dark.toml`,
`agata-gruvbox-light.toml`. They are generated from [`../palette.json`](../palette.json), so do
not edit them by hand.
