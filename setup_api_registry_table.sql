-- API Registry Table Schema
-- This table stores registered API endpoints for discovery and management

CREATE TABLE IF NOT EXISTS {catalog}.{schema}.api_registry (
  -- Unique identifier for the API
  api_id STRING NOT NULL,

  -- API metadata
  api_name STRING NOT NULL,
  description STRING,
  api_endpoint STRING NOT NULL,
  documentation_url STRING,
  http_method STRING DEFAULT 'GET',
  auth_type STRING DEFAULT 'none',
  token_info STRING,
  request_params STRING DEFAULT '{}',

  -- Status tracking
  status STRING DEFAULT 'pending',
  validation_message STRING,

  -- Audit fields
  user_who_requested STRING,
  created_at TIMESTAMP,
  modified_date TIMESTAMP,

  -- Primary key
  CONSTRAINT api_registry_pk PRIMARY KEY (api_id)
)
COMMENT 'Registry of external API endpoints for discovery and management'
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true'
);
