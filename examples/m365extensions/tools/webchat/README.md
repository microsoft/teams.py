# Web Chat / Direct Line harness

A small Direct Line client for exercising the sample on a **non-Teams** channel, so you can
see the half of the extension that Teams can't show: activities that pass straight
through to the Agents SDK app.

Nothing here is sample-specific — it drives whichever sample is currently bound to the bot
registration's endpoint.

## Setup

The bot itself is created with the [Teams CLI](https://microsoft.github.io/teams-sdk/cli/) — see the
[sample setup](../../README.md#setup). Use `teams app create --azure …` so the bot has an Azure Bot
resource, which is what exposes the Direct Line channel.

Direct Line is an Azure Bot channel, so its secret is fetched with the Azure CLI (the Teams CLI has
no Direct Line command). Direct Line is enabled by default on the Azure Bot registration:

```bash
az bot directline show --name <botName> --resource-group <rg> --with-secrets -o json
```

Then either export it or drop it in `.env` next to these files (gitignored):

```
DIRECTLINE_SECRET=<secret>
```

## Browser UI

```bash
python tools/webchat/serve.py        # http://localhost:3000
```

Serves `index.html` plus a `/api/token` endpoint that exchanges the Direct Line *secret* for
a short-lived *token*, so the secret stays in this process and never reaches the browser.
Use this when you want to see Adaptive Cards render.
