# Docker Deployment

This directory contains configuration files for deploying ShareBib with Docker.

## Quick Start

1. Copy the example configuration:

```bash
cp .env.example .env
```

2. (Optional) Edit `.env` to set a custom JWT secret:

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

4. Open your browser and follow the setup wizard to create your admin account.

## Files

- `docker-compose.yml` - Docker Compose configuration
- `.env.example` - Example environment variables
- `config.yaml.example` - Example YAML configuration (optional alternative to .env)
- `Caddyfile` - Caddy reverse proxy configuration (used in Docker image)
- `supervisord.conf` - Supervisor configuration (used in Docker image)

## Configuration

### Method 1: Environment Variables (Recommended)

Use `.env` file or set environment variables in `docker-compose.yml`.

See `.env.example` for all available options.

### Method 2: YAML Configuration (Optional)

You can also use `data/config.yaml` for configuration:

```bash
cp config.yaml.example data/config.yaml
# Edit data/config.yaml
```

**Note:** Environment variables take precedence over YAML configuration.

## Data Persistence

All data is stored in the `./data` directory:

- `data/paper_collector.db` - SQLite database
- `data/config.yaml` - Configuration file (auto-generated if using env vars)

**Important:** Back up the `./data` directory to preserve your data.

## OAuth Setup

To use OAuth authentication, add these variables to `.env`:

```bash
AUTH_TYPE=oauth
OAUTH_CLIENT_ID=your-client-id
OAUTH_CLIENT_SECRET=your-client-secret
OAUTH_AUTHORIZE_URL=https://auth.example.com/authorize
OAUTH_TOKEN_URL=https://auth.example.com/token
OAUTH_USERINFO_URL=https://auth.example.com/userinfo
OAUTH_REDIRECT_URI=https://papers.example.com/api/auth/oauth/callback
OAUTH_SCOPES=openid,profile,email  # Optional, comma-separated
OAUTH_ADMIN_GROUP=admins  # Optional, group name for admin access
```

Then restart:

```bash
docker compose restart
```

## Reverse Proxy

The Docker image includes Caddy as a reverse proxy:

- Frontend (static files) served on port 80
- Backend API proxied from internal port 8000

If you're using an external reverse proxy (nginx, Traefik, etc.), you can:

- Map port 80 to a different host port
- Configure SSL/TLS termination at your reverse proxy
- Set the OAuth redirect URI to match your domain
