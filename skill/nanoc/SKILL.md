---
name: nanoc
description: Use when controlling or inspecting a NanoC controller in Luanti/Minetest over MCP - techage machines, node numbers, ta_send_cmd/ta_req_data, nanoc_scan, nanoc_catalog, nanoc_exec, .nanoc files, techage automation, factory control. Trigger on NanoC, techage, Beduino commands, or when the user asks to automate machines in Luanti/Minetest. For questions about the running world/network state, use nanoc_scan/nanoc_catalog instead of searching the techage source.
license: AGPL-3.0-or-later
---

# NanoC controller (Luanti/Minetest)

The user runs a NanoC controller in a Luanti/Minetest world. It executes small
C-like programs and commands Techage/TechPack machines by node number. You
reach it through the `nanoc_*` MCP tools.

## First steps, always

1. Read the MCP resource `nanoc://workflow` for the loop and the gotchas.
2. `nanoc_scan` — get the techage network: node `number`, `name`, `label`,
   `state`, `inv`, `inv_state`, `caps`, `edges`.
3. `nanoc_catalog` — get topic semantics (send/request, payload, response).

Do not guess node numbers or topics. Take them from scan/catalog. Only nodes
with a numeric `number` can be addressed.

## Player first (normal case)

A normal player has **no mods and no libs** on the PC. Do not search the
filesystem for `techage`/`nanoc` and do not fetch GitHub. Everything needed is
served by the MCP server:
- `nanoc://workflow`, `nanoc://language`, `nanoc://manual`,
  `nanoc://reference`, `nanoc://topics`, `nanoc://cookbook`,
  `nanoc://examples/...`
- live: `nanoc_scan`, `nanoc_catalog`, `nanoc_read`.

**Runtime** questions (which nodes exist, state, inventories, connections):
use `nanoc_scan`/`nanoc_catalog`; never read source for this.

## Developer checkout only

Only if the workspace actually contains the repositories (development work:
fixing techage/nanoc or the compiler), source reading is expected. Players
normally do not have these. Use the GitHub repositories:
- <https://github.com/joe7575/techage> — `basis/command.lua` (send/beduino
  routing), `basic_machines/` (pusher, autocrafter, recipeblock, chests),
  `icta_controller/signaltower.lua`.
- <https://github.com/joe7575/nanoc_lib> — `src/nc_compiler.c`,
  `src/nc_runtime.c`, `src/nc_cfg.h` (language/VM limits).
- <https://github.com/joe7575/nanoc_mod> — `doc/manual.md`, `src/` (bridge,
  inspect, extfuncs, capabilities).
- <https://github.com/joe7575/beduino> — `BEPs/bep-005_ta_cmnd.md` (topics).

## Write and test

- Reference: `nanoc://language` (primer), `nanoc://manual`, `nanoc://reference`,
  `nanoc://topics`, `nanoc://cookbook`, `nanoc://examples/techage_monitor`,
  `nanoc://examples/termlib_demo`, `nanoc://examples/factory_control`,
  `nanoc://examples/fab_control`, `nanoc://examples/oven_control`.
- NanoC is C-like but not C: `func` instead of `void`, no floats, `//`
  comments, `{ }` blocks, no semicolons at line end, `int32`/`str8`/`u8`/`u16`/`u32`.
- Techage calls: `ta_send_cmd(number, topic, payload)` and
  `ta_req_data(number, topic, payload)`; string payloads for `ta_send_cmd`
  topics >= 64 and for `ta_req_data` topics >= 192, numeric arrays otherwise.
  Topic 1 on the controller itself is run/stop.
- Lint first with `nanoc_check`, then `nanoc_exec` (upload + compile + run +
  read output). On `compile failed:` read the line numbers and fix.
- Long-running logic needs a loop with `sleep(ms)`; after `main()` returns the
  program restarts automatically.

## NanoC quirks (compiler/VM)

- nanoclib **>= 0.2.2**: user functions with return values work in
  expressions; empty `for` ranges are skipped; only genuinely forward calls
  count against the 32-entry patch list. On older cores use a global result
  variable and guard `for i = 1 to 0` with `if (...)`.
- Strings inside functions use global storage; locals/parameters are
  read-only. Use global `str8` variables for mutable strings.
- No structs, no 2-D arrays, no floats; a single array block is max 127 words
  (512 bytes). The call stack is 128 words; deep recursion overflows.
- `ta_send_cmd`/`ta_req_data(_s)` can be used as plain statements (result
  discarded) on **nanoclib >= 0.2.5**. Assign it (`g_rc = ta_send_cmd(...)`)
  when you need the status; older cores reject bare value-returning calls.
- Recipe lists repeat duplicate inputs as separate slots; sum them per item
  name before checking stock or feeding a machine.

## Pitfalls

- One debugger/terminal client at a time; another attached client blocks
  control commands. If you get "controller is busy", close the other client.
- A failed compile leaves the controller stopped.
- The controller must be in a loaded/forceloaded area, otherwise `NOT_LOADED`.
- `printf` output comes back from `nanoc_read`/`nanoc_exec`; `log("...")` lines
  are prefixed `[log]`.
- In `nanoc_scan`, a pusher's `main` item is its configured filter, not a
  stuck item. Furnace topic 141 is the configured output name, not inventory;
  leftover furnace `src` items cannot be pulled by pushers.
- Do not move blocks or change the world (move/turn/pusher commands) unless the
  user explicitly asks for it. Prefer machine state commands.

## Typical request

"Make the furnace only run when the input chest has ore and stop when the
output chest is full." -> scan -> find furnace/chest numbers -> write a loop
that reads topic 131/192 states -> send topic 1 on/off -> check -> exec ->
read output -> refine.
