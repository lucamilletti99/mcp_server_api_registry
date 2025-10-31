#!/usr/bin/env python3
"""Setup API Registry table in Databricks."""

import os
import sys
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState

def setup_api_registry_table(catalog: str, schema: str, warehouse_id: str = None):
    """Create the api_registry table in the specified catalog.schema.

    Args:
        catalog: Catalog name (e.g., 'luca_milletti')
        schema: Schema name (e.g., 'custom_mcp_server')
        warehouse_id: SQL warehouse ID (optional, will use env var if not provided)
    """
    # Initialize Databricks client
    host = os.environ.get('DATABRICKS_HOST')
    if not host:
        print("❌ DATABRICKS_HOST environment variable not set")
        sys.exit(1)

    print(f"🔐 Connecting to Databricks: {host}")
    w = WorkspaceClient(host=host)

    # Get warehouse ID
    if not warehouse_id:
        warehouse_id = os.environ.get('DATABRICKS_SQL_WAREHOUSE_ID')

    if not warehouse_id:
        # Try to get first available warehouse
        print("📊 No warehouse ID provided, looking for available warehouses...")
        warehouses = list(w.warehouses.list())
        if warehouses:
            warehouse_id = warehouses[0].id
            print(f"✅ Using warehouse: {warehouses[0].name} ({warehouse_id})")
        else:
            print("❌ No SQL warehouses found. Please create one or provide warehouse_id")
            sys.exit(1)

    # Read SQL template
    sql_file = os.path.join(os.path.dirname(__file__), 'setup_api_registry_table.sql')
    with open(sql_file, 'r') as f:
        sql_template = f.read()

    # Replace placeholders
    sql = sql_template.replace('{catalog}', catalog).replace('{schema}', schema)

    # Split into individual statements (simple split by semicolon)
    statements = [s.strip() for s in sql.split(';') if s.strip() and not s.strip().startswith('--')]

    print(f"\n📝 Creating api_registry table in {catalog}.{schema}...")
    print(f"🔧 Using SQL warehouse: {warehouse_id}\n")

    # Execute each statement
    for i, statement in enumerate(statements, 1):
        if not statement:
            continue

        print(f"Executing statement {i}/{len(statements)}...")
        print(f"  {statement[:100]}...")

        try:
            result = w.statement_execution.execute_statement(
                warehouse_id=warehouse_id,
                statement=statement,
                wait_timeout='30s'
            )

            if result.status.state == StatementState.SUCCEEDED:
                print(f"  ✅ Success\n")
            else:
                error_msg = result.status.error.message if result.status.error else 'Unknown error'
                print(f"  ⚠️  Warning: {error_msg}\n")

        except Exception as e:
            print(f"  ❌ Error: {str(e)}\n")
            # Continue with other statements even if one fails
            continue

    # Verify table was created
    print("🔍 Verifying table creation...")
    verify_query = f"DESCRIBE TABLE {catalog}.{schema}.api_registry"

    try:
        result = w.statement_execution.execute_statement(
            warehouse_id=warehouse_id,
            statement=verify_query,
            wait_timeout='30s'
        )

        if result.status.state == StatementState.SUCCEEDED:
            print(f"✅ Table {catalog}.{schema}.api_registry created successfully!\n")

            # Show table structure
            if result.result and result.result.data_array:
                print("📋 Table structure:")
                columns = [col.name for col in result.manifest.schema.columns]
                for row in result.result.data_array[:10]:  # Show first 10 columns
                    col_name = row[0] if len(row) > 0 else ''
                    col_type = row[1] if len(row) > 1 else ''
                    print(f"  - {col_name}: {col_type}")

            print(f"\n🎉 Setup complete! You can now use {catalog}.{schema}.api_registry")
            return True

    except Exception as e:
        print(f"❌ Failed to verify table: {str(e)}")
        return False


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Setup API Registry table in Databricks')
    parser.add_argument('catalog', help='Catalog name (e.g., luca_milletti)')
    parser.add_argument('schema', help='Schema name (e.g., custom_mcp_server)')
    parser.add_argument('--warehouse-id', help='SQL warehouse ID (optional)')

    args = parser.parse_args()

    setup_api_registry_table(args.catalog, args.schema, args.warehouse_id)
