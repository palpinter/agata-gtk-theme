// Manual St probe: computed style of a widget chain, without switching the desktop theme.
// Run via tools/st-probe.sh, e.g.:
//   tools/st-probe.sh themes/Agata-Nord-Light '.quick-settings > .quick-toggle-has-menu > StButton.quick-toggle-menu-button.icon-button:checked'
// Chain syntax: nodes separated by ' > ', each [StType][#id][.class...][:pseudo...].
// Note: em lengths need a Clutter backend and read as -1 here; px values are exact.
const GLib = imports.gi.GLib;
imports.gi.versions.St = GLib.getenv('ST_VERSION');
imports.gi.versions.Clutter = GLib.getenv('ST_VERSION');
const {St, Gio} = imports.gi;

const [stockCss, appCss, ...specs] = ARGV;
const theme = new St.Theme({
    default_stylesheet: Gio.File.new_for_path(stockCss),
    application_stylesheet: appCss === '-' ? null : Gio.File.new_for_path(appCss),
});
const ctx = new St.ThemeContext();
ctx.set_theme(theme);

const hex = c => (c ? `#${[c.red, c.green, c.blue].map(x => x.toString(16).padStart(2, '0')).join('')}${
    c.alpha < 255 ? `@${(c.alpha / 255).toFixed(2)}` : ''}` : '-');
const sides = f => [St.Side.TOP, St.Side.RIGHT, St.Side.BOTTOM, St.Side.LEFT].map(f).join('/');
for (const spec of specs) {
    let node = null;
    for (const part of spec.split(' > ')) {
        const m = part.match(/^([A-Za-z]*)(#[\w-]+)?((?:\.[\w-]+)*)((?::[\w-]+)*)$/);
        if (!m)
            throw new Error(`cannot parse node "${part}"`);
        const T = (m[1] && St[m[1].replace(/^St/, '')]) || St.Widget;
        node = St.ThemeNode.new(ctx, node, theme, T.$gtype, m[2] ? m[2].slice(1) : null,
            m[3] ? m[3].slice(1).split('.').join(' ') : null,
            m[4] ? m[4].slice(1).split(':').join(' ') : null, '');
    }
    const sh = node.get_box_shadow();
    print(spec);
    print(`  bg=${hex(node.get_background_color())} fg=${hex(node.get_foreground_color())} ` +
          `shadow=${sh ? hex(sh.color) : '-'} border=${hex(node.get_border_color(St.Side.TOP))}`);
    print(`  margin=${sides(s => node.get_margin(s))} padding=${sides(s => node.get_padding(s))} ` +
          `radius=${[0, 1, 2, 3].map(c => node.get_border_radius(c)).join('/')} ` +
          `min-w=${node.get_min_width()} max-w=${node.get_max_width()} min-h=${node.get_min_height()}`);
}
