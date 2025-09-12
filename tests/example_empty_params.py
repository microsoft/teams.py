#!/usr/bin/env python3
"""
Example script demonstrating functions with empty parameters.

This script shows how to create and use AI functions that don't require parameters.
"""

import asyncio

from microsoft.teams.ai import Function


def get_current_time() -> str:
    """Function that returns current time - no parameters needed."""
    import datetime
    return f"Current time is: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"


async def get_random_joke() -> str:
    """Async function that returns a random joke - no parameters needed."""
    jokes = [
        "Why don't scientists trust atoms? Because they make up everything!",
        "Why did the scarecrow win an award? He was outstanding in his field!",
        "Why don't eggs tell jokes? They'd crack each other up!",
    ]
    import random
    return random.choice(jokes)


def main():
    """Demonstrate empty parameter functions."""
    print("=== Empty Parameter Functions Demo ===\n")

    # Create function with no parameters (sync)
    time_function = Function(
        name="get_time",
        description="Get the current time",
        parameter_schema=None,  # No parameters!
        handler=get_current_time,
    )

    # Create async function with no parameters
    joke_function = Function(
        name="get_joke",
        description="Get a random joke",
        parameter_schema=None,  # No parameters!
        handler=get_random_joke,
    )

    print("1. Created sync function with no parameters:")
    print(f"   Name: {time_function.name}")
    print(f"   Description: {time_function.description}")
    print(f"   Parameter Schema: {time_function.parameter_schema}")
    print(f"   Result: {time_function.handler()}")
    print()

    print("2. Created async function with no parameters:")
    print(f"   Name: {joke_function.name}")
    print(f"   Description: {joke_function.description}")
    print(f"   Parameter Schema: {joke_function.parameter_schema}")

    # Test async function
    async def test_async():
        result = await joke_function.handler()
        print(f"   Result: {result}")

    asyncio.run(test_async())
    print()

    print("✅ Successfully demonstrated empty parameter functions!")
    print("   - Functions can now be created with parameter_schema=None")
    print("   - Both sync and async handlers are supported")
    print("   - These functions work with OpenAI models and other AI integrations")


if __name__ == "__main__":
    main()
