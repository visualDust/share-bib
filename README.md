# ShareBib

A simple, self-hosted tool for managing and sharing BibTeX collections with labmates.

## Typical workflow

You curate papers in Zotero → right-click a collection → Export Collection → `.bib` → upload it here.

Your labmate opens the link you shared → exports the `.bib` → imports it into their own Zotero. Done.

<table>
  <tr>
    <td><img src="docs/images/index.png" alt="Collection index" width="400"></td>
    <td><img src="docs/images/collection.png" alt="Collection detail" width="400"></td>
  </tr>
  <tr>
    <td><img src="docs/images/crawl.png" alt="Crawl tasks" width="400"></td>
    <td><img src="docs/images/import.png" alt="Import .bib" width="400"></td>
  </tr>
  <tr>
    <td><img src="docs/images/duplicate.png" alt="Duplicate management" width="400"></td>
    <td><img src="docs/images/access.png" alt="Manage access" width="400"></td>
  </tr>
</table>

## Features

- Self-hosted, local login or OAuth
- Import and export `.bib` files (works with Zotero, etc.)
- Scheduled crawl tasks: auto-fetch new papers from arXiv RSS with keyword filtering (`+required`, `-excluded`, `*wildcard`)
- Duplication detection and merging
- Organize papers into collections with per-user access control
- **SDK and CLI for programmatic access and Agent skills** - automate paper management with your own scripts or shell workflows, as well as use with AI agents.
- i18n support (English, 中文)
- Desktop and mobile page layout

**Tested authentication methods:**

- Simple auth (username/password)
- OAuth with [Authentik](https://goauthentik.io/)

## Installation

### Claude Code

```bash
/plugin marketplace add visualdust/share-bib
/plugin install sharebib
```

### Other AI Agents

Using [vercel-labs/skills](https://skills.sh/):

```bash
npx skills add visualdust/share-bib -a codex    # Codex
npx skills add visualdust/share-bib -a cursor   # Cursor
npx skills add visualdust/share-bib -a windsurf # Windsurf
```

### Prerequisites

Install the ShareBib CLI tool required by the skill:

```bash
pip install sharebib
```

## AI Agent Quick Start

### 1. Get Your API Key

1. Log in to your ShareBib instance.
2. Go to **Settings**.
3. In **SDK API Keys**, click **Create API Key**.
4. Copy the generated key (starts with `pc_`).

### 2. Configure Authentication

Set environment variables:

```bash
export SHAREBIB_API_KEY="pc_xxxxxxxxxxxxxxxxxxxxxxxxx"
export SHAREBIB_BASE_URL="https://papers.example.com"
export SHAREBIB_TIMEOUT="30"
```

Or create `.sharebib/config.json`:

```json
{
  "api_key": "pc_xxxxxxxxxxxxxxxxxxxxxxxxx",
  "base_url": "https://papers.example.com",
  "timeout": 30
}
```

### 3. Use with Your AI Agent

Once installed, your AI agent can help with ShareBib workflows such as:

```text
List my accessible collections in ShareBib
Create a private reading-list collection for systems papers
Find Gavin's ShareBib user account so I can share a collection
Export the BibTeX for collection 1234 to a file
Search papers for "transformer" and summarize the top results
```

## Documentation

- [skills/sharebib/SKILL.md](skills/sharebib/SKILL.md) - agent-facing skill instructions and command reference
- [sdk/README.md](sdk/README.md) - Python SDK and CLI usage
- [AGENTS.md](AGENTS.md) - repository-level agent instructions

## Deploy with Docker

### Quick start

```yaml
# docker-compose.yml
services:
  sharebib:
    image: ghcr.io/visualdust/share-bib:latest
    ports:
      - "80:80"
    volumes:
      - ./data:/data
    restart: unless-stopped
```

```bash
docker compose up -d
```

Open `http://localhost` (or your domain) and follow the setup wizard to create your admin account.

### Production deployment

For production, it's recommended to set a custom JWT secret:

1. Copy the example files:

```bash
cp docker-compose.example.yml docker-compose.yml
cp .env.example .env
```

2. Generate and set a JWT secret in `.env`:

```bash
# Generate a secure secret
openssl rand -hex 32

# Add to .env
JWT_SECRET_KEY=your-generated-secret-here
```

3. Start the service:

```bash
docker compose up -d
```

### OAuth authentication

To use OAuth (e.g., with Authentik, Keycloak, GitHub), add these environment variables:

```yaml
# docker-compose.yml
services:
  sharebib:
    image: ghcr.io/visualdust/share-bib:latest
    ports:
      - "80:80"
    volumes:
      - ./data:/data
    environment:
      - AUTH_TYPE=oauth
      - OAUTH_CLIENT_ID=your-client-id
      - OAUTH_CLIENT_SECRET=your-client-secret
      - OAUTH_AUTHORIZE_URL=https://auth.example.com/authorize
      - OAUTH_TOKEN_URL=https://auth.example.com/token
      - OAUTH_USERINFO_URL=https://auth.example.com/userinfo
      - OAUTH_REDIRECT_URI=https://papers.example.com/api/auth/oauth/callback
      - OAUTH_SCOPES=openid,profile,email # Optional, comma-separated
      - OAUTH_ADMIN_GROUP=admins # Optional, group name for admin access
    restart: unless-stopped
```

### Environment variables

| Variable              | Default                | Description                                                    |
| --------------------- | ---------------------- | -------------------------------------------------------------- |
| `JWT_SECRET_KEY`      | auto-generated         | JWT signing key (persisted to `data/config.yaml` on first run) |
| `AUTH_TYPE`           | `simple`               | Auth mode: `simple` or `oauth`                                 |
| `OAUTH_CLIENT_ID`     | -                      | OAuth client ID (required if `AUTH_TYPE=oauth`)                |
| `OAUTH_CLIENT_SECRET` | -                      | OAuth client secret (required if `AUTH_TYPE=oauth`)            |
| `OAUTH_AUTHORIZE_URL` | -                      | OAuth authorization endpoint                                   |
| `OAUTH_TOKEN_URL`     | -                      | OAuth token endpoint                                           |
| `OAUTH_USERINFO_URL`  | -                      | OAuth user info endpoint                                       |
| `OAUTH_REDIRECT_URI`  | -                      | OAuth callback URL                                             |
| `OAUTH_SCOPES`        | `openid,profile,email` | OAuth scopes (comma-separated)                                 |
| `OAUTH_ADMIN_GROUP`   | `admins`               | OAuth group name for admin users                               |

### Configuration methods

ShareBib supports two configuration methods:

1. **Environment variables** (recommended for Docker) - Set via `docker-compose.yml` or `.env`
2. **YAML configuration** - Create `data/config.yaml` (see `docker/config.yaml.example`)

Environment variables take precedence over YAML configuration.

### Data

All persistent data (database, config) is stored in the `./data` volume. Back up this directory to migrate.

## Local development

### Setup

1. Copy the example configuration:

```bash
cp backend/.env.example backend/.env
```

2. (Optional) Edit `backend/.env` to customize ports or add allowed hosts:

```bash
# backend/.env
BACKEND_PORT=11550
FRONTEND_PORT=11551
ALLOWED_HOSTS=  # Leave empty for localhost, or add your domain
```

3. Start the services:

```bash
# Start backend + frontend in tmux
./scripts/start.sh

# Stop
./scripts/stop.sh
```

Requires: Python 3.13+, Node.js 20+, [uv](https://docs.astral.sh/uv/), tmux

## Python SDK and CLI

Automate paper management with the Python SDK and CLI. Perfect for custom crawlers, batch imports, and agent-facing shell workflows.

### Installation

```bash
pip install sharebib
```

For local development:

```bash
cd sdk
pip install -e .
```

For the latest unreleased version from GitHub:

```bash
pip install "git+https://github.com/visualdust/share-bib.git#subdirectory=sdk"
```

This installs both:

- the Python package: `sharebib`
- the CLI commands: `sharebib` and `sharebib-cli`

### Quick Start

```python
from sharebib import ShareBibClient

# Initialize with your API key (get it from Settings page)
client = ShareBibClient(
    base_url="http://localhost:11550",
    api_key="pc_your_api_key_here"
)

# Create a collection
collection = client.create_collection(
    title="My Papers",
    visibility="private",
    tags=["research"]
)

# Add a paper
paper = client.add_paper(
    collection_id=collection.id,
    title="Attention Is All You Need",
    authors=["Vaswani et al."],
    year=2017,
    url_arxiv="https://arxiv.org/abs/1706.03762",
    url_pdf="https://arxiv.org/pdf/1706.03762.pdf"
)

# List papers
papers = client.list_papers(collection.id)
for p in papers:
    print(f"{p.title} ({p.year})")
```

CLI example:

```bash
sharebib auth info
sharebib users search --q "gavin"
sharebib collections list
sharebib collections permissions list --id "collection-id"
sharebib collections export-bibtex --id "collection-id" --output ./papers.bib
sharebib papers search --q "transformer"
```

`sharebib` is the preferred command name; `sharebib-cli` remains available as a compatibility alias.

See [`sdk/README.md`](sdk/README.md) for full SDK/CLI documentation and [`sdk/example.py`](sdk/example.py) for comprehensive examples.

## Build from source

```bash
docker build -t share-bib .
docker run -d -p 80:80 -v ./data:/data share-bib
```
