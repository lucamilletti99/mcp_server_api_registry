# Workspace Requirements

This document outlines the Databricks workspace prerequisites and features required to deploy and use the API Registry MCP Server.

## Required Features

### 1. Databricks Apps (Required)

**Status:** Public Preview

The API Registry runs as a Databricks App, which must be enabled in your workspace.

**How to verify:**
```bash
databricks apps list
```

**How to enable:**
- Contact your Databricks account team to enable Apps for your workspace
- Or check the [Databricks Apps documentation](https://docs.databricks.com/en/dev-tools/databricks-apps/index.html)

**Requirements:**
- Workspace must be on AWS, Azure, or GCP
- Must have admin permissions to create apps
- OAuth must be configured for authentication

---

### 2. Foundation Model API / Model Serving (Required)

**Status:** Generally Available

The AI chat interface uses Databricks Foundation Model APIs, specifically the `databricks-claude-sonnet-4` endpoint.

**How to verify:**
```bash
# Check if you can access model serving
databricks serving-endpoints list

# Test the Claude Sonnet 4 endpoint
curl -X POST \
  https://your-workspace.cloud.databricks.com/serving-endpoints/databricks-claude-sonnet-4/invocations \
  -H "Authorization: Bearer $DATABRICKS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello"}], "max_tokens": 100}'
```

**Required OAuth Scope:**
- `all-apis` - Enables access to Foundation Model endpoints

**How to enable:**
- Foundation Model APIs are generally available in most regions
- Check [Databricks Foundation Model APIs documentation](https://docs.databricks.com/en/machine-learning/foundation-models/index.html)
- Verify your workspace region supports Foundation Models

---

### 3. SQL Warehouses (Required)

**Status:** Generally Available

The app requires SQL warehouses to:
- Query the `api_registry` table
- Execute SQL operations via MCP tools
- Validate user warehouse access for authentication

**How to verify:**
```bash
# List available warehouses
databricks warehouses list

# Or via SQL
SELECT * FROM system.compute.warehouses;
```

**Required OAuth Scope:**
- `sql` - Enables SQL warehouse and query execution

**Minimum Requirements:**
- At least one SQL warehouse must be running or available
- User must have `CAN_USE` permission on at least one warehouse
- Warehouse must have access to the catalog.schema where `api_registry` table is stored

**Recommended:**
- Serverless SQL Warehouse for best performance
- Set `DATABRICKS_SQL_WAREHOUSE_ID` in `.env.local` for default warehouse

---

### 4. Unity Catalog (Required)

**Status:** Generally Available

Unity Catalog is required to store the `api_registry` table.

**How to verify:**
```bash
# List catalogs
databricks catalogs list

# Check if Unity Catalog is enabled
databricks unity-catalog metastores list
```

**Required OAuth Scope:**
- `sql` - Enables catalog and schema access

**Minimum Requirements:**
- At least one Unity Catalog metastore attached to workspace
- User must have `USE CATALOG` and `USE SCHEMA` permissions
- User must have `CREATE TABLE` permission to create the `api_registry` table
- Or use an existing catalog.schema where the table already exists

**Table Location:**
- Any catalog and schema the user has access to
- Recommended: Create a dedicated schema like `your_catalog.api_registry`

---

### 5. DBFS Access (Optional)

**Status:** Generally Available

DBFS access is exposed via MCP tools but not required for core functionality.

**Required OAuth Scope:**
- `files.files` - Enables DBFS file operations

**How to verify:**
```bash
# List DBFS root
databricks fs ls dbfs:/
```

---

### 6. Workspace API Access (Required)

**Status:** Generally Available

The app uses the Databricks SDK to interact with workspace resources.

**Required Permissions:**
- User must be able to authenticate (OAuth or PAT)
- Service principal must have appropriate permissions for on-behalf-of operations
- Users need `CAN_USE` on SQL warehouses they want to query

---

## Authentication Requirements

### For Deployment (Admin)

To deploy the app, you need:
- Databricks CLI v0.260.0 or higher
- `DATABRICKS_HOST` configured
- Personal Access Token or OAuth authentication
- Permission to create Databricks Apps in the workspace

### For End Users

End users need:
- SSO/OAuth authentication to the workspace
- Access to at least one SQL warehouse (for warehouse access check)
- Permissions on the catalog.schema containing `api_registry` table

### On-Behalf-Of (OBO) Authentication

The app uses OBO authentication to run queries with the user's identity:
- User token is forwarded via `X-Forwarded-Access-Token` header
- Falls back to service principal if user has no warehouse access
- Ensures proper access control and audit logging

---

## Feature Summary Table

| Feature | Status | Required | Purpose |
|---------|--------|----------|---------|
| Databricks Apps | Public Preview | ✅ Yes | App hosting platform |
| Foundation Model API | Generally Available | ✅ Yes | AI chat interface |
| SQL Warehouses | Generally Available | ✅ Yes | Database operations |
| Unity Catalog | Generally Available | ✅ Yes | Table storage |
| DBFS Access | Generally Available | ⚠️ Optional | File operations (MCP tool) |
| Workspace API | Generally Available | ✅ Yes | SDK operations |

---

## Regional Availability

### Databricks Apps Support

- ✅ AWS: All commercial regions
- ✅ Azure: All commercial regions
- ✅ GCP: All commercial regions

Check latest availability at: https://docs.databricks.com/en/dev-tools/databricks-apps/index.html

### Foundation Model API Support

- ✅ Most AWS regions
- ✅ Most Azure regions
- ✅ Most GCP regions

Verify your region supports `databricks-claude-sonnet-4` at: https://docs.databricks.com/en/machine-learning/foundation-models/supported-models.html

---

## Troubleshooting

### "Apps not enabled in workspace"
**Solution:** Contact your Databricks account team to enable Apps preview

### "Model endpoint not found: databricks-claude-sonnet-4"
**Solution:**
- Verify Foundation Models are available in your region
- Check you have `all-apis` scope in `app.yaml`
- Try accessing the endpoint directly via API

### "No SQL warehouses found"
**Solution:**
- Create at least one SQL warehouse in the workspace
- Grant user `CAN_USE` permission on the warehouse
- Verify warehouse is running or can be started

### "Table api_registry not found"
**Solution:**
- Create the table using `setup_table.py` script
- Or run the SQL from `setup_api_registry_table.sql`
- Verify user has permissions on the catalog.schema

### "Permission denied" errors
**Solution:**
- Check OAuth scopes in `app.yaml` include `all-apis`, `sql`, `files.files`
- Verify user has necessary permissions on resources
- Check service principal has proper workspace access

---

## Pre-Deployment Checklist

Before deploying, verify:

- [ ] Databricks Apps is enabled in your workspace
- [ ] At least one SQL warehouse is available
- [ ] Unity Catalog is set up with an accessible catalog.schema
- [ ] Foundation Model API endpoint `databricks-claude-sonnet-4` is accessible
- [ ] You have Databricks CLI v0.260.0+ installed
- [ ] You are authenticated to Databricks (`databricks current-user me`)
- [ ] You have permissions to create Databricks Apps

---

## Additional Resources

- [Databricks Apps Documentation](https://docs.databricks.com/en/dev-tools/databricks-apps/index.html)
- [Foundation Model APIs](https://docs.databricks.com/en/machine-learning/foundation-models/index.html)
- [Unity Catalog](https://docs.databricks.com/en/data-governance/unity-catalog/index.html)
- [SQL Warehouses](https://docs.databricks.com/en/compute/sql-warehouse/index.html)
- [Databricks SDK for Python](https://docs.databricks.com/en/dev-tools/sdk-python.html)
