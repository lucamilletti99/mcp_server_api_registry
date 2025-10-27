/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AgentChatRequest } from '../models/AgentChatRequest';
import type { AgentChatResponse } from '../models/AgentChatResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AgentService {
    /**
     * Agent Chat
     * Chat with the agent using MCP orchestration.
     *
     * This endpoint uses the notebook agent pattern under the hood.
     * The frontend just sends messages and gets responses back.
     *
     * Args:
     * chat_request: Chat request with messages and model
     * request: FastAPI Request object for on-behalf-of auth
     *
     * Returns:
     * Agent response with tool call traces
     * @param requestBody
     * @returns AgentChatResponse Successful Response
     * @throws ApiError
     */
    public static agentChatApiAgentChatPost(
        requestBody: AgentChatRequest,
    ): CancelablePromise<AgentChatResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/agent/chat',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List Agent Tools
     * List available tools from MCP server.
     *
     * Returns:
     * Dictionary with tools list
     * @returns any Successful Response
     * @throws ApiError
     */
    public static listAgentToolsApiAgentToolsGet(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/agent/tools',
        });
    }
    /**
     * Reload Tools
     * Force reload tools from MCP server.
     *
     * Useful when you deploy new tools to the MCP server.
     *
     * Returns:
     * Dictionary with reloaded tools
     * @returns any Successful Response
     * @throws ApiError
     */
    public static reloadToolsApiAgentToolsReloadPost(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/agent/tools/reload',
        });
    }
}
