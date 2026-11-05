# Agata for Midnight Commander

Copy the skins to mc's user skin directory:

```bash
mkdir -p ~/.local/share/mc/skins
cp extras/mc/*.ini ~/.local/share/mc/skins/
```

Then pick one in mc under **Options → Appearance** (the change applies at once and mc saves it).
Other ways to select a skin:

- Set `skin=agata-nord-dark` in the `[Midnight-Commander]` section of `~/.config/mc/ini`. Quit
  every running mc first, because mc rewrites this file on exit.
- Use `MC_SKIN=agata-nord-dark` in the environment, or `mc -S agata-nord-dark` for one run.

mc does not follow the system light/dark preference. A shell alias can choose the variant at
start-up on GNOME:

```bash
alias mc='mc -S agata-nord-$(gsettings get org.gnome.desktop.interface color-scheme | grep -q dark && echo dark || echo light)'
```

## Requirements

The skins use true colors (`truecolors = true`), so they need:

- mc 4.8.19 or newer, built with S-Lang (`mc --version` says "Built with S-Lang");
- a true-color terminal that sets `COLORTERM=truecolor` (Alacritty, Ghostty, GNOME Console,
  Ptyxis and other VTE terminals do);
- a 256-color `TERM` (`tput colors` prints 256). Inside tmux, use `tmux-256color` and make sure
  `COLORTERM` reaches the pane.

Otherwise mc reports that it cannot use a 16M-color skin and loads its default skin.

## Design

Panels, the command line, the editor and the viewer use the terminal background, so mc blends
in with the Agata terminal schemes. Dialogs and menus use the GTK view color, as in Agata's GTK
dialogs. The cursor bar is accent colored, and hotkeys are accent colored and underlined, like
GTK mnemonics. File types are colored much like `ls`, with the variant's ANSI colors. Syntax
highlighting in the editor uses the terminal's 16 colors, so it matches when the terminal runs
an Agata scheme as well.

Files: `agata-nord-dark.ini`, `agata-nord-light.ini`, `agata-gruvbox-dark.ini`,
`agata-gruvbox-light.ini`. They are generated from [`../palette.json`](../palette.json), so do
not edit them by hand.
