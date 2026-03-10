---
name: sharebib
description: Operate ShareBib collections and papers - create collections, search users/papers, manage sharing, export BibTeX, and verify SDK API key access.
allowed-tools: Bash(sharebib *, sharebib-cli *)
---

# ShareBib Skill

## Purpose

Use this skill when the user asks to operate a ShareBib instance via API/CLI.

## When to Trigger

Trigger this skill when requests involve:

- ShareBib collections
- research paper metadata management
- adding, listing, inspecting, or removing papers
- searching users for sharing targets
- managing collection permissions
- exporting BibTeX from a collection
- SDK API key verification
- BibTeX / paper-management automation workflows

## Metadata Guidance

When creating or editing paper metadata:

- preserve source metadata when available
- prefer explicit identifiers like `arxiv_id` and `doi`
- do not invent missing authors / year / venue unless the user asked for inference
- use tags for lightweight categorization, not long prose
- before deleting or removing items, confirm scope if the target is ambiguous

## Agent Execution Checklist

Before running commands:

1. Confirm whether the task is read-only, write, or destructive.
2. Confirm required IDs (`collection-id`, `paper-id`) when the target is ambiguous.
3. Verify auth with `sharebib auth info` if configuration may be uncertain.
4. For destructive actions (`delete`, `remove`), confirm scope with the user if unclear.

After running commands:

1. Report the key result in plain language.
2. Include returned IDs when useful.
3. If a command fails, provide the likely cause and exact retry command.
4. Do not export or broaden sharing unless the user asked for it.

## Prerequisites

- Install from PyPI:
  ```bash
  pip install sharebib
  ```
- Or install the latest unreleased version from GitHub:
  ```bash
  pip install "git+https://github.com/visualdust/share-bib.git#subdirectory=sdk"
  ```
- API key format: `pc_...`
- Preferred CLI command: `sharebib`
- Compatibility alias: `sharebib-cli`

## Configuration

### Supported Sources (highest priority first)

1. CLI flags: `--api-key`, `--base-url`, `--timeout`, `--config`
2. Environment variables
3. Project config: `.sharebib/config.json`
4. User config: `~/.sharebib/config.json`

### Important Notes

**Parameter Order**: Global parameters should be placed before the subcommand:

```bash
# ✓ Correct
sharebib --api-key "..." --base-url "https://papers.example.com" collections list
sharebib-cli --api-key "..." --base-url "https://papers.example.com" collections list

# ✗ Wrong
sharebib collections list --api-key "..." --base-url "https://papers.example.com"
```

**Base URL Format**: Use the application root URL. Do **not** append `/api`:

```bash
# ✓ Correct
https://papers.example.com
http://localhost:11550

# ✗ Wrong
https://papers.example.com/api
http://localhost:11550/api
```

### Environment Variables

```bash
export SHAREBIB_API_KEY="pc_xxxxxxxxxxxxxxxxxxxxxxxxx"
export SHAREBIB_BASE_URL="https://papers.example.com"
export SHAREBIB_TIMEOUT="30"
```

### Config File Example

```json
{
  "api_key": "pc_xxxxxxxxxxxxxxxxxxxxxxxxx",
  "base_url": "https://papers.example.com",
  "timeout": 30
}
```

## Quick Command Reference

### Authentication

```bash
sharebib auth info
```

`sharebib-cli auth info` remains available as a compatibility alias.

Use this to:

- verify the API key works
- see which user the key belongs to
- confirm the instance URL is correct

### Collections

```bash
sharebib collections list
sharebib collections info --id "collection-id"
sharebib collections create --title "My Papers"
sharebib collections create --title "My Papers" --description "Reading list" --visibility private --tag ml --tag systems
sharebib collections export-bibtex --id "collection-id" --output ./papers.bib
sharebib collections permissions list --id "collection-id"
sharebib collections permissions add --id "collection-id" --user-id "user-id" --permission edit
sharebib collections permissions remove --id "collection-id" --user-id "user-id"
sharebib collections delete --id "collection-id"
```

### Users

```bash
sharebib users search --q "gavin"
```

### Papers

```bash
sharebib papers add --collection-id "collection-id" --title "Paper Title"
sharebib papers add --collection-id "collection-id" --title "Paper Title" --author "Author A" --author "Author B" --year 2024 --arxiv-id "2401.12345" --url-pdf "https://..."
sharebib papers list --collection-id "collection-id"
sharebib papers search --q "transformer" --limit 10
sharebib papers info --id "paper-id"
sharebib papers remove --collection-id "collection-id" --id "paper-id"
```

## Troubleshooting

### 401 Unauthorized

- Check that the API key starts with `pc_`
- Verify the key is still active in ShareBib settings
- Confirm you are pointing at the correct ShareBib instance

### 403 Forbidden

- The API key's user may not have access to the target collection
- The collection may be private and not shared with that user
- Write operations require edit permission

### 404 Not Found

- The collection or paper ID may be wrong
- If multiple commands fail, the base URL may be incorrect
- Confirm the base URL does not include `/api`

### Connection errors

- Verify `SHAREBIB_BASE_URL`
- Make sure the ShareBib instance is reachable
- Check for reverse proxy / TLS issues

### Command not found

```bash
pip install --upgrade sharebib
```

If you need the latest unreleased version instead:

```bash
pip install --upgrade "git+https://github.com/visualdust/share-bib.git#subdirectory=sdk"
```

## Safety Notes

- Never hardcode API keys in source files
- Prefer env vars or config files with restricted permissions
- For local config files on Unix:
  ```bash
  chmod 600 ~/.sharebib/config.json
  ```
- Confirm destructive actions before execution when user intent is unclear
