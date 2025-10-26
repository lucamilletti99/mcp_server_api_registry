# Agent Architecture Comparison

## Overview

This document compares three approaches for building an API Registry agent with Databricks Foundation Models.

---

## Approach 1: FastAPI Frontend Orchestration ❌ (Current - Not Recommended)

### Architecture
```
Browser → React Frontend → FastAPI Backend → Foundation Model
                ↓                ↓
         Parse tool calls  Execute MCP tools
                ↓                ↓
         Send back to    Return results
         Foundation Model
```

### How it works
1. User sends message from browser
2. FastAPI calls Foundation Model with tools
3. **Frontend** parses tool_calls from response
4. **Frontend** makes HTTP calls to `/api/chat/execute-tool` for each tool
5. **Frontend** sends tool results back to model
6. Model generates final response

### Problems
- 🐌 **5-6 network hops per query**
- 🔥 **Complex error handling** at each layer
- 📦 **Serialization overhead** (JSON → Python → JSON → Python)
- 🐛 **Hard to debug** (errors can happen at any layer)
- ❌ **No MLflow tracing** (manual instrumentation needed)
- 💔 **Type handling issues** (ToolResult serialization errors)
- 🌐 **Frontend does backend work** (orchestration logic in React)

### When to use
- **Never recommended** for production
- Only if you need everything in a single web app with no backend logic

---

## Approach 2: Databricks Notebook with MCP Client ✅ (Recommended)

### Architecture
```
Notebook Agent → Foundation Model (1 HTTP call)
       ↓                    ↓
MCP Client          Returns tool_calls
       ↓                    ↓
MCP Server          Execute tools via MCP (1 HTTP call)
(Databricks App)           ↓
       ↓             Return results to model
   Tools
```

### How it works
1. Agent runs in Databricks notebook
2. Connects to MCP server as a client
3. Loads tools from MCP server
4. Calls Foundation Model with tools
5. Model returns tool_calls
6. **Agent** executes tools via MCP client (direct Python)
7. Sends results back to model
8. **MLflow automatically traces everything**

### Benefits
- ⚡ **2-3 network hops** (only model + MCP calls)
- 🎯 **Direct Python execution** for agent logic
- 🔍 **Full MLflow tracing** automatically
- 🐛 **Easy debugging** (print statements, cell execution)
- 📊 **Step-by-step visibility** in notebook
- 🚀 **Production-ready** (official Databricks pattern)
- 🎨 **Beautiful visualization** in Databricks UI
- ♻️  **Reusable** (same MCP server for multiple agents)

### When to use
- ✅ **Interactive analysis and demos**
- ✅ **Development and debugging**
- ✅ **MLflow experiment tracking**
- ✅ **Production agentic workflows**
- ✅ **Scheduled jobs**
- ✅ **Databricks-native applications**

### Code Example
```python
# Connect to MCP server
tools, session = await load_mcp_tools(MCP_SERVER_URL, ws)

# Initialize agent
agent = APIMCPAgent(
    llm_endpoint="databricks-claude-sonnet-4",
    tools=tools,
    mcp_server_url=MCP_SERVER_URL,
    workspace_client=ws
)

# Run query - everything is traced in MLflow!
result = await agent.run("What APIs are in the registry?")
```

---

## Approach 3: Hybrid Pattern ⚡ (Best of Both Worlds)

### Architecture
```
Browser → FastAPI → Notebook Agent Code → Foundation Model
                         ↓                      ↓
                    MCP Client          Returns tool_calls
                         ↓                      ↓
                    MCP Server          Execute via MCP
                  (Databricks App)             ↓
                         ↓              Return results
                      Tools
```

### How it works
1. Keep FastAPI for web interface
2. **Import agent logic from notebook**
3. FastAPI endpoint calls notebook's agent
4. Agent uses MCP client pattern (Approach 2)
5. Return results to browser

### Benefits
- ✅ **Fast MCP-based execution** (Approach 2)
- ✅ **Web interface** for users (browser access)
- ✅ **Full MLflow tracing** (Approach 2)
- ✅ **Production-ready** (Databricks pattern)
- ✅ **Easy debugging** (develop in notebook, deploy via API)

### Implementation
```python
# In server/routers/chat.py
from notebooks.api_registry_mcp_agent import APIMCPAgent, load_mcp_tools

# Load tools once at startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    global AGENT_TOOLS
    ws = WorkspaceClient()
    AGENT_TOOLS, _ = await load_mcp_tools(MCP_SERVER_URL, ws)
    yield

app = FastAPI(lifespan=lifespan)

@router.post('/agent/query')
async def agent_query(request: AgentRequest):
    # Use notebook's agent pattern
    agent = APIMCPAgent(
        llm_endpoint=request.model or "databricks-claude-sonnet-4",
        tools=AGENT_TOOLS,
        mcp_server_url=MCP_SERVER_URL,
        workspace_client=WorkspaceClient()
    )

    # Run agent - fully traced in MLflow!
    result = await agent.run(request.query)

    return {
        "response": result["response"],
        "iterations": result["iterations"],
        "traces": result["traces"]
    }
```

### When to use
- ✅ **Production applications** with web UI
- ✅ **Public-facing APIs**
- ✅ **When you need both notebook development and web access**

---

## Feature Comparison Table

| Feature | FastAPI Frontend ❌ | Notebook MCP ✅ | Hybrid ⚡ |
|---------|-------------------|----------------|----------|
| **Network Hops** | 5-6 | 2-3 | 2-3 |
| **Serialization Overhead** | High | Low | Low |
| **MLflow Tracing** | Manual | Automatic | Automatic |
| **Debugging Ease** | Hard | Easy | Easy |
| **Development Speed** | Slow | Fast | Fast |
| **Production Ready** | No | Yes | Yes |
| **Web Interface** | Yes | No | Yes |
| **Interactive Dev** | No | Yes | Yes |
| **Step-by-step Visibility** | No | Yes | Yes |
| **Code Reusability** | Low | High | High |

---

## Recommendation

### For Development & Demos
**Use Approach 2 (Notebook MCP Agent)**
- Develop in notebooks
- Full MLflow tracing
- Easy to iterate
- Perfect for presentations

### For Production
**Use Approach 3 (Hybrid)**
- Develop agent logic in notebook
- Import into FastAPI for web access
- Get both observability and accessibility
- Best of both worlds

### Never Use
**Approach 1 (FastAPI Frontend Orchestration)**
- Too many network hops
- Complex error handling
- No tracing
- Hard to debug
- Not the Databricks way

---

## Migration Path

If you're currently using Approach 1:

1. **Create the notebook agent** (Approach 2)
   - Follow `notebooks/api_registry_mcp_agent.py`
   - Test with interactive queries
   - Verify MLflow traces work

2. **Integrate with FastAPI** (Approach 3)
   - Import agent from notebook
   - Create new `/agent/query` endpoint
   - Keep existing endpoints for backward compatibility

3. **Migrate frontend**
   - Update React app to call `/agent/query`
   - Remove frontend orchestration logic
   - Simplify error handling

4. **Remove old endpoints**
   - Deprecate `/api/chat/execute-tool`
   - Simplify `/api/chat/message`

---

## Key Takeaways

1. **MCP Client Pattern** (Approach 2) is the official Databricks recommendation
2. **Notebook development** gives you the best debugging experience
3. **MLflow tracing** is automatic when you follow the pattern
4. **Hybrid approach** (Approach 3) works great for production
5. **FastAPI-only orchestration** (Approach 1) should be avoided

---

## Resources

- [Databricks MCP Documentation](https://docs.databricks.com/aws/en/generative-ai/mcp/)
- [LangGraph MCP Agent Example](https://docs.databricks.com/aws/en/notebooks/source/generative-ai/langgraph-mcp-tool-calling-agent.html)
- [OpenAI Agent SDK with MCP](https://docs.databricks.com/aws/en/notebooks/source/generative-ai/openai-mcp-tool-calling-agent.html)
- [Building AI Agents](https://docs.databricks.com/en/generative-ai/tutorials/ai-agents.html)

---

**Bottom Line:** Follow the Databricks pattern. Use notebooks for development, MCP clients for tool execution, and MLflow for tracing. Your future self will thank you! 🚀
