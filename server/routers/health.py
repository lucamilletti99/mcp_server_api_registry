"""Health check router that exposes MCP health information."""

import os
from typing import Any, Dict

from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
from fastapi import APIRouter, Request
from fastmcp.server.dependencies import get_http_headers

router = APIRouter()


@router.get('/health')
async def get_health(request: Request) -> Dict[str, Any]:
  """Get MCP health check information including OBO auth status.

  This endpoint returns detailed information about:
  - Overall service health
  - Authentication mode (on-behalf-of or service-principal)
  - Authenticated user details (if OBO auth is active)
  - Available HTTP headers

  Returns:
      Dictionary with health status and authentication details
  """
  # Try to get user token from request headers (on-behalf-of authentication)
  user_token = request.headers.get('x-forwarded-access-token')
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
    'headers_present': list(request.headers.keys()),
  }
