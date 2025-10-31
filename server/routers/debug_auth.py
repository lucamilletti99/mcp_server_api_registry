"""Debug authentication endpoint to diagnose OBO issues."""

from fastapi import APIRouter, Request
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
import os

router = APIRouter()


@router.get('/auth-status')
async def get_auth_status(request: Request):
    """Debug endpoint to show current authentication status."""

    host = os.environ.get('DATABRICKS_HOST')
    user_token = request.headers.get('x-forwarded-access-token')

    status = {
        'has_databricks_host': bool(host),
        'databricks_host': host,
        'has_user_token': bool(user_token),
        'user_token_preview': user_token[:20] + '...' if user_token else None,
        'environment_auth_type': 'OBO' if user_token else 'Service Principal',
    }

    # Try to authenticate with user token
    if user_token:
        try:
            config = Config(host=host, token=user_token, auth_type='pat')
            user_client = WorkspaceClient(config=config)

            # Try to list warehouses
            try:
                warehouses = list(user_client.warehouses.list())
                status['user_warehouse_count'] = len(warehouses)
                status['user_warehouse_access'] = True
                status['user_warehouses'] = [
                    {'id': w.id, 'name': w.name, 'state': str(w.state)}
                    for w in warehouses[:5]  # Show first 5
                ]
            except Exception as e:
                status['user_warehouse_access'] = False
                status['user_warehouse_error'] = str(e)
        except Exception as e:
            status['user_auth_error'] = str(e)

    # Try service principal
    try:
        sp_client = WorkspaceClient(host=host)
        try:
            sp_warehouses = list(sp_client.warehouses.list())
            status['service_principal_warehouse_count'] = len(sp_warehouses)
            status['service_principal_warehouse_access'] = True
            status['service_principal_warehouses'] = [
                {'id': w.id, 'name': w.name, 'state': str(w.state)}
                for w in sp_warehouses[:5]
            ]
        except Exception as e:
            status['service_principal_warehouse_access'] = False
            status['service_principal_warehouse_error'] = str(e)
    except Exception as e:
        status['service_principal_auth_error'] = str(e)

    # Check all headers for debugging
    status['request_headers'] = {
        k: v for k, v in request.headers.items()
        if k.lower() in ['x-forwarded-access-token', 'authorization', 'user-agent']
    }

    return status
