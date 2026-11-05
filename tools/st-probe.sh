#!/usr/bin/env bash
# Print the computed St style of widget chains, evaluated with the stock GNOME Shell theme
# underneath an Agata gnome-shell.css, exactly as the User Themes extension layers them.
# Nothing on the desktop changes.
#
#   tools/st-probe.sh [--light] THEME_DIR|CSS_FILE|- 'CHAIN' ['CHAIN' ...]
#     --light   use the stock light theme underneath (what GNOME loads with a light color scheme)
#     -         stock theme only
#   CHAIN: nodes separated by ' > ', each [StType][#id][.class...][:pseudo...], e.g.
#     tools/st-probe.sh themes/Agata-Nord-Dark '#panel > StButton.panel-button:hover'
set -Eeuo pipefail

TOOLS="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
variant=dark
if [[ "${1:-}" == "--light" ]]; then variant=light; shift; fi
(($# >= 2)) || { sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }

app="$1"; shift
[[ -d "$app" ]] && app="$app/gnome-shell/gnome-shell.css"
[[ "$app" == "-" || -f "$app" ]] || { echo "Error: $app not found" >&2; exit 1; }

source "$TOOLS/shell-layer/st-env.sh"
WORK="$(mktemp -d)"
trap 'rm -rf -- "$WORK"' EXIT
extract_stock "$WORK"

# St without a stage logs harmless Clutter/GObject criticals; hide only those.
gjs "$TOOLS/shell-layer/st_probe.js" "$WORK/gnome-shell-$variant.css" "$app" "$@" \
    2> >(grep -v -E 'clutter_backend_get_resolution|pango_font_description_set_absolute_size|g_signal_handlers_disconnect_matched|invalid \(NULL\) pointer instance|^$' >&2)
