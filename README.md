# Chicago Marine Knowledge MCP

Thin MCP wrapper around the Chicago Marine Knowledge Service API.

This repo intentionally does not contain direct source connectors or duplicated
condition logic. It calls the REST service and exposes the result through MCP
tools, resources, and prompts.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the wrapper pattern, the
service dependency wiring, and the full MCP-tool-to-endpoint mapping.

## Service Dependency

By default, this MCP server calls:

```text
http://127.0.0.1:8000
```

Override with:

```bash
export MARINE_KNOWLEDGE_SERVICE_URL=https://your-service-host
```

## Install

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## Run Locally

Stdio mode:

```bash
python server.py
```

HTTP/SSE mode:

```bash
python http_server.py
```

The HTTP wrapper defaults to port `3000`. Override locally with:

```bash
PORT=3001 python http_server.py
```

## MCP Tools

```text
check_marine_knowledge_service()
list_marine_places()
get_marine_sources()
get_marine_context(place_id="monroe_harbor", response_profile="compact_llm")
get_marine_conditions(place_id="monroe_harbor", response_profile="compact_llm")
get_sailing_conditions(area_id="chicago_lakefront", response_profile="compact_llm")
```

## MCP Resources

```text
marine://places
marine://sources
```

## MCP Prompt

```text
chicago_marine_briefing_prompt(place_id="monroe_harbor")
lakewide_sailing_conditions_prompt(area_id="chicago_lakefront")
```

## Deployment Note

AWS deployment for MCP servers is coordinated in `~/git/mcp-aws-infra`.
This repo provides the application container; infrastructure resources such as
ECR, ECS, ALB routing, DNS, and GitHub deployment roles should be added there.
The ECS task sets `MARINE_KNOWLEDGE_SERVICE_URL` from the
`chicago_marine_knowledge_service_url` Terraform variable. Use the private
`service_internal_url` output from the `chicago-marine-knowledge-service`
Terraform deployment.

The public MCP endpoint is:

```text
https://chicago-marine-knowledge-mcp.tomschenkjr.net/sse
```

## Valid Place IDs

```text
monroe_harbor
oak_street_beach
foster_beach
63rd_street_beach
```
