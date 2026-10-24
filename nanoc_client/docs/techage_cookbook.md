# Techage cookbook for NanoC

Verified behaviour of the TA4 blocks used by NanoC. Everything here is
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

## Recipe adapter (ta4_recipe_adapter)

Read-only recipe source for machines whose recipes are not in a recipe block
(furnace, electronic fab). It uses the Beduino IOT sensor's size, textures and
wall/floor/ceiling variants; mount it on any face of the machine. It detects
the machine on its back side (the same direction logic as the IOT sensor
port 0), without a formspec. Right-click re-detects.

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
| 129 | request | - | 1 running, 2 blocked, 3 standby, 4 no power, 5 fault, 6 stopped |
| 141 | request | - | configured output name (`nvm.output`), **not** the `dst` contents |

Inputs go into `src` (2x2). A pusher can only pull from `dst`; leftover `src`
items stay until a matching recipe consumes them (there is no remote flush).
Push the ingredients first, then select the output via the adapter (topic 64),
then start.

## Electronic fab (ta4_electronic_fab)

| Topic | Kind | Payload | Meaning |
|---|---|---|---|
| 1 | send | `[0\|1]` | stop / start |
| 129 | request | - | state as above |

Recipes come from the adapter (topic 64). Output **and waste** are placed in
`dst`; e.g. chip recipes return `basic_materials:empty_spool`. Pull the product
with a filtered pusher, but also pull or clear the waste, otherwise `dst` fills
up and the fab stops.

## NanoC notes for plant programs

- `ta_send_cmd` and `ta_req_data(_s)` return a value, so a **bare call as a
  statement is a syntax error**. Assign the status (`g_rc = ta_send_cmd(...)`)
  or use the result in an expression. `sleep()` and `log()` return nothing and
  may stand alone.
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
