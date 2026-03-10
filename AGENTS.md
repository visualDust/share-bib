# Agent Instructions

Use the `sharebib` skill for requests about ShareBib collections, papers, SDK API keys, exports, or programmatic paper-management workflows.

This is the root-level agent instruction file for the repository. It applies to Claude Code, Codex, Cursor, Windsurf, and similar tools.

## Trigger

Typical triggers:

- ShareBib
- paper collection
- research papers
- BibTeX
- SDK / CLI paper automation

Invoke with:

```text
$sharebib
```

## Primary references

- [skills/sharebib/SKILL.md](skills/sharebib/SKILL.md) - agent-facing workflow and command reference
- [sdk/README.md](sdk/README.md) - human-facing SDK and CLI usage
- [README.md](README.md) - product overview and deployment notes

Preferred CLI command: `sharebib`
Compatibility alias: `sharebib-cli`

## Configuration

Supported configuration sources, highest priority first:

1. CLI flags (`--api-key`, `--base-url`, `--timeout`, `--config`)
2. Environment variables
3. Project config: `.sharebib/config.json`
4. User config: `~/.sharebib/config.json`

Environment variables:

```bash
export SHAREBIB_API_KEY="pc_xxxxxxxxxxxxxxxxxxxxxxxxx"
export SHAREBIB_BASE_URL="https://papers.example.com"
export SHAREBIB_TIMEOUT="30"
```

## Project guidelines

- Follow PEP 8 for Python code
- Keep docs aligned with real CLI behavior
- Never commit secrets or persist live API keys in repo files
- Prefer API-key-safe workflows for programmatic access
- Run basic verification after changes when practical
