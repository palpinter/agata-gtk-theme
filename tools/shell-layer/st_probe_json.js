// Batch St evaluator used by find_gaps.py.
// gjs st_probe_json.js STOCK_CSS APP_CSS|- SPECS.jsonl   (one JSON node chain per line)
// Prints one JSON object per chain: {fg, bg, shadow, border} as "r,g,b,a" strings.
const GLib = imports.gi.GLib;
imports.gi.versions.St = GLib.getenv('ST_VERSION');
imports.gi.versions.Clutter = GLib.getenv('ST_VERSION');
const {St, Gio} = imports.gi;

const [stockCss, appCss, specFile] = ARGV;
const theme = new St.Theme({
    default_stylesheet: Gio.File.new_for_path(stockCss),
    application_stylesheet: appCss === '-' ? null : Gio.File.new_for_path(appCss),
});
const ctx = new St.ThemeContext();
ctx.set_theme(theme);

const rgba = c => (c ? `${c.red},${c.green},${c.blue},${c.alpha}` : null);
const lines = new TextDecoder().decode(GLib.file_get_contents(specFile)[1]).split('\n').filter(Boolean);
const out = [];
for (const line of lines) {
    let node = null;
    for (const [type, id, cls, pseudo] of JSON.parse(line)) {
        const T = St[type] || St.Widget;
        node = St.ThemeNode.new(ctx, node, theme, T.$gtype, id, cls, pseudo, '');
    }
    const sh = node.get_box_shadow();
    out.push(JSON.stringify({
        fg: rgba(node.get_foreground_color()),
        bg: rgba(node.get_background_color()),
        shadow: sh ? rgba(sh.color) : null,
        border: rgba(node.get_border_color(St.Side.TOP)),
    }));
}
print(out.join('\n'));
