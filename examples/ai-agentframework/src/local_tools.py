"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import ast
import json
import math
import operator
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from agent_framework import tool
from pydantic import Field

_BINARY_OPS: dict[type, Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}
_UNARY_OPS: dict[type, Any] = {
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}
_MATH_FUNCS = {name: getattr(math, name) for name in dir(math) if not name.startswith("_")}
_MATH_FUNCS.update({"abs": abs, "round": round})


def _safe_eval(node: ast.expr) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPS:
        return _BINARY_OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_safe_eval(node.operand))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _MATH_FUNCS:
        return _MATH_FUNCS[node.func.id](*(_safe_eval(a) for a in node.args))
    raise ValueError("unsupported expression")


# Shows a simple tool with an optional parameter and no external dependencies.
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


# Shows how to safely evaluate untrusted model-provided input using an AST whitelist instead of eval().
@tool
def calculate(
    expression: Annotated[
        str, Field(description="A mathematical expression (e.g. '15% of 847', '(42 * 18) / 3', 'sqrt(144)', '2 ** 10')")
    ],
) -> str:
    """Evaluate a mathematical expression accurately. Use this for any arithmetic to avoid rounding errors."""
    expr = expression.lower().replace("% of", "/ 100 *").replace("^", "**")
    try:
        result = _safe_eval(ast.parse(expr, mode="eval").body)
        return str(result)
    except Exception as e:
        return f"Error: {e}"


# Shows a tool that makes an external HTTP call and parses a JSON response.
@tool
def get_exchange_rate(
    from_currency: Annotated[str, Field(description="Source currency code (e.g. 'USD', 'EUR', 'GBP')")],
    to_currency: Annotated[str, Field(description="Target currency code (e.g. 'INR', 'JPY', 'CAD')")],
    amount: Annotated[float, Field(description="Amount to convert")] = 1.0,
) -> str:
    """Get the current exchange rate between two currencies and convert an amount. Uses frankfurter.app."""
    url = f"https://api.frankfurter.app/latest?from={from_currency.upper()}&to={to_currency.upper()}"
    with urllib.request.urlopen(url, timeout=10) as response:  # noqa: S310
        data: dict[str, object] = json.loads(response.read())
    rates = data.get("rates", {})
    if not isinstance(rates, dict) or to_currency.upper() not in rates:
        return f"Could not get rate for {from_currency.upper()} → {to_currency.upper()}."
    rate = float(str(rates[to_currency.upper()]))  # type: ignore[arg-type]
    converted = rate * amount
    return f"{amount:g} {from_currency.upper()} = {converted:,.2f} {to_currency.upper()} (rate: {rate})"


tools = [get_current_datetime, calculate, get_exchange_rate]
