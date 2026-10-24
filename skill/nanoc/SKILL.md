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

**Do not grep the `techage` source to answer questions about the live world.**
If the user asks what machines exist, what a node's number/state/inventory is,
what is connected, or "what did we do so far": call `nanoc_scan` (and
`nanoc_catalog` for topics) first. The source only describes the mod; it does
not know the running world. Source reading is for mod development only.

## Write and test

- Reference: `nanoc://language` (primer), `nanoc://manual`, `nanoc://reference`,
  `nanoc://examples/techage_monitor` and `nanoc://examples/termlib_demo`.
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

## Pitfalls

- One debugger/terminal client at a time; another attached client blocks
  control commands. If you get "controller is busy", close the other client.
- A failed compile leaves the controller stopped.
- The controller must be in a loaded/forceloaded area, otherwise `NOT_LOADED`.
- `printf` output comes back from `nanoc_read`/`nanoc_exec`; `log("...")` lines
  are prefixed `[log]`.
- Do not move blocks or change the world (move/turn/pusher commands) unless the
  user explicitly asks for it. Prefer machine state commands.

## Typical request

"Make the furnace only run when the input chest has ore and stop when the
output chest is full." -> scan -> find furnace/chest numbers -> write a loop
that reads topic 131/192 states -> send topic 1 on/off -> check -> exec ->
read output -> refine.
