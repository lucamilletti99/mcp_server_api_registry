# API Registry Agent Notebook

## 🎯 Purpose

This notebook demonstrates the **recommended Databricks pattern** for building agentic applications with Foundation Models and custom tools.

## 🏗️ Architecture Comparison

### Current FastAPI Approach (Complex)
```
User Browser
    ↓ (HTTP)
Frontend React App
    ↓ (HTTP POST /api/chat/message)
FastAPI Chat Router
    ↓ (HTTP POST to serving endpoint)
Databricks Foundation Model
    ↓ (returns tool_calls)
Frontend parses response
    ↓ (HTTP POST /api/chat/execute-tool)
FastAPI executes MCP tools
    ↓ (HTTP back)
Frontend sends results back
    ↓ (HTTP POST /api/chat/message again)
Foundation Model generates final response
```

**Problems:**
- 🐌 5+ network hops per query
- 🔥 Complex error handling at each layer
- 📦 Serialization/deserialization overhead
- 🐛 Hard to debug
- 📊 No native MLflow tracing
- 💔 Tool results need careful type handling

### Notebook Approach (Recommended)
```
Notebook Cell
    ↓ (Direct Python call)
run_agent(user_query)
    ↓ (Python function call)
call_foundation_model()
    ↓ (1 HTTP call to serving endpoint)
Foundation Model returns tool_calls
    ↓ (Python function call)
execute_tool()
    ↓ (Direct function execution - NO HTTP!)
Tool returns Python dict
    ↓ (Send back to model)
Foundation Model generates response
    ✅ All traced in MLflow automatically!
```

**Benefits:**
- ⚡ 1-2 network hops per query (only model serving calls)
- 🎯 Direct Python function calls for tools
- 🔍 Full MLflow tracing out of the box
- 🐛 Easy to debug (add print statements anywhere)
- 📊 See step-by-step reasoning in notebook cells
- 🚀 Production-ready pattern
- 🎨 Beautiful visualization in Databricks UI

## 🚀 How to Use

### 1. Open the Notebook in Databricks

Navigate to your Databricks workspace:
- Go to **Workspace** → **Users** → **[your-email]**
- Click on `api_registry_agent.py`

### 2. Run the Setup Cells

Execute the first few cells to:
- Install dependencies
- Enable MLflow tracing
- Define tools and schemas

### 3. Try the Examples

The notebook includes three example queries:
1. **Simple query**: Check API registry health
2. **Complex query**: Multi-tool orchestration
3. **Discovery**: Search for specific APIs

### 4. View MLflow Traces

After running queries:
1. Click the **Experiments** icon in the sidebar
2. Select the latest run
3. View **Traces** tab to see:
   - Complete conversation flow
   - Each tool execution
   - Timing information
   - Input/output at every step

This gives you the "Databricks Playground" experience!

## 📊 MLflow Tracing Benefits

Every agent interaction is automatically logged:

```python
# MLflow captures:
- User query input
- Model calls (with latency)
- Tool executions (with parameters and results)
- Final response
- Total tokens used
- Error traces (if any)
```

You can:
- Compare different model responses
- Debug tool execution failures
- Optimize agent performance
- Monitor production usage
- Create dashboards

## 🔧 Customizing Tools

To add your own tools:

1. **Define the Python function:**
```python
def my_custom_tool(param1: str, param2: int) -> Dict[str, Any]:
    """Tool description for the model."""
    # Your logic here
    return {"result": "data"}
```

2. **Add to tool registry:**
```python
TOOL_REGISTRY["my_custom_tool"] = my_custom_tool
```

3. **Define the schema:**
```python
TOOLS.append({
    "type": "function",
    "function": {
        "name": "my_custom_tool",
        "description": "What the tool does",
        "parameters": {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "First parameter"},
                "param2": {"type": "integer", "description": "Second parameter"}
            },
            "required": ["param1"]
        }
    }
})
```

4. **Test it:**
```python
result = await run_agent("Use my custom tool to...")
```

## 🎯 When to Use This vs FastAPI

| Use Case | Use Notebook | Use FastAPI App |
|----------|-------------|-----------------|
| Interactive analysis | ✅ | ❌ |
| Demos & presentations | ✅ | ❌ |
| Development & debugging | ✅ | ❌ |
| MLflow experiment tracking | ✅ | ⚠️ (harder) |
| Claude CLI integration | ❌ | ✅ |
| Public web interface | ❌ | ✅ |
| Scheduled jobs | ✅ | ✅ (both work) |
| Production APIs for external clients | ❌ | ✅ |

## 🔗 Integration with FastAPI

You can **use both approaches** together:

1. **Keep FastAPI for:**
   - MCP server endpoints (for Claude CLI)
   - Public web UI
   - Admin dashboard

2. **Use Notebook for:**
   - Core agentic logic
   - Tool development
   - MLflow tracing
   - Interactive demos

3. **Import notebook code in FastAPI:**
```python
# In server/routers/chat.py
from notebooks.api_registry_agent import run_agent, TOOLS

@router.post('/agent/query')
async def agent_query(request: AgentRequest):
    # Use the notebook's agentic logic!
    result = await run_agent(request.query, model=request.model)
    return result
```

This gives you the best of both worlds:
- Fast, direct tool execution (notebook pattern)
- Web interface for users (FastAPI)
- Full MLflow tracing (notebook pattern)
- Claude CLI integration (FastAPI MCP server)

## 📚 Resources

- [Databricks Foundation Models](https://docs.databricks.com/en/machine-learning/foundation-models/index.html)
- [Building AI Agents with Foundation Models](https://docs.databricks.com/en/generative-ai/tutorials/ai-agents.html)
- [MLflow Tracing](https://mlflow.org/docs/latest/llms/tracing/index.html)
- [Databricks Apps](https://docs.databricks.com/en/dev-tools/databricks-apps/index.html)

## 🎓 Key Takeaways

1. **Direct Python > HTTP** for tool execution
2. **MLflow tracing** gives you observability for free
3. **Notebook pattern** is recommended by Databricks for agents
4. **FastAPI + Notebook** can work together beautifully
5. **Step-by-step visibility** makes debugging 10x easier

## 🚀 Next Steps

1. Run the notebook and see the traces in MLflow
2. Add your own custom tools
3. Try different Foundation Models (Claude 4, Llama 3.3, etc.)
4. Export the agentic logic to a production API endpoint
5. Set up monitoring dashboards in MLflow

**Have fun building agents! 🤖**
