# NanoC documentation — where to find what

Start here. This page is the map, not the manual.

## I want to…

| I want to… | Read |
|---|---|
| write a NanoC program | [`language.md`](language.md) — code-generation primer |
| look up a language detail (types, operators, limits) | [`reference.md`](reference.md) |
| learn how to call Techage machines from NanoC | [`manual.md`](manual.md) — section "Techage / Techage" |
| look up a topic number | [`techage_topics.md`](techage_topics.md) |
| see verified behaviour of a specific block | [`techage_cookbook.md`](techage_cookbook.md) |
| drive a controller over the MCP tools | [`workflow.md`](workflow.md) |
| see a complete program | [`examples/README.md`](examples/README.md) |

## The one rule that is easy to get wrong

Techage calls always take **three** arguments, and the payload type depends on
the topic:

```c
ta_send_cmd(number, topic, payload)      // -> status (0 = accepted)
ta_req_data(number, topic, payload)      // -> number
ta_req_data_s(number, topic, payload)    // -> string
```

| Call | numeric topics | string topics |
|---|---|---|
| `ta_send_cmd` | `< 64` | `>= 64` |
| `ta_req_data` | `< 192` | `>= 192` |

Numeric payloads are **array references**, never scalars:

```c
int32 p[0]
p[0] = 3
ta_send_cmd(1234, 2, p)     // correct
// ta_send_cmd(1234, 2, 3)  // compile error: array or string expected
// ta_req_data(1234, 130)   // compile error: array or string parameter required
```

A scalar is rejected at compile time (nanoclib >= 0.2.7). Before that it was
silently misread as an array address: the command returned `0` and did nothing.

Full details: [`manual.md`](manual.md) — section "Built-in functions".

## Where these files come from

The documentation lives in several repositories, each owning its part. This
directory holds copies so the client package is self-contained when installed
from git.

| File | Source repository | Owns |
|---|---|---|
| `language.md` | [`joe7575/nanoc`](https://github.com/joe7575/nanoc) — `docs/nanoc_llm_prompt.md` | the language |
| `reference.md` | [`joe7575/nanoc`](https://github.com/joe7575/nanoc) — `docs/nanoc_reference.md` | the language |
| `manual.md` | [`joe7575/nanoc_mod`](https://github.com/joe7575/nanoc_mod) — `doc/manual.md` | the in-game computer |
| `techage_topics.md` | [`joe7575/beduino`](https://github.com/joe7575/beduino) — `BEPs/bep-005_ta_cmnd.md` | the command protocol |
| `examples/README.md`, `examples/*.nanoc` | [`joe7575/nanoc_mod`](https://github.com/joe7575/nanoc_mod) — `examples/` | example programs and overview |
| `techage_cookbook.md` | this repository | verified block behaviour |
| `workflow.md` | this repository | how to drive the MCP tools |

The topic table is a shared specification: `beduino`, `techage`, `pdp13`,
`nanoc_lib` and `nanoc_mod` all reference it, so it stays in its own repository.

## Editing

Do not edit the vendored files here. Change the source repository, then run:

```bash
python tools/sync_docs.py            # copy + write docs/SOURCES.json
python tools/sync_docs.py --check    # fail if a copy is out of date
```

`docs/SOURCES.json` records the source commit of every file, so drift is
visible in review.

## Over MCP

The same files are served to AI clients as resources: `nanoc://index`,
`nanoc://language`, `nanoc://reference`, `nanoc://manual`, `nanoc://topics`,
`nanoc://cookbook`, `nanoc://workflow`, `nanoc://examples` (overview)
and `nanoc://examples/...`.
