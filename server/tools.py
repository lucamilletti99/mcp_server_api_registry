"""MCP Tools for Databricks operations."""

import json
import os
import uuid
from datetime import datetime
from typing import Dict, List
from urllib.parse import parse_qs, urlparse

import requests
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
from fastmcp.server.dependencies import get_http_headers


def get_workspace_client() -> WorkspaceClient:
  """Get a WorkspaceClient with on-behalf-of user authentication.

  Falls back to OAuth service principal authentication if user token is not available.

  Returns:
      WorkspaceClient configured with appropriate authentication
  """
  host = os.environ.get('DATABRICKS_HOST')

  # Try to get user token from request headers (on-behalf-of authentication)
  headers = get_http_headers()
  user_token = headers.get('x-forwarded-access-token')

  if user_token:
    # Use on-behalf-of authentication with user's token
    # Create Config with ONLY token auth to avoid OAuth conflict
    # auth_type='pat' forces token-only auth and disables auto-detection
    print(f'🔐 Using on-behalf-of authentication (user token)')
    config = Config(host=host, token=user_token, auth_type='pat')
    return WorkspaceClient(config=config)
  else:
    # Fall back to OAuth service principal authentication
    # WorkspaceClient will automatically use DATABRICKS_CLIENT_ID and DATABRICKS_CLIENT_SECRET
    # which are injected by Databricks Apps platform
    print(f'🔐 Using OAuth service principal authentication (fallback)')
    return WorkspaceClient(host=host)


def _execute_sql_query(
  query: str, warehouse_id: str = None, catalog: str = None, schema: str = None, limit: int = 100
) -> dict:
  """Helper function to execute SQL queries on Databricks SQL warehouse.

  Args:
      query: SQL query to execute
      warehouse_id: SQL warehouse ID (optional, uses env var if not provided)
      catalog: Catalog to use (optional)
      schema: Schema to use (optional)
      limit: Maximum number of rows to return (default: 100)

  Returns:
      Dictionary with query results or error message
  """
  try:
    # Initialize Databricks SDK with on-behalf-of authentication
    w = get_workspace_client()

    # Get warehouse ID from parameter or environment
    warehouse_id = warehouse_id or os.environ.get('DATABRICKS_SQL_WAREHOUSE_ID')
    if not warehouse_id:
      return {
        'success': False,
        'error': (
          'No SQL warehouse ID provided. Set DATABRICKS_SQL_WAREHOUSE_ID or pass warehouse_id.'
        ),
      }

    # Build the full query with catalog/schema if provided
    full_query = query
    if catalog and schema:
      full_query = f'USE CATALOG {catalog}; USE SCHEMA {schema}; {query}'

    print(f'🔧 Executing SQL on warehouse {warehouse_id}: {query[:100]}...')

    # Execute the query
    result = w.statement_execution.execute_statement(
      warehouse_id=warehouse_id, statement=full_query, wait_timeout='30s'
    )

    # Process results
    if result.result and result.result.data_array:
      columns = [col.name for col in result.manifest.schema.columns]
      data = []

      for row in result.result.data_array[:limit]:
        row_dict = {}
        for i, col in enumerate(columns):
          row_dict[col] = row[i]
        data.append(row_dict)

      return {'success': True, 'data': {'columns': columns, 'rows': data}, 'row_count': len(data)}
    else:
      return {
        'success': True,
        'data': {'message': 'Query executed successfully with no results'},
        'row_count': 0,
      }

  except Exception as e:
    print(f'❌ Error executing SQL: {str(e)}')
    return {'success': False, 'error': f'Error: {str(e)}'}


def _analyze_api_capabilities(data: Dict) -> Dict:
  """Analyze API response data to understand capabilities."""
  capabilities = {'data_structure': {}, 'available_fields': [], 'data_types': {}, 'insights': []}

  try:
    # Identify the structure
    if isinstance(data, dict):
      capabilities['data_structure']['type'] = 'object'
      capabilities['available_fields'] = list(data.keys())

      # Look for common API patterns
      if 'data' in data:
        capabilities['insights'].append('API uses "data" wrapper for results')
      if 'error' in data or 'Error Message' in data:
        capabilities['insights'].append('Response contains error information')
      if 'results' in data or 'items' in data:
        capabilities['insights'].append('API returns multiple items/results')

      # Analyze field types
      for key, value in data.items():
        if isinstance(value, dict):
          capabilities['data_types'][key] = 'nested_object'
          # Look deeper into nested objects
          if key == 'Meta Data':
            capabilities['insights'].append('Contains metadata about the request/data')
          elif 'Time Series' in key:
            capabilities['insights'].append(f'Time series data available: {key}')
        elif isinstance(value, list):
          capabilities['data_types'][key] = f'array (length: {len(value)})'
          if value and isinstance(value[0], dict):
            capabilities['insights'].append(f'{key} contains array of objects')
        else:
          capabilities['data_types'][key] = type(value).__name__

    elif isinstance(data, list):
      capabilities['data_structure']['type'] = 'array'
      capabilities['data_structure']['length'] = len(data)
      if data and isinstance(data[0], dict):
        capabilities['available_fields'] = list(data[0].keys())
        capabilities['insights'].append('Array of objects - likely list of records')

  except Exception as e:
    capabilities['error'] = f'Analysis error: {str(e)}'

  return capabilities


def _validate_api_endpoint(
  api_endpoint: str, http_method: str = 'GET', auth_type: str = 'none', token_info: str = '', timeout: int = 10
) -> Dict:
  """Validate an API endpoint by calling it and analyzing the response.

  Args:
      api_endpoint: Full URL of the API endpoint
      http_method: HTTP method to use
      auth_type: Authentication type (none, bearer, api_key, etc.)
      token_info: Authentication token or API key
      timeout: Request timeout in seconds

  Returns:
      Dictionary with validation results:
      - status: 'valid' or 'pending'
      - validation_message: Detailed message about validation
      - status_code: HTTP status code (if call succeeded)
  """
  try:
    # Build headers based on auth type
    headers_dict = {}
    if auth_type == 'bearer' and token_info:
      headers_dict['Authorization'] = f'Bearer {token_info}'
    elif auth_type == 'api_key' and token_info:
      headers_dict['X-API-Key'] = token_info

    # Call the API
    response = requests.request(method=http_method.upper(), url=api_endpoint, headers=headers_dict, timeout=timeout)

    if response.status_code == 200:
      # Success - build validation message
      try:
        sample_data = response.json()
        sample_preview = json.dumps(sample_data, indent=2)[:500]
      except Exception:
        sample_preview = response.text[:500]

      validation_message = f"""✅ VALIDATION SUCCESSFUL!

Endpoint Status: {response.status_code} OK
Authentication: Verified ✓
Data Retrieved: Valid JSON response received

Sample Response Preview:
{sample_preview}"""

      return {'status': 'valid', 'validation_message': validation_message, 'status_code': response.status_code}

    else:
      # Non-200 response
      validation_message = (
        f'⚠️  Validation returned status {response.status_code}\n' f'Response: {response.text[:200]}'
      )
      return {
        'status': 'pending',
        'validation_message': validation_message,
        'status_code': response.status_code,
      }

  except Exception as e:
    validation_message = f'⚠️  Validation error: {str(e)}'
    return {'status': 'pending', 'validation_message': validation_message}


def load_tools(mcp_server):
  """Register all MCP tools with the server.

  Args:
      mcp_server: The FastMCP server instance to register tools with
  """

  @mcp_server.tool
  def health() -> dict:
    """Check the health of the MCP server and Databricks connection."""
    headers = get_http_headers()
    user_token = headers.get('x-forwarded-access-token')
    user_token_present = bool(user_token)

    # Get basic info about the authenticated user if OBO token is present
    user_info = None
    if user_token_present:
      try:
        # Use user's token for on-behalf-of authentication
        # Create Config with ONLY token auth to avoid OAuth conflict
        # auth_type='pat' forces token-only auth and disables auto-detection
        config = Config(host=os.environ.get('DATABRICKS_HOST'), token=user_token, auth_type='pat')
        w = WorkspaceClient(config=config)
        current_user = w.current_user.me()
        user_info = {
          'username': current_user.user_name,
          'display_name': current_user.display_name,
          'active': current_user.active,
        }
      except Exception as e:
        user_info = {'error': f'Could not fetch user info: {str(e)}'}

    return {
      'status': 'healthy',
      'service': 'databricks-mcp',
      'databricks_configured': bool(os.environ.get('DATABRICKS_HOST')),
      'auth_mode': 'on-behalf-of' if user_token_present else 'service-principal',
      'user_auth_available': user_token_present,
      'user_token_preview': user_token[:20] + '...' if user_token else None,
      'authenticated_user': user_info,
      'headers_present': list(headers.keys()),
    }

  @mcp_server.tool
  def execute_dbsql(
    query: str,
    warehouse_id: str = None,
    catalog: str = None,
    schema: str = None,
    limit: int = 100,
  ) -> dict:
    """Execute a SQL query on Databricks SQL warehouse.

    Args:
        query: SQL query to execute
        warehouse_id: SQL warehouse ID (optional, uses env var if not provided)
        catalog: Catalog to use (optional)
        schema: Schema to use (optional)
        limit: Maximum number of rows to return (default: 100)

    Returns:
        Dictionary with query results or error message
    """
    return _execute_sql_query(query, warehouse_id, catalog, schema, limit)

  @mcp_server.tool
  def check_api_registry(warehouse_id: str = None, limit: int = 100) -> dict:
    """Check the Databricks API Registry to see all available API endpoints.

    This queries the luca_milletti.custom_mcp_server.api_registry table
    to return all registered API endpoints in the Lakebase instance.

    Args:
        warehouse_id: SQL warehouse ID (optional, uses env var if not provided)
        limit: Maximum number of rows to return (default: 100)

    Returns:
        Dictionary with API registry results including:
        - List of all registered API endpoints
        - API endpoint names and descriptions
        - API configurations and metadata
        - Current status of each endpoint
    """
    # Fixed query for the API registry table (fully-qualified table name)
    query = 'SELECT * FROM luca_milletti.custom_mcp_server.api_registry'

    # Don't pass catalog/schema since we're using fully-qualified table name
    # Passing them would prepend USE CATALOG/USE SCHEMA which interferes with results
    result = _execute_sql_query(query, warehouse_id, catalog=None, schema=None, limit=limit)

    # Add context to the result
    if result.get('success'):
      result['registry_info'] = {
        'catalog': 'luca_milletti',
        'schema': 'custom_mcp_server',
        'table': 'api_registry',
        'description': 'Databricks API Registry containing all available API endpoints',
      }

    return result

  @mcp_server.tool
  def call_api_endpoint(
    endpoint_url: str,
    http_method: str = 'GET',
    headers: str = None,
    body: str = None,
    timeout: int = 10,
  ) -> dict:
    """Call an API endpoint to check health and retrieve data.

    This tool makes HTTP requests to external API endpoints to validate
    they are working and return data. Useful for testing APIs in the registry.

    Args:
        endpoint_url: The full URL of the API endpoint to call
        http_method: HTTP method to use (GET, POST, PUT, DELETE, etc.) - default: GET
        headers: Optional JSON string of HTTP headers (e.g., '{"Authorization": "Bearer token"}')
        body: Optional JSON string of request body for POST/PUT requests
        timeout: Request timeout in seconds (default: 10)

    Returns:
        Dictionary with:
        - success: Boolean indicating if the request succeeded
        - status_code: HTTP status code
        - is_healthy: Boolean indicating if status is 2xx
        - response_data: Response body (parsed JSON if possible, else text)
        - response_preview: First 500 chars of response
        - headers: Response headers
        - error: Error message if request failed
    """
    try:
      # Parse headers if provided
      request_headers = {}
      if headers:
        try:
          request_headers = json.loads(headers)
        except json.JSONDecodeError:
          return {
            'success': False,
            'error': 'Invalid JSON format for headers',
          }

      # Parse body if provided
      request_body = None
      if body:
        try:
          request_body = json.loads(body)
        except json.JSONDecodeError:
          # If not JSON, use as plain text
          request_body = body

      print(f'🌐 Calling API: {http_method} {endpoint_url}')

      # Make the HTTP request
      response = requests.request(
        method=http_method.upper(),
        url=endpoint_url,
        headers=request_headers,
        json=request_body if isinstance(request_body, dict) else None,
        data=request_body if isinstance(request_body, str) else None,
        timeout=timeout,
      )

      # Check if response is healthy (2xx status code)
      is_healthy = 200 <= response.status_code < 300

      # Try to parse response as JSON
      try:
        response_data = response.json()
        response_type = 'json'
      except Exception:
        response_data = response.text
        response_type = 'text'

      # Create preview of response
      response_str = json.dumps(response_data, indent=2) if response_type == 'json' else response_data
      response_preview = response_str[:500] + '...' if len(response_str) > 500 else response_str

      return {
        'success': True,
        'status_code': response.status_code,
        'status_text': response.reason,
        'is_healthy': is_healthy,
        'response_type': response_type,
        'response_data': response_data,
        'response_preview': response_preview,
        'response_size': len(response.content),
        'headers': dict(response.headers),
        'url': endpoint_url,
        'method': http_method.upper(),
      }

    except requests.exceptions.Timeout:
      return {
        'success': False,
        'is_healthy': False,
        'error': f'Request timed out after {timeout} seconds',
        'url': endpoint_url,
        'method': http_method.upper(),
      }
    except requests.exceptions.ConnectionError:
      return {
        'success': False,
        'is_healthy': False,
        'error': 'Connection error - could not reach the endpoint',
        'url': endpoint_url,
        'method': http_method.upper(),
      }
    except Exception as e:
      print(f'❌ Error calling API: {str(e)}')
      return {
        'success': False,
        'is_healthy': False,
        'error': f'Error: {str(e)}',
        'url': endpoint_url,
        'method': http_method.upper(),
      }

  @mcp_server.tool
  def discover_api_endpoint(endpoint_url: str, api_key: str = None, timeout: int = 10) -> dict:
    """Discover API endpoint requirements and capabilities.

    This tool analyzes an API endpoint to determine:
    1. Whether it requires authentication (API key)
    2. What data and capabilities the API provides

    If authentication is required but not provided, the tool will indicate
    that the user should provide an API key.

    Args:
        endpoint_url: The full URL of the API endpoint to discover
        api_key: Optional API key if the endpoint requires authentication
        timeout: Request timeout in seconds (default: 10)

    Returns:
        Dictionary with discovery results including:
        - requires_auth: Boolean indicating if API key is needed
        - auth_detected: Details about detected authentication method
        - data_capabilities: What data the API provides
        - available_endpoints: Suggested endpoints or functions
        - sample_response: Sample data from the API
        - next_steps: Recommendations for user
    """
    try:
      # Parse the URL to understand structure
      parsed_url = urlparse(endpoint_url)
      query_params = parse_qs(parsed_url.query)
      base_url = f'{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}'

      print(f'🔍 Discovering API endpoint: {endpoint_url}')

      # First attempt: Call without API key
      try:
        response_no_auth = requests.get(endpoint_url, timeout=timeout)
        initial_status = response_no_auth.status_code
        initial_response = response_no_auth.text

        # Try to parse as JSON
        try:
          initial_data = response_no_auth.json()
        except Exception:
          initial_data = initial_response

      except Exception as e:
        return {
          'success': False,
          'error': f'Failed to reach endpoint: {str(e)}',
          'next_steps': ['Check if the URL is correct', 'Verify internet connectivity'],
        }

      # Analyze the response for authentication requirements
      requires_auth = False
      auth_hints = []

      # Check for auth indicators
      if initial_status in [401, 403]:
        requires_auth = True
        auth_hints.append(f'HTTP {initial_status} - Authentication required')

      # Check response content for API key mentions (common patterns)
      auth_keywords = ['api key', 'apikey', 'api_key', 'authentication', 'unauthorized', 'forbidden']
      response_lower = str(initial_data).lower()

      for keyword in auth_keywords:
        if keyword in response_lower:
          requires_auth = True
          auth_hints.append(f'Response mentions: "{keyword}"')

      # If API key is provided, try with authentication
      authenticated_response = None
      if api_key:
        print(f'🔑 Trying with provided API key...')

        # Try common API key patterns
        auth_attempts = [
          {'params': {**query_params, 'apikey': [api_key]}},
          {'params': {**query_params, 'api_key': [api_key]}},
          {'headers': {'Authorization': f'Bearer {api_key}'}},
          {'headers': {'X-API-Key': api_key}},
        ]

        for attempt in auth_attempts:
          try:
            # Flatten query params for requests
            params = {k: v[0] if isinstance(v, list) else v for k, v in attempt.get('params', {}).items()}

            auth_response = requests.get(
              base_url, params=params, headers=attempt.get('headers', {}), timeout=timeout
            )

            if auth_response.status_code == 200:
              authenticated_response = auth_response
              print(f'✅ Authentication successful!')
              break
          except Exception:
            continue

      # Analyze the data capabilities
      response_to_analyze = authenticated_response if authenticated_response else response_no_auth

      if response_to_analyze.status_code == 200:
        try:
          data = response_to_analyze.json()
          data_capabilities = _analyze_api_capabilities(data)
        except Exception:
          data = response_to_analyze.text
          data_capabilities = {'type': 'text', 'preview': data[:200]}

        # Build discovery results
        result = {
          'success': True,
          'endpoint_url': endpoint_url,
          'base_url': base_url,
          'requires_auth': requires_auth,
          'auth_detected': {
            'hints': auth_hints,
            'authenticated': bool(authenticated_response),
          }
          if requires_auth
          else None,
          'status_code': response_to_analyze.status_code,
          'data_capabilities': data_capabilities,
          'sample_response': data if isinstance(data, dict) else str(data)[:500],
        }

        # Determine next steps
        if requires_auth and not api_key:
          result['next_steps'] = [
            '⚠️  This API requires authentication',
            'Please provide an API key using the api_key parameter',
            'Common parameter names: apikey, api_key, or Authorization header',
          ]
        elif requires_auth and not authenticated_response:
          result['next_steps'] = [
            '⚠️  Authentication failed with provided API key',
            'Check if the API key is correct',
            'Try different authentication methods (query param vs header)',
          ]
        else:
          result['next_steps'] = [
            '✅ API is accessible and returning data',
            'Review data_capabilities to understand what the API provides',
            'Consider registering this endpoint in the api_registry',
          ]

        return result

      else:
        return {
          'success': False,
          'endpoint_url': endpoint_url,
          'status_code': response_to_analyze.status_code,
          'requires_auth': requires_auth,
          'auth_hints': auth_hints,
          'error': f'API returned status {response_to_analyze.status_code}',
          'next_steps': [
            'Check the endpoint URL',
            'Verify required parameters are included',
            'Provide API key if authentication is required',
          ],
        }

    except Exception as e:
      print(f'❌ Error discovering API: {str(e)}')
      return {
        'success': False,
        'error': f'Discovery error: {str(e)}',
        'next_steps': ['Check the endpoint URL', 'Verify the API is accessible'],
      }

  @mcp_server.tool
  def register_api_in_registry(
    api_name: str,
    description: str,
    api_endpoint: str,
    warehouse_id: str,
    http_method: str = 'GET',
    auth_type: str = 'none',
    token_info: str = '',
    request_params: str = '{}',
    validate_after_register: bool = True,
  ) -> dict:
    """Register a new API endpoint in the Lakebase api_registry table.

    This tool adds a discovered API to your registry for tracking and reuse.
    It automatically uses your authenticated user identity and validates the API.

    Args:
        api_name: Unique name for the API (e.g., "alphavantage_intraday_stock")
        description: Description of what the API does
        api_endpoint: Full URL of the API endpoint
        warehouse_id: SQL warehouse ID to use for database operations
        http_method: HTTP method (default: GET)
        auth_type: Authentication type (none, api_key, bearer, basic, etc.)
        token_info: Authentication token or API key (if applicable)
        request_params: JSON string of request parameters (default: "{}")
        validate_after_register: Whether to validate the API after registering (default: True)

    Returns:
        Dictionary with registration results including:
        - success: Boolean indicating if registration succeeded
        - api_id: Generated ID for the registered API
        - status: Initial status (pending or valid if validated)
        - validation_message: Results from validation if performed
    """
    try:
      # Get authenticated user info for user_who_requested field
      headers = get_http_headers()
      user_token = headers.get('x-forwarded-access-token')

      # Try to get username from authenticated user
      username = 'unknown'
      if user_token:
        try:
          config = Config(host=os.environ.get('DATABRICKS_HOST'), token=user_token, auth_type='pat')
          w = WorkspaceClient(config=config)
          current_user = w.current_user.me()
          # Extract username from email (e.g., luca.milletti@databricks.com -> luca.milletti)
          username = current_user.user_name.split('@')[0] if current_user.user_name else 'unknown'
        except Exception:
          username = 'unknown'

      # Generate unique API ID
      api_id = f'api-{str(uuid.uuid4())[:8]}'

      # Get current timestamp
      created_at = datetime.utcnow().isoformat() + 'Z'
      modified_date = created_at

      # Initial status
      status = 'pending'
      validation_message = 'Awaiting validation'

      # Optionally validate the API using helper function
      if validate_after_register:
        print(f'🔍 Validating API endpoint: {api_endpoint}')
        validation_result = _validate_api_endpoint(api_endpoint, http_method, auth_type, token_info, timeout=10)
        status = validation_result['status']
        validation_message = validation_result['validation_message']

      # Escape single quotes in strings for SQL
      def escape_sql_string(s):
        return s.replace("'", "''") if s else ''

      # Build INSERT query
      insert_query = f"""
INSERT INTO luca_milletti.custom_mcp_server.api_registry
(api_id, api_name, description, user_who_requested, modified_date,
 api_endpoint, http_method, auth_type, token_info, request_params,
 status, validation_message, created_at)
VALUES (
  '{api_id}',
  '{escape_sql_string(api_name)}',
  '{escape_sql_string(description)}',
  '{escape_sql_string(username)}',
  '{modified_date}',
  '{escape_sql_string(api_endpoint)}',
  '{escape_sql_string(http_method.upper())}',
  '{escape_sql_string(auth_type)}',
  '{escape_sql_string(token_info)}',
  '{escape_sql_string(request_params)}',
  '{escape_sql_string(status)}',
  '{escape_sql_string(validation_message)}',
  '{created_at}'
)
"""

      # Execute the INSERT using the SQL helper
      result = _execute_sql_query(insert_query, warehouse_id, catalog=None, schema=None, limit=1)

      if result.get('success'):
        return {
          'success': True,
          'api_id': api_id,
          'api_name': api_name,
          'status': status,
          'user_who_requested': username,
          'validation_message': validation_message if validate_after_register else 'Not validated',
          'message': f'✅ Successfully registered API "{api_name}" with ID: {api_id}',
          'next_steps': [
            f'View your registered API using: check_api_registry(warehouse_id="{warehouse_id}")',
            f'Test the API using: call_api_endpoint(endpoint_url="{api_endpoint}")',
          ],
        }
      else:
        return {
          'success': False,
          'error': f"Failed to insert into registry: {result.get('error')}",
          'attempted_query': insert_query[:500],
        }

    except Exception as e:
      print(f'❌ Error registering API: {str(e)}')
      return {'success': False, 'error': f'Registration error: {str(e)}'}

  @mcp_server.tool
  def list_warehouses() -> dict:
    """List all SQL warehouses in the Databricks workspace.

    Returns:
        Dictionary containing list of warehouses with their details
    """
    try:
      # Initialize Databricks SDK with on-behalf-of authentication
      w = get_workspace_client()

      # List SQL warehouses
      warehouses = []
      for warehouse in w.warehouses.list():
        warehouses.append(
          {
            'id': warehouse.id,
            'name': warehouse.name,
            'state': warehouse.state.value if warehouse.state else 'UNKNOWN',
            'size': warehouse.cluster_size,
            'type': warehouse.warehouse_type.value if warehouse.warehouse_type else 'UNKNOWN',
            'creator': warehouse.creator_name if hasattr(warehouse, 'creator_name') else None,
            'auto_stop_mins': warehouse.auto_stop_mins
            if hasattr(warehouse, 'auto_stop_mins')
            else None,
          }
        )

      return {
        'success': True,
        'warehouses': warehouses,
        'count': len(warehouses),
        'message': f'Found {len(warehouses)} SQL warehouse(s)',
      }

    except Exception as e:
      print(f'❌ Error listing warehouses: {str(e)}')
      return {'success': False, 'error': f'Error: {str(e)}', 'warehouses': [], 'count': 0}

  @mcp_server.tool
  def list_dbfs_files(path: str = '/') -> dict:
    """List files and directories in DBFS (Databricks File System).

    Args:
        path: DBFS path to list (default: '/')

    Returns:
        Dictionary with file listings or error message
    """
    try:
      # Initialize Databricks SDK with on-behalf-of authentication
      w = get_workspace_client()

      # List files in DBFS
      files = []
      for file_info in w.dbfs.list(path):
        files.append(
          {
            'path': file_info.path,
            'is_dir': file_info.is_dir,
            'size': file_info.file_size if not file_info.is_dir else None,
            'modification_time': file_info.modification_time,
          }
        )

      return {
        'success': True,
        'path': path,
        'files': files,
        'count': len(files),
        'message': f'Listed {len(files)} item(s) in {path}',
      }

    except Exception as e:
      print(f'❌ Error listing DBFS files: {str(e)}')
      return {'success': False, 'error': f'Error: {str(e)}', 'files': [], 'count': 0}