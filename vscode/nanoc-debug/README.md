# NanoC Debugger for VS Code

Minimal VS Code debugger extension that starts the `nanoc-dap` adapter
(from `nanoc_client`). It also provides basic syntax highlighting for
`.nanoc` files (`.nc` is accepted as an alias).

## Install

Build and install the VSIX (no `vsce` needed), then restart VS Code:

```bash
~/Projekte/nanoc_client/vscode/build-vsix.sh
code --install-extension ~/Projekte/nanoc_client/vscode/nanoc-debug.vsix
```

(Simply symlinking the folder into `~/.vscode/extensions` is not always picked
up by VS Code; the VSIX install is reliable.)

The extension looks for the adapter in this order:

1. `nanoc.dapPath` setting,
2. `~/.local/venvs/nanoc/bin/nanoc-dap` (the setup default),
3. `nanoc-dap` on `PATH`.

## Usage

Open the same `.nanoc` source file locally that is compiled on the controller
(so line numbers match), then add a `launch.json` configuration:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "type": "nanoc",
      "request": "attach",
      "name": "NanoC: attach",
      "host": "127.0.0.1",
      "port": 41100,
      "token": "<TOKEN from the controller>",
      "source": "${file}",
      "program": "${file}",
      "upload": true
    }
  ]
}
```

`${file}` is the active editor, so F5 always uses (and, with `"upload": true`,
uploads + compiles) the file you are looking at. Without `upload`, F5 only
attaches and the controller keeps whatever program it had. Breakpoints are
re-applied automatically after the upload.

Start it with F5. Breakpoints, stepping, the call stack and the Globals/Locals
variables view are available; `printf` output appears in the Debug Console.

## Edit / upload / download

While a debug session is active:

- **NanoC: Upload Program to Controller** (Ctrl+Alt+U) sends the active editor
  to the controller and recompiles it (breakpoints are re-applied automatically).
- **NanoC: Download Program from Controller** opens the controller's current
  program in a new editor tab.

Typical loop: attach (F5) → download → edit/save → upload (Ctrl+Alt+U) →
Continue (F5) → debug.

## Notes

- `program`/`source` with `${file}` use the *active editor*. If the active tab
  points to a missing file (VS Code restored a deleted tab), the extension
  falls back to the single `.nanoc`/`.nc` file in the workspace.
- Breakpoints belong to a file; breakpoints for other files are ignored, so a
  leftover breakpoint set in a deleted file cannot hijack the uploaded program.

## Linting

`.nanoc` files (`.nc` alias) are linted automatically on save (and on open) via the
local `nanoc-check` (unbalanced brackets, unknown functions, undeclared
variables). Findings show in the **Problems** panel and jump to the line on
double-click. Run it manually with **NanoC: Check Program (lint)**.
