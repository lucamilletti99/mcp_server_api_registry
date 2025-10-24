#!/bin/bash
# Wrapper script for running the MCP proxy via uvx

exec uvx --refresh --from git+ssh://git@github.com/databricks-solutions/custom-mcp-databricks-app.git dba-mcp-proxy "$@"