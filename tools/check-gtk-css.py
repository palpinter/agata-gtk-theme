#!/usr/bin/env python3
"""Parse the GTK stylesheets with the installed GTK and report every parsing error.

  tools/check-gtk-css.py                 check all themes/*/gtk-3.0 and gtk-4.0 stylesheets
  tools/check-gtk-css.py --gtk 4 FILE..  check specific files with one GTK version

Requires PyGObject with GTK 3 and GTK 4 (and a display, as GTK initialization needs one).
Exit status 1 if any stylesheet has problems. Unknown @named colors are not parse errors
(GTK resolves them at runtime), so they are not reported.
"""
import collections, pathlib, subprocess, sys


def check(version, files):
    import gi
    gi.require_version("Gtk", f"{version}.0")
    from gi.repository import Gtk
    Gtk.init(None) if version == "3" else Gtk.init()
    total = 0
    for path in files:
        errors = []
        provider = Gtk.CssProvider()

        def on_error(_provider, section, error):
            if version == "4":
                line = section.get_start_location().lines + 1
            else:
                line = section.get_start_line() + 1
            errors.append((line, error.message))

        provider.connect("parsing-error", on_error)
        try:
            provider.load_from_path(str(path))
        except Exception as exc:          # GTK 3 also raises on the first error
            if not errors:
                errors.append((0, str(exc)))
        total += len(errors)
        print(f"GTK {version}  {path}: {len(errors)} problem(s)")
        for message, n in collections.Counter(m for _, m in errors).most_common():
            lines = [l for l, m in errors if m == message][:8]
            print(f"    {n:3d}x {message}  (lines {lines})")
    return total


def main():
    args = sys.argv[1:]
    if args[:1] == ["--gtk"]:
        sys.exit(1 if check(args[1], args[2:]) else 0)
    themes = pathlib.Path(__file__).resolve().parent.parent / "themes"
    status = 0
    for version in ("3", "4"):
        files = sorted(str(p) for p in themes.glob(f"Agata-*/gtk-{version}.0/gtk*.css"))
        # One GTK major version per process.
        status |= subprocess.call([sys.executable, "-I", __file__, "--gtk", version, *files])
    sys.exit(status)


if __name__ == "__main__":
    main()
