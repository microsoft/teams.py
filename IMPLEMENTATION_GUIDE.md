# Teams Graph Python Implementation Guide

## Overview

This guide provides a step-by-step implementation plan for the Teams Graph Python integration, starting with a quick POC and progressing to a production-ready implementation.

## Branch Structure

- `afreenlikecaffeine/graph-package` - Analysis and planning documents
- `afreenlikecaffeine/graph-implementation` - Implementation work (current)

## Quick POC (30 minutes)

### Goal
Get `context.graph.me.get()` working with minimal code to validate the approach.

### POC Steps (Do This First!)

#### Step 1: Install Dependencies (5 minutes)
```bash
cd packages
# We'll add graph package alongside existing packages
uv add azure-identity msgraph-sdk
```

#### Step 2: Create Minimal Package Structure (5 minutes)
```
packages/graph/
├── pyproject.toml          # Package configuration
├── src/microsoft/teams/graph/
│   ├── __init__.py         # Main exports
│   ├── auth_provider.py    # Teams -> Graph auth bridge
│   └── context_extension.py # ActivityContext.graph property
└── tests/
    └── test_basic.py       # Basic POC tests
```

#### Step 3: Implement Core Auth Bridge (10 minutes)
Create the minimal authentication provider that bridges Teams SDK tokens to Graph SDK.

#### Step 4: Add Context Extension (5 minutes)
Add the `graph` property to `ActivityContext` with lazy initialization.

#### Step 5: Test POC (5 minutes)
Create a simple test that verifies `context.graph.me.get()` works.

## Full Implementation Plan

### Phase 1: Foundation (Week 1)

#### Day 1-2: Package Setup & Core Infrastructure
- [ ] Set up proper package structure with pyproject.toml
- [ ] Implement `TeamsContextAuthProvider` class
- [ ] Add dependency management and version constraints
- [ ] Set up basic test framework

#### Day 3-4: Context Integration
- [ ] Implement `enable_graph_integration()` function
- [ ] Add `ActivityContext.graph` property with lazy loading
- [ ] Implement token caching and refresh logic
- [ ] Add basic error handling

#### Day 5: Testing & Validation
- [ ] Create comprehensive unit tests for auth provider
- [ ] Test with mock Teams SDK context
- [ ] Validate token lifecycle management
- [ ] Performance baseline measurements

### Phase 2: Polish & Error Handling (Week 2)

#### Day 1-2: Error Translation
- [ ] Implement Graph SDK to Teams SDK error translation
- [ ] Add helpful error messages with suggested actions
- [ ] Handle common error scenarios (expired tokens, permissions, etc.)
- [ ] Create custom exception hierarchy

#### Day 3-4: Integration Testing
- [ ] Set up integration tests with real Graph API
- [ ] Test authentication flows end-to-end
- [ ] Validate all major Graph operations work
- [ ] Test error scenarios with real API

#### Day 5: Documentation & Examples
- [ ] Create usage examples for common scenarios
- [ ] Document API patterns and best practices
- [ ] Add troubleshooting guide
- [ ] Performance optimization review

### Phase 3: Production Readiness (Week 3)

#### Day 1-2: Advanced Features
- [ ] Support for custom scopes and configurations
- [ ] Connection pooling optimization
- [ ] Batch operation support
- [ ] Async context manager patterns

#### Day 3-4: Security & Performance
- [ ] Security review and penetration testing
- [ ] Performance benchmarking and optimization
- [ ] Memory usage analysis
- [ ] Token security validation

#### Day 5: Release Preparation
- [ ] Final testing and bug fixes
- [ ] Release notes and migration guide
- [ ] CI/CD pipeline setup
- [ ] Package publishing preparation

## Detailed Implementation Specifications

### POC Implementation Details

#### 1. Package Structure Setup

```bash
# Create the package directory
mkdir -p packages/graph/src/microsoft/teams/graph
mkdir -p packages/graph/tests

# Create __init__.py files for Python module structure
touch packages/graph/src/microsoft/__init__.py
touch packages/graph/src/microsoft/teams/__init__.py
touch packages/graph/src/microsoft/teams/graph/__init__.py
```

#### 2. pyproject.toml Configuration

```toml
[project]
name = "microsoft-teams-graph"
version = "0.1.0"
description = "Microsoft Graph integration for Teams AI Python SDK"
dependencies = [
    "microsoft-teams-api>=0.1.0",
    "microsoft-teams-app>=0.1.0", 
    "azure-identity>=1.15.0",
    "msgraph-sdk>=1.0.0"
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "pytest-mock>=3.10.0"
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/microsoft"]
```

#### 3. Core Auth Provider Implementation

```python
# packages/graph/src/microsoft/teams/graph/auth_provider.py
from azure.core.credentials import AccessToken, TokenCredentiali
from typing import Any, Optional, TYPE_CHECKING
from datetime import datetime, timedelta
import asyncio

if TYPE_CHECKING:
    from microsoft.teams.app.routing import ActivityContext

class TeamsContextAuthProvider(TokenCredential):
    """Bridges Teams SDK authentication with Microsoft Graph SDK."""
    
    def __init__(self, context: 'ActivityContext'):
        self._context = context
        self._cached_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
    
    def get_token(self, *scopes: str, **kwargs: Any) -> AccessToken:
        """Sync version - required by Azure Identity interface."""
        # For POC, use simple sync approach
        # Production version will handle async properly
        if self._is_token_valid():
            return AccessToken(self._cached_token, self._token_expiry)
        
        # Get token from Teams context
        user_token = self._context.user_graph_token
        if not user_token:
            raise ValueError("User must be signed in to access Graph API")
        
        self._cached_token = str(user_token)
        self._token_expiry = user_token.token.valid_to
        
        return AccessToken(self._cached_token, self._token_expiry)
    
    def _is_token_valid(self) -> bool:
        """Check if cached token is still valid."""
        if not self._cached_token or not self._token_expiry:
            return False
        
        # Add 5-minute buffer before expiry
        buffer_time = timedelta(minutes=5)
        return datetime.utcnow() + buffer_time < self._token_expiry
```

#### 4. Context Extension Implementation

```python
# packages/graph/src/microsoft/teams/graph/context_extension.py
from typing import TYPE_CHECKING, Optional
from msgraph import GraphServiceClient
from .auth_provider import TeamsContextAuthProvider

if TYPE_CHECKING:
    from microsoft.teams.app.routing import ActivityContext

def enable_graph_integration():
    """Enable Graph integration for all ActivityContext instances."""
    
    @property
    def graph(self) -> GraphServiceClient:
        """Get Microsoft Graph client configured with user's token."""
        # Lazy initialization
        if not hasattr(self, '_graph_client'):
            if not self.is_signed_in:
                raise ValueError(
                    "User must be signed in to access Graph API. "
                    "Call context.sign_in() first."
                )
            
            # Create auth provider that bridges Teams SDK -> Graph SDK
            auth_provider = TeamsContextAuthProvider(self)
            
            # Create Graph client with Teams SDK auth
            self._graph_client = GraphServiceClient(
                credentials=auth_provider,
                scopes=['https://graph.microsoft.com/.default']
            )
        
        return self._graph_client
    
    # Add graph property to ActivityContext
    from microsoft.teams.app.routing import ActivityContext
    ActivityContext.graph = graph
```

#### 5. Main Package Exports

```python
# packages/graph/src/microsoft/teams/graph/__init__.py
"""Microsoft Graph integration for Teams AI Python SDK."""

from .context_extension import enable_graph_integration
from .auth_provider import TeamsContextAuthProvider

__all__ = [
    'enable_graph_integration',
    'TeamsContextAuthProvider'
]

__version__ = '0.1.0'
```

#### 6. Basic POC Test

```python
# packages/graph/tests/test_basic.py
import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timedelta

from microsoft.teams.graph.auth_provider import TeamsContextAuthProvider
from microsoft.teams.graph import enable_graph_integration

class TestPOC:
    """Basic POC tests to validate the approach."""
    
    def test_auth_provider_with_valid_token(self):
        """Test that auth provider can extract token from context."""
        # Mock Teams SDK context
        mock_context = Mock()
        mock_context.is_signed_in = True
        
        # Mock user token
        mock_token = Mock()
        mock_token.__str__ = Mock(return_value="fake-token-123")
        mock_token.token.valid_to = datetime.utcnow() + timedelta(hours=1)
        mock_context.user_graph_token = mock_token
        
        # Test auth provider
        auth_provider = TeamsContextAuthProvider(mock_context)
        access_token = auth_provider.get_token()
        
        assert access_token.token == "fake-token-123"
        assert access_token.expires_on == mock_token.token.valid_to
    
    def test_auth_provider_no_token(self):
        """Test that auth provider raises error when no token available."""
        mock_context = Mock()
        mock_context.user_graph_token = None
        
        auth_provider = TeamsContextAuthProvider(mock_context)
        
        with pytest.raises(ValueError, match="User must be signed in"):
            auth_provider.get_token()
    
    def test_context_extension_integration(self):
        """Test that context extension can be added."""
        # Enable the integration
        enable_graph_integration()
        
        # Verify the property was added
        from microsoft.teams.app.routing import ActivityContext
        assert hasattr(ActivityContext, 'graph')
        
        # Test property access with signed-in context
        mock_context = Mock(spec=ActivityContext)
        mock_context.is_signed_in = True
        
        # Mock user token
        mock_token = Mock()
        mock_token.__str__ = Mock(return_value="fake-token-123")
        mock_token.token.valid_to = datetime.utcnow() + timedelta(hours=1)
        mock_context.user_graph_token = mock_token
        
        # This should not raise an error (though we can't test the full Graph client without mocking more)
        # For POC, just test that the property exists and can be accessed
        assert callable(getattr(ActivityContext, 'graph').fget)

if __name__ == "__main__":
    pytest.main([__file__])
```

### POC Usage Example

```python
# Example usage in a Teams bot (for testing POC)
from microsoft.teams.app import App
from microsoft.teams.api import MessageActivity
from microsoft.teams.graph import enable_graph_integration

# Enable Graph integration
app = App()
enable_graph_integration()

@app.on_message
async def test_graph_integration(context: ActivityContext[MessageActivity]):
    """Test the Graph integration POC."""
    if not context.is_signed_in:
        await context.sign_in()
        return
    
    try:
        # This is the magic line - zero configuration Graph access!
        me = await context.graph.me.get()
        await context.reply(f"Hello {me.display_name}! Graph integration works!")
        
    except Exception as e:
        await context.reply(f"Graph integration error: {str(e)}")
```

## Implementation Checkpoints

### POC Success Criteria (30 minutes)
- [ ] Package structure created
- [ ] Dependencies installed
- [ ] Auth provider implements basic token extraction
- [ ] Context extension adds `graph` property
- [ ] Basic tests pass
- [ ] Ready for real Teams app testing

### Phase 1 Success Criteria (1 week)
- [ ] Full authentication bridge implementation
- [ ] Comprehensive unit test coverage (>90%)
- [ ] Token caching and refresh working
- [ ] Integration with real Teams SDK context
- [ ] Performance baseline established

### Phase 2 Success Criteria (2 weeks)
- [ ] Error translation working correctly
- [ ] Integration tests with real Graph API passing
- [ ] Documentation and examples complete
- [ ] Common use cases validated

### Phase 3 Success Criteria (3 weeks)
- [ ] Production-ready code quality
- [ ] Security review completed
- [ ] Performance optimized
- [ ] Ready for release

## Next Steps

1. **Start with POC**: Follow the 30-minute POC plan to get basic functionality working
2. **Validate Approach**: Test POC with a real Teams bot to confirm the pattern works
3. **Iterate Based on Feedback**: Use POC learnings to refine the full implementation plan
4. **Implement Phases**: Follow the 3-week implementation plan for production-ready code

## Risk Mitigation

### Potential Issues & Solutions

1. **Authentication Complexity**
   - Risk: Azure Identity integration more complex than expected
   - Mitigation: Start with POC to validate approach early

2. **Token Lifecycle Management**
   - Risk: Token refresh not working correctly
   - Mitigation: Comprehensive testing of token expiry scenarios

3. **Performance Overhead**
   - Risk: Wrapper adds significant latency
   - Mitigation: Performance benchmarking throughout development

4. **Graph SDK API Changes**
   - Risk: Microsoft Graph SDK updates break our integration
   - Mitigation: Pin to specific version, test updates in isolation

Let's start with the POC! This will give us confidence that the approach works before investing in the full implementation.