# Sourced by the shell-layer tools. Locates the GNOME Shell St typelib and the matching mutter
# (Clutter) libraries so gjs can use St without a running shell, and extracts the stock theme.
#   Exports: ST_VERSION, GI_TYPELIB_PATH, LD_LIBRARY_PATH
#   Function: extract_stock DIR  ->  DIR/gnome-shell-dark.css, DIR/gnome-shell-light.css

ST_VERSION=""
for libdir in /usr/lib64 /usr/lib /usr/lib/x86_64-linux-gnu /usr/lib/aarch64-linux-gnu; do
    for typelib in "$libdir"/gnome-shell/St-*.typelib; do
        [[ -e "$typelib" ]] || continue
        ST_VERSION="$(basename "$typelib" .typelib)"
        ST_VERSION="${ST_VERSION#St-}"
        SHELL_LIBDIR="$libdir/gnome-shell"
        MUTTER_LIBDIR="$libdir/mutter-$ST_VERSION"
        break 2
    done
done
[[ -n "$ST_VERSION" ]] || { echo "Error: GNOME Shell St typelib not found (is gnome-shell installed?)" >&2; exit 1; }
[[ -d "$MUTTER_LIBDIR" ]] || { echo "Error: $MUTTER_LIBDIR not found (mutter matching St-$ST_VERSION)" >&2; exit 1; }
command -v gjs >/dev/null || { echo "Error: gjs is required" >&2; exit 1; }

export ST_VERSION
export GI_TYPELIB_PATH="$SHELL_LIBDIR:$MUTTER_LIBDIR${GI_TYPELIB_PATH:+:$GI_TYPELIB_PATH}"
export LD_LIBRARY_PATH="$SHELL_LIBDIR:$MUTTER_LIBDIR${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

STOCK_GRESOURCE="${STOCK_GRESOURCE:-/usr/share/gnome-shell/gnome-shell-theme.gresource}"

extract_stock() {
    local dir="$1" variant
    [[ -f "$STOCK_GRESOURCE" ]] || { echo "Error: $STOCK_GRESOURCE not found" >&2; return 1; }
    for variant in dark light; do
        gresource extract "$STOCK_GRESOURCE" "/org/gnome/shell/theme/gnome-shell-$variant.css" \
            > "$dir/gnome-shell-$variant.css"
    done
}
