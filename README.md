# 🔌 API Registry MCP Server

A Databricks app that helps you discover, register, and manage external API endpoints with an AI-powered chat interface and MCP server.

## What is this?

This is a complete API discovery and management platform that runs on Databricks Apps. It combines:

- **🤖 AI Chat Interface**: Natural language API registration powered by Claude
- **📊 API Registry**: Database-backed catalog of external API endpoints
- **🔍 Smart Discovery**: Automatic endpoint testing and validation
- **📚 Documentation Parser**: Extract endpoints from API documentation URLs
- **🛠️ MCP Server**: Expose API management tools to Claude CLI

## Quick Start

### Prerequisites

**Workspace Requirements:**
- Databricks Apps enabled (Public Preview)
- Foundation Model API with `databricks-claude-sonnet-4` endpoint
- At least one SQL Warehouse
- Unity Catalog with an accessible catalog.schema

See [WORKSPACE_REQUIREMENTS.md](WORKSPACE_REQUIREMENTS.md) for detailed workspace setup requirements and troubleshooting.

**Local Development:**
- Python 3.12+ with `uv` package manager
- Databricks CLI (`databricks`) v0.260.0+
- (Optional) Claude CLI for MCP integration

### 1. Clone and Setup

**Note:** All deployment commands run on your LOCAL machine, not in Databricks.

```bash
# On your local machine (not in Databricks):
git clone https://github.com/lucamilletti99/mcp_server_api_registry.git
cd mcp_server_api_registry

# Run interactive setup
./setup.sh
```

This will:
- Install `uv` if not present (on your local machine)
- Configure Databricks CLI authentication
- Install all Python dependencies locally
- Create `.env.local` configuration file

### 2. Create the API Registry Table

The app needs a table to store registered APIs. Run this SQL in your Databricks workspace:

```sql
CREATE TABLE IF NOT EXISTS your_catalog.your_schema.api_registry (
  api_id STRING NOT NULL,
  api_name STRING NOT NULL,
  description STRING,
  api_endpoint STRING NOT NULL,
  documentation_url STRING,
  http_method STRING DEFAULT 'GET',
  auth_type STRING DEFAULT 'none',
  token_info STRING,
  request_params STRING DEFAULT '{}',
  status STRING DEFAULT 'pending',
  validation_message STRING,
  user_who_requested STRING,
  created_at TIMESTAMP,
  modified_date TIMESTAMP,
  PRIMARY KEY (api_id)
);
```

Or use the provided script:
```bash
uv run python setup_table.py your_catalog your_schema
```

### 3. Deploy to Databricks

Deploy from your local machine to Databricks Apps:

```bash
# Run from your local machine (requires Databricks CLI authentication)
./deploy.sh
```

This script will:
- Build the frontend
- Package the Python backend
- Upload everything to your Databricks workspace
- Deploy as a Databricks App

Your app will be available at: `https://your-app.databricksapps.com`

### 4. (Optional) Add MCP Server to Claude CLI

```bash
# Get your app URL
export DATABRICKS_APP_URL=$(./app_status.sh | grep "App URL" | awk '{print $NF}')
export DATABRICKS_HOST="https://your-workspace.cloud.databricks.com"

# Add to Claude
claude mcp add api-registry --scope user -- \
  uvx --refresh --from git+ssh://git@github.com/lucamilletti99/mcp_server_api_registry.git dba-mcp-proxy \
  --databricks-host $DATABRICKS_HOST \
  --databricks-app-url $DATABRICKS_APP_URL
```

## Features

### Web UI

Access the web interface at your app URL:

1. **Chat Playground**: AI-powered API registration
   - Natural language: "Register the Alpha Vantage stock API"
   - Automatic endpoint discovery and testing
   - Documentation URL parsing
   - Smart pattern matching

2. **API Registry**: View and manage registered APIs
   - Edit API details and documentation URLs
   - Test API health
   - Delete APIs
   - Filter and search

3. **MCP Info**: View available MCP tools and prompts
   - See all exposed tools
   - Copy setup instructions
   - View architecture diagram

4. **Traces**: Debug AI agent execution
   - View tool calls and responses
   - Inspect trace details
   - Monitor performance

### MCP Tools

When added to Claude CLI, the following tools are available:

- `smart_register_api`: One-step API registration with automatic discovery
- `register_api_in_registry`: Manual API registration
- `check_api_registry`: List all registered APIs
- `review_api_documentation_for_endpoints`: Discover new endpoints from documentation
- `call_api_endpoint`: Test API endpoints with custom headers
- `execute_dbsql`: Run SQL queries against Databricks
- `discover_api_endpoint`: Validate and test API endpoints
- `fetch_api_documentation`: Parse API documentation from URLs
- `list_warehouses`: List available SQL warehouses

## Configuration

### Environment Variables (`.env.local`)

```bash
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=your-personal-access-token  # For local development
DATABRICKS_SQL_WAREHOUSE_ID=your-warehouse-id  # Optional default warehouse
```

### App Configuration (`config.yaml`)

```yaml
name: mcp-server-api-registry
display_name: API Registry MCP Server
description: AI-powered API discovery and management platform
```

## Development

### Local Development

```bash
# Start dev server (frontend + backend with hot reload)
./watch.sh

# Access at:
# - Frontend: http://localhost:5173
# - Backend: http://localhost:8000
# - API Docs: http://localhost:8000/docs
```

### Code Formatting

```bash
./fix.sh  # Format Python (ruff) and TypeScript (prettier)
```

### Debugging

```bash
# Check app status
./app_status.sh

# Stream app logs
uv run python dba_logz.py https://your-app.databricksapps.com --duration 60

# Test API endpoints
uv run python dba_client.py https://your-app.databricksapps.com /api/user/me
```

## Project Structure

```
├── server/                     # FastAPI backend
│   ├── app.py                 # Main application + MCP server
│   ├── tools.py               # MCP tools implementation
│   └── routers/               # API endpoints
│       ├── agent_chat.py      # AI chat endpoint
│       ├── registry.py        # API registry CRUD
│       └── db_resources.py    # Databricks resources
├── client/                    # React TypeScript frontend
│   └── src/
│       ├── pages/             # Page components
│       └── components/        # Reusable UI components
├── prompts/                   # MCP prompts (markdown)
├── dba_mcp_proxy/            # MCP proxy for Claude CLI
├── setup_table.py            # Database table setup script
├── setup_api_registry_table.sql  # Table schema
├── deploy.sh                 # Deploy to Databricks Apps
├── watch.sh                  # Local development server
└── pyproject.toml           # Python dependencies
```

## Authentication

The app uses **On-Behalf-Of (OBO) authentication**:
- User's OAuth token is forwarded from Databricks Apps
- Falls back to service principal if user has no SQL warehouse access
- All operations run with proper user context

## Usage Examples

### Registering an API via Chat

```
User: Register the Alpha Vantage stock API, here's the docs: https://www.alphavantage.co/documentation/

AI: I'll register the Alpha Vantage API for you.
[Fetches documentation, discovers endpoints, tests them, registers the best one]

✅ Successfully registered "alphavantage_stock" with validation: HTTP 200 OK
```

### Discovering New Endpoints

```
User: Can you check the SEC API documentation and find more endpoints?

AI: Let me review the SEC API documentation for new endpoints.
[Fetches stored documentation URL, parses it, tests discovered endpoints]

Found 5 working endpoints:
1. /search/filings
2. /company/{CIK}
3. /facts/{CIK}
...
```

### Querying the Registry

```
User: Show me all registered APIs

AI: Here are your registered APIs:
- alphavantage_stock: Alpha Vantage stock market data
- fred_series_api: Federal Reserve Economic Data
- sec_api: SEC filings and company data
...
```

## Troubleshooting

**For detailed workspace requirements and setup issues, see [WORKSPACE_REQUIREMENTS.md](WORKSPACE_REQUIREMENTS.md)**

**Table not found error:**
- Create the `api_registry` table in your selected catalog.schema
- Or use a different catalog.schema that has the table

**Authentication failures:**
- Ensure Databricks CLI is authenticated: `databricks current-user me`
- Check `.env.local` has correct `DATABRICKS_HOST`

**MCP server not responding:**
- Verify app is deployed: `./app_status.sh`
- Check Claude logs: `tail -f ~/Library/Logs/Claude/*.log`
- Test proxy: `uvx --from git+ssh://... dba-mcp-proxy --help`

**Smart registration failing:**
- Check app logs: `uv run python dba_logz.py YOUR_APP_URL --search "ERROR"`
- Verify warehouse has access to required catalogs
- Try manual registration with `register_api_in_registry`

**Databricks Apps not enabled:**
- See [WORKSPACE_REQUIREMENTS.md](WORKSPACE_REQUIREMENTS.md) for enabling preview features

**Foundation Model endpoint errors:**
- Verify `databricks-claude-sonnet-4` is available in your region
- Check [WORKSPACE_REQUIREMENTS.md](WORKSPACE_REQUIREMENTS.md) for regional availability

## License

See [LICENSE.md](LICENSE.md)

## Security

See [SECURITY.md](SECURITY.md) for reporting security vulnerabilities.
