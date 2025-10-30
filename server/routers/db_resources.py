"""Database resources router for listing warehouses, catalogs, and schemas."""

import os
from typing import Any, Dict, List

from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
from fastapi import APIRouter, HTTPException
from fastmcp.server.dependencies import get_http_headers
from pydantic import BaseModel

router = APIRouter()


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
        config = Config(host=host, token=user_token, auth_type='pat')
        return WorkspaceClient(config=config)
    else:
        # Fall back to OAuth service principal authentication
        return WorkspaceClient(host=host)


class Warehouse(BaseModel):
    """SQL Warehouse information."""

    id: str
    name: str
    state: str
    size: str | None = None
    type: str | None = None


class Catalog(BaseModel):
    """Catalog information."""

    name: str
    comment: str | None = None


class Schema(BaseModel):
    """Schema information."""

    name: str
    catalog_name: str
    comment: str | None = None


class CatalogSchema(BaseModel):
    """Combined catalog.schema information."""

    catalog_name: str
    schema_name: str
    full_name: str
    comment: str | None = None


@router.get('/warehouses')
async def list_warehouses() -> Dict[str, Any]:
    """List all SQL warehouses in the Databricks workspace.

    Returns:
        Dictionary with list of warehouses and their details
    """
    try:
        w = get_workspace_client()

        warehouses = []
        for warehouse in w.warehouses.list():
            warehouses.append(
                Warehouse(
                    id=warehouse.id,
                    name=warehouse.name,
                    state=warehouse.state.value if warehouse.state else 'UNKNOWN',
                    size=warehouse.cluster_size,
                    type=warehouse.warehouse_type.value if warehouse.warehouse_type else None,
                )
            )

        return {'warehouses': [w.model_dump() for w in warehouses], 'count': len(warehouses)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to list warehouses: {str(e)}')


@router.get('/catalogs')
async def list_catalogs() -> Dict[str, Any]:
    """List all catalogs in the Databricks workspace.

    Returns:
        Dictionary with list of catalogs
    """
    try:
        w = get_workspace_client()

        catalogs = []
        for catalog in w.catalogs.list():
            catalogs.append(
                Catalog(
                    name=catalog.name,
                    comment=catalog.comment if hasattr(catalog, 'comment') else None,
                )
            )

        return {'catalogs': [c.model_dump() for c in catalogs], 'count': len(catalogs)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to list catalogs: {str(e)}')


@router.get('/schemas/{catalog_name}')
async def list_schemas(catalog_name: str) -> Dict[str, Any]:
    """List all schemas in a specific catalog.

    Args:
        catalog_name: Name of the catalog

    Returns:
        Dictionary with list of schemas in the catalog
    """
    try:
        w = get_workspace_client()

        schemas = []
        for schema in w.schemas.list(catalog_name=catalog_name):
            schemas.append(
                Schema(
                    name=schema.name,
                    catalog_name=catalog_name,
                    comment=schema.comment if hasattr(schema, 'comment') else None,
                )
            )

        return {'schemas': [s.model_dump() for s in schemas], 'catalog': catalog_name, 'count': len(schemas)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to list schemas: {str(e)}')


@router.get('/catalog-schemas')
async def list_all_catalog_schemas() -> Dict[str, Any]:
    """List all catalog.schema combinations available in the workspace.

    This is useful for populating a dropdown that shows catalog_name.schema_name format.

    Returns:
        Dictionary with list of all catalog.schema combinations
    """
    try:
        w = get_workspace_client()

        catalog_schemas = []

        # Iterate through all catalogs
        for catalog in w.catalogs.list():
            catalog_name = catalog.name

            # For each catalog, get all schemas
            try:
                for schema in w.schemas.list(catalog_name=catalog_name):
                    catalog_schemas.append(
                        CatalogSchema(
                            catalog_name=catalog_name,
                            schema_name=schema.name,
                            full_name=f'{catalog_name}.{schema.name}',
                            comment=schema.comment if hasattr(schema, 'comment') else None,
                        )
                    )
            except Exception as e:
                # Skip catalogs that can't be accessed
                print(f'Warning: Could not list schemas for catalog {catalog_name}: {str(e)}')
                continue

        return {'catalog_schemas': [cs.model_dump() for cs in catalog_schemas], 'count': len(catalog_schemas)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to list catalog schemas: {str(e)}')


@router.get('/validate-api-registry-table')
async def validate_api_registry_table(catalog: str, schema: str, warehouse_id: str) -> Dict[str, Any]:
    """Validate if api_registry table exists in the specified catalog.schema.

    Args:
        catalog: Catalog name
        schema: Schema name
        warehouse_id: SQL warehouse ID to execute the validation query

    Returns:
        Dictionary indicating if the table exists and any error messages
    """
    try:
        from databricks.sdk.service.sql import StatementState
        import time

        w = get_workspace_client()

        # Build table name
        table_name = f'{catalog}.{schema}.api_registry'

        # Try to query the table with LIMIT 0 to check existence without fetching data
        query = f'SELECT * FROM {table_name} LIMIT 0'

        print(f'🔍 Validating table existence: {table_name}')

        # Execute the statement
        statement = w.statement_execution.execute_statement(
            warehouse_id=warehouse_id, statement=query, wait_timeout='30s'
        )

        # Wait for completion
        max_wait = 30
        start_time = time.time()

        while statement.status.state in [StatementState.PENDING, StatementState.RUNNING]:
            if time.time() - start_time > max_wait:
                return {
                    'exists': False,
                    'error': 'Validation query timed out',
                    'table_name': table_name,
                    'message': f'Could not validate table {table_name} within {max_wait} seconds',
                }

            time.sleep(0.5)
            statement = w.statement_execution.get_statement(statement.statement_id)

        # Check final state
        if statement.status.state == StatementState.SUCCEEDED:
            return {
                'exists': True,
                'table_name': table_name,
                'catalog': catalog,
                'schema': schema,
                'message': f'Table {table_name} exists and is accessible',
            }
        else:
            error_message = statement.status.error.message if statement.status.error else 'Unknown error'

            # Check if it's a table not found error
            if 'TABLE_OR_VIEW_NOT_FOUND' in error_message or 'does not exist' in error_message.lower():
                return {
                    'exists': False,
                    'error': 'TABLE_NOT_FOUND',
                    'table_name': table_name,
                    'message': f'No api_registry table exists in {catalog}.{schema}',
                    'suggestion': f'Create the api_registry table in {catalog}.{schema} or select a different catalog.schema',
                }
            else:
                return {
                    'exists': False,
                    'error': error_message,
                    'table_name': table_name,
                    'message': f'Error validating table: {error_message}',
                }

    except Exception as e:
        error_str = str(e)

        # Check if it's a table not found error
        if 'TABLE_OR_VIEW_NOT_FOUND' in error_str or 'does not exist' in error_str.lower():
            return {
                'exists': False,
                'error': 'TABLE_NOT_FOUND',
                'table_name': f'{catalog}.{schema}.api_registry',
                'message': f'No api_registry table exists in {catalog}.{schema}',
                'suggestion': f'Create the api_registry table in {catalog}.{schema} or select a different catalog.schema',
            }

        return {
            'exists': False,
            'error': str(e),
            'table_name': f'{catalog}.{schema}.api_registry',
            'message': f'Failed to validate table: {str(e)}',
        }
