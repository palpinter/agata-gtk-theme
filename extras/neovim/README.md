# Agata for Neovim

Color schemes for Neovim 0.9 or newer (tested with 0.12), with matching lualine themes.

| Color scheme | Variant |
|---|---|
| `agata-nord` | Nord Dark or Nord Light, following `'background'` |
| `agata-gruvbox` | Gruvbox Dark or Gruvbox Light, following `'background'` |
| `agata-nord-dark`, `agata-nord-light`, `agata-gruvbox-dark`, `agata-gruvbox-light` | one fixed variant |

## Installation

Copy the files into your Neovim configuration:

```bash
mkdir -p ~/.config/nvim/colors ~/.config/nvim/lua/lualine/themes
cp extras/neovim/colors/*.lua ~/.config/nvim/colors/
cp extras/neovim/lua/lualine/themes/*.lua ~/.config/nvim/lua/lualine/themes/
```

`~/.local/share/nvim/site/` works the same way and keeps the files out of a config repository.
Both directories stay on the `runtimepath` with lazy.nvim. With lazy.nvim you can also load a
local clone as a plugin:

```lua
{ dir = "~/src/agata-gtk-theme/extras/neovim", name = "agata", lazy = false, priority = 1000 }
```

Then select the scheme:

```lua
vim.cmd.colorscheme("agata-nord")
```

In LazyVim, add `lua/plugins/colorscheme.lua`:

```lua
return {
  { "LazyVim/LazyVim", opts = { colorscheme = "agata-nord" } },
}
```

lualine picks up the matching theme by itself when its theme is `"auto"`, which is LazyVim's
default. Otherwise set `theme = "agata-nord"` (or a fixed variant) in the lualine options.

## Dark and Light

At start-up Neovim asks the terminal for its background color and sets `'background'`. The
`agata-nord` and `agata-gruvbox` schemes use that value to pick Dark or Light. When the terminal
follows the system preference (Ghostty does with
`theme = light:Agata-Nord-Light,dark:Agata-Nord-Dark`), a new Neovim instance matches it.
A running instance does not notice the change. Run `:set background=light` (or `dark`) and the
scheme reloads in the other variant.

## What is covered

- Editor UI: floats, popup menu, status and tab lines, diagnostics, LSP, diffs, spelling. Floats
  and menus use the GTK view color, and selections use the Agata accent bar, as in the
  Midnight Commander skins.
- Syntax: the legacy groups, Tree-sitter captures and LSP semantic tokens. Nord variants follow
  the official Nord mapping (nord-vim), Gruvbox variants follow gruvbox. The colors are the
  `syntax` roles in [`../palette.json`](../palette.json). Nord Dark comments are a little
  lighter than Nord's `#616e88`, because the Agata background is lighter than Nord's.
- Plugins: gitsigns, telescope, neo-tree, which-key, noice, nvim-notify, indent-blankline,
  flash, nvim-cmp, blink.cmp, dashboard, mason and mini.icons. Most other plugins link their
  groups to the standard ones and follow automatically.
- `:terminal` uses the variant's 16 ANSI colors.

Files: `colors/*.lua` and `lua/lualine/themes/*.lua`. They are generated from
[`../palette.json`](../palette.json), so do not edit them by hand. To change a color, override
it from a `ColorScheme` autocommand in your own configuration.
