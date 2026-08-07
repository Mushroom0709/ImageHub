# Domain docs

## Layout

**Single-context.** One `CONTEXT.md` at the repo root holds the project-wide context. Architecture decision records live in `docs/adr/`.

```
CONTEXT.md           # project-wide context
docs/
  adr/               # architecture decision records
    0001-*.md
    0002-*.md
```

## Reading rules

- **Always read `CONTEXT.md`** before making non-trivial changes to the repo. It describes the project's goals, architecture, conventions, and gotchas.
- **Read ADRs** when a decision they describe is relevant to the work at hand. Don't read all of them upfront — they're reference material.
- ADRs are numbered sequentially and never modified after acceptance (except for typo fixes). A new decision supersedes an old one by writing a new ADR that references the old.

## Writing rules

- Update `CONTEXT.md` when you learn something about the project that future-you or another agent will need to know.
- Write an ADR when a decision has meaningful trade-offs or will affect future work. Small, reversible decisions don't need one.
- ADR format: `#### 000X — <short title>`. Status: Accepted / Superseded by NNNN.
