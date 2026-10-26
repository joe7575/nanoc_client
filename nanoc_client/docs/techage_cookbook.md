# Techage cookbook for NanoC

Verified behaviour of the Techage blocks used by NanoC (TA3/TA4/TA5).
Everything here is
available at runtime through the `nanoc_*` tools; no mod source is required.

Every call is one of:

```c
ta_send_cmd(number, topic, payload)   // -> status
ta_req_data(number, topic, payload)   // -> number
ta_req_data_s(number, topic, payload) // -> string
```

Numeric payloads are `int32[]` arrays (`int32 p[0]` has one element,
`p[0] = value`). String payloads are `str8`. The payload type depends on the
topic: `ta_send_cmd` uses strings for topics >= 64, `ta_req_data(_s)` for
topics >= 192; all other topics use numeric arrays.

## Pusher (ta4_pusher)

| Topic | Kind | Payload | Meaning |
|---|---|---|---|
| 1 | send | `[0\|1]` | stop / start |
| 65 | send | `"item name"` | only push this item (`""` clears the filter) |
| 20 | send | `[n]` | push limit: stop after n items |
| 68 | send | `[n]` | alias for 20 |
| 150 | request | - | number of items pushed since start |
| 129 | request | - | state: 1 running, 2 blocked, 3 standby, 6 stopped |

Start sequence: set filter (65), set limit (20), start (1). Poll 150 until it
reaches the limit. The pusher stops itself at the limit. The pusher's `main`
inventory (visible in `nanoc_scan`) holds the configured filter item, not a
buffer of items waiting to be pushed.

## Autocrafter (ta4_autocrafter)

| Topic | Kind | Payload | Meaning |
|---|---|---|---|
| 10 | send | `[hi, lo, idx]` | recipe from a recipe block; `num = hi*65536 + lo` |
| 11 | send | - | flush the input (`src`) inventory |
| 1 | send | `[0\|1]` | stop / start |
| 129 | request | - | 1 running, 2 blocked, 3 standby, 4 no power, 5 fault, 6 stopped |

The recipe is taken from the recipe block, so the program does not need the
ingredient string. Output: crafter `dst` -> pusher -> output chest.

## Chest (ta4_chest)

| Topic | Kind | Payload | Meaning |
|---|---|---|---|
| 131 | request | - | 0 empty, 1 loaded, 2 full |
| 140 | request | `[1, idx]` | item count in slot idx |
| 140 | request | `[2, idx]` | item name in slot idx |
| 140 | request | `[3]` | store size (e.g. 2000) |
| 192 | request | `"item"` | item count by name; **substring match** |

## Recipe block (ta4_recipeblock)

| Topic | Kind | Payload | Response |
|---|---|---|---|
| 156 | request | - | max recipes (10) |
| 157 | request | - | selected recipe index (1..10) |
| 158 | request | `[idx]` | output count (0 = empty) |
| 193 | request | `"idx"` | output item name (string) |
| 194 | request | `"idx,slot"` | input item name at slot 1..9 (string) |

A configured recipe with output count 0 is empty. Duplicate input items appear
in multiple slots; count them to get the required amount.

## Signal tower (ta4_signaltower)

| Topic | Kind | Payload | Meaning |
|---|---|---|---|
| 2 | send | `[0\|1\|2\|3]` | off / green / amber / red |
| 130 | request | - | current colour |

## Door controller II (ta3_doorcontroller2)

| Topic | Kind | Payload | Meaning |
|---|---|---|---|
| 1 | send | `[0\|1]` | stop / start |
| 9 | send | `[cmd, idx]` | `0`=exchange, `1`=set, `2`=dig, `3`=reset, `4`=to1 (initial), `5`=to2 (exchange); `idx`=slot 1..6 |
| 147 | request | `[idx]` | slot state: `1`=initial, `2`=exchange |

Topic 147 is a **request** (`ta_req_data`), not a send. Example:

```c
int32 p[1]
int32 q[0]
p[0] = 4
p[1] = slot
ta_send_cmd(dc, 9, p)       // {4, slot} = to1
p[0] = 5
ta_send_cmd(dc, 9, p)       // {5, slot} = to2
q[0] = slot
printf("%d\n", ta_req_data(dc, 147, q))
```

## Display (ta4_display, ta4_display2, ta3_monitor)

| Topic | Kind | Payload | Meaning |
|---|---|---|---|
| 17 | send | - | clear |
| 67 | send | `"text"` | add one line (scroll) |
| 68 | send | `"<row> <text>"` | write row 1..n (space separated) |

Payloads are strings. NanoBasic `dclr(dp)` is topic 17;
`dputs(dp, 0, text)` is topic 67 (add line); `dputs(dp, row, text)` with
row > 0 is topic 68 and needs a **space** between row and text. Example:

```c
int32 p0[0]
ta_send_cmd(display, 67, "closed")
ta_send_cmd(display, 68, "1 closed")
ta_send_cmd(display, 17, p0)
```

## Other command blocks

- **TA5 fly controller** (`ta5_flycontroller`): topics `11`, `18`, `19`, `24`,
  request `129` (same movement semantics as the move controller).
- **TA5 teleport block** (`ta5_tele_tube` / `_pipe`): topics `1` (start/stop),
  request `129` (state); the wireless pair is shown in the scan as an edge
  with `via = "teleport"`.
- **TA3 monitor** (`ta3_monitor`): same display topics `17`/`67`/`68`.
- Building lamps, the observer, the Basic Terminal, flip-flop, timer and the
  command/mesecons converters have **no Beduino interface** (they are
  power-controlled, string-command-only or formspec-only). They appear in the
  scan but have no `caps`.
- The scan includes TA3/TA4/TA5 command blocks; TA1/TA2 are excluded.

## Recipe adapter (ta4_recipe_adapter)

Recipe source for machines that do not expose recipes themselves. It is a
compact block with its own animated texture; mount it on any face of the
machine. It detects the machine on its back side (the same direction logic as
the IOT sensor port 0), without a formspec. Right-click re-detects.

The **TA3 furnace needs it**. The **TA4 electronic fab** provides the same
topics directly (see below), so it works without an adapter.

| Topic | Kind | Payload | Meaning |
|---|---|---|---|
| 64 | send | `"idx"` | select the recipe on the target (furnace output / fab recipe); push furnace inputs first |
| 156 | request | - | number of recipes |
| 158 | request | `[idx]` | output count |
| 160 | request | - | target machine node number |
| 193 | request | `"idx"` | output item name |
| 194 | request | `"idx,slot"` | input item name |
| 195 | request | `"name"` | recipe index for an output name (0 = not found) |
| 161 | request | `[idx]` | furnace recipe time; 0 for the fab |
| 162 | request | `[idx,slot]` | input count |
| 163 | request | `[idx]` | number of inputs |

Duplicate recipe slots are listed separately (bronze is `copper_ingot` three
times plus `tin_ingot`). Sum topic 162 per item name before checking stock or
feeding the machine, otherwise only one of the duplicates is produced.

## Furnace (ta3_furnace / ta4_furnace_top)

| Topic | Kind | Payload | Meaning |
|---|---|---|---|
| 1 | send | `[0\|1]` | stop / start |
| 11 | send | - | move leftover `src` items to `dst` (refused while running; returns 1/0) |
| 129 | request | - | 1 running, 2 blocked, 3 standby, 4 no power, 5 fault, 6 stopped |
| 141 | request | - | configured output name (`nvm.output`), **not** the `dst` contents |

Inputs go into `src` (2x2). A pusher can only pull from `dst`; leftover `src`
items stay until a matching recipe consumes them. Use topic 11 to move them to
`dst` (like the autocrafter flush) and then remove them with a pusher.
Push the ingredients first, then select the output via the adapter (topic 64),
then start.

## Electronic fab (ta2/ta3/ta4_electronic_fab)

| Topic | Kind | Payload | Meaning |
|---|---|---|---|
| 1 | send | `[0\|1]` | stop / start |
| 64 | send | `"idx"` | select recipe *idx* |
| 129 | request | - | state as above |
| 156 | request | - | number of recipes |
| 158 | request | `[idx]` | output count |
| 160 | request | - | own node number |
| 161 | request | `[idx]` | 0 (fab recipes have no time) |
| 162 | request | `[idx,slot]` | input count |
| 163 | request | `[idx]` | number of input slots (4) |
| 193 | request | `"idx"` | output item name |
| 194 | request | `"idx,slot"` | input item name |
| 195 | request | `"name"` | recipe index for an output name (0 = not found) |

The fab selects the recipe with topic 64 and processes it automatically when
the inputs are in `src`. Output **and waste** are placed in `dst`; e.g. chip
recipes return `basic_materials:empty_spool`. Pull the product with a filtered
pusher, but also pull or clear the waste, otherwise `dst` fills up and the fab
stops.

## NanoC notes for plant programs

- NanoBasic `hold`/`release` have no NanoC equivalent (commands are
  synchronous); `sleep(1)` is seconds, use `sleep(1000)` in NanoC.
- `goto`/`gosub` become functions/loops; `str$` becomes `str()`. NanoBasic
  `daytime$` is not available in NanoC; use `millis()` or omit the time.
- `ta_send_cmd`/`ta_req_data(_s)` may be used as plain statements; their result
  is discarded. Assign it (`g_rc = ta_send_cmd(...)`) if you need the status.
  This needs **nanoclib >= 0.2.5**; older cores reject bare value-returning
  calls. `sleep()` and `log()` return nothing and always worked as statements.
- Recipe data lists duplicate inputs as separate slots. Sum the counts per item
  name before checking stock or feeding a machine (bronze: 3x copper + 1x tin).
- `for i = 1 to 0` executes the body **once** (do-while); guard descending
  ranges with `if (...)`.
- User functions are statements, not expressions; store results in a global
  (e.g. `g_res`). External `ta_*` calls do work in expressions.
- At most 32 forward declarations; define functions before use or inline.
- Mutable strings inside functions must be globals; string locals/parameters
  are read-only.
- A single array is limited to 127 words (512 bytes); the call stack is 128
  words.
- `sleep(ms)`; `millis()`; `key()` returns one byte (-1 when empty), so build
  numbers from byte values or wait for newline 10/13.
