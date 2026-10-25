#!/usr/bin/env python3
"""Build a VSIX for the NanoC VS Code extension without vsce or zip.

Run from anywhere:
    python3 vscode/build_vsix.py
    py vscode\\build_vsix.py          (Windows)

The result is vscode/nanoc-debug.vsix (gitignored).
"""

import json
import os
import shutil
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
EXT = os.path.join(HERE, "nanoc-debug")
OUT = os.path.join(HERE, "nanoc-debug.vsix")


def main():
    with open(os.path.join(EXT, "package.json"), encoding="utf-8") as f:
        version = json.load(f)["version"]

    with tempfile.TemporaryDirectory() as tmp:
        work = os.path.join(tmp, "work")
        os.makedirs(work)
        shutil.copytree(
            EXT, os.path.join(work, "extension"),
            ignore=shutil.ignore_patterns("node_modules", "*.vsix", ".git"))

        manifest = f'''<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011">
  <Metadata>
    <Identity Language="en-US" Id="nanoc-debug" Version="{version}" Publisher="joe7575" />
    <DisplayName>NanoC Debugger</DisplayName>
    <Description xml:space="preserve">Debug NanoC controllers via nanoc-dap</Description>
    <Tags>debugger,nanoc,minetest,luanti</Tags>
    <Categories>Debuggers,Programming Languages</Categories>
    <GalleryFlags>Public</GalleryFlags>
    <Properties>
      <Property Id="Microsoft.VisualStudio.Code.Engine" Value="^1.75.0" />
    </Properties>
  </Metadata>
  <Installation>
    <InstallationTarget Id="Microsoft.VisualStudio.Code"/>
  </Installation>
  <Dependencies/>
  <Assets>
    <Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true" />
  </Assets>
</PackageManifest>
'''
        content_types = '''<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension=".json" ContentType="application/json"/>
  <Default Extension=".js" ContentType="application/javascript"/>
  <Default Extension=".vsixmanifest" ContentType="text/xml"/>
</Types>
'''
        for name, text in (
            ("extension.vsixmanifest", manifest),
            ("[Content_Types].xml", content_types),
        ):
            with open(os.path.join(work, name), "w", encoding="utf-8") as f:
                f.write(text)

        if os.path.exists(OUT):
            os.remove(OUT)
        with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
            for root, _, files in os.walk(work):
                for name in files:
                    full = os.path.join(root, name)
                    arc = os.path.relpath(full, work).replace(os.sep, "/")
                    z.write(full, arc)
    print("built:", OUT)


if __name__ == "__main__":
    main()
