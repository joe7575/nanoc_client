# NanoC Client

Control your **NanoC controller** in a Luanti/Minetest world from your own PC:
write programs in VS Code, upload them, watch the terminal, and let an AI
assistant (GitHub Copilot) inspect and drive your machines.

This guide is written for **players**. You do not need access to the server,
its configuration or its logs.

---

## What you need

Three things come from the **server owner**, one from **the game**.

| Item | Where it comes from | Example |
|---|---|---|
| **Host** (address) | ask the server owner | `play.example.org` |
| **Port** | ask the server owner | `41100` |
| **TLS fingerprint** | ask the server owner | `AB:CD:EF:12:...:34:56` |
| **Token** | your controller, in game | `<your token>` |

### Ask the server owner for

> "I want to use the NanoC external client. Please send me the **host**, the
> **port** and the **SHA-256 fingerprint** of the NanoC bridge certificate."

The connection is **always encrypted (TLS)**. The fingerprint is how your PC
verifies that it is really talking to your server and not to an impostor. You
do not need any certificate file — the fingerprint is enough.

### Get your token in game

The token belongs to **your** controller and only you can create it:

1. Right-click your NanoC controller to open its window.
2. Press the **Token** button.
3. A window shows the token. Select the text and copy it.

Notes:

- Pressing **Token** again creates a **new** token. The old one stops working
  immediately, so update your configuration afterwards.
- Keep the token private. Anyone with host, port, fingerprint and token can
  control your controller.
- **Stand near your controller** (or keep its area loaded) while you connect.
  A controller in an unloaded part of the world cannot be reached.

---

## Install

You need **Python 3.8 or newer**.

### Windows

1. Install Python from <https://www.python.org/downloads/> and tick
   **"Add python.exe to PATH"** during setup.
2. Open **PowerShell** and run:

   ```powershell
   py -m pip install "git+https://github.com/joe7575/nanoc_client.git"
   ```

3. Check it worked:

   ```powershell
   nanoc ping --help
   ```

If Windows says `nanoc` is not recognized, use the module form instead — it
always works:

```powershell
py -m nanoc_client.nanoc ping --help
```

### Linux

```bash
python3 -m pip install --user "git+https://github.com/joe7575/nanoc_client.git"
```

If `nanoc` is still not found, add the user script directory to your `PATH`:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

Check:

```bash
nanoc ping --help
```

---

## First connection test

Replace the placeholders with your values. The fingerprint may be written with
or without colons.

### Linux

```bash
nanoc ping \
  --host play.example.org \
  --port 41100 \
  --tls \
  --tls-fingerprint "AB:CD:EF:12:...:34:56" \
  --token YOUR_TOKEN_HERE
```

### Windows (PowerShell)

```powershell
nanoc ping `
  --host play.example.org `
  --port 41100 `
  --tls `
  --tls-fingerprint "AB:CD:EF:12:...:34:56" `
  --token YOUR_TOKEN_HERE
```

A working connection prints something like:

```
Controller 6845 "C1" at (120, 45, 890) available
  owner you, running, program loaded, nanoclib 0.2.8
```

That means: bridge reachable, TLS verified, token accepted, controller found.

---

## Use it with GitHub Copilot in VS Code

This is the most convenient way: you describe what you want in plain language
and Copilot works on your controller.

### 1. Install the prerequisites

- **VS Code** with the **GitHub Copilot** extension, signed in.
- The NanoC client (see [Install](#install) above).

### 2. Create the MCP configuration

Create a folder `.vscode` in your project folder and inside it a file
`mcp.json`:

```json
{
  "servers": {
    "nanoc": {
      "type": "stdio",
      "command": "nanoc-mcp",
      "env": {
        "NANOC_HOST": "play.example.org",
        "NANOC_PORT": "41100",
        "NANOC_TOKEN": "YOUR_TOKEN_HERE",
        "NANOC_TLS": "1",
        "NANOC_TLS_FINGERPRINT": "AB:CD:EF:12:...:34:56"
      }
    }
  }
}
```

On **Windows**, if `nanoc-mcp` is not found, use the full path to the script,
for example:

```json
"command": "C:\\Users\\<you>\\AppData\\Local\\Programs\\Python\\Python312\\Scripts\\nanoc-mcp.exe"
```

On **Linux** the usual path is:

```json
"command": "/home/<you>/.local/bin/nanoc-mcp"
```

> Keep this file private. It contains your token. If you share your project,
> add `.vscode/mcp.json` to `.gitignore`.

### 3. Start the server

1. Press `Ctrl+Shift+P` to open the command palette.
2. Run **MCP: List Servers**.
3. Select `nanoc` and choose **Start Server**.

The status must show **Running**. After changing `mcp.json` or your token,
choose **Restart Server** (or reload the window).

### 4. Talk to your controller

Open the Copilot chat and switch to **Agent** mode. Then simply ask:

```
Check with nanoc_ping whether my controller is reachable.
```

```
Scan my plant and list all machines with their numbers and state.
```

```
Read main.nanoc, check it, and upload it to the controller.
```

Copilot picks the right tools by itself. You can also name a tool explicitly,
for example "use `nanoc_catalog` to look up topic 192".

### Available tools

| Tool | What it does |
|---|---|
| `nanoc_ping` | Check connection, token and controller state |
| `nanoc_scan` | List nearby machines with number, state and inventory |
| `nanoc_catalog` | Look up what a topic number means |
| `nanoc_check` | Check a program for errors before uploading |
| `nanoc_push` | Upload and compile a program |
| `nanoc_program_get` | Read the program currently on the controller |
| `nanoc_run` / `nanoc_stop` | Start / pause the controller |
| `nanoc_read` | Read the controller's terminal output |
| `nanoc_exec` | Upload, run and read in one step |

> **Careful with `nanoc_exec` and `nanoc_push`:** both replace the program
> stored on the controller. If a working program is running, read it first with
> `nanoc_program_get` and keep a copy.

The server also hands Copilot the NanoC documentation, so it knows the language
and the Techage topics without you explaining them.

---

## Terminal view (TUI)

A live view of the controller's screen, including colours and keyboard input:

```bash
nanoc tui --host play.example.org --port 41100 --tls \
  --tls-fingerprint "AB:CD:EF:12:...:34:56" --token <TOKEN>
```

Keys: type and press Enter to send a line; **F1–F8** send the function keys;
**Ctrl-C / Ctrl-Q / Ctrl-X** quit.

On **Windows** the terminal view needs one extra package:

```powershell
py -m pip install windows-curses
```

---

## Debugging in VS Code

With the NanoC debugger extension you can set breakpoints, step through your
program and inspect variables.

1. Install the extension `nanoc-debug` (`.vsix` file) via
   **Extensions → … → Install from VSIX**.
2. Open your `.nanoc` file.
3. Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "type": "nanoc",
      "request": "attach",
      "name": "NanoC",
      "host": "play.example.org",
      "port": 41100,
      "token": "<YOUR TOKEN>",
      "tls": true,
      "tlsFingerprint": "AB:CD:EF:12:...:34:56",
      "source": "${file}",
      "program": "${file}",
      "upload": true
    }
  ]
}
```

4. Press **F5**.

With `"upload": true` your current file is uploaded before attaching. Remove
`upload` and `program` if you only want to look at the program that is already
running.

Program output appears in the **NanoC terminal** (open it with `Ctrl+Alt+T`).
`log("...")` messages appear in the Debug Console.

---

## Troubleshooting

### `handshake failed: bad token`

- The token is wrong or outdated. Press **Token** in the controller window
  again and copy the new value.
- The token belongs to a **different** controller.
- Your controller's area is not loaded. Walk to it and try again.

### `certificate verify failed` or `fingerprint mismatch`

- The fingerprint does not match the server. Ask the server owner for the
  current value — it changes when the server certificate is renewed.
- Make sure you copied the whole fingerprint, including all colon-separated
  groups.

### Connection refused / timeout

- Host or port is wrong — check with the server owner.
- The server's NanoC bridge is not running. Only the server owner can fix that.

### `nanoc` or `nanoc-mcp` is not recognized

- **Windows:** use `py -m nanoc_client.nanoc ...` instead of `nanoc ...`.
- **Linux:** add `~/.local/bin` to your `PATH` (see [Install](#install)).
- In VS Code, use the full path in `mcp.json` (see above).

### The tools do not appear in Copilot chat

1. **MCP: List Servers** → is `nanoc` **Running**?
2. Is the chat in **Agent** mode?
3. Run **Developer: Reload Window**.
4. Update VS Code and the Copilot extension.

### A command returns success but nothing happens

- Check that the machine number is correct — use `nanoc_scan` instead of
  guessing.
- Some machines need a moment. Send the command, wait, then read the state.
- Make sure the target machine is in a loaded area of the world.

---

## Security

- Your **token** is a key to your controller. Do not post it, do not commit it.
- The connection is always TLS-encrypted and verified against the fingerprint.
- Only **one** client can control a controller at a time. Other clients can
  watch the terminal but cannot send commands.
- If you suspect your token leaked, press **Token** in the controller window to
  create a new one. The old token stops working immediately.

---

## License

AGPL-3.0-or-later. Source: <https://github.com/joe7575/nanoc_client>
