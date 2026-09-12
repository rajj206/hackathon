# Later Azure Deployment: Personal Pay-As-You-Go Guardrails

This is a deployment **planning note only**. The repository does not provision resources,
select a subscription, or store subscription IDs and credentials.

## Recommended MVP resource boundary

Keep the first personal-subscription deployment intentionally small:

1. One resource group dedicated to the hackathon app.
2. One Azure Container Apps consumption environment.
3. One Container App with minimum replicas `0` and maximum replicas `1`.
4. Optional Azure Files storage only when demo data must survive scale-to-zero/restarts.
5. Optional Azure OpenAI chat deployment for extraction and answer synthesis.
6. Optional Azure AI Speech resource only when recording transcription is demonstrated.

Do not add Azure AI Search, Cosmos DB, Azure SQL, Redis, GPU compute, AKS, or a model-hosting
cluster for this MVP. The in-process retriever and SQLite database are deliberate cost
boundaries.

## Important SQLite constraint

SQLite is appropriate for the local app and a low-traffic, single-replica demonstration.
If it is mounted from Azure Files, keep the Container App at maximum one replica and avoid
concurrent writers. Before enabling multiple replicas or production traffic, move records
to a managed concurrent database and uploaded files to Blob Storage.

For a disposable cloud demo, the app can use ephemeral container storage instead. That is
cheaper and simpler, but records disappear after restart or scale-to-zero.

## Authentication boundary

- Do not put a subscription ID in application settings. Subscription selection belongs to
  deployment tooling/operator context, not runtime code.
- Use `DefaultAzureCredential` for Azure OpenAI. During local Azure integration testing,
  authenticate with `az login`; in Azure, assign a managed identity.
- Grant only the minimum Azure OpenAI data-plane role required by the app.
- The current Azure Speech file adapter requires `AZURE_SPEECH_KEY` and
  `AZURE_SPEECH_REGION`. Store the key in a Container Apps secret at deployment time.
- Never commit `.env`, exported credentials, CLI token caches, or uploaded source material.

## Cost controls before a later deployment

- Create a budget and low-threshold alerts before enabling paid services.
- Confirm Azure OpenAI model availability and quota in the chosen region.
- Use the smallest chat deployment that meets the demo quality requirement.
- Keep local heuristic extraction and local answer generation as the default.
- Enable Azure OpenAI and Speech independently, only for the scenarios being demonstrated.
- Keep Container Apps minimum replicas at zero and maximum replicas at one.
- Apply short retention to application logs and uploaded demo data.
- Delete the resource group after the event if no longer needed.

Prices, free grants, quotas, and regional availability change. Check the Azure pricing
calculator and the subscription's quota pages immediately before deployment rather than
embedding estimates in this repository.

## Runtime settings used later

Only these runtime values are needed by the existing adapters:

```dotenv
DATA_DIR=/data
EXTRACTOR_PROVIDER=azure-openai
CHAT_PROVIDER=azure-openai
TRANSCRIPTION_PROVIDER=local
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/
AZURE_OPENAI_CHAT_DEPLOYMENT=<deployment-name>
AZURE_OPENAI_API_VERSION=2024-10-21
```

For Azure Speech, switch `TRANSCRIPTION_PROVIDER` to `azure-speech` and inject the Speech
key and region through the deployment platform's secret/configuration features. No Azure
configuration is required for the default offline mode.

## Deferred deployment checklist

- Review local tests and source handling.
- Decide whether cloud demo data may be ephemeral.
- Create/select resources interactively in the intended personal subscription.
- Configure managed identity and least-privilege role assignments.
- Add secrets through Azure, not Git.
- Re-run the API smoke path against the deployed URL.
- Confirm scale-to-zero and inspect actual cost after the demo.

No step in this checklist has been executed.

## Concise manual setup

Use the Azure portal when you are ready:

1. Create one resource group in the region you intend to use.
2. If available in the subscription, create an Azure OpenAI resource and deploy one
   small chat model. Record only its endpoint and deployment name in your local `.env`.
3. Grant your signed-in user the Azure OpenAI data-plane user role, run `az login`, and
   keep `AZURE_OPENAI_API_KEY` unset to use `DefaultAzureCredential`.
4. If recording transcription is needed, create one Azure AI Speech resource. Copy its
   key and region into the local environment only; never commit them.
5. Install the optional adapters with `pip install -e ".[azure]"`, select the desired
   providers in `.env`, and start the app with Uvicorn.
6. Open the local web UI, create an expert, and manually upload documents, TXT meeting
   transcripts, or recordings. Compressed audio/video requires `ffmpeg` on `PATH`.
7. After the demo, inspect actual usage and delete optional paid resources when they are
   no longer needed.

No CI/CD system, release workflow, infrastructure template, or automated provisioning is
required for this MVP.
