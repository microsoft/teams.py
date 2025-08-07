# Teams Graph Integration Demo

This demo application showcases how to use Microsoft Graph APIs within a Teams bot built with the
Teams AI SDK for Python.

## Features

- User authentication via Teams OAuth
- Profile information retrieval
- Email listing with Mail.Read scope
- Proper error handling and user feedback
- Interactive command interface

## Commands

- `signin` - Authenticate with Microsoft Graph
- `profile` - Display user profile information
- `emails` - Show recent emails (requires Mail.Read permission)
- `signout` - Sign out of Microsoft Graph
- `help` - Show available commands

## Setup

1. Configure OAuth connection in Azure Bot registration
2. Set connection name to "graph" (or update `default_connection_name` in app options)
3. Configure appropriate Microsoft Graph permissions:
   - `User.Read` (for profile access)
   - `Mail.Read` (for email access)

## Running

From the demo directory:

```bash
python main.py

Or from the repository root:
python packages/graph/tests/demo/main.py

Architecture

The demo uses the microsoft.teams.graph package which provides:

- get_graph_client() - Main factory function for Graph clients
- get_user_graph_client() - Convenience function with User.Read scope
- TeamsTokenCredential - Bridge between Teams OAuth and Azure identity
```
