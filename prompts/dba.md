# Build Your Own Databricks App

Hello! 👋 This prompt will help you create your own Databricks app from a template!

## Step 1: Check GitHub CLI Installation

First, let me check if you have the GitHub CLI (`gh`) installed. If not, I'll ask if you'd like me to install it for you.

## Step 2: Repository Creation

I'll ask you where you want to create your new repository and what you'd like to name it. Then I'll use the template from:
https://github.com/databricks-solutions/claude-databricks-app-template

I'll show you exactly what command I'm about to run and ask for your confirmation (y/n) before creating the repository.

## Step 3: Repository Access

Once the repository is created, I'll show you the URL to access it on GitHub. I'll handle both SSH and HTTPS access methods as needed.

## Step 4: Local Clone

I'll ask you where on your local disk you'd like to clone the repository. After validating the path, I'll confirm the clone location with you and then clone the repository there.

## Step 5: Follow Template Instructions

Once cloned, I'll read the `.claude/commands/dba.md` file from your new repository and follow those instructions precisely to help you set up your Databricks app.

If there are any issues accessing the cloned directory, I'll ask you to restart Claude in that directory and run `/dba` to continue the setup process.

Let's get started building your Databricks app!