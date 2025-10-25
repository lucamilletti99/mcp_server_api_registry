"""Chat router for interacting with Databricks Foundation Models using MCP tools."""

import json
import os
from typing import Any, Dict, List

import httpx
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


def get_workspace_client() -> WorkspaceClient:
    """Get authenticated Databricks workspace client."""
    config = Config(
        host=os.environ.get('DATABRICKS_HOST'),
        token=os.environ.get('DATABRICKS_TOKEN'),
    )
    return WorkspaceClient(config=config)


class ChatMessage(BaseModel):
    """A single chat message."""

    role: str  # 'user' or 'assistant'
    content: str


class ChatRequest(BaseModel):
    """Request to send a chat message."""

    messages: List[ChatMessage]
    model: str = 'databricks-meta-llama-3-3-70b-instruct'  # Default model
    max_tokens: int = 4096


class ToolCall(BaseModel):
    """A tool call made by the model."""

    id: str
    type: str
    function: Dict[str, Any]


class ChatResponse(BaseModel):
    """Response from the chat endpoint."""

    role: str
    content: str
    tool_calls: List[ToolCall] | None = None
    finish_reason: str


@router.get('/models')
async def list_available_models() -> Dict[str, Any]:
    """List Databricks Foundation Models that support tool calling.

    Returns:
        Dictionary with available models and their capabilities
    """
    # These are the Databricks Foundation Models that support tool calling
    # Based on Databricks Model Serving catalog
    models = [
        {
            'id': 'databricks-claude-sonnet-4-5',
            'name': 'Claude Sonnet 4.5',
            'provider': 'Anthropic',
            'supports_tools': True,
            'context_window': 200000,
            'type': 'Pay-per-token',
        },
        {
            'id': 'databricks-claude-opus-4-1',
            'name': 'Claude Opus 4.1',
            'provider': 'Anthropic',
            'supports_tools': True,
            'context_window': 200000,
            'type': 'Pay-per-token',
        },
        {
            'id': 'databricks-claude-sonnet-4',
            'name': 'Claude Sonnet 4',
            'provider': 'Anthropic',
            'supports_tools': True,
            'context_window': 200000,
            'type': 'Pay-per-token',
        },
        {
            'id': 'databricks-claude-3-7-sonnet',
            'name': 'Claude 3.7 Sonnet',
            'provider': 'Anthropic',
            'supports_tools': True,
            'context_window': 200000,
            'type': 'Pay-per-token',
        },
        {
            'id': 'databricks-meta-llama-3-3-70b-instruct',
            'name': 'Meta Llama 3.3 70B Instruct',
            'provider': 'Meta',
            'supports_tools': True,
            'context_window': 128000,
            'type': 'Pay-per-token',
        },
        {
            'id': 'databricks-meta-llama-3-1-405b-instruct',
            'name': 'Meta Llama 3.1 405B Instruct',
            'provider': 'Meta',
            'supports_tools': True,
            'context_window': 128000,
            'type': 'Pay-per-token',
        },
        {
            'id': 'databricks-meta-llama-3-1-8b-instruct',
            'name': 'Meta Llama 3.1 8B Instruct',
            'provider': 'Meta',
            'supports_tools': False,
            'context_window': 128000,
            'type': 'Pay-per-token',
        },
        {
            'id': 'databricks-llama-4-maverick',
            'name': 'Llama 4 Maverick',
            'provider': 'Meta',
            'supports_tools': False,
            'context_window': 128000,
            'type': 'Pay-per-token',
        },
        {
            'id': 'databricks-gemma-3-12b',
            'name': 'Gemma 3 12B',
            'provider': 'Google',
            'supports_tools': True,
            'context_window': 32000,
            'type': 'Pay-per-token',
        },
        {
            'id': 'databricks-gpt-oss-120b',
            'name': 'GPT OSS 120B',
            'provider': 'OpenAI',
            'supports_tools': True,
            'context_window': 8192,
            'type': 'Pay-per-token',
        },
        {
            'id': 'databricks-gpt-oss-20b',
            'name': 'GPT OSS 20B',
            'provider': 'OpenAI',
            'supports_tools': True,
            'context_window': 8192,
            'type': 'Pay-per-token',
        },
    ]

    return {'models': models, 'default': 'databricks-meta-llama-3-3-70b-instruct'}


def convert_mcp_tools_to_openai_format(mcp_tools: List[Any]) -> List[Dict[str, Any]]:
    """Convert MCP tools to OpenAI function calling format.

    Args:
        mcp_tools: List of tools from FastMCP

    Returns:
        List of tools in OpenAI format for Databricks Foundation Models
    """
    openai_tools = []

    for tool in mcp_tools:
        # Extract parameters from the tool's input schema
        parameters = {'type': 'object', 'properties': {}, 'required': []}

        if hasattr(tool, 'schema') and tool.schema:
            schema = tool.schema
            if 'inputSchema' in schema:
                input_schema = schema['inputSchema']
                parameters = {
                    'type': input_schema.get('type', 'object'),
                    'properties': input_schema.get('properties', {}),
                    'required': input_schema.get('required', []),
                }

        openai_tool = {
            'type': 'function',
            'function': {
                'name': tool.key,
                'description': tool.description or f'{tool.key.replace("_", " ").title()}',
                'parameters': parameters,
            },
        }
        openai_tools.append(openai_tool)

    return openai_tools


async def get_mcp_tools() -> List[Dict[str, Any]]:
    """Get tools from the MCP server in OpenAI format.

    Returns:
        List of tools in OpenAI format
    """
    from server.app import mcp_server as mcp

    tools_list = []

    # Get tools dynamically from FastMCP
    if hasattr(mcp, '_tool_manager'):
        mcp_tools = await mcp._tool_manager.list_tools()
        tools_list = convert_mcp_tools_to_openai_format(mcp_tools)

    return tools_list


async def execute_mcp_tool(tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool on the MCP server.

    Args:
        tool_name: Name of the tool to execute
        tool_args: Arguments to pass to the tool

    Returns:
        Result from the tool execution
    """
    from server.app import mcp_server as mcp

    try:
        # Get the tool from the MCP server
        if hasattr(mcp, '_tool_manager'):
            # Call the tool with the provided arguments
            result = await mcp._tool_manager.call_tool(tool_name, tool_args)
            return result
    except Exception as e:
        return {
            'error': str(e),
            'tool_name': tool_name,
            'status': 'failed',
        }


@router.post('/message', response_model=ChatResponse)
async def send_chat_message(request: ChatRequest) -> ChatResponse:
    """Send a message to a Databricks Foundation Model with MCP tool support.

    Args:
        request: Chat request with messages, model selection, and parameters

    Returns:
        Response from the model including any tool calls
    """
    try:
        # Get MCP tools
        tools = await get_mcp_tools()

        # Get Databricks workspace client
        w = get_workspace_client()

        # Convert messages to the format expected by Databricks
        messages = [{'role': msg.role, 'content': msg.content} for msg in request.messages]

        # Prepare the request payload
        payload = {
            'messages': messages,
            'max_tokens': request.max_tokens,
        }

        # Only add tools if we have any
        if tools:
            payload['tools'] = tools

        # Call the Foundation Model via Databricks serving endpoint
        # Foundation Models are accessed through the /serving-endpoints API
        endpoint_name = request.model

        # Use httpx to call the serving endpoint directly
        base_url = os.environ.get('DATABRICKS_HOST', '').rstrip('/')
        token = os.environ.get('DATABRICKS_TOKEN', '')

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f'{base_url}/serving-endpoints/{endpoint_name}/invocations',
                headers={
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json',
                },
                json=payload,
                timeout=120.0,  # 2 minute timeout for model inference
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f'Failed to call model: {response.text}',
                )

            result = response.json()

        # Extract the response
        if 'choices' in result and len(result['choices']) > 0:
            choice = result['choices'][0]
            message = choice.get('message', {})

            # Check if there are tool calls
            tool_calls = None
            if 'tool_calls' in message and message['tool_calls']:
                tool_calls = [
                    ToolCall(
                        id=tc.get('id', ''),
                        type=tc.get('type', 'function'),
                        function=tc.get('function', {}),
                    )
                    for tc in message['tool_calls']
                ]

            return ChatResponse(
                role=message.get('role', 'assistant'),
                content=message.get('content', ''),
                tool_calls=tool_calls,
                finish_reason=choice.get('finish_reason', 'stop'),
            )
        else:
            raise HTTPException(status_code=500, detail='Unexpected response format from model')

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to process chat message: {str(e)}')


@router.post('/execute-tool')
async def execute_tool(tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute an MCP tool and return the result.

    Args:
        tool_name: Name of the tool to execute
        tool_args: Arguments for the tool

    Returns:
        Tool execution result
    """
    try:
        result = await execute_mcp_tool(tool_name, tool_args)
        return {'success': True, 'result': result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to execute tool: {str(e)}')


@router.get('/tools')
async def get_available_tools() -> Dict[str, Any]:
    """Get all available MCP tools in OpenAI format.

    Returns:
        Dictionary with tools list
    """
    tools = await get_mcp_tools()
    return {'tools': tools, 'count': len(tools)}
