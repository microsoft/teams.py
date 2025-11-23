# Deferred AI Test

Test application demonstrating approval workflow using `ApprovalPlugin`.

## What This Demonstrates

This test shows how to use the `ApprovalPlugin` to wrap functions that require human approval before execution.

### How It Works

1. **User asks to buy stocks**: "Buy 10 shares of MSFT"
2. **AI calls the function**: The AI model calls `buy_stock(stock="MSFT", quantity=10)`
3. **Plugin intercepts**: ApprovalPlugin wraps the function and defers execution
4. **Approval requested**: User sees approval request with function details
5. **User responds**: "yes" or "no"
6. **Plugin resumes**:
   - If approved → executes original function and returns result
   - If denied → returns cancellation message

## Usage

```bash
# Start the app
python src/main.py

# In chat, ask to buy stocks
> Buy 10 shares of MSFT

# You'll see approval request
> Approval Required
> Function: buy_stock
> Parameters: {'stock': 'MSFT', 'quantity': 10}
>
> Please respond with:
> - 'yes' or 'approve' to confirm
> - 'no' or 'deny' to cancel

# Respond with approval
> yes

# Stock purchase executes
> ✅ Successfully purchased 10 shares of MSFT. Order executed at market price.
```

## Code Overview

```python
# Create your function
stock_function = Function(
    name="buy_stock",
    description="purchase stocks by specifying ticker symbol and quantity",
    parameter_schema=BuyStockParams,
    handler=lambda params: f"✅ Successfully purchased {params.quantity} shares of {params.stock}",
)

# Wrap it with approval
approval_plugin = ApprovalPlugin(
    sender=ctx,
    fn_names=["buy_stock"]  # Functions that need approval
)

# Add to ChatPrompt
chat_prompt = ChatPrompt(
    model=ai_model,
    functions=[stock_function],
    memory=memory,
).with_plugin(approval_plugin)

# Use normally - approval happens automatically
if await chat_prompt.requires_resuming():
    result = await chat_prompt.resume(ctx.activity)
else:
    result = await chat_prompt.send(ctx.activity.text)
```

## Key Benefits

- ✅ **Clean code**: Just specify which functions need approval
- ✅ **No function modification**: Original functions stay unchanged
- ✅ **Automatic deferral**: Plugin handles all the deferred execution logic
- ✅ **Reusable**: Same plugin works across different ChatPrompts
- ✅ **Natural UX**: AI calls functions normally, approval is transparent
