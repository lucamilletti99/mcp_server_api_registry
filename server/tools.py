"""MCP Tools for Databricks operations."""

import os

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
    # Fixed query for the API registry table
    query = 'SELECT * FROM luca_milletti.custom_mcp_server.api_registry'

    # Use the catalog and schema explicitly
    catalog = 'luca_milletti'
    schema = 'custom_mcp_server'

    # Execute the query using the helper function
    result = _execute_sql_query(query, warehouse_id, catalog, schema, limit)

    # Add context to the result
    if result.get('success'):
      result['registry_info'] = {
        'catalog': catalog,
        'schema': schema,
        'table': 'api_registry',
        'description': 'Databricks API Registry containing all available API endpoints',
      }

    return result

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