# Vendored NanoC documentation

These files are copied from the sibling repositories so that the client
package is self-contained when installed from git:

| File | Source |
|---|---|
| `language.md` | `nanoc/docs/nanoc_llm_prompt.md` (NanoC code-generation primer) |
| `reference.md` | `nanoc/docs/nanoc_reference.md` (full language reference) |
| `manual.md` | `nanoc_mod/doc/manual.md` (player manual, incl. Techage) |
| `techage_topics.md` | `beduino/BEPs/bep-005_ta_cmnd.md` (topic table) |
| `examples/*.nanoc` | `nanoc_mod/examples/` |
| `techage_cookbook.md` | Original here: verified TA4 API behaviour for NanoC |

Do not edit them here. Run `python tools/sync_docs.py` after changing a source;
`docs/SOURCES.json` records the source paths and git commits. The same files
are served to AI clients over MCP as resources (`nanoc://language`,
`nanoc://reference`, `nanoc://manual`, `nanoc://topics`,
`nanoc://examples/...`), as `nanoc://cookbook` and as the `nanoc://workflow`
quick start. The cookbook is original, not vendored.
