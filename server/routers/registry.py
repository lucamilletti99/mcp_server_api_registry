"""API Registry router - manage registered APIs."""

import os
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
from databricks.sdk.service.sql import StatementState

router = APIRouter()


class RegisteredAPI(BaseModel):
    """Model for a registered API."""
    api_id: str
    api_name: str
    description: Optional[str] = None
    api_endpoint: str
    http_method: str = 'GET'
    auth_type: str = 'none'
    status: str = 'pending'
    user_who_requested: Optional[str] = None
    created_at: Optional[str] = None
    modified_date: Optional[str] = None
    last_validated: Optional[str] = None


class APIRegistryResponse(BaseModel):
    """Response containing list of registered APIs."""
    apis: List[RegisteredAPI]
    count: int


def get_workspace_client(request: Request = None) -> WorkspaceClient:
    """Get authenticated Databricks workspace client.

    Args:
        request: FastAPI Request object to extract user token from

    Returns:
        WorkspaceClient configured with appropriate authentication
    """
    host = os.environ.get('DATABRICKS_HOST')

    # Try to get user token from request headers (on-behalf-of authentication)
    user_token = None
    if request:
        user_token = request.headers.get('x-forwarded-access-token')

    if user_token:
        # Use on-behalf-of authentication with user's token
        print(f"🔐 Using OBO authentication for user")
        config = Config(host=host, token=user_token, auth_type='pat')
        return WorkspaceClient(config=config)
    else:
        # Fall back to OAuth service principal authentication
        print(f"⚠️  No user token found, falling back to service principal")
        return WorkspaceClient(host=host)


def get_default_warehouse_id(ws: WorkspaceClient) -> Optional[str]:
    """Get the first available SQL warehouse."""
    try:
        warehouses = list(ws.warehouses.list())
        if warehouses:
            return warehouses[0].id
    except Exception as e:
        print(f"Failed to list warehouses: {e}")
    return None


@router.get('/list', response_model=APIRegistryResponse)
async def list_apis(
    catalog: str,
    schema: str,
    warehouse_id: str,
    request: Request
) -> APIRegistryResponse:
    """List all registered APIs from the registry table.

    Args:
        catalog: Catalog name
        schema: Schema name
        warehouse_id: SQL warehouse ID
        request: Request object for authentication

    Returns:
        List of registered APIs
    """
    try:
        ws = get_workspace_client(request)

        # Build fully-qualified table name
        table_name = f'{catalog}.{schema}.api_registry'

        # Query the registry table
        query = f"""
        SELECT
            api_id,
            api_name,
            description,
            api_endpoint,
            http_method,
            auth_type,
            status,
            user_who_requested,
            created_at,
            modified_date,
            validation_message as last_validated
        FROM {table_name}
        ORDER BY modified_date DESC
        """

        # Execute query
        statement = ws.statement_execution.execute_statement(
            warehouse_id=warehouse_id,
            statement=query,
            wait_timeout='30s'
        )

        # Wait for completion
        if statement.status.state != StatementState.SUCCEEDED:
            # Check if it's a table not found error
            error_message = statement.status.error.message if statement.status.error else 'Unknown error'

            if 'TABLE_OR_VIEW_NOT_FOUND' in error_message or 'does not exist' in error_message.lower():
                raise HTTPException(
                    status_code=404,
                    detail=f'No api_registry table exists in {catalog}.{schema}'
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f'Query failed: {error_message}'
                )

        # Parse results
        apis = []
        if statement.result and statement.result.data_array:
            # Get column names
            columns = [col.name for col in statement.manifest.schema.columns]

            # Parse each row
            for row in statement.result.data_array:
                api_data = {}
                for i, value in enumerate(row):
                    if i < len(columns):
                        api_data[columns[i]] = value

                apis.append(RegisteredAPI(**api_data))

        return APIRegistryResponse(
            apis=apis,
            count=len(apis)
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(f"Failed to list APIs: {e}")
        import traceback
        traceback.print_exc()

        # Check if it's a table not found error in the exception message
        error_str = str(e)
        if 'TABLE_OR_VIEW_NOT_FOUND' in error_str or 'does not exist' in error_str.lower():
            raise HTTPException(
                status_code=404,
                detail=f'No api_registry table exists in {catalog}.{schema}'
            )

        raise HTTPException(
            status_code=500,
            detail=f'Failed to list APIs: {str(e)}'
        )


@router.post('/update/{api_id}')
async def update_api(
    api_id: str,
    catalog: str,
    schema: str,
    warehouse_id: str,
    api_name: str,
    description: str,
    api_endpoint: str,
    request: Request
):
    """Update an existing API in the registry.

    Args:
        api_id: ID of the API to update
        catalog: Catalog name
        schema: Schema name
        warehouse_id: SQL warehouse ID
        api_name: New name
        description: New description
        api_endpoint: New endpoint URL
        request: Request object for authentication

    Returns:
        Success message
    """
    try:
        ws = get_workspace_client(request)

        # Build fully-qualified table name
        table_name = f'{catalog}.{schema}.api_registry'

        # Update query
        query = f"""
        UPDATE {table_name}
        SET
            api_name = '{api_name}',
            description = '{description}',
            api_endpoint = '{api_endpoint}',
            modified_date = CURRENT_TIMESTAMP()
        WHERE api_id = '{api_id}'
        """

        # Execute update
        statement = ws.statement_execution.execute_statement(
            warehouse_id=warehouse_id,
            statement=query,
            wait_timeout='30s'
        )

        if statement.status.state != StatementState.SUCCEEDED:
            raise HTTPException(
                status_code=500,
                detail=f'Update failed: {statement.status.state}'
            )

        return {"message": "API updated successfully"}

    except Exception as e:
        print(f"Failed to update API: {e}")
        raise HTTPException(
            status_code=500,
            detail=f'Failed to update API: {str(e)}'
        )


@router.delete('/delete/{api_id}')
async def delete_api(
    api_id: str,
    catalog: str,
    schema: str,
    warehouse_id: str,
    request: Request
):
    """Delete an API from the registry.

    Args:
        api_id: ID of the API to delete
        catalog: Catalog name
        schema: Schema name
        warehouse_id: SQL warehouse ID
        request: Request object for authentication

    Returns:
        Success message
    """
    try:
        ws = get_workspace_client(request)

        # Build fully-qualified table name
        table_name = f'{catalog}.{schema}.api_registry'

        # Delete query
        query = f"""
        DELETE FROM {table_name}
        WHERE api_id = '{api_id}'
        """

        # Execute delete
        statement = ws.statement_execution.execute_statement(
            warehouse_id=warehouse_id,
            statement=query,
            wait_timeout='30s'
        )

        if statement.status.state != StatementState.SUCCEEDED:
            raise HTTPException(
                status_code=500,
                detail=f'Delete failed: {statement.status.state}'
            )

        return {"message": "API deleted successfully"}

    except Exception as e:
        print(f"Failed to delete API: {e}")
        raise HTTPException(
            status_code=500,
            detail=f'Failed to delete API: {str(e)}'
        )
