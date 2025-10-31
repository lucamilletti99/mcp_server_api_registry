# 🔌 API Registry MCP Server

A Databricks app that helps you discover, register, and manage external API endpoints with an AI-powered chat interface and MCP server.

## What is this?

This is a complete API discovery and management platform that runs on Databricks Apps. It combines:

- **🤖 AI Chat Interface**: Natural language API registration powered by Claude
- **📊 API Registry**: Database-backed catalog of external API endpoints
- **🔍 Smart Discovery**: Automatic endpoint testing and validation
- **📚 Documentation Parser**: Extract endpoints from API documentation URLs
- **🛠️ MCP Server**: Programmatic API management tools

## Quick Start

### Prerequisites

**Workspace Requirements:**
- Databricks Apps enabled (Public Preview)
- Foundation Model API with `databricks-claude-sonnet-4` endpoint
- **At least one SQL Warehouse** (required for table operations and MCP tools)
  - [How to create a SQL Warehouse](https://docs.databricks.com/en/compute/sql-warehouse/create.html)
  - Serverless SQL Warehouses recommended for best performance
- Unity Catalog with an accessible catalog.schema

See [WORKSPACE_REQUIREMENTS.md](WORKSPACE_REQUIREMENTS.md) for detailed workspace setup requirements and troubleshooting.

**Local Development:**
- Python 3.12+ with `uv` package manager
- Databricks CLI (`databricks`) v0.260.0+

**Authentication Setup:**
- **Recommended:** Personal Access Token (PAT) authentication
- [How to create a Personal Access Token](https://docs.databricks.com/en/dev-tools/auth/pat.html)
- You'll need your PAT during the setup process

### 1. Clone and Setup

**Note:** All deployment commands run on your LOCAL machine, not in Databricks.

```bash
# On your local machine (not in Databricks):
git clone https://github.com/lucamilletti99/mcp_server_api_registry.git
cd mcp_server_api_registry

# Run interactive setup
# When prompted, press Enter to use default values shown in brackets
./setup.sh
```

**Setup Tips:**
- Use **Personal Access Token (PAT)** authentication when prompted
- Press Enter to accept default values (shown in brackets)
- Default source code path: `/Workspace/Users/your-email@company.com/app-name`
- MCP server name will default to your app name

This will:
- Install `uv` if not present (on your local machine)
- Configure Databricks CLI authentication
- **Configure your app name** (must start with `mcp-`)
- Install all Python dependencies locally
- Create `.env.local` configuration file

**Important:** The app name you choose during setup will be saved in `.env.local` and used automatically by `./deploy.sh`. You can override it at deployment time with the `--app-name` flag if needed.

### 2. Create the API Registry Table

**IMPORTANT: Make sure you completed step 1 (./setup.sh) before proceeding!**

**Prerequisites for this step:**
- ✅ You must have at least one SQL Warehouse created in your workspace
- ✅ The warehouse must be running or available to start
- 📖 [How to create a SQL Warehouse](https://docs.databricks.com/en/compute/sql-warehouse/create.html)

The app needs a table to store registered APIs. You can create it using either method:

**Option 1: Using the Python Script (Recommended)**

```bash
# The script automatically loads your .env.local configuration
uv run python setup_table.py your_catalog your_schema

# Optional: specify a warehouse ID
uv run python setup_table.py your_catalog your_schema --warehouse-id abc123
```

**Option 2: Manually via Databricks SQL Editor**

You can also run the SQL directly in Databricks:

1. Open the [Databricks SQL Editor](https://docs.databricks.com/en/sql/user/queries/index.html) in your workspace
2. Copy the contents of `setup_api_registry_table.sql`
3. Replace `{catalog}` with your catalog name (e.g., `lucam_ws_demo`)
4. Replace `{schema}` with your schema name (e.g., `custom_mcp_server`)
5. Run the query

```sql
-- Example SQL (replace placeholders):
CREATE TABLE IF NOT EXISTS your_catalog.your_schema.api_registry (
  api_id STRING NOT NULL,
  api_name STRING NOT NULL,
  description STRING,
  api_endpoint STRING NOT NULL,
  documentation_url STRING,
  http_method STRING,
  auth_type STRING,
  token_info STRING,
  request_params STRING,
  status STRING,
  validation_message STRING,
  user_who_requested STRING,
  created_at TIMESTAMP,
  modified_date TIMESTAMP,
  CONSTRAINT api_registry_pk PRIMARY KEY (api_id)
)
COMMENT 'Registry of external API endpoints for discovery and management'
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true'
);
```

**What the Python script does:**
- ✅ Automatically loads `DATABRICKS_HOST` from `.env.local`
- ✅ Auto-detects and uses an available SQL warehouse
- ✅ Creates the `api_registry` table with proper schema
- ✅ Verifies the table was created successfully

**Troubleshooting:**
- **"DATABRICKS_HOST not set"** → Run `./setup.sh` first
- **"No SQL warehouses found"** → Create one using [this guide](https://docs.databricks.com/en/compute/sql-warehouse/create.html)
- **"Permission denied"** → Ensure you have `CAN_USE` permission on the warehouse
- You can also manually run the SQL from `setup_api_registry_table.sql` in Databricks SQL Editor

### 3. Deploy to Databricks

Deploy from your local machine to Databricks Apps.

**First Deployment (App doesn't exist yet)**

Create and deploy the app in one step:

```bash
# First time deployment - creates the app and deploys
./deploy.sh --create

# OR with a custom app name
./deploy.sh --app-name mcp-my-api-registry --create
```

The `--create` flag:
- Creates the Databricks App if it doesn't exist
- Then deploys your code to it
- **Use this for your very first deployment**

**Subsequent Deployments (App already exists)**

After the app is created, just deploy updates:

```bash
# Update existing app with latest code
./deploy.sh

# OR update with verbose output for debugging
./deploy.sh --verbose
```

**Common Deployment Scenarios:**

```bash
# First time: Create app with default name from .env.local
./deploy.sh --create

# First time: Create app with custom name
./deploy.sh --app-name mcp-prod-registry --create

# Update existing app after code changes
./deploy.sh

# Deploy to different app name (must exist already)
./deploy.sh --app-name mcp-dev-registry

# Debug deployment issues
./deploy.sh --verbose
```

**App Naming Rules:**
- App names **must start with `mcp-`**
- Use lowercase letters, numbers, and hyphens only
- Examples: `mcp-api-registry`, `mcp-prod-registry`, `mcp-dev-1`

**What the deployment script does:**
1. Shows configuration summary
2. Validates the app name (must start with `mcp-`)
3. Builds the frontend
4. Packages the Python backend
5. Uploads everything to your Databricks workspace
6. Deploys as a Databricks App

Your app will be available at: `https://your-app.databricksapps.com`

**Troubleshooting:**
- **"App not found"** → Use `--create` flag to create it first
- **Build errors** → Use `--verbose` to see detailed output
- **Authentication failed** → Run `./setup.sh` to reconfigure

### 4. Access Your App

Once deployed, your app will be available at the URL shown in the deployment output:

```
✅ Deployment complete!

Your app is available at:
https://your-app.databricksapps.com
```

Open this URL in your browser to access the web interface and start registering APIs!

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

### Backend Capabilities

The app provides programmatic tools via its MCP server interface:

- **Smart API Registration**: One-step API registration with automatic discovery
- **Manual Registration**: Detailed API configuration and registration
- **Registry Management**: List and manage all registered APIs
- **Documentation Discovery**: Extract endpoints from API documentation URLs
- **Endpoint Testing**: Validate and test API endpoints with custom headers
- **SQL Integration**: Run SQL queries against Databricks warehouses
- **Warehouse Management**: List and configure SQL warehouses

## Configuration

### Environment Variables (`.env.local`)

```bash
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=your-personal-access-token  # For local development
DATABRICKS_SQL_WAREHOUSE_ID=your-warehouse-id  # Optional default warehouse
```

### App Configuration (`app.yaml`)

The app is pre-configured with On-Behalf-Of (OBO) authentication:

```yaml
# On-Behalf-Of user authorization is enabled by default
# The app acts with the identity of the authenticated user
scopes:
  - "all-apis"     # Foundation Model API access
  - "sql"          # SQL warehouse and query execution
  - "files.files"  # DBFS file operations
```

**What this means:**
- ✅ **OBO is enabled by default** - no additional setup needed
- ✅ Users authenticate with their Databricks credentials when accessing the app
- ✅ All operations run with the user's permissions (not a service principal)
- ✅ Proper access control and audit logging

**Verifying OBO in the UI:**

After deploying, you can verify OBO is working:

1. Open your deployed app URL in a browser
2. You'll be prompted to authenticate with Databricks (OAuth)
3. Once logged in, the app will show your user identity
4. All API operations will run with your permissions

**Alternative: Service Principal Fallback**

If a user doesn't have SQL warehouse access, the app automatically falls back to using a service principal for database operations while still maintaining user context for other operations.

## Deployment Tips

### Multiple Deployments

You can deploy multiple instances of the app for different purposes (dev, staging, prod):

```bash
# Development instance
./deploy.sh --app-name mcp-dev-api-registry --create

# Staging instance
./deploy.sh --app-name mcp-staging-api-registry --create

# Production instance
./deploy.sh --app-name mcp-prod-api-registry --create
```

Each deployment will have its own:
- Unique URL
- Independent database (if using different catalogs/schemas)
- Separate authentication scope
- Isolated API registry data

### Best Practices

- **Use descriptive names**: `mcp-{environment}-{purpose}` (e.g., `mcp-prod-customer-apis`)
- **Test with `--verbose`**: See detailed deployment logs if something fails
- **Use `--create`**: Automatically creates the app if it doesn't exist
- **Keep names short**: Easier to reference in MCP setup commands

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

**App not accessible:**
- Verify app is deployed: `./app_status.sh`
- Check app logs: Visit `https://your-app.databricksapps.com/logz` in browser
- Ensure you have network access to the workspace

**API registration failing:**
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
