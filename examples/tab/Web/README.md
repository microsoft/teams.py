# Tab Web frontend

The React/Vite frontend for the Tab example. The Python bot serves the built assets.

## Build

```bash
npm install
npm run build
```

> **Microsoft-managed devices:** direct access to `registry.npmjs.org` is blocked, so `npm install` may fail. Your machine should already default to the Central Feed Services (CFS) proxy; if not, follow the setup instructions at [aka.ms/CFS](https://aka.ms/CFS). External contributors are unaffected.

> This sample depends on `@microsoft/teams.*` packages. On a managed device, a newly published version may be held in CFS for ~7 days before it can be installed, so `npm install` can fail to resolve a just-released version until the quarantine clears.
