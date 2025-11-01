/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class DebugService {
    /**
     * Get Auth Status
     * Debug endpoint to show current authentication status.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getAuthStatusApiDebugAuthStatusGet(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/debug/auth-status',
        });
    }
}
