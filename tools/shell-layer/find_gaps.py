#!/usr/bin/env python3
"""List (selector, property) pairs where stock GNOME Shell sets a visible color and Agata leaves it
untouched on that element. Every candidate is checked by evaluating real St (via gjs and
st_probe_json.js) twice: stock theme only, and stock + Agata without the compatibility layer.

Usage: find_gaps.py STOCK_DARK_CSS THEME_GNOME_SHELL_CSS OUT_JSON [EVAL_CSS]
  EVAL_CSS: evaluate this stylesheet instead of the stripped one (to check a generated layer).
Needs GI_TYPELIB_PATH / LD_LIBRARY_PATH / ST_VERSION set (see st-env.sh).
"""
import json, os, pathlib, re, subprocess, sys, tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from shellcss import parse  # noqa: E402

BEGIN = "/* BEGIN Agata GNOME Shell 47+ compatibility layer"
END = "/* END Agata GNOME Shell 47+ compatibility layer */"
PROP = {"color": "fg", "background-color": "bg", "background": "bg", "box-shadow": "shadow", "border-color": "border"}
SKIP = re.compile(r"LookingGlass|\.lg-|toggle-switch|screen-(recording|sharing)|privacy-indicator|qr-code")


def classes_of(sel):
    return set(re.findall(r"\.([A-Za-z_][\w-]*)", sel)) | {"#" + x for x in re.findall(r"#([A-Za-z_][\w-]*)", sel)}


def chain(sel):
    """Selector -> list of [StType, id, classes, pseudo-classes] nodes, or None if not representable."""
    if re.search(r"[*\[]|:(first|last|nth|only)-|:ltr|:rtl|:not|::|\+|~", sel):
        return None
    out = []
    for comp in re.split(r"\s*>\s*|\s+", sel.strip()):
        m = re.fullmatch(r"([A-Za-z][\w]*)?((?:#[\w-]+)?)((?:\.[\w-]+)*)((?::[\w-]+)*)", comp)
        if not m:
            return None
        t = m.group(1)
        idv = m.group(2)[1:] if m.group(2) else None
        cls = " ".join(m.group(3)[1:].split(".")) if m.group(3) else None
        ps = " ".join(m.group(4)[1:].split(":")) if m.group(4) else None
        out.append([t[2:] if t and t.startswith("St") else "Widget", idv, cls, ps])
    return out


def main():
    stock_css, agata_css, out_json = sys.argv[1:4]
    eval_css = sys.argv[4] if len(sys.argv) > 4 else None
    work = pathlib.Path(tempfile.mkdtemp(prefix="agata-gaps-"))
    text = pathlib.Path(agata_css).read_text(encoding="utf-8")
    if BEGIN in text:
        text = text[text.index(END) + len(END):]
    stripped = work / "agata-without-layer.css"
    stripped.write_text(text, encoding="utf-8")

    stock, agata = parse(stock_css), parse(str(stripped))
    agata_classes = set().union(*(classes_of(s) for sels, _ in agata for s in sels))
    cands = []
    for sels, decls in stock:
        for s in sels:
            # Selectors with classes Agata never styles are handled by section (A) of the layer.
            if (classes_of(s) - agata_classes) or SKIP.search(s):
                continue
            for k, v, imp in decls:
                if k in PROP and not imp and re.search(r"#|rgba|accent|st-|white|black", v) and "url(" not in v:
                    c = chain(s)
                    if c:
                        cands.append((s, k, c))
    spec_file = work / "specs.jsonl"
    spec_file.write_text("\n".join(json.dumps(c) for _, _, c in cands) + "\n")

    def run(app):
        r = subprocess.run(["gjs", str(HERE / "st_probe_json.js"), stock_css, app, str(spec_file)],
                           capture_output=True, text=True, env=os.environ, timeout=600)
        rows = [json.loads(line) for line in r.stdout.splitlines() if line.startswith("{")]
        if len(rows) != len(cands):
            sys.exit(f"St probe failed ({len(rows)}/{len(cands)} results):\n{r.stderr[-2000:]}")
        return rows

    base, with_agata = run("-"), run(eval_css or str(stripped))

    def visible(v):
        return v is not None and not v.endswith(",0")

    # A gap: GNOME's value really shows in the stock theme, and Agata leaves it untouched.
    gaps = sorted({(s, k) for (s, k, _), b, a in zip(cands, base, with_agata)
                   if b[PROP[k]] == a[PROP[k]] and visible(b[PROP[k]])})
    pairs = {(s, k) for s, k, _ in cands}
    json.dump(gaps, open(out_json, "w"), indent=0)
    print(f"{pathlib.Path(agata_css).parent.parent.name}: {len(pairs)} candidates, "
          f"{len(pairs) - len(gaps)} covered by Agata, {len(gaps)} gaps")


if __name__ == "__main__":
    main()
