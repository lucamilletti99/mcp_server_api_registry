/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class HealthService {
    /**
     * Get Health
     * Get MCP health check information including OBO auth status.
     *
     * This endpoint returns detailed information about:
     * - Overall service health
     * - Authentication mode (on-behalf-of or service-principal)
     * - Authenticated user details (if OBO auth is active)
     * - Available HTTP headers
     *
     * Returns:
     * Dictionary with health status and authentication details
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getHealthApiHealthGet(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/health',
        });
    }
}
