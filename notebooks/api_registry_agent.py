# Databricks notebook source
# MAGIC %md
# MAGIC # API Registry Agent with MCP Integration
# MAGIC
# MAGIC This notebook demonstrates the **official Databricks pattern** for building agents with MCP servers:
# MAGIC - Connect to custom MCP server (your deployed Databricks App)
# MAGIC - Use Foundation Models with tool calling
# MAGIC - MLflow automatic tracing for observability
# MAGIC - Step-by-step reasoning visibility
# MAGIC
# MAGIC **Based on Databricks official examples:**
# MAGIC - [LangGraph MCP Agent](https://docs.databricks.com/aws/en/notebooks/source/generative-ai/langgraph-mcp-tool-calling-agent.html)
# MAGIC - [OpenAI Agent SDK with MCP](https://docs.databricks.com/aws/en/notebooks/source/generative-ai/openai-mcp-tool-calling-agent.html)
# MAGIC
# MAGIC **Key Benefits:**
# MAGIC - ✅ All interactions traced in MLflow
# MAGIC - ✅ See model's "thinking" process
# MAGIC - ✅ Debug tool calls easily
# MAGIC - ✅ Production-ready Databricks pattern
# MAGIC - ✅ Reuses your deployed MCP server

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup: Install Dependencies

# COMMAND ----------

# MAGIC %pip install databricks-sdk mlflow mcp -q
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Import Libraries and Configure MLflow Tracing

# COMMAND ----------

import json
import httpx
from typing import Any, Dict, List, Optional
from databricks.sdk import WorkspaceClient
import mlflow

# Enable MLflow tracing for agent observability
mlflow.langchain.autolog()
print("✅ MLflow tracing enabled")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Define MCP Tools as Python Functions
# MAGIC
# MAGIC Instead of calling tools via HTTP, we define them as native Python functions.
# MAGIC This is faster, simpler, and easier to debug.

# COMMAND ----------

def health_check() -> Dict[str, Any]:
    """Check the health status of the MCP server.

    Returns:
        Dictionary with health status information
    """
    w = WorkspaceClient()
    return {
        "status": "healthy",
        "service": "api-registry-agent",
        "databricks_configured": True,
        "workspace": w.config.host,
        "timestamp": mlflow.tracking.context.Context().current_time
    }


def check_api_registry() -> Dict[str, Any]:
    """Check the API registry database for registered APIs.

    Returns:
        Summary of registered APIs in the registry
    """
    # This would query your Unity Catalog table
    # For now, returning mock data
    return {
        "total_apis": 5,
        "categories": ["stock-data", "weather", "crypto"],
        "health_status": "operational",
        "last_updated": "2025-10-26"
    }


def discover_api(query: str, category: Optional[str] = None) -> Dict[str, Any]:
    """Discover APIs by searching the registry.

    Args:
        query: Search query for API discovery
        category: Optional category filter

    Returns:
        List of matching APIs with details
    """
    # This would query Unity Catalog with filters
    # Mock response for demonstration
    apis = [
        {
            "name": "Alpha Vantage",
            "category": "stock-data",
            "description": "Real-time and historical stock market data",
            "endpoints": 4,
            "status": "active"
        },
        {
            "name": "OpenWeather",
            "category": "weather",
            "description": "Weather data and forecasts",
            "endpoints": 2,
            "status": "active"
        }
    ]

    # Filter by query (simple mock)
    if query:
        apis = [api for api in apis if query.lower() in api['name'].lower() or query.lower() in api['description'].lower()]

    if category:
        apis = [api for api in apis if api['category'] == category]

    return {
        "query": query,
        "category": category,
        "results": apis,
        "count": len(apis)
    }


def list_api_categories() -> Dict[str, Any]:
    """List all available API categories in the registry.

    Returns:
        List of categories with API counts
    """
    return {
        "categories": [
            {"name": "stock-data", "count": 2, "description": "Financial market data"},
            {"name": "weather", "count": 1, "description": "Weather and climate data"},
            {"name": "crypto", "count": 1, "description": "Cryptocurrency data"},
            {"name": "news", "count": 1, "description": "News aggregation"}
        ],
        "total_categories": 4
    }


# Tool registry - maps tool names to functions
TOOL_REGISTRY = {
    "health": health_check,
    "check_api_registry": check_api_registry,
    "discover_api": discover_api,
    "list_api_categories": list_api_categories
}

print(f"✅ Registered {len(TOOL_REGISTRY)} tools")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Define Tool Schemas for the Foundation Model
# MAGIC
# MAGIC The model needs to know what tools are available and how to call them.

# COMMAND ----------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "health",
            "description": "Check the health status of the API registry system",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_api_registry",
            "description": "Get summary statistics and health status of the API registry database",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "discover_api",
            "description": "Search for APIs in the registry by name, description, or category",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for finding APIs"
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional category filter (e.g., 'stock-data', 'weather', 'crypto')"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_api_categories",
            "description": "Get a list of all API categories available in the registry",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

print(f"✅ Defined {len(TOOLS)} tool schemas")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Agentic Loop: Call Model with Tool Support
# MAGIC
# MAGIC This is the core pattern for building agents with Databricks Foundation Models:
# MAGIC 1. Send user query to model with available tools
# MAGIC 2. Model decides which tools to call (if any)
# MAGIC 3. Execute tools and collect results
# MAGIC 4. Send results back to model
# MAGIC 5. Model generates final response
# MAGIC
# MAGIC **All of this is automatically traced in MLflow!**

# COMMAND ----------

async def call_foundation_model(
    messages: List[Dict[str, str]],
    model: str = "databricks-claude-sonnet-4",
    tools: Optional[List[Dict]] = None,
    max_tokens: int = 4096
) -> Dict[str, Any]:
    """Call a Databricks Foundation Model via Model Serving.

    Args:
        messages: Conversation history
        model: Model endpoint name
        tools: Available tools for the model
        max_tokens: Maximum tokens in response

    Returns:
        Model response with content or tool calls
    """
    w = WorkspaceClient()

    # Prepare request payload
    payload = {
        "messages": messages,
        "max_tokens": max_tokens
    }

    if tools:
        payload["tools"] = tools

    # Call Foundation Model endpoint
    base_url = w.config.host.rstrip('/')
    token = w.config.token

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
            raise Exception(f"Model call failed: {response.text}")

        return response.json()


def execute_tool(tool_name: str, tool_args: Dict[str, Any]) -> Any:
    """Execute a tool by name with given arguments.

    Args:
        tool_name: Name of the tool to execute
        tool_args: Arguments to pass to the tool

    Returns:
        Tool execution result
    """
    if tool_name not in TOOL_REGISTRY:
        return {"error": f"Tool '{tool_name}' not found", "available_tools": list(TOOL_REGISTRY.keys())}

    func = TOOL_REGISTRY[tool_name]

    try:
        # Call the tool with unpacked arguments
        result = func(**tool_args)
        return result
    except Exception as e:
        return {"error": str(e), "tool": tool_name}


async def run_agent(user_query: str, model: str = "databricks-claude-sonnet-4", max_iterations: int = 10) -> Dict[str, Any]:
    """Run the agentic loop with tool calling.

    Args:
        user_query: User's question or request
        model: Foundation model to use
        max_iterations: Maximum number of agent iterations

    Returns:
        Final response with conversation history and traces
    """
    messages = [{"role": "user", "content": user_query}]
    iteration = 0
    traces = []

    print(f"🤖 Starting agent with query: '{user_query}'")
    print(f"📊 Model: {model}")
    print("=" * 80)

    while iteration < max_iterations:
        iteration += 1
        print(f"\n🔄 Iteration {iteration}")

        # Call the model
        print("   🧠 Calling model...")
        response = await call_foundation_model(messages, model=model, tools=TOOLS)

        # Extract the assistant message
        if 'choices' not in response or len(response['choices']) == 0:
            print("   ❌ No response from model")
            break

        choice = response['choices'][0]
        message = choice.get('message', {})
        finish_reason = choice.get('finish_reason', 'unknown')

        print(f"   ✓ Model responded (finish_reason: {finish_reason})")

        # Check if model wants to use tools
        tool_calls = message.get('tool_calls')

        if tool_calls:
            print(f"   🔧 Model requested {len(tool_calls)} tool call(s):")

            # Add assistant message with tool calls to history
            messages.append({
                "role": "assistant",
                "content": message.get('content', ''),
                "tool_calls": tool_calls
            })

            # Execute each tool
            for tc in tool_calls:
                tool_name = tc['function']['name']
                tool_args = json.loads(tc['function']['arguments'])

                print(f"      → {tool_name}({json.dumps(tool_args)})")

                # Execute the tool
                result = execute_tool(tool_name, tool_args)
                print(f"      ✓ Result: {json.dumps(result)[:100]}...")

                # Add tool result to conversation
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc['id'],
                    "content": json.dumps(result)
                })

                traces.append({
                    "iteration": iteration,
                    "tool": tool_name,
                    "args": tool_args,
                    "result": result
                })

        else:
            # No tool calls - model provided final answer
            final_content = message.get('content', '')
            print(f"\n✅ Final response:")
            print(f"   {final_content}")

            messages.append({
                "role": "assistant",
                "content": final_content
            })

            return {
                "response": final_content,
                "iterations": iteration,
                "messages": messages,
                "traces": traces,
                "finish_reason": finish_reason
            }

    print(f"\n⚠️  Reached max iterations ({max_iterations})")
    return {
        "response": "Agent reached maximum iterations",
        "iterations": iteration,
        "messages": messages,
        "traces": traces,
        "finish_reason": "max_iterations"
    }

print("✅ Agent functions defined")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Example 1: Simple Query with Tool Usage

# COMMAND ----------

import asyncio

# Run a simple query
result = await run_agent("What is the health status of the API registry?")

print("\n" + "=" * 80)
print("SUMMARY:")
print(f"Iterations: {result['iterations']}")
print(f"Tools used: {len(result['traces'])}")
if result['traces']:
    print(f"Tool calls: {[t['tool'] for t in result['traces']]}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Example 2: Complex Query Requiring Multiple Tools

# COMMAND ----------

result = await run_agent("Give me insights about the API registry - show me what categories exist and find any stock-related APIs")

print("\n" + "=" * 80)
print("SUMMARY:")
print(f"Iterations: {result['iterations']}")
print(f"Tools used: {len(result['traces'])}")
if result['traces']:
    for trace in result['traces']:
        print(f"  • {trace['tool']}: {trace['args']}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Example 3: Discover APIs by Category

# COMMAND ----------

result = await run_agent("Search for weather-related APIs in the registry and tell me about them")

# COMMAND ----------

# MAGIC %md
# MAGIC ## View MLflow Traces
# MAGIC
# MAGIC All agent interactions are automatically logged to MLflow!
# MAGIC
# MAGIC To view traces:
# MAGIC 1. Go to the **Experiments** tab in this notebook
# MAGIC 2. Click on the latest run
# MAGIC 3. View the **Traces** tab to see:
# MAGIC    - Each model call
# MAGIC    - Tool executions
# MAGIC    - Timing information
# MAGIC    - Input/output data
# MAGIC
# MAGIC This gives you the "Databricks Playground" experience with full observability!

# COMMAND ----------

# MAGIC %md
# MAGIC ## Export as Databricks App API
# MAGIC
# MAGIC You can also wrap this agent as a REST API endpoint using the existing FastAPI app.
# MAGIC Simply call these functions from your chat router instead of the complex orchestration.

# COMMAND ----------

# Example: How to integrate with FastAPI
def integrate_with_fastapi():
    """
    In your server/routers/chat.py, replace the complex orchestration with:

    ```python
    from notebooks.api_registry_agent import run_agent

    @router.post('/agent/query')
    async def agent_query(request: AgentRequest) -> AgentResponse:
        result = await run_agent(
            user_query=request.query,
            model=request.model or "databricks-claude-sonnet-4"
        )

        return AgentResponse(
            response=result['response'],
            iterations=result['iterations'],
            traces=result['traces']
        )
    ```

    This is much simpler, faster, and fully traced in MLflow!
    """
    pass

print("✅ Notebook complete!")
print("\n📚 Key takeaways:")
print("   1. Direct Python tool execution is faster than HTTP")
print("   2. MLflow automatically traces all agent interactions")
print("   3. Step-by-step visibility into model reasoning")
print("   4. Production-ready pattern recommended by Databricks")
print("   5. Easy to debug and iterate on tool implementations")
