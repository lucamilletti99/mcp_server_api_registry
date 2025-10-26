# Getting Started with the API Registry Agent

## 🎯 What We Built

You now have a **production-ready agent** following the official Databricks pattern for MCP integration!

### Files Created

1. **`api_registry_mcp_agent.py`** - Main notebook with MCP agent
2. **`GETTING_STARTED.md`** - This file
3. **`../docs/agent_architecture_comparison.md`** - Detailed architecture comparison

## 🚀 Quick Start

### Step 1: Open the Notebook in Databricks

1. Log into your Databricks workspace
2. Navigate to **Workspace** → **Users** → **[your-email]**
3. Find `api_registry_mcp_agent.py`
4. Click to open

### Step 2: Run the Setup Cells

Execute the first cells in order:
1. **Install dependencies** - Installs `databricks-sdk`, `mlflow`, `mcp`
2. **Restart Python** - Loads the new packages
3. **Configuration** - Sets your MCP server URL
4. **Load tools** - Connects to your deployed MCP server

### Step 3: Try the Examples

The notebook includes three examples:
- **Example 1**: Check API registry health
- **Example 2**: Discover APIs by query
- **Example 3**: Complex multi-tool query

Run each cell to see the agent in action!

### Step 4: View MLflow Traces

1. Click **Experiments** in the sidebar
2. Select the latest run
3. Click the **Traces** tab
4. Explore:
   - Complete conversation flow
   - Each tool execution with timing
   - Model inputs/outputs
   - Error traces (if any)

This is the "Databricks Playground" experience! 🎨

## 🏗️ Architecture

### How It Works

```
Your Notebook
    ↓
APIMCPAgent class
    ↓ (calls)
Foundation Model (Claude/Llama)
    ↓ (returns tool_calls)
MCP Client
    ↓ (HTTP to deployed app)
Your MCP Server (Databricks App)
    ↓
Tools (check_api_registry, discover_api, etc.)
```

### Key Benefits

- ✅ **2-3 network hops** vs 5-6 in FastAPI approach
- ✅ **Automatic MLflow tracing** - no manual instrumentation
- ✅ **Step-by-step visibility** - see model's reasoning process
- ✅ **Easy debugging** - add print statements anywhere
- ✅ **Production-ready** - official Databricks pattern
- ✅ **Reusable** - same MCP server, multiple use cases

## 📝 Customization

### Change the Model

Edit the configuration cell:
```python
LLM_ENDPOINT = "databricks-meta-llama-3-3-70b-instruct"  # Try Llama!
LLM_ENDPOINT = "databricks-claude-opus-4-1"  # Try Opus!
```

### Add More Tools

Tools are defined in your MCP server (`server/tools.py`):
1. Add new tool function with `@mcp.tool()` decorator
2. Deploy the MCP server: `./deploy.sh`
3. Re-run the "Load tools" cell in notebook
4. New tool is automatically available!

### Adjust Max Iterations

Change in agent initialization:
```python
agent = APIMCPAgent(
    # ... other params
    max_iterations=20  # Allow more tool calls
)
```

## 🔧 Troubleshooting

### "Connection refused" to MCP server

**Problem**: Can't connect to MCP server URL

**Solution**:
1. Verify your MCP server is deployed: `./app_status.sh`
2. Check the URL in the configuration cell
3. Ensure you're authenticated: Check workspace client initialization succeeds

### "Tool not found"

**Problem**: Agent tries to call a tool that doesn't exist

**Solution**:
1. Re-run the "Load tools" cell to refresh
2. Check your MCP server has the tool deployed
3. Verify tool name matches exactly

### "MLflow traces not showing"

**Problem**: Don't see traces in Experiments tab

**Solution**:
1. Ensure `mlflow.autolog()` cell was executed
2. Check you're looking at the correct experiment
3. Wait a few seconds for traces to appear (async logging)

### "Model timeout"

**Problem**: Model call takes too long

**Solution**:
1. Check if Foundation Model endpoint is running
2. Increase timeout in `call_model()` method
3. Simplify the query or reduce tool complexity

## 🎓 Learning Path

### Beginner
1. Run the example queries as-is
2. Modify queries to ask different questions
3. View MLflow traces to understand flow

### Intermediate
1. Add a new tool to your MCP server
2. Test it in the notebook
3. Compare performance of different models

### Advanced
1. Implement streaming responses
2. Add memory/conversation history
3. Deploy as a production endpoint
4. Integrate with FastAPI (hybrid approach)

## 🚀 Next Steps

### Option 1: Keep Using Notebooks (Recommended for Development)

**Pros:**
- Easy development and debugging
- Full MLflow tracing
- Perfect for demos and analysis

**Use cases:**
- Data analysis workflows
- Research and experimentation
- Interactive demos
- Scheduled jobs via Databricks Jobs

### Option 2: Integrate with FastAPI (Recommended for Production)

**Pros:**
- Web interface for users
- REST API for external clients
- Keep the MCP pattern benefits

**How:**
See `docs/agent_architecture_comparison.md` for the **Hybrid Pattern** implementation.

```python
# In server/routers/chat.py
from notebooks.api_registry_mcp_agent import APIMCPAgent

@router.post('/agent/query')
async def agent_query(request: AgentRequest):
    agent = APIMCPAgent(...)
    result = await agent.run(request.query)
    return result
```

### Option 3: Deploy as Databricks Job

**Pros:**
- Scheduled execution
- Production monitoring
- Email notifications

**How:**
1. Create a Databricks job pointing to this notebook
2. Set schedule (hourly, daily, etc.)
3. Configure alerts for failures

## 📚 Resources

### Databricks Documentation
- [Custom MCP Servers](https://docs.databricks.com/aws/en/generative-ai/mcp/custom-mcp)
- [LangGraph MCP Agent Example](https://docs.databricks.com/aws/en/notebooks/source/generative-ai/langgraph-mcp-tool-calling-agent.html)
- [OpenAI Agent SDK with MCP](https://docs.databricks.com/aws/en/notebooks/source/generative-ai/openai-mcp-tool-calling-agent.html)
- [MLflow Tracing](https://mlflow.org/docs/latest/llms/tracing/index.html)

### Your Project Files
- `docs/agent_architecture_comparison.md` - Detailed comparison
- `server/tools.py` - MCP server tool definitions
- `server/app.py` - MCP server setup

## 💡 Tips

### Tip 1: Start Simple
Begin with single-tool queries to understand the flow before trying complex multi-tool scenarios.

### Tip 2: Use MLflow Traces
Always check traces after queries - they show you exactly what the model is thinking!

### Tip 3: Iterate in Notebooks
Develop and test in notebooks, then move to production APIs when stable.

### Tip 4: Monitor Token Usage
Check MLflow traces for token counts - optimize prompts if costs are high.

### Tip 5: Experiment with Models
Different models have different strengths. Claude 4 is great for reasoning, Llama for speed.

## 🎉 You're Ready!

You now have:
- ✅ A working agent following Databricks best practices
- ✅ Full MLflow tracing for observability
- ✅ Easy debugging with notebook cells
- ✅ Production-ready architecture
- ✅ Reusable MCP server

**Start exploring and building amazing agents!** 🤖

---

**Questions?** Check the comparison document or Databricks documentation above.

**Issues?** See the Troubleshooting section.

**Ready for production?** See the Hybrid Pattern in the comparison doc.
