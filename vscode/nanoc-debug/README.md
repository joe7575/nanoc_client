# NanoC Debugger for VS Code

Minimal VS Code debugger extension that starts the `nanoc-dap` adapter
(from `nanoc_client`). It also provides basic syntax highlighting for
`.nanoc` / `.nc` files.

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
      "source": "${workspaceFolder}/myprogram.nanoc"
    }
  ]
}
```

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

## Linting

`.nanoc` / `.nc` files are linted automatically on save (and on open) via the
local `nanoc-check` (unbalanced brackets, unknown functions, undeclared
variables). Findings show in the **Problems** panel and jump to the line on
double-click. Run it manually with **NanoC: Check Program (lint)**.
