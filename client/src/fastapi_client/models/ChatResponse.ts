/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ToolCall } from './ToolCall';
/**
 * Response from the chat endpoint.
 */
export type ChatResponse = {
    role: string;
    content?: (string | null);
    tool_calls?: (Array<ToolCall> | null);
    finish_reason: string;
};

