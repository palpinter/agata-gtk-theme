#!/usr/bin/env bash
# Nord and Gruvbox editions must stay line-for-line identical apart from colors (and the
# theme name). Reports every text file where the two differ in anything else.
set -Eeuo pipefail

THEMES="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../themes" && pwd -P)"
normalize() {
    sed -E 's/#[0-9A-Fa-f]{3,8}\b/#X/g; s/rgba?\([^)]*\)/RGB/g; s/Agata-(Nord|Gruvbox)/Agata-E/g' "$1"
}
status=0
for variant in Dark Light; do
    while IFS= read -r -d '' file; do
        rel="${file#"$THEMES/Agata-Nord-$variant/"}"
        other="$THEMES/Agata-Gruvbox-$variant/$rel"
        if [[ ! -f "$other" ]]; then
            echo "missing in Gruvbox-$variant: $rel"; status=1; continue
        fi
        n="$(diff <(normalize "$file") <(normalize "$other") | grep -c '^[<>]' || true)"
        if [[ "$n" != 0 ]]; then
            echo "non-color difference ($n lines): $variant $rel"; status=1
        fi
    done < <(find "$THEMES/Agata-Nord-$variant" -type f \( -name '*.css' -o -name themerc -o -name '*.xml' -o -name '*.rc' -o -name gtkrc \) -print0)
done
((status == 0)) && echo "Nord/Gruvbox parity: OK"
exit "$status"
