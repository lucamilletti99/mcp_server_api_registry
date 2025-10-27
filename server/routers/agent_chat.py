"""Agent chat router - uses notebook MCP agent for orchestration.

This router provides a simple chat interface that delegates all orchestration
to the notebook agent pattern. The notebook handles:
- Connecting to MCP server
- Calling Foundation Models
- Executing tools via MCP
- MLflow tracing

The frontend just sends messages and gets responses back.
"""

import asyncio
import os
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
import httpx
import json

from server.trace_manager import get_trace_manager

router = APIRouter()

# Cache the MCP tools at startup so we don't reload them on every request
_tools_cache: Optional[List[Dict[str, Any]]] = None
_mcp_server_url: Optional[str] = None


def get_workspace_client(request: Request = None) -> WorkspaceClient:
    """Get authenticated Databricks workspace client with on-behalf-of user auth.

    Uses the user's OAuth token from X-Forwarded-Access-Token header when available.
    Falls back to OAuth service principal authentication if user token is not available.

    Args:
        request: FastAPI Request object to extract user token from

    Returns:
        WorkspaceClient configured with appropriate authentication
    """
    host = os.environ.get('DATABRICKS_HOST')

    # Try to get user token from request headers (on-behalf-of authentication)
    user_token = None
    if request:
        user_token = request.headers.get('x-forwarded-access-token')

    if user_token:
        # Use on-behalf-of authentication with user's token
        # auth_type='pat' forces token-only auth and disables auto-detection
        config = Config(host=host, token=user_token, auth_type='pat')
        return WorkspaceClient(config=config)
    else:
        # Fall back to OAuth service principal authentication
        return WorkspaceClient(host=host)


class ChatMessage(BaseModel):
    """A single chat message."""
    role: str  # 'user' or 'assistant'
    content: str


class AgentChatRequest(BaseModel):
    """Request to chat with the agent."""
    messages: List[ChatMessage]
    model: str = 'databricks-claude-sonnet-4'  # Claude Sonnet 4 (best model for tool calling)
    max_tokens: int = 4096
    system_prompt: Optional[str] = None  # Optional custom system prompt


class AgentChatResponse(BaseModel):
    """Response from the agent."""
    response: str
    iterations: int
    tool_calls: List[Dict[str, Any]]
    trace_id: Optional[str] = None  # MLflow-style trace ID


async def load_mcp_tools_cached(force_reload: bool = False) -> List[Dict[str, Any]]:
    """Load tools from MCP server (cached).

    Args:
        force_reload: Force reload even if cached

    Returns:
        List of tools in OpenAI format
    """
    global _tools_cache

    # Return cached tools if available
    if _tools_cache is not None and not force_reload:
        return _tools_cache

    # Import the MCP server instance from the app
    from server.app import mcp_server as mcp

    # Get tools directly from the MCP server instance (no HTTP!)
    if hasattr(mcp, '_tool_manager'):
        mcp_tools = await mcp._tool_manager.list_tools()

        # Convert to OpenAI format
        openai_tools = []
        for tool in mcp_tools:
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool.key,
                    "description": tool.description or tool.key,
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
            openai_tools.append(openai_tool)

        # Cache the tools
        _tools_cache = openai_tools
        return openai_tools

    return []


async def call_foundation_model(
    messages: List[Dict[str, str]],
    model: str,
    tools: Optional[List[Dict]] = None,
    max_tokens: int = 4096,
    request: Request = None
) -> Dict[str, Any]:
    """Call a Databricks Foundation Model.

    Args:
        messages: Conversation history
        model: Model endpoint name
        tools: Available tools
        max_tokens: Maximum response tokens
        request: FastAPI Request object for on-behalf-of auth

    Returns:
        Model response
    """
    ws = get_workspace_client(request)
    base_url = ws.config.host.rstrip('/')
    token = ws.config.token

    # Validate we have the required credentials
    if not base_url:
        raise HTTPException(
            status_code=500,
            detail='DATABRICKS_HOST not configured'
        )
    if not token:
        raise HTTPException(
            status_code=500,
            detail='No authentication token available (check OAuth configuration)'
        )

    payload = {
        "messages": messages,
        "max_tokens": max_tokens
    }

    if tools:
        payload["tools"] = tools

    # Log the request payload for debugging
    import sys
    print(f"[Model Call] Sending {len(messages)} messages, {len(tools) if tools else 0} tools", flush=True)
    print(f"[Model Call] Messages structure:", flush=True)
    for i, msg in enumerate(messages):
        role = msg.get('role')
        content_preview = str(msg.get('content', ''))[:100] if 'content' in msg else 'N/A'
        has_tool_calls = 'tool_calls' in msg
        has_tool_call_id = 'tool_call_id' in msg
        print(f"  [{i}] role={role}, content_preview={content_preview}, has_tool_calls={has_tool_calls}, has_tool_call_id={has_tool_call_id}", flush=True)
    sys.stdout.flush()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f'{base_url}/serving-endpoints/{model}/invocations',
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
            },
            json=payload,
            timeout=120.0
        )

        if response.status_code != 200:
            error_detail = f'Model call failed: {response.text}'

            # Provide more helpful error messages for common issues
            if response.status_code == 401:
                error_detail += ' (Authentication failed - check OAuth token)'
            elif response.status_code == 403:
                error_detail += ' (Permission denied - check app.yaml scopes include "all-apis")'
            elif response.status_code == 404:
                error_detail += f' (Model endpoint "{model}" not found)'

            raise HTTPException(
                status_code=response.status_code,
                detail=error_detail
            )

        return response.json()


async def execute_mcp_tool(tool_name: str, tool_args: Dict[str, Any]) -> str:
    """Execute a tool directly via MCP server instance.

    Args:
        tool_name: Name of the tool
        tool_args: Tool arguments

    Returns:
        Tool result as string
    """
    # Import the MCP server instance from the app
    from server.app import mcp_server as mcp

    try:
        # Execute the tool directly (no HTTP!)
        if hasattr(mcp, '_tool_manager'):
            result = await mcp._tool_manager.call_tool(tool_name, tool_args)

            # Convert ToolResult to string
            if hasattr(result, 'model_dump'):
                result_dict = result.model_dump()
                if 'content' in result_dict:
                    content_list = result_dict['content']
                    if isinstance(content_list, list) and len(content_list) > 0:
                        first_content = content_list[0]
                        if isinstance(first_content, dict) and 'text' in first_content:
                            return first_content['text']
                return json.dumps(result_dict)
            elif hasattr(result, 'content'):
                # FastMCP ToolResult
                content_parts = []
                for content in result.content:
                    if hasattr(content, 'text'):
                        content_parts.append(content.text)
                return "".join(content_parts)
            else:
                return str(result)

    except Exception as e:
        return f"Error executing tool {tool_name}: {str(e)}"

    return f"Tool {tool_name} not found"


async def run_agent_loop(
    user_messages: List[Dict[str, str]],
    model: str,
    tools: List[Dict[str, Any]],
    max_iterations: int = 10,
    request: Request = None,
    custom_system_prompt: Optional[str] = None,
    trace_id: Optional[str] = None
) -> Dict[str, Any]:
    """Run the agentic loop.

    This is the core logic from the notebook, adapted for FastAPI.

    Args:
        user_messages: User conversation history
        model: Model endpoint name
        tools: Available tools
        max_iterations: Max agent iterations
        request: FastAPI Request object for on-behalf-of auth
        custom_system_prompt: Optional custom system prompt from user
        trace_id: Optional trace ID for MLflow tracing

    Returns:
        Final response with traces and trace_id
    """
    # Use custom system prompt if provided, otherwise use default
    if custom_system_prompt:
        system_prompt = custom_system_prompt
    else:
        # Default system prompt to set the context and role for the agent
        system_prompt = """You are an API Registry Agent powered by MCP (Model Context Protocol) tools. Your role is to help users discover, register, query, and test API endpoints with minimal friction.

## Available Tools

### Smart Registration Tools (USE THESE FIRST!)
- **smart_register_api**: ONE-STEP registration! Combines discovery, validation, and registration. Use this when users want to register an API - it automatically tries common patterns and auth methods.
- **fetch_api_documentation**: Fetch and parse API docs from URLs to extract endpoints, parameters, and examples. Use when users provide a documentation link.
- **try_common_api_patterns**: Automatically test common endpoint patterns (/api, /v1, /search, etc.) with multiple auth methods.

### Manual Tools (Use if smart tools fail)
- **discover_api_endpoint**: Manually discover a specific API endpoint with authentication
- **register_api_in_registry**: Manually register an API (only if smart_register_api fails)

### Query & Test Tools
- **check_api_registry**: View all registered APIs in the registry
- **call_api_endpoint**: Make HTTP requests to test API endpoints
- **execute_dbsql**: Execute SQL queries against Databricks
- **list_warehouses**: List available SQL warehouses
- **list_dbfs_files**: Browse DBFS file system
- **health**: Check system health status

## Smart Registration Workflow

When a user wants to register an API, follow this streamlined approach:

1. **Use smart_register_api first!** This handles everything in one step:
   - If they provide a documentation URL, pass it to documentation_url parameter
   - If they provide an API key, pass it to api_key parameter
   - If they provide a base URL or endpoint, pass it to endpoint_url parameter
   - The tool will automatically:
     * Fetch documentation if URL provided
     * Try common endpoint patterns (/api, /v1, /search, /data, /query, etc.)
     * Test multiple auth methods (Bearer header, API key header, query params)
     * Discover the best working configuration
     * Register the API with validation

2. **Only if smart_register_api fails**, use the manual approach:
   - fetch_api_documentation (if doc URL provided)
   - try_common_api_patterns (to find working endpoints)
   - discover_api_endpoint (for specific endpoint testing)
   - register_api_in_registry (manual registration)

3. **Always get the warehouse_id first** by calling list_warehouses before registration

## Examples

**User: "Register the SEC API, here's the documentation: https://sec-api.io/docs"**
→ Call list_warehouses to get warehouse_id
→ Call smart_register_api with:
  - api_name: "sec_api"
  - description: "SEC API for financial filings"
  - endpoint_url: "https://api.sec-api.io"
  - warehouse_id: "<from list_warehouses>"
  - documentation_url: "https://sec-api.io/docs"
  - api_key: "<if user provided>"

**User: "I want to add the Alpha Vantage stock API, my API key is ABC123"**
→ Call list_warehouses
→ Call smart_register_api with:
  - api_name: "alphavantage_stock"
  - description: "Alpha Vantage stock market data API"
  - endpoint_url: "https://www.alphavantage.co"
  - warehouse_id: "<from list_warehouses>"
  - api_key: "ABC123"

## General Guidelines

1. **Always use smart_register_api for API registration** - it reduces the user journey from 4+ steps to 1-2 steps
2. **Minimize back-and-forth** - the smart tools handle discovery automatically
3. **Get warehouse_id early** - call list_warehouses before any SQL/registration operations
4. **Be transparent** - explain what the smart tools are doing (fetching docs, trying patterns, etc.)
5. **Handle failures gracefully** - if smart tools fail, fall back to manual approach with clear explanation
6. **Test after registration** - use call_api_endpoint to verify registered APIs work

You are helpful, efficient, and minimize user friction through intelligent tool orchestration."""

    # Prepend system message to conversation
    messages = [{"role": "system", "content": system_prompt}] + user_messages.copy()
    traces = []
    trace_manager = get_trace_manager()

    for iteration in range(max_iterations):
        # Call the model with tracing
        print(f"[Agent Loop] Iteration {iteration + 1}: Calling model with {len(messages)} messages")

        # Add LLM span
        import time
        llm_span_id = None
        if trace_id:
            llm_span_id = trace_manager.add_span(
                trace_id=trace_id,
                name=f'llm:/serving-endpoints/{model}/invocations',
                inputs={'messages': [{'role': m.get('role'), 'content_preview': str(m.get('content', ''))[:100]} for m in messages]},
                span_type='LLM'
            )

        llm_start_time = time.time()
        response = await call_foundation_model(messages, model=model, tools=tools, request=request)
        llm_duration = time.time() - llm_start_time

        if trace_id and llm_span_id:
            trace_manager.complete_span(
                trace_id=trace_id,
                span_id=llm_span_id,
                outputs={'response': response},
                status='SUCCESS'
            )

        # Extract assistant message
        if 'choices' not in response or len(response['choices']) == 0:
            print(f"[Agent Loop] No choices in response, breaking")
            break

        choice = response['choices'][0]
        message = choice.get('message', {})
        finish_reason = choice.get('finish_reason', 'unknown')

        print(f"[Agent Loop] Model response - finish_reason: {finish_reason}")
        print(f"[Agent Loop] Message keys: {list(message.keys())}")

        # Check for Claude-style tool_use in content
        content = message.get('content', '')
        tool_use_blocks = []
        if isinstance(content, list):
            tool_use_blocks = [item for item in content if isinstance(item, dict) and item.get('type') == 'tool_use']

        # Check for OpenAI-style tool_calls
        tool_calls = message.get('tool_calls')

        print(f"[Agent Loop] Tool calls: {len(tool_calls) if tool_calls else 0}")
        print(f"[Agent Loop] Tool use blocks: {len(tool_use_blocks)}")

        if tool_use_blocks:
            # Claude format: content contains tool_use blocks
            # BUT Databricks requires OpenAI format in requests even for Claude models
            print(f"[Agent Loop] Processing Claude tool_use blocks (converting to OpenAI format)")

            # Convert Claude tool_use to OpenAI tool_calls format for the request
            tool_calls_openai = []
            for i, tool_use in enumerate(tool_use_blocks):
                tool_calls_openai.append({
                    "id": tool_use.get('id'),
                    "type": "function",
                    "function": {
                        "name": tool_use.get('name'),
                        "arguments": json.dumps(tool_use.get('input', {}))
                    }
                })

            # Add assistant message in OpenAI format (required by Databricks)
            assistant_msg = {
                "role": "assistant",
                "tool_calls": tool_calls_openai
            }
            # Include text content if present (not just tool_use blocks)
            text_content = ""
            if isinstance(content, list):
                text_blocks = [item.get('text', '') for item in content if isinstance(item, dict) and item.get('type') == 'text']
                text_content = ''.join(text_blocks)
            if text_content:
                assistant_msg["content"] = text_content

            messages.append(assistant_msg)

            # Execute each tool and add results in OpenAI format
            for tool_use in tool_use_blocks:
                tool_name = tool_use.get('name')
                tool_args = tool_use.get('input', {})
                tool_id = tool_use.get('id')

                print(f"[Agent Loop] Executing tool: {tool_name}")

                # Add tool span
                tool_span_id = None
                if trace_id:
                    tool_span_id = trace_manager.add_span(
                        trace_id=trace_id,
                        name=tool_name,
                        inputs=tool_args,
                        parent_id=llm_span_id,
                        span_type='TOOL'
                    )

                # Execute via MCP
                tool_start_time = time.time()
                result = await execute_mcp_tool(tool_name, tool_args)
                tool_duration = time.time() - tool_start_time

                if trace_id and tool_span_id:
                    trace_manager.complete_span(
                        trace_id=trace_id,
                        span_id=tool_span_id,
                        outputs={'result': result[:500] if len(str(result)) > 500 else result},
                        status='SUCCESS'
                    )

                # Ensure result is not empty
                if not result or result.strip() == "":
                    result = f"Tool {tool_name} completed successfully (no output)"

                # Add tool result in OpenAI format (required by Databricks)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": result
                })

                traces.append({
                    "iteration": iteration + 1,
                    "tool": tool_name,
                    "args": tool_args,
                    "result": result
                })

        elif tool_calls:
            # OpenAI/GPT format: tool_calls array
            print(f"[Agent Loop] Processing OpenAI tool_calls")

            # IMPORTANT: Do NOT include content when tool_calls are present!
            # Claude includes tool_use blocks in content which conflicts with tool_calls format
            assistant_msg = {
                "role": "assistant",
                "tool_calls": tool_calls
            }
            # Note: Intentionally NOT including content field even if present
            # because it may contain Claude-formatted tool_use blocks

            messages.append(assistant_msg)

            # Execute each tool
            for tc in tool_calls:
                tool_name = tc['function']['name']
                tool_args = json.loads(tc['function']['arguments'])

                # Add tool span
                tool_span_id = None
                if trace_id:
                    tool_span_id = trace_manager.add_span(
                        trace_id=trace_id,
                        name=tool_name,
                        inputs=tool_args,
                        parent_id=llm_span_id,
                        span_type='TOOL'
                    )

                # Execute via MCP
                tool_start_time = time.time()
                result = await execute_mcp_tool(tool_name, tool_args)
                tool_duration = time.time() - tool_start_time

                if trace_id and tool_span_id:
                    trace_manager.complete_span(
                        trace_id=trace_id,
                        span_id=tool_span_id,
                        outputs={'result': result[:500] if len(str(result)) > 500 else result},
                        status='SUCCESS'
                    )

                # Ensure result is not empty
                if not result or result.strip() == "":
                    result = f"Tool {tool_name} completed successfully (no output)"

                # Add tool result to conversation (OpenAI format)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc['id'],
                    "content": result
                })

                traces.append({
                    "iteration": iteration + 1,
                    "tool": tool_name,
                    "args": tool_args,
                    "result": result
                })

        else:
            # Final answer from model
            final_content = message.get('content', '')

            # Complete the trace
            if trace_id:
                trace_manager.complete_trace(trace_id, status='SUCCESS')

            return {
                "response": final_content,
                "iterations": iteration + 1,
                "traces": traces,
                "finish_reason": finish_reason,
                "trace_id": trace_id
            }

    # Complete the trace with max_iterations status
    if trace_id:
        trace_manager.complete_trace(trace_id, status='SUCCESS')

    return {
        "response": "Agent reached maximum iterations",
        "iterations": max_iterations,
        "traces": traces,
        "finish_reason": "max_iterations",
        "trace_id": trace_id
    }


@router.post('/chat', response_model=AgentChatResponse)
async def agent_chat(chat_request: AgentChatRequest, request: Request) -> AgentChatResponse:
    """Chat with the agent using MCP orchestration.

    This endpoint uses the notebook agent pattern under the hood.
    The frontend just sends messages and gets responses back.

    Args:
        chat_request: Chat request with messages and model
        request: FastAPI Request object for on-behalf-of auth

    Returns:
        Agent response with tool call traces
    """
    try:
        # Create a trace for this conversation
        trace_manager = get_trace_manager()
        trace_id = trace_manager.create_trace(
            request_metadata={
                "model": chat_request.model,
                "message_count": len(chat_request.messages),
                "first_message": chat_request.messages[0].content[:100] if chat_request.messages else ""
            }
        )

        # Add root span for the agent
        root_span_id = trace_manager.add_span(
            trace_id=trace_id,
            name="agent",
            inputs={"messages": [{"role": msg.role, "content": msg.content[:100]} for msg in chat_request.messages]},
            span_type='AGENT'
        )

        # Load tools (cached after first call)
        tools = await load_mcp_tools_cached()

        # Convert Pydantic messages to dict
        messages = [{"role": msg.role, "content": msg.content} for msg in chat_request.messages]

        # Run the agent loop (this is the notebook pattern)
        result = await run_agent_loop(
            user_messages=messages,
            model=chat_request.model,
            tools=tools,
            max_iterations=10,
            request=request,
            custom_system_prompt=chat_request.system_prompt,
            trace_id=trace_id
        )

        # Complete root span
        trace_manager.complete_span(
            trace_id=trace_id,
            span_id=root_span_id,
            outputs={"response": result["response"][:500]},
            status='SUCCESS'
        )

        return AgentChatResponse(
            response=result["response"],
            iterations=result["iterations"],
            tool_calls=result["traces"],
            trace_id=trace_id
        )

    except Exception as e:
        # Log the full exception for debugging
        import traceback
        error_traceback = traceback.format_exc()
        print(f"[Agent Chat Error] {error_traceback}", flush=True)
        raise HTTPException(
            status_code=500,
            detail=f'Agent chat failed: {str(e)}'
        )


@router.get('/tools')
async def list_agent_tools() -> Dict[str, Any]:
    """List available tools from MCP server.

    Returns:
        Dictionary with tools list
    """
    try:
        tools = await load_mcp_tools_cached()
        return {
            "tools": tools,
            "count": len(tools),
            "server_url": _mcp_server_url
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f'Failed to list tools: {str(e)}'
        )


@router.post('/tools/reload')
async def reload_tools() -> Dict[str, Any]:
    """Force reload tools from MCP server.

    Useful when you deploy new tools to the MCP server.

    Returns:
        Dictionary with reloaded tools
    """
    try:
        tools = await load_mcp_tools_cached(force_reload=True)
        return {
            "message": "Tools reloaded successfully",
            "count": len(tools),
            "tools": [t["function"]["name"] for t in tools]
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f'Failed to reload tools: {str(e)}'
        )
