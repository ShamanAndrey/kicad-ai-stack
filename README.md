# kicad-ai-stack

A workspace for designing boards with Claude Code and KiCad 10: the library and MCP server, a one-command
setup, and the working rules. Two repositories make it up:

* **[kicad-mcp-layer](https://github.com/ShamanAndrey/kicad-mcp-layer)**, the library: an MCP server that
  drives KiCad 10 through kicad-cli, its IPC API and lossless file edits, and `kicad_layer.design`, a
  board as data with the KiCad files as build outputs. Install it alone if that is all you need.
* **kicad-ai-stack**, this repository: the setup script that fetches and wires everything, and the rules
  a Claude Code session works by.

One folder per role:

- `kicad-mcp-layer/` the product: `kicad_layer.design`, a board as data with the KiCad files as build outputs,
  and the MCP server that checks, reads, renders, exports and edits KiCad projects. Its own README covers
  install, tools and configuration.
- `research/` is created on your machine by the tools and is not part of this repository: `references/`
  is the document library `doc_fetch` fills with the datasheets and reference designs you need, `parts/`
  holds the fact sheets `doc_facts` reads. Bring your own documents; none are redistributed.
- `tools/` where FreeRouting and its Java runtime go; `tools/README.md` says which.
- `projects/` the boards. They are private repositories and are not part of this one; the hello-world
  example that exercises the whole loop is `kicad-mcp-layer/examples/hello_world`.
- `CLAUDE.md` the working rules Claude Code reads in this folder.

## Setting it up

Install KiCad 10.0.6 from kicad.org, have Python 3.12 or newer and git on the PATH, then:

```
python bootstrap.py
```

It clones the library into `kicad-mcp-layer/` (its own repository), creates its virtual environment and
installs it, writes `.mcp.json` with this machine's paths so Claude Code finds the server when opened
in this folder, and runs the health check. Options: `--tools` fetches FreeRouting and, on Windows, a
Java runtime into `tools/`; `--ipc` adds KiCad's live API; `--browser` adds a headless Chromium for
stubborn datasheet portals; `--dry-run` only tells you what it would do. Every step keeps what is
already there, so run it again after a `git pull`.

The server starts read-only with the core tools. `KICAD_LAYER_MODE=write` and `KICAD_LAYER_TOOLS=full`
in `.mcp.json` unlock design edits and the routers. Datasheets are not in the repository: `doc_fetch`
brings the ones you need into `research/references/`.

## Finding your way

Searching for AI-assisted PCB design with KiCad, a KiCad MCP server, or KiCad with Claude Code? The
library is [kicad-mcp-layer](https://github.com/ShamanAndrey/kicad-mcp-layer); this repository is the
workspace that sets it up. Its tool reference is `kicad-mcp-layer/docs/tools.md`, the authoring API
`kicad-mcp-layer/docs/design-api.md`.

## A word to visitors

This whole stack stands on KiCad, which is free, open source, and funded by donations. Its developers'
plans for the next release, an API for the schematic editor among them, would let this project do far
more than it does today. Please visit [kicad.org](https://www.kicad.org/) and
[donate to KiCad](https://www.kicad.org/donate/).

## Licence

MIT, see [LICENSE](LICENSE); `kicad-mcp-layer` is MIT under its own LICENSE. Datasheets, reference designs
and KiCad's demo projects are not redistributed here.
