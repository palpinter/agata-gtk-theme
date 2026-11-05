#!/usr/bin/env python3
"""Pack extras/vscode/ into a VSIX that `code --install-extension` accepts, without npm or vsce.

  tools/pack-vscode-theme.py [OUTPUT.vsix]    default: agata-theme-<version>.vsix in the current directory

Run tools/gen-app-themes.py first if palette.json changed. VS Code only loads extensions that are
installed this way (or from the Marketplace); copying the folder into ~/.vscode/extensions is not
enough, because VS Code reads its list of installed extensions from extensions.json.
"""
import json, pathlib, sys, zipfile
from xml.sax.saxutils import escape

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "extras" / "vscode"

pkg = json.loads((SRC / "package.json").read_text(encoding="utf-8"))
out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else f"{pkg['name']}-{pkg['version']}.vsix")
files = [SRC / "package.json", SRC / "README.md", *sorted((SRC / "themes").glob("*.json"))]

content_types = """<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension=".json" ContentType="application/json"/>
  <Default Extension=".md" ContentType="text/markdown"/>
  <Default Extension=".vsixmanifest" ContentType="text/xml"/>
</Types>
"""
manifest = f"""<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011">
  <Metadata>
    <Identity Language="en-US" Id="{pkg['name']}" Version="{pkg['version']}" Publisher="{pkg['publisher']}"/>
    <DisplayName>{escape(pkg['displayName'])}</DisplayName>
    <Description xml:space="preserve">{escape(pkg['description'])}</Description>
    <Categories>{','.join(pkg['categories'])}</Categories>
    <Properties>
      <Property Id="Microsoft.VisualStudio.Code.Engine" Value="{pkg['engines']['vscode']}"/>
      <Property Id="Microsoft.VisualStudio.Code.ExtensionKind" Value="ui,workspace"/>
    </Properties>
  </Metadata>
  <Installation>
    <InstallationTarget Id="Microsoft.VisualStudio.Code"/>
  </Installation>
  <Dependencies/>
  <Assets>
    <Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true"/>
    <Asset Type="Microsoft.VisualStudio.Services.Content.Details" Path="extension/README.md" Addressable="true"/>
  </Assets>
</PackageManifest>
"""
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("[Content_Types].xml", content_types)
    z.writestr("extension.vsixmanifest", manifest)
    for f in files:
        z.write(f, "extension/" + f.relative_to(SRC).as_posix())
print(f"wrote {out}")
