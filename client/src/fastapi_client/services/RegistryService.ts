/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { APIRegistryResponse } from '../models/APIRegistryResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class RegistryService {
    /**
     * List Apis
     * List all registered APIs from the registry table.
     *
     * Args:
     * catalog: Catalog name
     * schema: Schema name
     * warehouse_id: SQL warehouse ID
     * request: Request object for authentication
     *
     * Returns:
     * List of registered APIs
     * @param catalog
     * @param schema
     * @param warehouseId
     * @returns APIRegistryResponse Successful Response
     * @throws ApiError
     */
    public static listApisApiRegistryListGet(
        catalog: string,
        schema: string,
        warehouseId: string,
    ): CancelablePromise<APIRegistryResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/registry/list',
            query: {
                'catalog': catalog,
                'schema': schema,
                'warehouse_id': warehouseId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Api
     * Update an existing API in the registry.
     *
     * Args:
     * api_id: ID of the API to update
     * catalog: Catalog name
     * schema: Schema name
     * warehouse_id: SQL warehouse ID
     * api_name: New name
     * description: New description
     * api_endpoint: New endpoint URL
     * request: Request object for authentication
     * documentation_url: Optional documentation URL
     *
     * Returns:
     * Success message
     * @param apiId
     * @param catalog
     * @param schema
     * @param warehouseId
     * @param apiName
     * @param description
     * @param apiEndpoint
     * @param documentationUrl
     * @returns any Successful Response
     * @throws ApiError
     */
    public static updateApiApiRegistryUpdateApiIdPost(
        apiId: string,
        catalog: string,
        schema: string,
        warehouseId: string,
        apiName: string,
        description: string,
        apiEndpoint: string,
        documentationUrl?: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/registry/update/{api_id}',
            path: {
                'api_id': apiId,
            },
            query: {
                'catalog': catalog,
                'schema': schema,
                'warehouse_id': warehouseId,
                'api_name': apiName,
                'description': description,
                'api_endpoint': apiEndpoint,
                'documentation_url': documentationUrl,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Api
     * Delete an API from the registry.
     *
     * Args:
     * api_id: ID of the API to delete
     * catalog: Catalog name
     * schema: Schema name
     * warehouse_id: SQL warehouse ID
     * request: Request object for authentication
     *
     * Returns:
     * Success message
     * @param apiId
     * @param catalog
     * @param schema
     * @param warehouseId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static deleteApiApiRegistryDeleteApiIdDelete(
        apiId: string,
        catalog: string,
        schema: string,
        warehouseId: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/registry/delete/{api_id}',
            path: {
                'api_id': apiId,
            },
            query: {
                'catalog': catalog,
                'schema': schema,
                'warehouse_id': warehouseId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
