# Check Databricks API Registry

**IMMEDIATE ACTION REQUIRED:** Query the API registry table right now to see all available API endpoints in the Lakebase instance.

You must execute this exact SQL query immediately using the `execute_dbsql` tool:

```sql
SELECT * FROM luca_milletti.custom_mcp_server.api_registry
```

**What this query does:**
- Queries the Unity Catalog table containing the API registry
- Located in catalog: `luca_milletti`
- Located in schema: `custom_mcp_server`
- Table name: `api_registry`

**Information you'll get:**
- List of all registered API endpoints
- API endpoint names and descriptions
- API endpoint configurations
- Current status of each API endpoint
- Metadata about available APIs in the Lakebase instance

**Why this matters:**
- Understand what API endpoints are available in the system
- Check the status and configuration of APIs
- Verify API registry is properly populated
- Troubleshoot API availability issues
- Document available endpoints for integration

**Important Notes:**
- This query uses your authenticated user credentials (on-behalf-of auth)
- You must have access to the `luca_milletti.custom_mcp_server` catalog and schema
- The query will use the default SQL warehouse configured in the environment
- If you need to specify a warehouse, add the `warehouse_id` parameter to the tool call

**Execute this SQL query now using the execute_dbsql MCP tool to see all available API endpoints in the registry.**
