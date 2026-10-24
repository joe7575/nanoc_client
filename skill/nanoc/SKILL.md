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

## Runtime vs. development

**Runtime** questions ("what nodes exist, what is a node's number/state/
inventory, what is connected, what did we do so far"): call `nanoc_scan`,
`nanoc_catalog` and `nanoc_read`. Do not read the techage source for this; it
cannot know the running world.

**Development** (fixing techage/nanoc, writing or debugging a NanoC program,
understanding compiler limits): the source is the reference and reading it is
expected. Use the GitHub repositories (not a local checkout):
- <https://github.com/joe7575/techage> — `basis/command.lua` (send/beduino
  routing), `basic_machines/` (pusher, autocrafter, recipeblock, chests),
  `icta_controller/signaltower.lua`.
- <https://github.com/joe7575/nanoc_lib> — `src/nc_compiler.c`,
  `src/nc_runtime.c`, `src/nc_cfg.h` (language/VM limits).
- <https://github.com/joe7575/nanoc_mod> — `doc/manual.md`, `src/` (bridge,
  inspect, extfuncs, capabilities).
- <https://github.com/joe7575/beduino> — `BEPs/bep-005_ta_cmnd.md` (topics).

If a repository is still private, the MCP resources (`nanoc://language`,
`nanoc://manual`, `nanoc://topics`, `nanoc://examples/...`) are the fallback;
they do not carry the mod source.

## Write and test

- Reference: `nanoc://language` (primer), `nanoc://manual`, `nanoc://reference`,
  `nanoc://topics`, `nanoc://examples/techage_monitor`,
  `nanoc://examples/termlib_demo`, `nanoc://examples/plant_control`.
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

- `for i = 1 to 0` executes the body **once** (do-while). Guard descending
  ranges with `if (...)`.
- User functions are statements, not expressions. Return values via a global
  (e.g. `g_res`); external `ta_*` calls do work in expressions.
- At most 32 forward declarations; define functions before use or inline
  helpers.
- Strings inside functions use global storage; locals are read-only. Use
  global `str8` variables for mutable strings.
- No structs, no 2-D arrays, no floats; a single array block is max 127 words
  (512 bytes). The call stack is 128 words; deep recursion overflows.

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
