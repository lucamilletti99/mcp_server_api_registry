# API Registry Workflow

This workflow guides you through discovering, registering, and using external API endpoints with the MCP server.

## Overview

The API registry workflow consists of four main steps:

1. **Discover** - Analyze the API endpoint to understand authentication and data capabilities
2. **Register** - Store the API configuration in the Lakebase registry
3. **Validate** - Confirm the API is working correctly
4. **Use** - Execute SQL queries or retrieve data from the registered API

## Step 1: Discover API Endpoint

**When to use:** You have an API URL and need to understand how to authenticate and what data it provides.

### Tool: `discover_api_endpoint`

**Parameters:**
- `endpoint_url` (required): The full API URL to discover
- `api_key` (optional): API key if you already know authentication is required
- `timeout` (optional): Request timeout in seconds (default: 10)

### Example: Discovering Alpha Vantage API

```
discover_api_endpoint(
  endpoint_url="https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=IBM&interval=5min&apikey=demo"
)
```

**Expected Output:**
```json
{
  "success": true,
  "endpoint_url": "https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=IBM&interval=5min&apikey=demo",
  "status_code": 200,
  "requires_auth": true,
  "auth_detection": {
    "detected": true,
    "method": "URL parameter (apikey)",
    "confidence": "high"
  },
  "data_capabilities": {
    "detected_fields": ["Meta Data", "Time Series (5min)", "symbol", "interval", "output size"],
    "structure": "object",
    "summary": "API provides stock market time series data with meta information"
  },
  "next_steps": [
    "API is functional with authentication",
    "Use register_api_in_registry to save this configuration",
    "Set auth_type to 'api_key' and token_info to your API key"
  ]
}
```

### What the Discovery Tool Does:

1. **Tests without authentication** - Makes initial request to detect if auth is required
2. **Detects authentication patterns** - Looks for:
   - HTTP status codes (401, 403)
   - Error messages containing "unauthorized", "forbidden", "authentication required"
   - Common auth keywords in response
3. **Tries multiple auth methods** (if API key provided):
   - URL parameter: `?apikey=XXX` or `?api_key=XXX`
   - Bearer token: `Authorization: Bearer XXX`
   - Custom header: `X-API-Key: XXX`
4. **Analyzes data capabilities** - Examines response structure to understand what data is available
5. **Provides next steps** - Tells you what to do next

### Common Discovery Scenarios:

**Scenario A: No API Key Provided**
```
discover_api_endpoint(endpoint_url="https://api.example.com/data")
```
- If auth required: Returns `requires_auth: true` and asks you to provide `api_key`
- If no auth needed: Returns `requires_auth: false` and you can register directly

**Scenario B: API Key Provided**
```
discover_api_endpoint(
  endpoint_url="https://api.example.com/data",
  api_key="your-secret-key-here"
)
```
- Automatically tests multiple authentication patterns
- Returns which auth method worked
- Shows you the data structure

## Step 2: Register API in Registry

**When to use:** After discovering an API, you want to save its configuration for reuse.

### Tool: `register_api_in_registry`

**Required Parameters:**
- `api_name`: Descriptive name for the API (e.g., "Alpha Vantage Stock Data")
- `description`: What this API does and what data it provides
- `api_endpoint`: The full API URL
- `warehouse_id`: Databricks SQL warehouse ID for validation queries

**Optional Parameters:**
- `http_method`: HTTP method to use (default: "GET")
- `auth_type`: Authentication type - "none", "api_key", "bearer_token", "custom_header" (default: "none")
- `token_info`: The actual API key or token value (default: "")
- `request_params`: Additional request parameters as JSON string (default: "{}")
- `validate_after_register`: Whether to validate the endpoint after registration (default: true)

### Example: Registering Alpha Vantage API

```
register_api_in_registry(
  api_name="Alpha Vantage - IBM Stock 5min Intervals",
  description="Stock market time series data for IBM with 5-minute intervals. Provides OHLC (Open, High, Low, Close) prices and trading volume.",
  api_endpoint="https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=IBM&interval=5min&apikey=demo",
  warehouse_id="your-warehouse-id-here",
  http_method="GET",
  auth_type="api_key",
  token_info="demo",
  validate_after_register=true
)
```

**Expected Output:**
```json
{
  "success": true,
  "message": "API 'Alpha Vantage - IBM Stock 5min Intervals' registered successfully",
  "api_id": "api-a1b2c3d4",
  "status": "valid",
  "validation": {
    "status_code": 200,
    "is_healthy": true,
    "message": "API endpoint is valid and responding correctly"
  },
  "registry_entry": {
    "api_id": "api-a1b2c3d4",
    "api_name": "Alpha Vantage - IBM Stock 5min Intervals",
    "user_who_requested": "luca_milletti",
    "created_at": "2025-10-25T10:30:00"
  }
}
```

### What Registration Does:

1. **Generates unique API ID** - Creates a unique identifier like `api-a1b2c3d4`
2. **Captures user context** - Records who registered the API using on-behalf-of authentication
3. **Validates endpoint** (if enabled) - Makes a test call to verify the API works
4. **Stores in Lakebase** - Inserts configuration into `luca_milletti.custom_mcp_server.api_registry` table
5. **Returns confirmation** - Provides the API ID and validation results

### Registration Fields Explained:

- **api_id**: Auto-generated unique identifier for this API
- **api_name**: Human-readable name you provide
- **description**: Details about what the API does
- **user_who_requested**: Your username (auto-captured from authentication)
- **modified_date**: Timestamp when registered (auto-generated)
- **api_endpoint**: The full URL with all query parameters
- **http_method**: GET, POST, PUT, DELETE, etc.
- **auth_type**: How to authenticate with the API
- **token_info**: The actual secret key/token (stored securely)
- **request_params**: Additional parameters as JSON
- **status**: "valid" or "pending" based on validation
- **validation_message**: Details from validation test
- **created_at**: When the API was first registered

## Step 3: Validate Registered API

**When to use:** You want to check if a registered API is still working correctly.

### Tool: `call_api_endpoint`

**Parameters:**
- `endpoint_url` (required): The API URL to call
- `http_method` (optional): HTTP method (default: "GET")
- `headers` (optional): JSON string of custom headers
- `body` (optional): JSON string of request body for POST/PUT
- `timeout` (optional): Request timeout in seconds (default: 10)

### Example: Testing a Registered API

```
call_api_endpoint(
  endpoint_url="https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=IBM&interval=5min&apikey=demo",
  http_method="GET",
  timeout=15
)
```

**Expected Output:**
```json
{
  "success": true,
  "status_code": 200,
  "is_healthy": true,
  "response_data": {
    "Meta Data": {
      "1. Information": "Intraday (5min) open, high, low, close prices and volume",
      "2. Symbol": "IBM",
      "3. Last Refreshed": "2025-10-25 15:55:00"
    },
    "Time Series (5min)": {
      "2025-10-25 15:55:00": {
        "1. open": "180.50",
        "2. high": "180.75",
        "3. low": "180.40",
        "4. close": "180.65",
        "5. volume": "25630"
      }
    }
  },
  "response_preview": "{\n  \"Meta Data\": {\n    \"1. Information\": \"Intraday (5min)...",
  "message": "API call successful"
}
```

### What Validation Does:

1. **Makes HTTP request** - Calls the API with specified method and parameters
2. **Checks response** - Verifies HTTP status code and response data
3. **Determines health** - Sets `is_healthy: true` if status is 200-299
4. **Returns full data** - Provides complete response for inspection
5. **Provides preview** - Shows first 500 characters for quick review

## Step 4: Use Registered APIs

**When to use:** Query the registry to find APIs or retrieve data from registered endpoints.

### Tool: `execute_dbsql`

**Retrieve All Registered APIs:**
```
execute_dbsql(
  warehouse_id="your-warehouse-id",
  query="SELECT * FROM luca_milletti.custom_mcp_server.api_registry ORDER BY created_at DESC"
)
```

**Find APIs by Name:**
```
execute_dbsql(
  warehouse_id="your-warehouse-id",
  query="SELECT * FROM luca_milletti.custom_mcp_server.api_registry WHERE api_name LIKE '%Alpha Vantage%'"
)
```

**Get API Details by ID:**
```
execute_dbsql(
  warehouse_id="your-warehouse-id",
  query="SELECT * FROM luca_milletti.custom_mcp_server.api_registry WHERE api_id = 'api-a1b2c3d4'"
)
```

**Find APIs Registered by User:**
```
execute_dbsql(
  warehouse_id="your-warehouse-id",
  query="SELECT * FROM luca_milletti.custom_mcp_server.api_registry WHERE user_who_requested = 'luca_milletti'"
)
```

## Complete Workflow Example

**User Request:** "I want to use the Alpha Vantage API to get IBM stock data"

### Step-by-Step:

**1. Discover the API:**
```
User: "Can you discover this API for me? https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=IBM&interval=5min&apikey=demo"

Claude calls:
discover_api_endpoint(
  endpoint_url="https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=IBM&interval=5min&apikey=demo"
)

Result:
- Requires authentication: Yes (apikey parameter)
- Data available: Stock time series with OHLC prices
- Next step: Register with auth_type='api_key'
```

**2. Register the API:**
```
User: "Great! Please register this API so I can use it later."

Claude calls:
register_api_in_registry(
  api_name="Alpha Vantage - IBM Stock Data",
  description="Real-time and historical stock data for IBM with 5-minute intervals",
  api_endpoint="https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=IBM&interval=5min&apikey=demo",
  warehouse_id="abc123warehouse",
  http_method="GET",
  auth_type="api_key",
  token_info="demo"
)

Result:
- API ID: api-a1b2c3d4
- Status: valid
- Successfully registered
```

**3. Validate the API:**
```
User: "Can you test if the API is working?"

Claude calls:
call_api_endpoint(
  endpoint_url="https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=IBM&interval=5min&apikey=demo"
)

Result:
- Status: 200 OK
- Healthy: Yes
- Data returned with latest stock prices
```

**4. Use the Registered API:**
```
User: "Show me all my registered APIs"

Claude calls:
execute_dbsql(
  warehouse_id="abc123warehouse",
  query="SELECT api_name, description, api_endpoint, status FROM luca_milletti.custom_mcp_server.api_registry WHERE user_who_requested = 'luca_milletti'"
)

Result:
- Shows table with all registered APIs
- Includes the newly registered Alpha Vantage API
```

## Common Patterns

### Pattern 1: API with Bearer Token Authentication

**Discovery:**
```
discover_api_endpoint(
  endpoint_url="https://api.example.com/v1/data",
  api_key="your-bearer-token-here"
)
```

**Registration:**
```
register_api_in_registry(
  api_name="Example API Data",
  description="Data from example.com API",
  api_endpoint="https://api.example.com/v1/data",
  warehouse_id="your-warehouse-id",
  auth_type="bearer_token",
  token_info="your-bearer-token-here"
)
```

### Pattern 2: API with Custom Header Authentication

**Discovery:**
```
discover_api_endpoint(
  endpoint_url="https://api.example.com/v1/data",
  api_key="your-api-key-here"
)
```

**Registration:**
```
register_api_in_registry(
  api_name="Example API Data",
  description="Data from example.com API",
  api_endpoint="https://api.example.com/v1/data",
  warehouse_id="your-warehouse-id",
  auth_type="custom_header",
  token_info="X-API-Key: your-api-key-here"
)
```

### Pattern 3: Public API (No Authentication)

**Discovery:**
```
discover_api_endpoint(
  endpoint_url="https://api.publicdata.com/v1/info"
)
```

**Registration:**
```
register_api_in_registry(
  api_name="Public Data API",
  description="Public data endpoint with no authentication required",
  api_endpoint="https://api.publicdata.com/v1/info",
  warehouse_id="your-warehouse-id",
  auth_type="none"
)
```

### Pattern 4: POST Request with Body

**Registration:**
```
register_api_in_registry(
  api_name="Example POST API",
  description="API that accepts POST requests with JSON body",
  api_endpoint="https://api.example.com/v1/create",
  warehouse_id="your-warehouse-id",
  http_method="POST",
  auth_type="bearer_token",
  token_info="your-token",
  request_params='{"field1": "value1", "field2": "value2"}'
)
```

**Testing:**
```
call_api_endpoint(
  endpoint_url="https://api.example.com/v1/create",
  http_method="POST",
  headers='{"Authorization": "Bearer your-token", "Content-Type": "application/json"}',
  body='{"field1": "value1", "field2": "value2"}'
)
```

## Troubleshooting

### Issue: "API requires authentication but no API key provided"

**Solution:** Run discovery again with the API key:
```
discover_api_endpoint(
  endpoint_url="https://api.example.com/data",
  api_key="your-actual-api-key"
)
```

### Issue: "API validation failed with status 401"

**Possible causes:**
1. Wrong authentication type (try different auth_type values)
2. Invalid or expired API key
3. API key in wrong format

**Solution:** Re-discover with correct credentials and try different auth patterns

### Issue: "API endpoint returned 404"

**Possible causes:**
1. Incorrect URL or endpoint path
2. API version changed
3. Resource doesn't exist

**Solution:** Verify the URL in API documentation and update endpoint

### Issue: "Timeout error"

**Possible causes:**
1. API is slow or unresponsive
2. Network connectivity issues
3. Timeout too short for this API

**Solution:** Increase timeout parameter:
```
discover_api_endpoint(
  endpoint_url="https://api.example.com/data",
  timeout=30  # Increase from default 10 seconds
)
```

### Issue: "Cannot find warehouse_id"

**Solution:** List available warehouses:
```
list_warehouses()
```
Copy the warehouse ID from the results and use it in registration.

## Best Practices

1. **Always discover before registering** - Understand authentication requirements first
2. **Use descriptive names** - Make api_name clear and searchable
3. **Include details in description** - Document what data the API provides
4. **Test after registration** - Use `call_api_endpoint` to verify it works
5. **Store API keys securely** - Use token_info field for authentication secrets
6. **Document query parameters** - Include important parameters in the endpoint URL
7. **Query the registry** - Use SQL to find and manage your registered APIs
8. **Monitor validation status** - Check the status field to ensure APIs remain valid
9. **Update when needed** - Re-register APIs if endpoints or auth changes

## Security Considerations

- **API keys are stored** in the Lakebase registry - ensure proper access controls
- **On-behalf-of authentication** means each user only sees their own registered APIs
- **Validate regularly** to detect if APIs become unauthorized or deprecated
- **Use warehouse permissions** to control who can query the registry
- **Never share API keys** in descriptions or names - only in token_info field

## Summary

The API registry workflow follows this pattern:

1. **Discover** → Understand authentication and capabilities
2. **Register** → Store configuration in Lakebase
3. **Validate** → Confirm the API works
4. **Use** → Query registry and call APIs as needed

Each step is supported by specific MCP tools that handle the complexity of API integration, authentication detection, and data management.
