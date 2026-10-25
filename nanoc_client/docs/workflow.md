# NanoC workflow for AI clients

You are controlling a **NanoC controller** in a Luanti/Minetest world over the
MCP tools `nanoc_*`. The controller runs programs written in NanoC (a small
C-like language) and can command Techage/TechPack nodes by node number.

## Connection

The tools take `host`, `port`, `token`, `tls` per call. Defaults come from the
environment (`NANOC_HOST`, `NANOC_PORT`, `NANOC_TOKEN`, `NANOC_TLS`). The token
is shown in-game in the controller form (**Token** button) and belongs to one
controller. Without it the tools fail.

## The loop

1. `nanoc_scan` — dump the Techage network around the controller as JSON:
   nodes with `number`, `name`, `label`, `state`, `inv`, `inv_state`, `caps`,
   and `edges`. Use the **`number`** fields; that is how programs address nodes.
2. `nanoc_catalog` — dump the topic catalog (topic -> kind/name/payload/response)
   and the node name-pattern rules. Use it to pick the right topic for each node.
   For verified block behaviour (pusher filter/limit, autocrafter recipe
   reference, chest and recipe-block topics, signal tower), read
   `nanoc://cookbook`.
3. Write the program (see `nanoc://language`, `nanoc://manual`,
   `nanoc://reference`, `nanoc://examples/...`).
4. `nanoc_check` — local lint before uploading. Returns `file:line: message`
   or `OK`.
5. `nanoc_exec` — upload, compile, run and read the terminal output in one call.
   If the compile fails, the returned text starts with `compile failed:`.
6. Refine and repeat. Use `nanoc_program_get` to read what is currently stored,
   `nanoc_run` / `nanoc_stop` to resume/pause without uploading.

## Program basics

```c
func main() {
    int32 n = 6
    printf("chest %d: %d\n", n, ta_req_data(n, 131, [0]))
}
```

- `func` declares a function (no `void`); statements end at the line end
  (`;` only separates statements on one line).
- Types: `int32`, `uint32`, `str8`, `u8`, `u16`, `u32`. No floats.
- Comments: `//`. Blocks: `{ }`. Equality: `==`, inequality: `!=`.
- Arrays: `int32 a[10]`; pass arrays by reference with `int32[]` parameters.
- String literals: `str8 name = "text"`. Escapes `\n`, `\t`, `\\`, `\"`.

## Techage calls

```c
ta_send_cmd(number, topic, payload)      // -> status (0 = ok)
ta_req_data(number, topic, payload)      // -> numeric result
ta_req_data_s(number, topic, payload)    // -> string result
```

**Payload type depends on the topic and the function:**

| Call | numeric topics | string topics |
|---|---|---|
| `ta_send_cmd` | `< 64` | `>= 64` |
| `ta_req_data` | `< 192` | `>= 192` |

Numeric payloads are written as an array literal, e.g. `[1]`, `[2, idx]`,
`[x, y, z]`; string payloads as a string literal. The catalog lists the
expected payload for each topic. Topic `1` on the controller itself is
run/stop (`[1]` = on/run, `[0]` = off/stop).

Node states from topic `129`: 1 running, 2 blocked, 3 standby, 4 no power,
5 fault, 6 stopped, 7 unloaded, 8 inactive.

## Scan JSON

```json
{"center": {...}, "radius": 8,
 "nodes": [{"id": "6", "number": "6", "name": "techage:ta4_autocrafter",
            "label": "ta4 autocrafter", "state": "RUNNING",
            "inv_state": "loaded", "inv": {"main": [{"item": "default:stone",
            "count": 12}]}, "caps": {128: "identify", 129: "state", ...}}],
 "edges": [{"from": "6", "to": "4", "dir": ...}]}
```

Nodes without a techage number use their position string as `id`; only nodes
with a `number` can be addressed by the program. The scan is limited to TA4
nodes, TA5 teleport bridges, Hyperloop chests/tanks and the given radius
(1–16), centered on the controller owner while that player is online (otherwise
the controller). Teleport bridges (`techage:ta5_tele_tube` / `_pipe`) show
their wireless pair as `via = "teleport"`; Hyperloop chests/tanks
(`techage:ta5_hl_chest` / `_tank`) show their paired block as
`via = "hyperloop"` and carry a `hyperloop` object with `role`
(server/client), `conn_name`, `remote_name` and `conn_status`.

## Important behavior and limits

- **One debugger at a time.** The first client that attaches owns the
  controller; other clients only see output. Close the terminal/TUI/DAP client
  before using the MCP tools, and vice versa.
- **Upload stops on compile errors.** A failed compile leaves the controller
  stopped; fix the errors and upload again.
- **Program end restarts it.** After `main()` returns or `end` is reached, the
  controller restarts the program on the next tick. Long-running control logic
  belongs in a `while (1) { ... sleep(1000) ... }` loop.
- **CPU budget.** The server throttles the VM and yields; a tight loop without
  `sleep()` is spread over ticks. Use `sleep(ms)` for polling intervals.
- **The controller must be loaded.** If the area is unloaded the bridge reports
  `NOT_LOADED`; keep the controller in a loaded/forceloaded area.
- **`printf` output** goes to the controller terminal (channel returned by
  `nanoc_read`/`nanoc_exec`). **`log("...")`** goes to the debug channel and is
  shown in the VS Code Debug Console; MCP read also returns log lines prefixed
  with `[log]`.
- **Do not move blocks or change the world** unless explicitly asked. Prefer
  commands that only change machine state (on/off, limits, recipes).

## Debugging

- `nanoc_program_get` to inspect the stored program.
- `nanoc_check` for syntax/typos without touching the server.
- On a runtime error the program stops; the next `nanoc_read` or `nanoc_exec`
  shows the message. Use `nanoc://examples/techage_monitor.nanoc` as a pattern
  for reading chest states and crafter states.
