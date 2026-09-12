# ExpertTwin Azure MVP Assessment

## Scope

This is a clean-room, focused MVP inspired by architectural patterns in the upstream
LLM Engineers Handbook repository. No handbook/PDF prose is copied. The target preserves
engineering judgment from user-supplied work history, rather than imitating writing style.

## Reusable patterns assessed

| Upstream pattern | MVP reuse |
|---|---|
| Domain models separated from infrastructure | Pydantic decision, evidence, fingerprint, citation, and API models |
| ETL/feature-engineering stages | Parse → decision extraction → fingerprint derivation → retrieval |
| Chunked evidence retrieval | Page/slide/segment evidence stored in SQLite and ranked locally |
| RAG service boundary | Typed FastAPI endpoints and a provider-driven chat service |
| Configuration externalization | `.env` settings with no embedded credentials |
| Testable pipeline components | Dependency-injected extractor, transcriber, answerer, and database |

## AWS/heavy-stack components deliberately replaced

| Upstream/AWS-oriented component | Azure/local MVP choice | Reason |
|---|---|---|
| SageMaker training/inference | Optional Azure OpenAI chat/extraction | No model hosting or GPU needed |
| S3/data warehouse flows | Local uploads + configurable data directory | Lowest-cost offline demo |
| MongoDB | SQLite | Single-process MVP, durable, zero service cost |
| Qdrant + sentence-transformer downloads | TF-IDF/cosine + lexical overlap | No vector service or heavyweight model |
| ZenML orchestration | Cohesive synchronous application services | Avoid operational overhead for hackathon |
| Fine-tuning/preference training | Decision-record fingerprint | Preserves judgment from evidence, not prose style |
| AWS credentials/roles | DefaultAzureCredential for Azure OpenAI | Passwordless locally/managed identity in Azure |
| Speech assumptions | Azure Speech key-based adapter | The selected Speech SDK file adapter requires a key |

## Target Azure mapping

- **Azure Container Apps**: optional future host; consumption plan can scale to zero.
- **Azure Files or mounted storage**: possible SQLite demo persistence; for production,
  migrate records to Azure SQL or Cosmos DB after concurrency requirements justify it.
- **Azure OpenAI**: optional decision extraction and grounded answer synthesis.
- **Azure AI Speech**: optional recording transcription; configured explicitly with key/region.
- **Managed Identity / DefaultAzureCredential**: used for Azure OpenAI where supported.

No Azure resources are provisioned by this MVP.

For a later personal Pay-As-You-Go deployment, the planned boundary is one Container App
on the consumption plan with minimum replicas zero and maximum replicas one. SQLite
remains a single-replica demo database. Paid Azure OpenAI and Speech adapters are opt-in;
Azure AI Search, managed databases, AKS, GPU compute, and fine-tuning remain excluded.
Subscription selection and credentials are deployment concerns and are not application
configuration.
