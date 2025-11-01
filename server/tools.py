"""MCP Tools for Databricks operations."""

import json
import os
import re
import uuid
from datetime import datetime
from typing import Dict, List
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
from fastmcp.server.dependencies import get_http_headers
from contextvars import ContextVar

# Context variable to store user token for OBO authentication
# This is set by execute_mcp_tool() before calling tools
_user_token_context: ContextVar[str | None] = ContextVar('user_token', default=None)


def get_workspace_client() -> WorkspaceClient:
  """Get a WorkspaceClient with on-behalf-of user authentication.

  Falls back to OAuth service principal authentication if:
  - User token is not available
  - User has no access to SQL warehouses

  Returns:
      WorkspaceClient configured with appropriate authentication
  """
  host = os.environ.get('DATABRICKS_HOST')

  # Try to get user token from multiple sources (in order of preference)
  # 1. First try the context variable (set by execute_mcp_tool)
  user_token = _user_token_context.get()
  if user_token:
    print(f'[get_workspace_client] ✅ Got token from context variable')
  else:
    # 2. Fallback to request headers (for direct HTTP calls to tools)
    headers = get_http_headers()
    print(f'[get_workspace_client] Headers received: {list(headers.keys())}')
    user_token = headers.get('x-forwarded-access-token')

  print(f'[get_workspace_client] User token found: {bool(user_token)}')
  if user_token:
    print(f'[get_workspace_client] Token preview: {user_token[:20]}...')

  if user_token:
    # Try on-behalf-of authentication with user's token
    print(f'🔐 Attempting OBO authentication for user')
    config = Config(host=host, token=user_token, auth_type='pat')
    user_client = WorkspaceClient(config=config)

    # Verify user has access to SQL warehouses
    has_warehouse_access = False

    try:
      warehouses = list(user_client.warehouses.list())
      if warehouses:
        has_warehouse_access = True
        print(f'✅ User has access to {len(warehouses)} warehouse(s)')
    except Exception as e:
      print(f'⚠️  User cannot list warehouses: {str(e)}')

    # If user has warehouse access, use OBO; otherwise fallback to service principal
    if has_warehouse_access:
      print(f'✅ Using OBO authentication - user has warehouse access')
      return user_client
    else:
      print(f'⚠️  User has no warehouse access, falling back to service principal')
      return WorkspaceClient(host=host)
  else:
    # Fall back to OAuth service principal authentication
    # WorkspaceClient will automatically use DATABRICKS_CLIENT_ID and DATABRICKS_CLIENT_SECRET
    # which are injected by Databricks Apps platform
    print(f'⚠️  No user token found, falling back to service principal')
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


def _fetch_api_documentation(url: str, timeout: int = 10) -> Dict:
  """Fetch and parse API documentation from a URL.

  Args:
      url: URL of the API documentation page
      timeout: Request timeout in seconds

  Returns:
      Dictionary with documentation content and extracted endpoints
  """
  try:
    print(f'📚 Fetching API documentation from: {url}')
    response = requests.get(url, timeout=timeout)

    if response.status_code != 200:
      return {
        'success': False,
        'error': f'Failed to fetch documentation (status {response.status_code})'
      }

    content = response.text

    # Extract common API patterns from documentation
    endpoints = []

    # Look for URL patterns (http/https URLs)
    url_pattern = r'https?://[^\s<>"\']+(?:/[^\s<>"\']*)?'
    found_urls = re.findall(url_pattern, content)

    # Look for API endpoint paths
    path_pattern = r'/api/[^\s<>"\']+|/v\d+/[^\s<>"\']+|/[a-z_]+/[a-z_]+'
    found_paths = re.findall(path_pattern, content)

    # Look for parameter names (common API parameter patterns)
    param_patterns = ['apikey', 'api_key', 'token', 'function', 'symbol', 'query']
    found_params = []
    for param in param_patterns:
      if param in content.lower():
        found_params.append(param)

    # Extract code examples (often in <code>, <pre>, or ``` blocks)
    code_pattern = r'<code>(.*?)</code>|<pre>(.*?)</pre>|```(.*?)```'
    code_examples = re.findall(code_pattern, content, re.DOTALL)

    return {
      'success': True,
      'url': url,
      'content_preview': content[:1000],
      'found_urls': list(set(found_urls))[:10],
      'found_paths': list(set(found_paths))[:10],
      'found_params': found_params,
      'code_examples_count': len(code_examples),
      'content_length': len(content)
    }

  except Exception as e:
    print(f'❌ Error fetching documentation: {str(e)}')
    return {'success': False, 'error': f'Error: {str(e)}'}


def _try_common_endpoint_patterns(
  base_url: str, api_key: str = None, timeout: int = 10
) -> Dict:
  """Try common API endpoint patterns to discover working endpoints.

  Args:
      base_url: Base URL of the API (e.g., 'https://api.example.com')
      api_key: Optional API key for authentication
      timeout: Request timeout in seconds

  Returns:
      Dictionary with successful endpoints found
  """
  try:
    parsed = urlparse(base_url)
    base = f'{parsed.scheme}://{parsed.netloc}'

    # Common API endpoint patterns
    patterns = [
      '',  # Base URL itself
      '/api',
      '/api/v1',
      '/api/v2',
      '/v1',
      '/v2',
      '/search',
      '/query',
      '/data',
      '/status',
      '/health',
      '/docs',
      '/swagger',
    ]

    successful_endpoints = []

    print(f'🔍 Trying common endpoint patterns for: {base}')

    for pattern in patterns:
      test_url = base + pattern

      # Try different auth methods
      auth_attempts = [
        {'headers': {}, 'params': {}},  # No auth
      ]

      if api_key:
        auth_attempts.extend([
          {'headers': {'Authorization': f'Bearer {api_key}'}, 'params': {}},
          {'headers': {'X-API-Key': api_key}, 'params': {}},
          {'headers': {}, 'params': {'apikey': api_key}},
          {'headers': {}, 'params': {'api_key': api_key}},
        ])

      for attempt in auth_attempts:
        try:
          response = requests.get(
            test_url,
            headers=attempt['headers'],
            params=attempt['params'],
            timeout=timeout
          )

          if response.status_code == 200:
            try:
              data = response.json()
              successful_endpoints.append({
                'url': test_url,
                'status_code': 200,
                'auth_method': 'authenticated' if api_key and attempt['headers'] else 'none',
                'response_preview': json.dumps(data, indent=2)[:300]
              })
              print(f'✅ Found working endpoint: {test_url}')
              break  # Stop trying other auth methods for this pattern
            except Exception:
              # Not JSON, skip
              pass
        except Exception:
          continue

    return {
      'success': True,
      'base_url': base,
      'successful_endpoints': successful_endpoints,
      'count': len(successful_endpoints)
    }

  except Exception as e:
    print(f'❌ Error trying patterns: {str(e)}')
    return {'success': False, 'error': f'Error: {str(e)}'}


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
  def check_api_registry(
    warehouse_id: str,
    catalog: str,
    schema: str,
    limit: int = 100
  ) -> dict:
    """Check the Databricks API Registry to see all available API endpoints.

    This queries the api_registry table in the specified catalog.schema.

    Args:
        warehouse_id: SQL warehouse ID (required)
        catalog: Catalog name (required)
        schema: Schema name (required)
        limit: Maximum number of rows to return (default: 100)

    Returns:
        Dictionary with API registry results including:
        - List of all registered API endpoints
        - API endpoint names and descriptions
        - API configurations and metadata
        - Current status of each endpoint
    """
    if not catalog or not schema:
      return {
        'success': False,
        'error': 'catalog and schema parameters are required',
        'message': 'Please provide both catalog and schema parameters to locate the api_registry table',
      }

    # Build fully-qualified table name
    table_name = f'{catalog}.{schema}.api_registry'
    query = f'SELECT * FROM {table_name}'

    print(f'📊 Querying API registry table: {table_name}')

    # Don't pass catalog/schema to _execute_sql_query since we're using fully-qualified table name
    # Passing them would prepend USE CATALOG/USE SCHEMA which interferes with results
    result = _execute_sql_query(query, warehouse_id, catalog=None, schema=None, limit=limit)

    # Add context to the result
    if result.get('success'):
      result['registry_info'] = {
        'catalog': catalog,
        'schema': schema,
        'table': 'api_registry',
        'full_table_name': table_name,
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
    catalog: str,
    schema: str,
    documentation_url: str = None,
    http_method: str = 'GET',
    auth_type: str = 'none',
    token_info: str = '',
    request_params: str = '{}',
    validate_after_register: bool = True,
  ) -> dict:
    """Register a new API endpoint in the api_registry table.

    This tool adds a discovered API to your registry for tracking and reuse.
    It automatically uses your authenticated user identity and validates the API.

    Args:
        api_name: Unique name for the API (e.g., "alphavantage_intraday_stock")
        description: Description of what the API does
        api_endpoint: Full URL of the API endpoint
        warehouse_id: SQL warehouse ID to use for database operations
        catalog: Catalog name (required)
        schema: Schema name (required)
        documentation_url: Optional URL to API documentation for endpoint discovery
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
    if not catalog or not schema:
      return {
        'success': False,
        'error': 'catalog and schema parameters are required',
        'message': 'Please provide both catalog and schema parameters to locate the api_registry table',
      }

    # Build fully-qualified table name
    table_name = f'{catalog}.{schema}.api_registry'
    print(f'📝 Registering API in table: {table_name}')
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
          # Store full email (e.g., luca.milletti@databricks.com)
          username = current_user.user_name if current_user.user_name else 'unknown'
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

      # Build INSERT query with dynamic table name
      insert_query = f"""
INSERT INTO {table_name}
(api_id, api_name, description, user_who_requested, modified_date,
 api_endpoint, documentation_url, http_method, auth_type, token_info, request_params,
 status, validation_message, created_at)
VALUES (
  '{api_id}',
  '{escape_sql_string(api_name)}',
  '{escape_sql_string(description)}',
  '{escape_sql_string(username)}',
  '{modified_date}',
  '{escape_sql_string(api_endpoint)}',
  '{escape_sql_string(documentation_url) if documentation_url else 'NULL'}',
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

  @mcp_server.tool
  def fetch_api_documentation(documentation_url: str, timeout: int = 10) -> dict:
    """Fetch and parse API documentation from a URL.

    This tool automatically fetches API documentation pages and extracts
    useful information like endpoint URLs, parameters, and code examples.
    Use this when the user provides a documentation link.

    Args:
        documentation_url: URL of the API documentation page
        timeout: Request timeout in seconds (default: 10)

    Returns:
        Dictionary with:
        - success: Boolean indicating if fetch succeeded
        - content_preview: Preview of documentation content
        - found_urls: List of API URLs found in the documentation
        - found_paths: List of API endpoint paths found
        - found_params: List of common parameter names found
        - code_examples_count: Number of code examples in the docs
    """
    return _fetch_api_documentation(documentation_url, timeout)

  @mcp_server.tool
  def try_common_api_patterns(base_url: str, api_key: str = None, timeout: int = 10) -> dict:
    """Try common API endpoint patterns to discover working endpoints.

    This tool automatically tests common API patterns like /api, /v1, /search, etc.
    with different authentication methods to find working endpoints.

    Args:
        base_url: Base URL of the API (e.g., 'https://api.example.com')
        api_key: Optional API key for authentication
        timeout: Request timeout in seconds (default: 10)

    Returns:
        Dictionary with:
        - success: Boolean indicating if search succeeded
        - successful_endpoints: List of working endpoints found
        - count: Number of working endpoints discovered
    """
    return _try_common_endpoint_patterns(base_url, api_key, timeout)

  @mcp_server.tool
  def smart_register_api(
    api_name: str,
    description: str,
    endpoint_url: str,
    warehouse_id: str,
    catalog: str,
    schema: str,
    api_key: str = None,
    documentation_url: str = None,
  ) -> dict:
    """Smart one-step API registration with automatic discovery and validation.

    This tool simplifies the API registration process by:
    1. Optionally fetching documentation if provided
    2. Automatically trying common endpoint patterns
    3. Testing multiple authentication methods
    4. Discovering the best working configuration
    5. Registering the API in one step

    Use this tool to register an API with minimal user input required.

    Args:
        api_name: Unique name for the API (e.g., "sec_api_search")
        description: Description of what the API does
        endpoint_url: Base URL or specific endpoint URL to try
        warehouse_id: SQL warehouse ID for database operations
        catalog: Catalog name (required)
        schema: Schema name (required)
        api_key: Optional API key (will try multiple auth methods)
        documentation_url: Optional documentation URL to fetch additional info

    Returns:
        Dictionary with registration results and discovery insights
    """
    try:
      print(f'🚀 Smart registration starting for: {api_name}')

      # Step 1: Fetch documentation if provided
      doc_insights = None
      if documentation_url:
        print(f'📚 Fetching documentation...')
        doc_result = _fetch_api_documentation(documentation_url)
        if doc_result.get('success'):
          doc_insights = {
            'urls_found': len(doc_result.get('found_urls', [])),
            'params_found': doc_result.get('found_params', []),
          }

      # Step 2: Try common patterns to find working endpoints
      print(f'🔍 Discovering working endpoints...')
      pattern_result = _try_common_endpoint_patterns(endpoint_url, api_key)

      working_endpoint = None
      auth_method = 'none'
      final_api_key = ''

      if pattern_result.get('success') and pattern_result.get('successful_endpoints'):
        # Use the first successful endpoint found
        best_endpoint = pattern_result['successful_endpoints'][0]
        working_endpoint = best_endpoint['url']
        auth_method = 'api_key' if best_endpoint['auth_method'] == 'authenticated' else 'none'
        final_api_key = api_key if auth_method == 'api_key' else ''

        print(f'✅ Found working endpoint: {working_endpoint}')
      else:
        # No patterns worked, use the original endpoint
        print(f'🔍 No patterns matched, will register the original endpoint')
        working_endpoint = endpoint_url
        if api_key:
          auth_method = 'api_key'
          final_api_key = api_key

      # Step 3: Register the API using the helper logic
      print(f'📝 Registering API in registry...')

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
          # Store full email (e.g., luca.milletti@databricks.com)
          username = current_user.user_name if current_user.user_name else 'unknown'
        except Exception:
          username = 'unknown'

      # Generate unique API ID
      api_id = f'api-{str(uuid.uuid4())[:8]}'

      # Get current timestamp
      created_at = datetime.utcnow().isoformat() + 'Z'
      modified_date = created_at

      # Validate the API
      print(f'🔍 Validating API endpoint: {working_endpoint}')
      validation_result = _validate_api_endpoint(working_endpoint, 'GET', auth_method, final_api_key, timeout=10)
      status = validation_result['status']
      validation_message = validation_result['validation_message']

      # Escape single quotes in strings for SQL
      def escape_sql_string(s):
        return s.replace("'", "''") if s else ''

      # Build INSERT query
      table_name = f'{catalog}.{schema}.api_registry'
      insert_query = f"""
INSERT INTO {table_name}
(api_id, api_name, description, user_who_requested, modified_date,
 api_endpoint, documentation_url, http_method, auth_type, token_info, request_params,
 status, validation_message, created_at)
VALUES (
  '{api_id}',
  '{escape_sql_string(api_name)}',
  '{escape_sql_string(description)}',
  '{escape_sql_string(username)}',
  '{modified_date}',
  '{escape_sql_string(working_endpoint)}',
  '{escape_sql_string(documentation_url) if documentation_url else 'NULL'}',
  'GET',
  '{escape_sql_string(auth_method)}',
  '{escape_sql_string(final_api_key)}',
  '{{}}',
  '{escape_sql_string(status)}',
  '{escape_sql_string(validation_message)}',
  '{created_at}'
)
"""

      # Execute the INSERT using the SQL helper
      result = _execute_sql_query(insert_query, warehouse_id, catalog=None, schema=None, limit=1)

      if not result.get('success'):
        registration_result = {
          'success': False,
          'error': f"Failed to insert into registry: {result.get('error')}",
        }
      else:
        registration_result = {
          'success': True,
          'api_id': api_id,
          'api_name': api_name,
          'status': status,
          'user_who_requested': username,
          'validation_message': validation_message,
          'message': f'✅ Successfully registered API "{api_name}" with ID: {api_id}',
        }

      # Add discovery insights to the result
      if registration_result.get('success'):
        registration_result['discovery_insights'] = {
          'documentation_fetched': doc_insights is not None,
          'doc_insights': doc_insights,
          'patterns_tried': pattern_result.get('count', 0),
          'working_endpoints_found': len(pattern_result.get('successful_endpoints', [])),
          'auth_method_used': auth_method,
          'final_endpoint': working_endpoint,
        }

      return registration_result

    except Exception as e:
      print(f'❌ Error in smart registration: {str(e)}')
      return {
        'success': False,
        'error': f'Smart registration error: {str(e)}',
        'next_steps': [
          'Try using register_api_in_registry directly with exact endpoint URL',
          'Use discover_api_endpoint first to validate the endpoint',
        ],
      }

  @mcp_server.tool
  def review_api_documentation_for_endpoints(
    api_id: str,
    warehouse_id: str,
    catalog: str,
    schema: str,
    api_key: str = None,
  ) -> dict:
    """Review an API's documentation to discover new endpoints.

    This tool fetches the documentation URL stored in the registry for a specific API,
    parses the documentation, and attempts to discover additional endpoints that could
    be added to the registry.

    Args:
        api_id: The ID of the API in the registry to review
        warehouse_id: SQL warehouse ID to query the registry
        catalog: Catalog name (required)
        schema: Schema name (required)
        api_key: Optional API key to test discovered endpoints

    Returns:
        Dictionary with:
        - success: Boolean indicating if review succeeded
        - api_info: Information about the API from registry
        - documentation_url: The documentation URL that was reviewed
        - documentation_insights: Parsed information from documentation
        - discovered_endpoints: List of potential endpoints found
        - tested_endpoints: Results from testing discovered endpoints
        - next_steps: Recommendations for registering new endpoints
    """
    try:
      if not catalog or not schema:
        return {
          'success': False,
          'error': 'catalog and schema parameters are required',
        }

      # Step 1: Query the registry to get the API details including documentation_url
      table_name = f'{catalog}.{schema}.api_registry'
      query = f"""
        SELECT api_id, api_name, description, api_endpoint, documentation_url, auth_type, token_info
        FROM {table_name}
        WHERE api_id = '{api_id}'
      """

      print(f'📊 Fetching API details from registry: {api_id}')
      result = _execute_sql_query(query, warehouse_id, catalog=None, schema=None, limit=1)

      if not result.get('success') or not result.get('data', {}).get('rows'):
        return {
          'success': False,
          'error': f'API with id "{api_id}" not found in registry',
          'next_steps': ['Verify the api_id is correct', 'Use check_api_registry to list all APIs'],
        }

      # Get API details
      api_row = result['data']['rows'][0]
      api_name = api_row.get('api_name')
      documentation_url = api_row.get('documentation_url')
      base_endpoint = api_row.get('api_endpoint')

      if not documentation_url:
        return {
          'success': False,
          'error': f'API "{api_name}" has no documentation_url in the registry',
          'next_steps': [
            'Add a documentation_url to this API using update_api endpoint',
            'Or provide documentation URL when registering new APIs',
          ],
        }

      print(f'📚 Reviewing documentation for API: {api_name}')
      print(f'📄 Documentation URL: {documentation_url}')

      # Step 2: Fetch and parse the documentation
      doc_result = _fetch_api_documentation(documentation_url)

      if not doc_result.get('success'):
        return {
          'success': False,
          'error': f"Failed to fetch documentation: {doc_result.get('error')}",
          'documentation_url': documentation_url,
        }

      # Step 3: Try to discover endpoints from the documentation URLs
      discovered_endpoints = []
      tested_endpoints = []

      # Get unique URLs from documentation
      found_urls = doc_result.get('found_urls', [])[:10]  # Limit to first 10 URLs
      found_paths = doc_result.get('found_paths', [])[:10]

      print(f'🔍 Found {len(found_urls)} URLs and {len(found_paths)} paths in documentation')

      # Use api_key from registry if not provided
      if not api_key and api_row.get('token_info'):
        api_key = api_row.get('token_info')
        print(f'🔑 Using API key from registry')

      # Try discovered URLs
      for url in found_urls:
        discovered_endpoints.append({
          'type': 'url',
          'endpoint': url,
          'source': 'documentation',
        })

      # Try combining base endpoint with discovered paths
      if base_endpoint:
        from urllib.parse import urlparse
        parsed_base = urlparse(base_endpoint)
        base_url = f'{parsed_base.scheme}://{parsed_base.netloc}'

        for path in found_paths:
          full_url = base_url + path
          discovered_endpoints.append({
            'type': 'path',
            'endpoint': full_url,
            'source': 'documentation + base_url',
          })

      # Step 4: Test a few discovered endpoints
      print(f'🧪 Testing discovered endpoints (up to 5)...')
      endpoints_to_test = discovered_endpoints[:5]

      for endpoint_info in endpoints_to_test:
        endpoint_url = endpoint_info['endpoint']
        print(f'  Testing: {endpoint_url}')

        try:
          # Try calling the endpoint with API key if available
          headers_json = None
          if api_key:
            # Try common API key header patterns
            headers_json = json.dumps({'Authorization': f'Bearer {api_key}'})

          test_result = call_api_endpoint(endpoint_url, headers=headers_json)

          tested_endpoints.append({
            'endpoint': endpoint_url,
            'source': endpoint_info['source'],
            'status_code': test_result.get('status_code'),
            'is_healthy': test_result.get('is_healthy', False),
            'success': test_result.get('success', False),
            'response_preview': test_result.get('response_preview', '')[:200],
          })

        except Exception as e:
          tested_endpoints.append({
            'endpoint': endpoint_url,
            'source': endpoint_info['source'],
            'error': str(e),
            'success': False,
          })

      # Build response with insights
      working_endpoints = [ep for ep in tested_endpoints if ep.get('is_healthy')]

      return {
        'success': True,
        'api_info': {
          'api_id': api_id,
          'api_name': api_name,
          'base_endpoint': base_endpoint,
        },
        'documentation_url': documentation_url,
        'documentation_insights': {
          'urls_found': len(found_urls),
          'paths_found': len(found_paths),
          'parameters_found': doc_result.get('found_params', []),
          'content_length': doc_result.get('content_length'),
        },
        'discovered_endpoints': discovered_endpoints[:20],  # Return up to 20 discovered
        'discovered_count': len(discovered_endpoints),
        'tested_endpoints': tested_endpoints,
        'working_endpoints': working_endpoints,
        'working_count': len(working_endpoints),
        'next_steps': [
          f'✅ Found {len(discovered_endpoints)} potential endpoints in documentation',
          f'✅ Tested {len(tested_endpoints)} endpoints, {len(working_endpoints)} are working',
          'Consider registering working endpoints using register_api_in_registry',
          'Test additional discovered endpoints using call_api_endpoint',
        ] if working_endpoints else [
          f'Found {len(discovered_endpoints)} potential endpoints in documentation',
          'Most endpoints require additional configuration or authentication',
          'Review the documentation_insights for parameter requirements',
          'Try testing endpoints manually with call_api_endpoint',
        ],
      }

    except Exception as e:
      print(f'❌ Error reviewing API documentation: {str(e)}')
      return {
        'success': False,
        'error': f'Review error: {str(e)}',
        'next_steps': [
          'Verify the api_id exists in the registry',
          'Check if the documentation_url is accessible',
        ],
      }