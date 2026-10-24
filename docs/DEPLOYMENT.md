# Deployment guide (NOT executed by the author)

> Everything in this project was built and tested **locally** against Azurite and the Functions Core Tools host.
> These commands are a reference for a future deployment; they have **not** been run, so verify names, runtimes and
> flags with `az <command> --help` first. Do not create resources without checking current pricing.

## Local run (verified)
```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements-dev.txt
npx --yes azurite --location .azurite --silent &          # blob emulator on :10000
npm install --prefix .tools azure-functions-core-tools@4  # Functions Core Tools
cp local.settings.sample.json local.settings.json         # then add GOOGLE_API_KEY locally
export KB_STORAGE_BACKEND=azure AZURE_STORAGE_CONNECTION_STRING=UseDevelopmentStorage=true \
       AZURE_STORAGE_API_VERSION=2026-06-06               # pin only if Azurite lags the SDK
python -m kb.cli upload-raw && python -m kb.cli run       # ingest (calls Gemini)
.tools/node_modules/.bin/func start                       # API on :7071
python mcp_server.py                                      # MCP over stdio
pytest                                                    # offline tests; Azurite tests auto-skip if it is down
```

## Azure (unverified reference)
Needs an Azure account (free account: https://azure.microsoft.com/free; requires a payment method for identity
verification). Expected demo cost is a few cents to a few dollars per month; set a budget alert first.
```bash
RG=rg-llm-kb; LOC=eastus; SA=llmkb$RANDOM; APP=llm-kb-$RANDOM; AI=ai-llm-kb
az group create -n $RG -l $LOC
az storage account create -n $SA -g $RG -l $LOC --sku Standard_LRS --allow-blob-public-access false
az monitor app-insights component create -a $AI -g $RG -l $LOC     # may need: az extension add -n application-insights
az functionapp create -n $APP -g $RG --storage-account $SA --flexconsumption-location $LOC \
   --runtime python --runtime-version <version from: az functionapp list-flexconsumption-runtimes>
az functionapp identity assign -n $APP -g $RG                      # managed identity
az role assignment create --assignee <principalId> --role "Storage Blob Data Contributor" \
   --scope $(az storage account show -n $SA -g $RG --query id -o tsv)
az functionapp config appsettings set -n $APP -g $RG --settings KB_STORAGE_BACKEND=azure \
   AZURE_STORAGE_ACCOUNT_URL=https://$SA.blob.core.windows.net GOOGLE_API_KEY=<from your own secure store>
func azure functionapp publish $APP
# cleanup: az group delete -n $RG --yes
```

## Monitoring
Logs are single-line JSON (`event`, `request_id`, counts, durations). Once connected to Application Insights:
```kusto
traces | extend e = parse_json(message) | where e.event in ("pipeline_finished","compile_failed","unhandled_error")
| project timestamp, e.event, e.compiled, e.failed, e.duration_s
```
Suggested alerts (not configured): failed requests > 5 in 15 min; any `compile_failed`; timer `scheduled_ingest` failure.

## Known deployment considerations
- Azure HTTP triggers time out at ~230 s; a cold full ingest (10 Gemini calls) can exceed that via `/ingest`.
  The pipeline is resumable and the timer trigger has a longer limit, so prefer the timer for full runs.
- `fastembed` downloads its ONNX model on first use; plan for the cold start or bake it into the package.
