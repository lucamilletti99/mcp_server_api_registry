/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response from the agent.
 */
export type AgentChatResponse = {
    response: string;
    iterations: number;
    tool_calls: Array<Record<string, any>>;
    trace_id?: (string | null);
};

