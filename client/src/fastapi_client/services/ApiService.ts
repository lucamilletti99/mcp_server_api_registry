/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ChatRequest } from '../models/ChatRequest';
import type { ChatResponse } from '../models/ChatResponse';
import type { Trace } from '../models/Trace';
import type { TraceListResponse } from '../models/TraceListResponse';
import type { UserInfo } from '../models/UserInfo';
import type { UserWorkspaceInfo } from '../models/UserWorkspaceInfo';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ApiService {
    /**
     * Get Current User
     * Get current user information from Databricks.
     * @returns UserInfo Successful Response
     * @throws ApiError
     */
    public static getCurrentUserApiUserMeGet(): CancelablePromise<UserInfo> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/user/me',
        });
    }
    /**
     * Get User Workspace Info
     * Get user information along with workspace details.
     * @returns UserWorkspaceInfo Successful Response
     * @throws ApiError
     */
    public static getUserWorkspaceInfoApiUserMeWorkspaceGet(): CancelablePromise<UserWorkspaceInfo> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/user/me/workspace',
        });
    }
    /**
     * List Prompts
     * List all available prompts.
     * @returns string Successful Response
     * @throws ApiError
     */
    public static listPromptsApiPromptsGet(): CancelablePromise<Array<Record<string, string>>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/prompts',
        });
    }
    /**
     * Get Prompt
     * Get the content of a specific prompt.
     * @param promptName
     * @returns string Successful Response
     * @throws ApiError
     */
    public static getPromptApiPromptsPromptNameGet(
        promptName: string,
    ): CancelablePromise<Record<string, string>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/prompts/{prompt_name}',
            path: {
                'prompt_name': promptName,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Mcp Info
     * Get MCP server information including URL and capabilities.
     *
     * Returns:
     * Dictionary with MCP server details
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getMcpInfoApiMcpInfoInfoGet(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/mcp_info/info',
        });
    }
    /**
     * Get Mcp Discovery
     * Get MCP discovery information including prompts and tools.
     *
     * This endpoint dynamically discovers available prompts and tools
     * from the FastMCP server instance.
     *
     * Returns:
     * Dictionary with prompts and tools lists and servername
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getMcpDiscoveryApiMcpInfoDiscoveryGet(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/mcp_info/discovery',
        });
    }
    /**
     * Get Mcp Config
     * Get MCP configuration for Claude Code setup.
     *
     * Returns:
     * Dictionary with configuration needed for Claude MCP setup
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getMcpConfigApiMcpInfoConfigGet(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/mcp_info/config',
        });
    }
    /**
     * Get Mcp Prompt Content
     * Get the content of a specific MCP prompt.
     *
     * Args:
     * prompt_name: The name of the prompt
     *
     * Returns:
     * Dictionary with prompt name and content
     * @param promptName
     * @returns string Successful Response
     * @throws ApiError
     */
    public static getMcpPromptContentApiMcpInfoPromptPromptNameGet(
        promptName: string,
    ): CancelablePromise<Record<string, string>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/mcp_info/prompt/{prompt_name}',
            path: {
                'prompt_name': promptName,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
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
