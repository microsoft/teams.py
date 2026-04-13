"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import json
import math
import random
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Annotated

from agent_framework import tool
from pydantic import Field


@tool
def get_current_datetime(
    utc_offset_hours: Annotated[
        int, Field(description="UTC offset in hours (e.g. -8 for PST, 0 for UTC, 5 for IST)")
    ] = 0,
) -> str:
    """Get the current date and time for a given UTC offset."""
    tz = timezone(timedelta(hours=utc_offset_hours))
    now = datetime.now(tz)
    label = f"UTC{'+' if utc_offset_hours >= 0 else ''}{utc_offset_hours}"
    return now.strftime(f"%A, %B %d, %Y at %I:%M %p ({label})")


@tool
def calculate(
    expression: Annotated[
        str, Field(description="A mathematical expression (e.g. '15% of 847', '(42 * 18) / 3', 'sqrt(144)', '2 ** 10')")
    ],
) -> str:
    """Evaluate a mathematical expression accurately. Use this for any arithmetic to avoid rounding errors."""
    expr = expression.lower().replace("% of", "/ 100 *").replace("^", "**")
    allowed = {name: getattr(math, name) for name in dir(math) if not name.startswith("_")}
    allowed["abs"] = abs
    allowed["round"] = round
    try:
        result = eval(expr, {"__builtins__": {}}, allowed)  # noqa: S307
        return str(result)
    except Exception as e:
        return f"Error: {e}"


@tool
def random_pick(
    items: Annotated[list[str], Field(description="List of items to pick from (e.g. team members, options)")],
    count: Annotated[int, Field(description="Number of items to pick")] = 1,
) -> str:
    """Randomly select one or more items from a list. Use this for standup order, assignments, or picking a winner."""
    if not items:
        return "Error: list is empty."
    count = min(count, len(items))
    picked = random.SystemRandom().sample(items, count)
    if count == 1:
        return picked[0]
    return ", ".join(picked)


@tool
def get_exchange_rate(
    from_currency: Annotated[str, Field(description="Source currency code (e.g. 'USD', 'EUR', 'GBP')")],
    to_currency: Annotated[str, Field(description="Target currency code (e.g. 'INR', 'JPY', 'CAD')")],
    amount: Annotated[float, Field(description="Amount to convert")] = 1.0,
) -> str:
    """Get the current exchange rate between two currencies and convert an amount. Uses frankfurter.app."""
    url = f"https://api.frankfurter.app/latest?from={from_currency.upper()}&to={to_currency.upper()}"
    with urllib.request.urlopen(url) as response:  # noqa: S310
        data: dict[str, object] = json.loads(response.read())
    rates = data.get("rates", {})
    if not isinstance(rates, dict) or to_currency.upper() not in rates:
        return f"Could not get rate for {from_currency.upper()} → {to_currency.upper()}."
    rate = float(str(rates[to_currency.upper()]))  # type: ignore[arg-type]
    converted = rate * amount
    return f"{amount:g} {from_currency.upper()} = {converted:,.2f} {to_currency.upper()} (rate: {rate})"


tools = [get_current_datetime, calculate, random_pick, get_exchange_rate]
