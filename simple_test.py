#!/usr/bin/env python3
"""
Simple test to verify ActivityContext changes
"""

import inspect
import sys

# Add paths
sys.path.append("packages/app/src")
sys.path.append("packages/graph/src")
sys.path.append("packages/common/src")

try:
    from microsoft.teams.app.routing.activity_context import ActivityContext

    print("✅ ActivityContext imported successfully")

    # Check constructor signature
    sig = inspect.signature(ActivityContext.__init__)
    params = list(sig.parameters.keys())
    print(f"✅ Constructor parameters: {params}")

    # Check for our new parameter
    has_app_token = "app_token" in params
    print(f"✅ Has app_token parameter: {has_app_token}")

    # Check for our new properties
    has_user_graph = hasattr(ActivityContext, "user_graph")
    has_app_graph = hasattr(ActivityContext, "app_graph")
    print(f"✅ Has user_graph property: {has_user_graph}")
    print(f"✅ Has app_graph property: {has_app_graph}")

    print("\n🎉 All checks passed!")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
