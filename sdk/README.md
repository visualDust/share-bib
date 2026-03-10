# ShareBib Python SDK and CLI

Python SDK and command-line interface for interacting with the ShareBib API.

## Installation

### Install from PyPI

```bash
pip install sharebib
```

This installs:

- the Python package: `sharebib`
- the preferred CLI command: `sharebib`
- the compatibility CLI alias: `sharebib-cli`

### Install the latest unreleased version from GitHub

```bash
pip install "git+https://github.com/visualdust/share-bib.git#subdirectory=sdk"
```

### Local development

```bash
cd sdk
pip install -e .
```

## Authentication

1. Log in to your ShareBib instance
2. Go to **Settings**
3. In **SDK API Keys**, click **Create API Key**
4. Copy the generated key (starts with `pc_`)

![API Key Management](https://raw.githubusercontent.com/visualdust/share-bib/main/sdk/api-key-screenshot.png)

## Configuration

Supported configuration sources, highest priority first:

1. CLI flags / SDK constructor arguments
2. Environment variables
3. Project config: `.sharebib/config.json`
4. User config: `~/.sharebib/config.json`

### Environment variables

```bash
export SHAREBIB_API_KEY="pc_your_api_key_here"
export SHAREBIB_BASE_URL="http://localhost:11550"
export SHAREBIB_TIMEOUT="30"
```

> `SHAREBIB_BASE_URL` should be the application root URL. Do **not** append `/api`.

### Config file example

```json
{
  "api_key": "pc_your_api_key_here",
  "base_url": "http://localhost:11550",
  "timeout": 30
}
```

## CLI Quick Start

### Verify auth

```bash
sharebib auth info
```

> `sharebib` is the preferred CLI name. `sharebib-cli` remains available as a compatibility alias.
> You can also run the CLI as `python -m sharebib`.

### List collections

```bash
sharebib collections list
```

### Search users for sharing

```bash
sharebib users search --q "gavin"
```

### Create a collection

```bash
sharebib collections create \
  --title "My Research Papers" \
  --description "Papers I'm reading" \
  --visibility private \
  --tag machine-learning \
  --tag nlp
```

### Add a paper

```bash
sharebib papers add \
  --collection-id "your-collection-id" \
  --title "Attention Is All You Need" \
  --author "Ashish Vaswani" \
  --author "Noam Shazeer" \
  --venue "NeurIPS" \
  --year 2017 \
  --arxiv-id "1706.03762" \
  --url-arxiv "https://arxiv.org/abs/1706.03762" \
  --url-pdf "https://arxiv.org/pdf/1706.03762.pdf" \
  --tag transformers \
  --tag attention
```

### List papers in a collection

```bash
sharebib papers list --collection-id "your-collection-id"
```

### Inspect a paper

```bash
sharebib papers info --id "paper-id"
```

### Remove a paper from a collection

```bash
sharebib papers remove --collection-id "your-collection-id" --id "paper-id"
```

### Search accessible papers

```bash
sharebib papers search --q "transformer" --limit 10
```

### Manage collection permissions

```bash
sharebib collections permissions list --id "your-collection-id"
sharebib collections permissions add --id "your-collection-id" --user-id "user-id" --permission edit
sharebib collections permissions remove --id "your-collection-id" --user-id "user-id"
```

### Export BibTeX

```bash
sharebib collections export-bibtex --id "your-collection-id" --output ./papers.bib
```

## SDK Quick Start

```python
from sharebib import ShareBibClient

client = ShareBibClient(
    base_url="http://localhost:11550",
    api_key="pc_your_api_key_here",
)

me = client.get_current_user()
print(me.username)

collection = client.create_collection(
    title="My Research Papers",
    description="Papers I'm reading",
    visibility="private",
    tags=["machine-learning", "nlp"],
)
print(f"Created collection: {collection.title} ({collection.id})")

paper = client.add_paper(
    collection_id=collection.id,
    title="Attention Is All You Need",
    authors=["Vaswani et al."],
    venue="NeurIPS",
    year=2017,
    arxiv_id="1706.03762",
    url_arxiv="https://arxiv.org/abs/1706.03762",
    url_pdf="https://arxiv.org/pdf/1706.03762.pdf",
    tags=["transformers", "attention"],
)
print(f"Added paper: {paper.title}")

for item in client.list_papers(collection.id):
    print(item.title)

for user in client.search_users("gavin"):
    print(user.username)

results = client.search_papers("transformer", limit=5)
print(len(results))

bibtex = client.export_collection_bibtex(collection.id)
print(bibtex[:120])
```

## API Surface

### Auth

- `get_current_user()` / `auth_info()`

### Users

- `search_users(q, limit=10)`

### Collections

- `list_collections()`
- `create_collection(...)`
- `get_collection(collection_id)`
- `list_collection_permissions(collection_id)`
- `set_collection_permission(collection_id, user_id=..., permission=...)`
- `remove_collection_permission(collection_id, user_id)`
- `export_collection_bibtex(collection_id)`
- `delete_collection(collection_id)`

### Papers

- `add_paper(collection_id, title, ...)`
- `list_papers(collection_id)`
- `search_papers(q, limit=50, year=None, status=None)`
- `get_paper(paper_id)`
- `remove_paper(collection_id, paper_id)`

## Error Handling

```python
from sharebib import ShareBibAPIError, ShareBibClient

client = ShareBibClient("http://localhost:11550", "pc_your_api_key_here")

try:
    client.get_collection("nonexistent-id")
except ShareBibAPIError as exc:
    print(exc)
    print(exc.status_code)
```

## License

MIT
