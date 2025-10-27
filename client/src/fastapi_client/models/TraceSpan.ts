/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Model for a trace span.
 */
export type TraceSpan = {
    span_id: string;
    name: string;
    start_time_ms: number;
    end_time_ms?: (number | null);
    duration_ms?: (number | null);
    parent_id?: (string | null);
    attributes?: Record<string, any>;
    inputs?: (Record<string, any> | null);
    outputs?: (Record<string, any> | null);
    span_type?: string;
    status?: string;
};

