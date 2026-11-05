#!/usr/bin/env bash
# Rebuild the generated "GNOME Shell 47+ compatibility layer" at the top of every
# themes/*/gnome-shell/gnome-shell.css from the GNOME Shell installed on this machine.
#
#   tools/regenerate-shell-layer.sh           rewrite the four gnome-shell.css files
#   tools/regenerate-shell-layer.sh --check   only report; exit 1 if anything would change
#
# Requires: gnome-shell (its St typelib and stock theme gresource), mutter, gjs, python3, glib2.
# The output depends on the installed GNOME version; run it on the GNOME release you target.
set -Eeuo pipefail

TOOLS="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO="$(dirname -- "$TOOLS")"
MODE="${1:---write}"
[[ "$MODE" == "--write" || "$MODE" == "--check" ]] || { echo "usage: $0 [--check]" >&2; exit 2; }

source "$TOOLS/shell-layer/st-env.sh"
WORK="$(mktemp -d)"
trap 'rm -rf -- "$WORK"' EXIT
extract_stock "$WORK"
echo "GNOME Shell (St) $ST_VERSION, stock theme from $STOCK_GRESOURCE"

# (D) needs the St-verified gap list for each theme.
for theme in "$REPO"/themes/Agata-*/; do
    theme="${theme%/}"
    python3 -I "$TOOLS/shell-layer/find_gaps.py" "$WORK/gnome-shell-dark.css" \
        "$theme/gnome-shell/gnome-shell.css" "$WORK/gaps-$(basename "$theme").json"
done

python3 -I "$TOOLS/shell-layer/gen_layer.py" --stock "$WORK/gnome-shell-dark.css" \
    --themes "$REPO/themes" --gaps-dir "$WORK" --shell-version "$ST_VERSION" "$MODE"

"$TOOLS/check-parity.sh"
