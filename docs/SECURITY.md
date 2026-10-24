# Security model

| Concern | Implementation |
|---|---|
| Secrets in source | None. `GOOGLE_API_KEY` and storage settings come from env / `local.settings.json` (gitignored). `local.settings.sample.json` has an empty key. The only connection string used is the public Azurite shorthand `UseDevelopmentStorage=true`. |
| API authentication | `/search`, `/answer`, `/articles`, `/ingest` use Azure Functions `AuthLevel.FUNCTION`: callers send `x-functions-key`. Keys are issued and stored by the Functions host. `/health` is anonymous. A unit test asserts every protected route's auth level. **Caveat:** the local Core Tools host does not enforce function keys; enforcement applies only on a deployed app and has not been exercised here. |
| MCP access control | MCP server is read-only and exposes exactly three tools (tested). The ingest endpoint is intentionally not exposed. It forwards `KB_API_KEY`; it holds no storage credentials and no Gemini key. |
| Azure → Blob access | Code supports `AZURE_STORAGE_ACCOUNT_URL` + `DefaultAzureCredential` (managed identity when deployed, `az login` locally), so no storage keys are needed in a deployment. Implemented but only the connection-string path has been tested (against Azurite). |
| Data integrity | SHA-256 recorded at upload, verified at every download; tampering raises `IntegrityError` (tested on both backends). Cache files are `.npy` + JSON, not pickle. |
| Input validation | Query ≤ 1000 chars, `top_k` 1–10, body ≤ 10 KB, JSON-object bodies only; blob and container names are validated against path traversal. |
| Error handling | Callers get generic messages plus a `request_id`; details go to structured logs only (tested for non-leakage). |
| Prompt injection | Retrieved wiki text is placed in the prompt. The corpus is owner-controlled; if untrusted users could upload to `raw/`, treat compiled articles as untrusted. Answers are constrained to the provided articles but this is not a hard guarantee. |

## Upgrade path: Microsoft Entra ID
Function keys are shared secrets: simple, but not per-user and hard to revoke selectively. For real enterprise use:
enable App Service Authentication (Easy Auth) on the Function App with an Entra app registration, require
callers to present an Entra access token, and for MCP use the Entra client-credentials flow (or OAuth per the MCP
authorization spec for remote servers). Not implemented.
