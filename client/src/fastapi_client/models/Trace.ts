/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TraceSpan } from './TraceSpan';
/**
 * Model for a complete trace.
 */
export type Trace = {
    request_id: string;
    trace_id: string;
    timestamp_ms: number;
    execution_time_ms?: (number | null);
    status?: string;
    spans?: Array<TraceSpan>;
    request_metadata?: Record<string, any>;
};

