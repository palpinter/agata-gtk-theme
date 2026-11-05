"""Shared helpers: parse St CSS, colors, Sass-compatible St color functions."""
import re, colorsys
def parse(path):
    t = re.sub(r"/\*.*?\*/", "", open(path, encoding="utf-8").read(), flags=re.S)
    rules = []
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", t):
        sel = " ".join(m.group(1).split())
        if sel.startswith("@") or re.match(r"^(from|to|\d+%)$", sel): continue
        decls = []
        for d in split_decls(m.group(2)):
            k, _, v = d.partition(":")
            if not _: continue
            v = " ".join(v.split()); imp = v.endswith("!important")
            if imp: v = v[: -len("!important")].strip()
            decls.append((k.strip(), v, imp))
        rules.append(([s.strip() for s in split_top(sel)], decls))
    return rules
def split_top(s, sep=","):
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch == "(": depth += 1
        elif ch == ")": depth -= 1
        if ch == sep and depth == 0: out.append(cur); cur = ""
        else: cur += ch
    out.append(cur); return [x.strip() for x in out if x.strip()]
def split_decls(body): return [d.strip() for d in split_top(body, ";") if d.strip()]
NAMED = {"white": (255,255,255,1.0), "black": (0,0,0,1.0), "transparent": (0,0,0,0.0)}
COLOR_RE = r"#[0-9A-Fa-f]{3,8}\b|rgba?\([^()]*\)|\b(?:white|black|transparent)\b|-st-accent-fg-color|-st-accent-color"
def to_rgba(tok):
    tok = tok.strip()
    if tok in NAMED: return NAMED[tok]
    if tok.startswith("#"):
        h = tok[1:]
        if len(h) == 3: h = "".join(c*2 for c in h)
        a = int(h[6:8], 16)/255 if len(h) == 8 else 1.0
        return (int(h[0:2],16), int(h[2:4],16), int(h[4:6],16), a)
    m = re.match(r"rgba?\(([^)]*)\)", tok)
    if m:
        parts = [p.strip() for p in re.split(r"[,\s/]+", m.group(1)) if p.strip()]
        r, g, b = (float(p) for p in parts[:3]); a = float(parts[3].rstrip("%"))/(100 if parts[3].endswith("%") else 1) if len(parts) > 3 else 1.0
        return (round(r), round(g), round(b), a)
    return None
def fmt(c):
    r, g, b, a = c
    r, g, b = (max(0, min(255, round(x))) for x in (r, g, b))
    if a >= 0.9995: return "#%02x%02x%02x" % (r, g, b)
    return "rgba(%d, %d, %d, %s)" % (r, g, b, ("%.3f" % a).rstrip("0").rstrip(".") or "0")
def _hsl(c):
    h, l, s = colorsys.rgb_to_hls(c[0]/255, c[1]/255, c[2]/255); return h, s, l
def _rgb(h, s, l, a):
    r, g, b = colorsys.hls_to_rgb(h, max(0, min(1, l)), max(0, min(1, s))); return (r*255, g*255, b*255, a)
def lighten(c, amt):  h, s, l = _hsl(c); return _rgb(h, s, l + amt, c[3])
def darken(c, amt):   h, s, l = _hsl(c); return _rgb(h, s, l - amt, c[3])
def transparentize(c, amt): return (c[0], c[1], c[2], max(0.0, c[3] - amt))
def mix(c1, c2, w):
    # Sass mix(): weight w of c1, alpha-aware.
    p = w; wn = p*2 - 1; da = c1[3] - c2[3]
    w1 = ((wn if wn*da == -1 else (wn + da)/(1 + wn*da)) + 1)/2; w2 = 1 - w1
    return (c1[0]*w1 + c2[0]*w2, c1[1]*w1 + c2[1]*w2, c1[2]*w1 + c2[2]*w2, c1[3]*p + c2[3]*(1-p))
def num(s):
    s = s.strip(); return float(s[:-1])/100 if s.endswith("%") else float(s)
def evaluate(expr, resolve):
    """Evaluate a color expression (hex/rgba/named/-st-accent*/st-* functions) to an RGBA tuple.
    `resolve(token)` maps a leaf color token to RGBA (applies the theme mapping)."""
    expr = expr.strip()
    m = re.match(r"^(st-mix|st-lighten|st-darken|st-transparentize)\((.*)\)$", expr)
    if m:
        args = split_top(m.group(2))
        f = m.group(1)
        if f == "st-mix": return mix(evaluate(args[0], resolve), evaluate(args[1], resolve), num(args[2]))
        c = evaluate(args[0], resolve); a = num(args[1])
        return {"st-lighten": lighten, "st-darken": darken, "st-transparentize": transparentize}[f](c, a)
    return resolve(expr)
