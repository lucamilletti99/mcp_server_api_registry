/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class DatabaseService {
    /**
     * List Warehouses
     * List all SQL warehouses in the Databricks workspace.
     *
     * Returns:
     * Dictionary with list of warehouses and their details
     * @returns any Successful Response
     * @throws ApiError
     */
    public static listWarehousesApiDbWarehousesGet(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/db/warehouses',
        });
    }
    /**
     * List Catalogs
     * List all catalogs in the Databricks workspace.
     *
     * Returns:
     * Dictionary with list of catalogs
     * @returns any Successful Response
     * @throws ApiError
     */
    public static listCatalogsApiDbCatalogsGet(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/db/catalogs',
        });
    }
    /**
     * List Schemas
     * List all schemas in a specific catalog.
     *
     * Args:
     * catalog_name: Name of the catalog
     *
     * Returns:
     * Dictionary with list of schemas in the catalog
     * @param catalogName
     * @returns any Successful Response
     * @throws ApiError
     */
    public static listSchemasApiDbSchemasCatalogNameGet(
        catalogName: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/db/schemas/{catalog_name}',
            path: {
                'catalog_name': catalogName,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List All Catalog Schemas
     * List all catalog.schema combinations available in the workspace.
     *
     * This is useful for populating a dropdown that shows catalog_name.schema_name format.
     *
     * Returns:
     * Dictionary with list of all catalog.schema combinations
     * @returns any Successful Response
     * @throws ApiError
     */
    public static listAllCatalogSchemasApiDbCatalogSchemasGet(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/db/catalog-schemas',
        });
    }
}
