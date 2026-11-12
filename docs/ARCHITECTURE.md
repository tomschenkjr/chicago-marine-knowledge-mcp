# Architecture

This repo is a **thin MCP wrapper**. It exposes the
[Chicago Marine Knowledge Service](https://github.com/tomschenkjr/chicago-marine-knowledge-service)
REST API as MCP tools, resources, and prompts. It deliberately contains **no**
source connectors and **no** condition logic — all of that lives in the service.

```
   MCP client (Claude, etc.)
        │  MCP over SSE
        ▼
   chicago-marine-knowledge-mcp        ← this repo (thin wrapper)
        │  REST over HTTP
        ▼
   chicago-marine-knowledge-service    ← domain logic, source collection
        │
   City of Chicago · NOAA GLERL Dever Crib · NOAA Weather/Marine MCP
```

## Why a separate wrapper

Keeping the MCP surface separate from the domain service means:

- The service can be tested, versioned, and reused as a plain REST API.
- The MCP layer stays trivial: every tool is a one-line passthrough to the
  client in [`client.py`](../client.py).
- The two deploy independently — the service is a private ECS service; this
  wrapper is the public, internet-facing MCP endpoint.

If you find yourself adding parsing, source calls, or condition logic here,
it belongs in the service instead.

## Components

| File | Responsibility |
| --- | --- |
| [`server.py`](../server.py) | `FastMCP` instance; defines all tools, resources, and prompts |
| [`client.py`](../client.py) | `MarineKnowledgeServiceClient` — async HTTP client for the service REST API |
| [`http_server.py`](../http_server.py) | FastAPI host that mounts the MCP SSE app and adds a `/health` route |
| [`scripts/query_mcp.py`](../scripts/query_mcp.py) | Deterministic SSE test harness (not an LLM) for exercising the tools locally |

## Transports

- **stdio** — `python server.py`. Used for local MCP clients.
- **HTTP/SSE** — `python http_server.py`. Used in production; serves the MCP SSE
  app plus a `/health` endpoint on `PORT` (default `3000`). DNS rebinding
  protection is disabled in `server.py` because the server runs behind a public
  ALB.

## Service dependency

The wrapper resolves the service base URL from `MARINE_KNOWLEDGE_SERVICE_URL`,
falling back to `http://127.0.0.1:8000` for local development. In production this
is set to `http://cmk-service:8000` — the service's ECS Service Connect alias —
by the `mcp-aws-infra` ECS task definition (sourced from the service Terraform's `service_internal_url` output).

```
MARINE_KNOWLEDGE_SERVICE_URL   (this wrapper, env var)
        ▲
        │  set by mcp-aws-infra ECS task definition
        │
chicago_marine_knowledge_service_url   (mcp-aws-infra Terraform variable)
        ▲
        │  copied from
        │
service_internal_url   (chicago-marine-knowledge-service Terraform output)
```

If the service is unreachable, tool calls surface the HTTP error from
`httpx.raise_for_status()`; the wrapper does not retry or cache.

## MCP surface

Tools (see [`server.py`](../server.py) for signatures):

| Tool | Service endpoint |
| --- | --- |
| `check_marine_knowledge_service` | `GET /health` |
| `list_marine_places` | `GET /v1/marine/places` |
| `get_marine_sources` | `GET /v1/marine/sources` |
| `get_marine_context` | `POST /v1/marine/context` |
| `get_marine_conditions` | `POST /v1/marine/context` (condition-focused alias) |
| `get_sailing_conditions` | `POST /v1/marine/sailing-conditions` |

Resources: `marine://places`, `marine://sources` (JSON snapshots of the
corresponding endpoints).

Prompts: `chicago_marine_briefing_prompt`, `lakewide_sailing_conditions_prompt`
— templates that instruct a client to call the right tool and keep the answer
source-grounded.

## Deployment

CI/CD ([`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml)) builds
the container, pushes it to ECR, and rolls the `chicago-marine-knowledge-mcp`
ECS service in `mcp-cluster` on every push to `main`, assuming a GitHub OIDC
role. The shared infrastructure (ECR repo, ECS service, ALB host routing for
`chicago-marine-knowledge-mcp.tomschenkjr.net`, ACM cert, OIDC role, and the
`MARINE_KNOWLEDGE_SERVICE_URL` wiring) is defined in `mcp-aws-infra`. See the
[README](../README.md) deployment note and the `mcp-aws-infra` docs for details.
