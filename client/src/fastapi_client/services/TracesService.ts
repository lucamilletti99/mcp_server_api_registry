/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Trace } from '../models/Trace';
import type { TraceListResponse } from '../models/TraceListResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class TracesService {
    /**
     * List Traces
     * List recent traces.
     *
     * Args:
     * limit: Maximum number of traces to return (default: 50)
     * offset: Number of traces to skip (default: 0)
     *
     * Returns:
     * List of traces with metadata
     * @param limit
     * @param offset
     * @returns TraceListResponse Successful Response
     * @throws ApiError
     */
    public static listTracesApiTracesListGet(
        limit: number = 50,
        offset?: number,
    ): CancelablePromise<TraceListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/traces/list',
            query: {
                'limit': limit,
                'offset': offset,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Trace
     * Get detailed trace information by ID.
     *
     * Args:
     * trace_id: The trace ID to retrieve
     *
     * Returns:
     * Complete trace with all spans and metadata
     * @param traceId
     * @returns Trace Successful Response
     * @throws ApiError
     */
    public static getTraceApiTracesTraceIdGet(
        traceId: string,
    ): CancelablePromise<Trace> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/traces/{trace_id}',
            path: {
                'trace_id': traceId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
