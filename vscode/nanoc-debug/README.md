# NanoC Debugger for VS Code

Minimal VS Code debugger extension that starts the `nanoc-dap` adapter
(from `nanoc_client`). It also provides basic syntax highlighting for
`.nanoc` / `.nc` files.

## Install (from this folder, no vsce needed)

```bash
mkdir -p ~/.vscode/extensions
ln -sfn ~/Projekte/nanoc_client/vscode/nanoc-debug ~/.vscode/extensions/nanoc-debug
```

Then reload VS Code (**Developer: Reload Window**).

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
