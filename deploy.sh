#!/bin/bash

# Deploy the Databricks App Template to Databricks.
# For configuration options see README.md and .env.local.
# Usage: ./deploy.sh [--verbose] [--create] [--app-name <name>]

set -e

# Parse command line arguments
VERBOSE=false
CREATE_APP=false
CUSTOM_APP_NAME=""
while [[ $# -gt 0 ]]; do
  case $1 in
    --verbose)
      VERBOSE=true
      echo "🔍 Verbose mode enabled"
      shift
      ;;
    --create)
      CREATE_APP=true
      echo "🔧 App creation mode enabled"
      shift
      ;;
    --app-name)
      CUSTOM_APP_NAME="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1"
      echo "Usage: ./deploy.sh [--verbose] [--create] [--app-name <name>]"
      echo ""
      echo "Options:"
      echo "  --verbose       Enable verbose output"
      echo "  --create        Create the app if it doesn't exist"
      echo "  --app-name      Custom app name (must start with 'mcp-')"
      echo ""
      echo "Example:"
      echo "  ./deploy.sh --app-name mcp-my-custom-registry"
      exit 1
      ;;
  esac
done

# Function to print timing info
print_timing() {
  if [ "$VERBOSE" = true ]; then
    echo "⏱️  $(date '+%H:%M:%S') - $1"
  fi
}

# Load environment variables from .env.local if it exists.
print_timing "Loading environment variables"
if [ -f .env.local ]
then
  set -a
  source .env.local
  set +a
fi

# Handle custom app name if provided
if [ -n "$CUSTOM_APP_NAME" ]; then
  echo "🏷️  Using custom app name: $CUSTOM_APP_NAME"

  # Validate app name starts with "mcp-"
  if [[ ! "$CUSTOM_APP_NAME" =~ ^mcp- ]]; then
    echo "❌ Error: App name must start with 'mcp-'"
    echo "   Provided: $CUSTOM_APP_NAME"
    echo "   Example: mcp-my-custom-registry"
    exit 1
  fi

  # Override DATABRICKS_APP_NAME with custom name
  export DATABRICKS_APP_NAME="$CUSTOM_APP_NAME"
  echo "✅ App name validated: $DATABRICKS_APP_NAME"

  # Update DBA_SOURCE_CODE_PATH to match the custom app name
  # Extract the directory part and replace just the app folder name
  if [ -n "$DBA_SOURCE_CODE_PATH" ]; then
    # Get the parent directory
    PARENT_DIR=$(dirname "$DBA_SOURCE_CODE_PATH")
    # Use custom app name for the folder
    export DBA_SOURCE_CODE_PATH="$PARENT_DIR/$CUSTOM_APP_NAME"
    echo "📁 Updated workspace path: $DBA_SOURCE_CODE_PATH"
  fi
fi

# Validate required configuration
if [ -z "$DBA_SOURCE_CODE_PATH" ]
then
  echo "❌ DBA_SOURCE_CODE_PATH is not set. Please run ./setup.sh first."
  exit 1
fi

if [ -z "$DATABRICKS_APP_NAME" ]
then
  echo "❌ DATABRICKS_APP_NAME is not set. Please run ./setup.sh first or provide --app-name."
  exit 1
fi

if [ -z "$DATABRICKS_AUTH_TYPE" ]
then
  echo "❌ DATABRICKS_AUTH_TYPE is not set. Please run ./setup.sh first."
  exit 1
fi

# Handle authentication based on type
print_timing "Starting authentication"
echo "🔐 Authenticating with Databricks..."

if [ "$DATABRICKS_AUTH_TYPE" = "pat" ]; then
  # PAT Authentication
  if [ -z "$DATABRICKS_HOST" ] || [ -z "$DATABRICKS_TOKEN" ]; then
    echo "❌ PAT authentication requires DATABRICKS_HOST and DATABRICKS_TOKEN. Please run ./setup.sh first."
    exit 1
  fi
  
  echo "Using Personal Access Token authentication"
  export DATABRICKS_HOST="$DATABRICKS_HOST"
  export DATABRICKS_TOKEN="$DATABRICKS_TOKEN"
  
  # Test connection
  if ! databricks current-user me >/dev/null 2>&1; then
    echo "❌ PAT authentication failed. Please check your credentials."
    echo "💡 Try running: databricks auth login --host $DATABRICKS_HOST"
    echo "💡 Or run ./setup.sh to reconfigure authentication"
    exit 1
  fi
  
elif [ "$DATABRICKS_AUTH_TYPE" = "profile" ]; then
  # Profile Authentication
  if [ -z "$DATABRICKS_CONFIG_PROFILE" ]; then
    echo "❌ Profile authentication requires DATABRICKS_CONFIG_PROFILE. Please run ./setup.sh first."
    exit 1
  fi
  
  echo "Using profile authentication: $DATABRICKS_CONFIG_PROFILE"
  
  # Test connection
  if ! databricks current-user me --profile "$DATABRICKS_CONFIG_PROFILE" >/dev/null 2>&1; then
    echo "❌ Profile authentication failed. Please check your profile configuration."
    echo "💡 Try running: databricks auth login --host <your-host> --profile $DATABRICKS_CONFIG_PROFILE"
    echo "💡 Or run ./setup.sh to reconfigure authentication"
    exit 1
  fi
  
else
  echo "❌ Invalid DATABRICKS_AUTH_TYPE: $DATABRICKS_AUTH_TYPE. Must be 'pat' or 'profile'."
  exit 1
fi

echo "✅ Databricks authentication successful"
print_timing "Authentication completed"

# Display configuration summary
echo ""
echo "📋 Deployment Configuration"
echo "============================"
echo "App Name:              $DATABRICKS_APP_NAME"
echo "Workspace Path:        $DBA_SOURCE_CODE_PATH"
echo "Authentication:        $DATABRICKS_AUTH_TYPE"
if [ "$DATABRICKS_AUTH_TYPE" = "profile" ]; then
  echo "Profile:               $DATABRICKS_CONFIG_PROFILE"
else
  echo "Databricks Host:       $DATABRICKS_HOST"
fi
echo "============================"
echo ""

# Function to display app info
display_app_info() {
  echo ""
  echo "📱 App Name: $DATABRICKS_APP_NAME"
  
  # Get app URL
  if [ "$DATABRICKS_AUTH_TYPE" = "profile" ]; then
    APP_URL=$(databricks apps get "$DATABRICKS_APP_NAME" --profile "$DATABRICKS_CONFIG_PROFILE" --output json 2>/dev/null | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('url', 'URL not available'))
except: 
    print('URL not available')
" 2>/dev/null)
  else
    APP_URL=$(databricks apps get "$DATABRICKS_APP_NAME" --output json 2>/dev/null | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('url', 'URL not available'))
except: 
    print('URL not available')
" 2>/dev/null)
  fi
  
  echo "🌐 App URL: $APP_URL"
  echo ""
}

# Display initial app info
display_app_info

# Check if app needs to be created
if [ "$CREATE_APP" = true ]; then
  print_timing "Starting app creation check"
  echo "🔍 Checking if app '$DATABRICKS_APP_NAME' exists..."
  
  # Check if app exists
  if [ "$DATABRICKS_AUTH_TYPE" = "profile" ]; then
    APP_EXISTS=$(databricks apps list --profile "$DATABRICKS_CONFIG_PROFILE" 2>/dev/null | grep -c "^$DATABRICKS_APP_NAME " 2>/dev/null || echo "0")
  else
    APP_EXISTS=$(databricks apps list 2>/dev/null | grep -c "^$DATABRICKS_APP_NAME " 2>/dev/null || echo "0")
  fi
  
  # Clean up the variable (remove any whitespace/newlines)
  APP_EXISTS=$(echo "$APP_EXISTS" | head -1 | tr -d '\n')
  
  if [ "$APP_EXISTS" -eq 0 ]; then
    echo "❌ App '$DATABRICKS_APP_NAME' does not exist. Creating it..."
    echo "⏳ This may take several minutes..."
    
    if [ "$DATABRICKS_AUTH_TYPE" = "profile" ]; then
      if [ "$VERBOSE" = true ]; then
        databricks apps create "$DATABRICKS_APP_NAME" --profile "$DATABRICKS_CONFIG_PROFILE"
      else
        databricks apps create "$DATABRICKS_APP_NAME" --profile "$DATABRICKS_CONFIG_PROFILE" > /dev/null 2>&1
      fi
    else
      if [ "$VERBOSE" = true ]; then
        databricks apps create "$DATABRICKS_APP_NAME"
      else
        databricks apps create "$DATABRICKS_APP_NAME" > /dev/null 2>&1
      fi
    fi
    
    echo "✅ App '$DATABRICKS_APP_NAME' created successfully"
    
    # Verify creation
    if [ "$DATABRICKS_AUTH_TYPE" = "profile" ]; then
      APP_EXISTS=$(databricks apps list --profile "$DATABRICKS_CONFIG_PROFILE" | grep -c "^$DATABRICKS_APP_NAME " || echo "0")
    else
      APP_EXISTS=$(databricks apps list | grep -c "^$DATABRICKS_APP_NAME " || echo "0")
    fi
    
    if [ "$APP_EXISTS" -eq 0 ]; then
      echo "❌ Failed to create app '$DATABRICKS_APP_NAME'"
      exit 1
    fi
  else
    echo "✅ App '$DATABRICKS_APP_NAME' already exists"
  fi
  
  print_timing "App creation check completed"
fi

mkdir -p build

# Generate requirements.txt from pyproject.toml without editable installs
print_timing "Starting requirements generation"
echo "📦 Generating requirements.txt..."
if [ "$VERBOSE" = true ]; then
  echo "Using custom script to avoid editable installs..."
fi

if ! uv run python scripts/generate_semver_requirements.py; then
  echo "❌ Failed to generate requirements.txt"
  echo "💡 Check if pyproject.toml exists and is valid"
  echo "💡 Try running: uv run python scripts/generate_semver_requirements.py"
  exit 1
fi

echo "✅ Requirements generated successfully"
print_timing "Requirements generation completed"

# Build frontend
print_timing "Starting frontend build"
echo "🏗️  Building frontend..."

# Check if node_modules exists
if [ ! -d "client/node_modules" ]; then
  echo "⚠️  node_modules not found. Installing dependencies first..."
  cd client
  if [ "$VERBOSE" = true ]; then
    npm install
  else
    npm install > /dev/null 2>&1
  fi
  if [ $? -ne 0 ]; then
    echo "❌ npm install failed"
    echo "💡 Try running: cd client && npm install"
    exit 1
  fi
  cd ..
  echo "✅ Dependencies installed"
fi

# Build the frontend
cd client
if [ "$VERBOSE" = true ]; then
  npm run build
  BUILD_EXIT_CODE=$?
else
  BUILD_OUTPUT=$(npm run build 2>&1)
  BUILD_EXIT_CODE=$?
fi

if [ $BUILD_EXIT_CODE -ne 0 ]; then
  cd ..
  echo "❌ Frontend build failed"
  echo ""
  echo "Error details:"
  if [ "$VERBOSE" != true ]; then
    echo "$BUILD_OUTPUT"
  fi
  echo ""
  echo "💡 Troubleshooting steps:"
  echo "   1. Check if client/package.json exists"
  echo "   2. Try: cd client && npm install && npm run build"
  echo "   3. Run with --verbose flag to see full output: ./deploy.sh --verbose"
  exit 1
fi

cd ..
echo "✅ Frontend build complete"
print_timing "Frontend build completed"

# Create workspace directory and upload source
print_timing "Starting workspace setup"
echo "📂 Creating workspace directory: $DBA_SOURCE_CODE_PATH"

MKDIR_OUTPUT=""
MKDIR_SUCCESS=false

if [ "$DATABRICKS_AUTH_TYPE" = "profile" ]; then
  if MKDIR_OUTPUT=$(databricks workspace mkdirs "$DBA_SOURCE_CODE_PATH" --profile "$DATABRICKS_CONFIG_PROFILE" 2>&1); then
    MKDIR_SUCCESS=true
  fi
else
  if MKDIR_OUTPUT=$(databricks workspace mkdirs "$DBA_SOURCE_CODE_PATH" 2>&1); then
    MKDIR_SUCCESS=true
  fi
fi

if [ "$MKDIR_SUCCESS" = false ]; then
  echo "❌ Failed to create workspace directory"
  echo ""
  echo "Error details:"
  echo "$MKDIR_OUTPUT"
  echo ""
  echo "💡 Path: $DBA_SOURCE_CODE_PATH"
  echo "💡 Possible causes:"
  echo "   1. You don't have permissions to create directories in /Workspace/Users/"
  echo "   2. The parent directory doesn't exist"
  echo "   3. Invalid characters in the path"
  echo ""
  echo "💡 Try manually creating the directory:"
  if [ "$DATABRICKS_AUTH_TYPE" = "profile" ]; then
    echo "   databricks workspace mkdirs \"$DBA_SOURCE_CODE_PATH\" --profile $DATABRICKS_CONFIG_PROFILE"
  else
    echo "   databricks workspace mkdirs \"$DBA_SOURCE_CODE_PATH\""
  fi
  exit 1
fi

echo "✅ Workspace directory created"

echo "📤 Syncing source code to workspace..."
# Use databricks sync to properly update all files including requirements.txt
if [ "$DATABRICKS_AUTH_TYPE" = "profile" ]; then
  if ! databricks sync . "$DBA_SOURCE_CODE_PATH" --profile "$DATABRICKS_CONFIG_PROFILE"; then
    echo "❌ Failed to sync source code to workspace"
    echo "💡 Check network connectivity and workspace permissions"
    exit 1
  fi
else
  if ! databricks sync . "$DBA_SOURCE_CODE_PATH"; then
    echo "❌ Failed to sync source code to workspace"
    echo "💡 Check network connectivity and workspace permissions"
    exit 1
  fi
fi
echo "✅ Source code synced successfully"
print_timing "Workspace setup completed"

# Deploy to Databricks
print_timing "Starting Databricks deployment"
echo "🚀 Deploying app '$DATABRICKS_APP_NAME' to Databricks..."
echo "   This may take several minutes..."

DEPLOY_SUCCESS=false
if [ "$DATABRICKS_AUTH_TYPE" = "profile" ]; then
  if [ "$VERBOSE" = true ]; then
    if databricks apps deploy "$DATABRICKS_APP_NAME" --source-code-path "$DBA_SOURCE_CODE_PATH" --debug --profile "$DATABRICKS_CONFIG_PROFILE"; then
      DEPLOY_SUCCESS=true
    fi
  else
    if databricks apps deploy "$DATABRICKS_APP_NAME" --source-code-path "$DBA_SOURCE_CODE_PATH" --profile "$DATABRICKS_CONFIG_PROFILE"; then
      DEPLOY_SUCCESS=true
    fi
  fi
else
  if [ "$VERBOSE" = true ]; then
    if databricks apps deploy "$DATABRICKS_APP_NAME" --source-code-path "$DBA_SOURCE_CODE_PATH" --debug; then
      DEPLOY_SUCCESS=true
    fi
  else
    if databricks apps deploy "$DATABRICKS_APP_NAME" --source-code-path "$DBA_SOURCE_CODE_PATH"; then
      DEPLOY_SUCCESS=true
    fi
  fi
fi

if [ "$DEPLOY_SUCCESS" = false ]; then
  echo ""
  echo "❌ Deployment failed"
  echo ""
  echo "💡 Troubleshooting steps:"
  echo "   1. Check if Databricks Apps is enabled in your workspace"
  echo "   2. Verify app.yaml exists and is valid"
  echo "   3. Check app logs: databricks apps logs $DATABRICKS_APP_NAME"
  echo "   4. Run with --verbose for detailed output: ./deploy.sh --verbose"
  echo "   5. See WORKSPACE_REQUIREMENTS.md for prerequisites"
  exit 1
fi

print_timing "Databricks deployment completed"

echo ""
echo "✅ Deployment complete!"
echo ""

# Get the actual app URL from the apps list
echo "🔍 Getting app URL..."
if [ "$DATABRICKS_AUTH_TYPE" = "profile" ]; then
  APP_URL=$(databricks apps list --profile "$DATABRICKS_CONFIG_PROFILE" --output json 2>/dev/null | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    if isinstance(data, list):
        apps = data
    else:
        apps = data.get('apps', [])
    for app in apps:
        if app.get('name') == '"'"'$DATABRICKS_APP_NAME'"'"':
            print(app.get('url', ''))
            break
except: pass
" 2>/dev/null)
else
  APP_URL=$(databricks apps list --output json 2>/dev/null | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    if isinstance(data, list):
        apps = data
    else:
        apps = data.get('apps', [])
    for app in apps:
        if app.get('name') == '"'"'$DATABRICKS_APP_NAME'"'"':
            print(app.get('url', ''))
            break
except: pass
" 2>/dev/null)
fi

if [ -n "$APP_URL" ]; then
  echo "Your app is available at:"
  echo "$APP_URL"
  echo ""
  echo "📊 Monitor deployment logs at (visit in browser):"
  echo "$APP_URL/logz"
else
  # Fallback to workspace URL if we can't get the app URL
  if [ "$DATABRICKS_AUTH_TYPE" = "profile" ]; then
    WORKSPACE_URL=$(databricks workspace current --profile "$DATABRICKS_CONFIG_PROFILE" 2>/dev/null | grep -o 'https://[^/]*' || echo "https://<your-databricks-workspace>")
  else
    WORKSPACE_URL="$DATABRICKS_HOST"
  fi
  echo "Your app should be available at:"
  echo "$WORKSPACE_URL/apps/$DATABRICKS_APP_NAME"
  echo ""
  echo "📊 Monitor deployment logs at (visit in browser):"
  echo "Check 'databricks apps list' for the actual app URL, then add /logz"
fi

echo ""
if [ "$DATABRICKS_AUTH_TYPE" = "profile" ]; then
  echo "To check the status:"
  echo "databricks apps list --profile $DATABRICKS_CONFIG_PROFILE"
else
  echo "To check the status:"
  echo "databricks apps list"
fi
echo ""
echo "💡 If the app fails to start, visit the /logz endpoint in your browser for installation issues."
echo "💡 The /logz endpoint requires browser authentication (OAuth) and cannot be accessed via curl."