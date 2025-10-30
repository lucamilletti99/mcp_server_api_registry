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
