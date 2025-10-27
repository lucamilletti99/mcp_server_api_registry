/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ChatRequest } from '../models/ChatRequest';
import type { ChatResponse } from '../models/ChatResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ChatService {
    /**
     * List Available Models
     * List Databricks Foundation Models that support tool calling.
     *
     * Returns:
     * Dictionary with available models and their capabilities
     * @returns any Successful Response
     * @throws ApiError
     */
    public static listAvailableModelsApiChatModelsGet(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/chat/models',
        });
    }
    /**
     * Send Chat Message
     * Send a message to a Databricks Foundation Model with MCP tool support.
     *
     * Args:
     * request: Chat request with messages, model selection, and parameters
     *
     * Returns:
     * Response from the model including any tool calls
     * @param requestBody
     * @returns ChatResponse Successful Response
     * @throws ApiError
     */
    public static sendChatMessageApiChatMessagePost(
        requestBody: ChatRequest,
    ): CancelablePromise<ChatResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/chat/message',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Execute Tool Endpoint
     * Execute an MCP tool and return the result.
     *
     * Args:
     * tool_name: Name of the tool to execute (from query parameter)
     * tool_args: Arguments for the tool (from request body)
     *
     * Returns:
     * Tool execution result
     * @param toolName Name of the tool to execute
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static executeToolEndpointApiChatExecuteToolPost(
        toolName: string,
        requestBody: Record<string, any>,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/chat/execute-tool',
            query: {
                'tool_name': toolName,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Available Tools
     * Get all available MCP tools in OpenAI format.
     *
     * Returns:
     * Dictionary with tools list
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getAvailableToolsApiChatToolsGet(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/chat/tools',
        });
    }
}
