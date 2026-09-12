# kicad-ai-stack: the KiCad workspace

The stack for designing boards with Claude Code and KiCad 10. One folder per role:

- `kicad-mcp-layer/` the library (`kicad_layer.design`, a board as data) and the MCP server, a git repo.
  Its `CLAUDE.md` has the rules for changing it; the plan is `research/notes/09-kicad-mcp-layer-roadmap.md`.
- `projects/` one folder per board, each a private git repo built on the library, not published with the
  workspace (`.gitignore`). A board's own rules are in its `WORKFLOW.md`; the boards themselves are listed
  in `CLAUDE.local.md`, which stays on this machine.
- `research/` shared knowledge, kept on this machine and not published: `references/` the document library (datasheets and reference designs;
  read them through the `doc_*` tools), `notes/` the numbered research notes and the rulings in
  `00-design-inputs.md`, `repos/` cloned repositories, `trials/` experiments kept as evidence,
  `parts/` fact sheets per part (`doc_facts` reads them; ask it before any datasheet).
- `tools/` FreeRouting and its Java runtime, where the library looks for them.
- `.mcp.json` registers the server with this folder as the workspace; every path a tool takes must be
  under it.

Working here: read `kicad-mcp-layer/CLAUDE.md` before touching the library, a project's `WORKFLOW.md`
before touching a board, and `research/notes/00-design-inputs.md` before changing how anything works.
Commit at milestones without asking; never push.
