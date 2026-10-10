#!/bin/bash
# Build a VSIX for the NanoC VS Code extension (no vsce needed).
# Usage: ./build-vsix.sh [output.vsix]
# Then:  code --install-extension <output.vsix>
set -e

here="$(cd "$(dirname "$0")" && pwd)"
ext="$here/nanoc-debug"
out="${1:-$here/nanoc-debug.vsix}"
work="$(mktemp -d)"

mkdir -p "$work/extension"
cp -r "$ext/." "$work/extension/"

cat > "$work/extension.vsixmanifest" <<'XML'
<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011">
  <Metadata>
    <Identity Language="en-US" Id="nanoc-debug" Version="0.3.0" Publisher="joe7575" />
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
XML

cat > "$work/[Content_Types].xml" <<'XML'
<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension=".json" ContentType="application/json"/>
  <Default Extension=".js" ContentType="application/javascript"/>
  <Default Extension=".vsixmanifest" ContentType="text/xml"/>
</Types>
XML

rm -f "$out"
( cd "$work" && zip -qr "$out" . )
rm -rf "$work"
echo "built: $out"
