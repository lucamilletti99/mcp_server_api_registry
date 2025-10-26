# Databricks notebook source
# MAGIC %md
# MAGIC # API Registry Agent with MCP Integration
# MAGIC
# MAGIC This notebook demonstrates the **official Databricks pattern** for building agents with MCP servers.
# MAGIC
# MAGIC **Architecture:**
# MAGIC ```
# MAGIC Notebook Agent
# MAGIC     ↓
# MAGIC Foundation Model (Claude/Llama)
# MAGIC     ↓ (requests tool calls)
# MAGIC MCP Client
# MAGIC     ↓ (HTTP to your deployed app)
# MAGIC Custom MCP Server (Databricks App)
# MAGIC     ↓
# MAGIC Tools (check_api_registry, discover_api, etc.)
# MAGIC ```
# MAGIC
# MAGIC **Based on Databricks official examples:**
# MAGIC - [LangGraph MCP Agent](https://docs.databricks.com/aws/en/notebooks/source/generative-ai/langgraph-mcp-tool-calling-agent.html)
# MAGIC - [OpenAI Agent SDK with MCP](https://docs.databricks.com/aws/en/notebooks/source/generative-ai/openai-mcp-tool-calling-agent.html)
# MAGIC
# MAGIC **Key Benefits:**
# MAGIC - ✅ All interactions traced in MLflow
# MAGIC - ✅ Reuses your deployed MCP server
# MAGIC - ✅ Production-ready Databricks pattern
# MAGIC - ✅ Step-by-step reasoning visibility

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup: Install Dependencies

# COMMAND ----------

# MAGIC %pip install databricks-sdk mlflow mcp==0.10.0 httpx -q
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration: Set Your MCP Server URL
# MAGIC
# MAGIC Replace with your deployed Databricks App URL

# COMMAND ----------

import os
from databricks.sdk import WorkspaceClient

# TODO: Replace with your MCP server URL from deployment
MCP_SERVER_URL = "https://mcp-server-api-registry-1720970340056130.10.azure.databricksapps.com/mcp"

# Foundation Model endpoint to use
LLM_ENDPOINT = "databricks-claude-sonnet-4"

# Initialize workspace client for authentication
ws = WorkspaceClient()

print(f"✅ MCP Server: {MCP_SERVER_URL}")
print(f"✅ LLM Endpoint: {LLM_ENDPOINT}")
print(f"✅ Workspace: {ws.config.host}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Connect to MCP Server and Load Tools
# MAGIC
# MAGIC We'll connect to your deployed MCP server and discover available tools.

# COMMAND ----------

from mcp import ClientSession
from mcp.client.sse import sse_client
from databricks.sdk.oauth import OAuthClient
import json
from typing import List, Dict, Any
import httpx

# Enable MLflow tracing
import mlflow
mlflow.autolog()
print("✅ MLflow tracing enabled")


class DatabricksOAuthProvider:
    """OAuth provider for Databricks MCP server authentication."""

    def __init__(self, workspace_client: WorkspaceClient):
        self.ws = workspace_client

    def get_token(self) -> str:
        """Get OAuth token for MCP server access."""
        return self.ws.config.token


async def load_mcp_tools(mcp_server_url: str, ws: WorkspaceClient) -> tuple[List[Dict[str, Any]], ClientSession]:
    """Load tools from the MCP server.

    Args:
        mcp_server_url: URL of the deployed MCP server
        ws: Workspace client for authentication

    Returns:
        Tuple of (tools list in OpenAI format, MCP client session)
    """
    print(f"🔌 Connecting to MCP server at {mcp_server_url}...")

    # Create OAuth headers for authentication
    headers = {"Authorization": f"Bearer {ws.config.token}"}

    # Connect to MCP server via SSE
    async with sse_client(mcp_server_url, headers=headers) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            # Initialize the session
            await session.initialize()
            print("✅ Connected to MCP server")

            # List available tools
            tools_response = await session.list_tools()
            print(f"📦 Found {len(tools_response.tools)} tools")

            # Convert MCP tools to OpenAI format
            openai_tools = []
            for tool in tools_response.tools:
                openai_tool = {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description or tool.name,
                        "parameters": tool.inputSchema if hasattr(tool, 'inputSchema') else {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    }
                }
                openai_tools.append(openai_tool)
                print(f"   • {tool.name}: {tool.description}")

            return openai_tools, session

# Load tools asynchronously
import asyncio
tools, mcp_session = await load_mcp_tools(MCP_SERVER_URL, ws)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Define Agent Class
# MAGIC
# MAGIC Following the Databricks pattern, we'll create an agent that:
# MAGIC 1. Calls the Foundation Model with tools
# MAGIC 2. Executes tool calls via MCP
# MAGIC 3. Returns results to the model
# MAGIC 4. Continues until done

# COMMAND ----------

from typing import Optional, Generator
import httpx


class APIMCPAgent:
    """Agent that uses Foundation Models with MCP tool calling.

    This follows the official Databricks pattern for MCP agents.
    """

    def __init__(
        self,
        llm_endpoint: str,
        tools: List[Dict[str, Any]],
        mcp_server_url: str,
        workspace_client: WorkspaceClient,
        max_iterations: int = 10
    ):
        """Initialize the agent.

        Args:
            llm_endpoint: Name of the Foundation Model endpoint
            tools: List of tools in OpenAI format
            mcp_server_url: URL of the MCP server
            workspace_client: Databricks workspace client
            max_iterations: Maximum agentic loop iterations
        """
        self.llm_endpoint = llm_endpoint
        self.tools = tools
        self.mcp_server_url = mcp_server_url
        self.ws = workspace_client
        self.max_iterations = max_iterations

    async def call_model(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """Call the Foundation Model via serving endpoint.

        Args:
            messages: Conversation history
            tools: Available tools for the model

        Returns:
            Model response with content or tool calls
        """
        base_url = self.ws.config.host.rstrip('/')
        token = self.ws.config.token

        payload = {
            "messages": messages,
            "max_tokens": 4096
        }

        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f'{base_url}/serving-endpoints/{self.llm_endpoint}/invocations',
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

    async def execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """Execute a tool via the MCP server.

        Args:
            tool_name: Name of the tool to execute
            tool_args: Arguments for the tool

        Returns:
            Tool result as string
        """
        # Call MCP server to execute tool
        headers = {"Authorization": f"Bearer {self.ws.config.token}"}

        async with sse_client(self.mcp_server_url, headers=headers) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                # Call the tool
                result = await session.call_tool(tool_name, tool_args)

                # Extract text content from result
                content_parts = []
                for content in result.content:
                    if hasattr(content, 'text'):
                        content_parts.append(content.text)

                return "".join(content_parts)

    async def run(self, user_query: str) -> Dict[str, Any]:
        """Run the agentic loop.

        Args:
            user_query: User's question or request

        Returns:
            Final response with traces
        """
        messages = [{"role": "user", "content": user_query}]
        traces = []

        print(f"🤖 Starting agent with query: '{user_query}'")
        print(f"📊 Model: {self.llm_endpoint}")
        print(f"🔧 Tools: {len(self.tools)}")
        print("=" * 80)

        for iteration in range(self.max_iterations):
            print(f"\n🔄 Iteration {iteration + 1}")

            # Call the model
            print("   🧠 Calling model...")
            response = await self.call_model(messages, tools=self.tools)

            # Extract assistant message
            if 'choices' not in response or len(response['choices']) == 0:
                print("   ❌ No response from model")
                break

            choice = response['choices'][0]
            message = choice.get('message', {})
            finish_reason = choice.get('finish_reason', 'unknown')

            print(f"   ✓ Model responded (finish_reason: {finish_reason})")

            # Check for tool calls
            tool_calls = message.get('tool_calls')

            if tool_calls:
                print(f"   🔧 Model requested {len(tool_calls)} tool call(s):")

                # Add assistant message with tool calls
                messages.append({
                    "role": "assistant",
                    "content": message.get('content') or "",
                    "tool_calls": tool_calls
                })

                # Execute each tool
                for tc in tool_calls:
                    tool_name = tc['function']['name']
                    tool_args = json.loads(tc['function']['arguments'])

                    print(f"      → {tool_name}({json.dumps(tool_args)})")

                    # Execute via MCP
                    result = await self.execute_tool(tool_name, tool_args)
                    print(f"      ✓ Result: {result[:100]}...")

                    # Add tool result to conversation
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
                print(f"\n✅ Final response:")
                print(f"   {final_content}")

                messages.append({
                    "role": "assistant",
                    "content": final_content
                })

                return {
                    "response": final_content,
                    "iterations": iteration + 1,
                    "messages": messages,
                    "traces": traces,
                    "finish_reason": finish_reason
                }

        print(f"\n⚠️  Reached max iterations ({self.max_iterations})")
        return {
            "response": "Agent reached maximum iterations",
            "iterations": self.max_iterations,
            "messages": messages,
            "traces": traces,
            "finish_reason": "max_iterations"
        }


# Initialize the agent
agent = APIMCPAgent(
    llm_endpoint=LLM_ENDPOINT,
    tools=tools,
    mcp_server_url=MCP_SERVER_URL,
    workspace_client=ws,
    max_iterations=10
)

print("✅ Agent initialized")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Example 1: Check API Registry Health

# COMMAND ----------

result = await agent.run("What is the health status of the API registry?")

print("\n" + "=" * 80)
print("SUMMARY:")
print(f"Iterations: {result['iterations']}")
print(f"Tools used: {len(result['traces'])}")
if result['traces']:
    print(f"Tool calls: {[t['tool'] for t in result['traces']]}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Example 2: Discover APIs

# COMMAND ----------

result = await agent.run("Search for stock market APIs in the registry and tell me about them")

print("\n" + "=" * 80)
print("SUMMARY:")
print(f"Iterations: {result['iterations']}")
print(f"Tools used: {len(result['traces'])}")
if result['traces']:
    for trace in result['traces']:
        print(f"  • {trace['tool']}: {trace['args']}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Example 3: Complex Multi-Tool Query

# COMMAND ----------

result = await agent.run(
    "Give me insights about the API registry. "
    "First check its health, then list what categories exist, "
    "and finally find any weather-related APIs."
)

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
# MAGIC    - Each model call with latency
# MAGIC    - Tool executions with parameters
# MAGIC    - Complete conversation flow
# MAGIC    - Input/output data at every step
# MAGIC
# MAGIC This gives you the "Databricks Playground" experience with full observability!

# COMMAND ----------

# MAGIC %md
# MAGIC ## Key Takeaways
# MAGIC
# MAGIC **Architecture:**
# MAGIC - ✅ Agent connects to MCP server as a client
# MAGIC - ✅ Tools are defined once in MCP server, used everywhere
# MAGIC - ✅ Foundation Models call tools via MCP protocol
# MAGIC - ✅ MLflow automatically traces everything
# MAGIC
# MAGIC **Advantages of this pattern:**
# MAGIC 1. **Separation of concerns**: Agent logic separate from tool implementation
# MAGIC 2. **Reusability**: Same MCP server can be used by multiple agents/apps
# MAGIC 3. **Scalability**: Tools can access Databricks resources (Unity Catalog, etc.)
# MAGIC 4. **Observability**: Full MLflow tracing out of the box
# MAGIC 5. **Production-ready**: Official Databricks pattern
# MAGIC
# MAGIC **Next steps:**
# MAGIC - Add more tools to your MCP server
# MAGIC - Try different Foundation Models (Claude 4, Llama 3.3, etc.)
# MAGIC - Deploy this agent as a Databricks job
# MAGIC - Integrate with your FastAPI app for web access

# COMMAND ----------

# MAGIC %md
# MAGIC ## Integration with FastAPI
# MAGIC
# MAGIC You can expose this agent via your existing FastAPI app:
# MAGIC
# MAGIC ```python
# MAGIC # In server/routers/chat.py
# MAGIC from notebooks.api_registry_mcp_agent import APIMCPAgent
# MAGIC
# MAGIC @router.post('/agent/query')
# MAGIC async def agent_query(request: AgentRequest):
# MAGIC     agent = APIMCPAgent(
# MAGIC         llm_endpoint=request.model,
# MAGIC         tools=tools,  # loaded once at startup
# MAGIC         mcp_server_url=MCP_SERVER_URL,
# MAGIC         workspace_client=WorkspaceClient()
# MAGIC     )
# MAGIC     result = await agent.run(request.query)
# MAGIC     return result
# MAGIC ```
# MAGIC
# MAGIC This gives you the best of both worlds:
# MAGIC - Fast, efficient MCP tool execution
# MAGIC - Web interface for users
# MAGIC - Full MLflow tracing
# MAGIC - Production-ready Databricks pattern
