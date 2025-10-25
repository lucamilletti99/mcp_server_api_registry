#!/bin/bash

# Test script to check API registry table

echo "Testing API registry table..."
echo ""

# Load environment
source .env.local
export DATABRICKS_HOST
export DATABRICKS_TOKEN

APP_URL="https://mcp-server-api-registry-1720970340056130.10.azure.databricksapps.com"
WAREHOUSE_ID="694340ce4f05d316"

echo "1. Testing table existence with DESCRIBE..."
cd dba_mcp_proxy
echo '{"jsonrpc": "2.0", "id": "1", "method": "tools/call", "params": {"name": "execute_dbsql", "arguments": {"query": "DESCRIBE TABLE luca_milletti.custom_mcp_server.api_registry", "warehouse_id": "'$WAREHOUSE_ID'"}}}' | python3 mcp_client.py --databricks-host $DATABRICKS_HOST --databricks-app-url $APP_URL 2>&1

echo ""
echo "2. Testing row count..."
echo '{"jsonrpc": "2.0", "id": "2", "method": "tools/call", "params": {"name": "execute_dbsql", "arguments": {"query": "SELECT COUNT(*) as total_rows FROM luca_milletti.custom_mcp_server.api_registry", "warehouse_id": "'$WAREHOUSE_ID'"}}}' | python3 mcp_client.py --databricks-host $DATABRICKS_HOST --databricks-app-url $APP_URL 2>&1

echo ""
echo "3. Testing SELECT * query..."
echo '{"jsonrpc": "2.0", "id": "3", "method": "tools/call", "params": {"name": "check_api_registry", "arguments": {"warehouse_id": "'$WAREHOUSE_ID'"}}}' | python3 mcp_client.py --databricks-host $DATABRICKS_HOST --databricks-app-url $APP_URL 2>&1
