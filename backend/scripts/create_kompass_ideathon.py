"""Create the Ideathon team and workflow in Kompass.

What it does, in order:
  1. Finds the Ideathon tools and agents by name (already created in Kompass). Pass
     ``--create-tools-agents`` to create them instead.
  2. Creates the sequential team Cluster -> Rank -> Pitch from those agents.
  3. Creates four workflow components: init -> team agent -> adapter -> output.
  4. Creates the workflow (flow) that links them.

Default is a dry run: every payload is printed and nothing is sent. Pass ``--apply`` to send.

Unverified details are marked ASSUMPTION below. The first --apply run tells us whether they hold.

Environment (never commit values):
  KOMPASS_GATEWAY_URL     API gateway origin (default: staging)
  KOMPASS_TENANT_ID       tenant header (default: devtest)
  KOMPASS_ACCESS_TOKEN    bearer token from staging login (required with --apply)
  HUB_PUBLIC_API_BASE     public KonnektIdea API base the tools call (needed for --create-tools-agents)

Usage:
  python scripts/create_kompass_ideathon.py                  # dry run
  python scripts/create_kompass_ideathon.py --apply          # team + workflow from existing tools/agents
  python scripts/create_kompass_ideathon.py --apply --create-tools-agents
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import httpx

DEFAULT_GATEWAY = "https://aistudio-apigateway-v2-staging.dotkonnekt.com"
AGENTIC_PREFIX = "/api/v2"  # tool-registry, agents, teams: as served by the API gateway
WORKFLOW_PREFIX = "/api/v1"  # flows: as served by the API gateway; components path not in the gateway map
TOOL_AUTH_HEADER = "{{env.AISTUDIO_TOOL_AUTH_TOKEN}}"
TOOL_NAMES = ["ik_get_idea", "ik_ideathon_entries", "ik_search_similar"]
AGENT_NAMES = {
    "ideathon-cluster": "Ideathon Cluster",
    "ideathon-rank": "Ideathon Rank",
    "ideathon-pitch": "Ideathon Pitch",
}
TEAM_NAME = "KonnektIdea Ideathon"
FLOW_NAME = "Ideathon Pipeline"
ORDER = ["ideathon-cluster", "ideathon-rank", "ideathon-pitch"]


# --------------------------------------------------------------------------- #
# tools and agents (only used with --create-tools-agents)
# --------------------------------------------------------------------------- #


def tools(hub_base: str) -> list[dict[str, Any]]:
    """Custom HTTP tools the Ideathon agents call back into the KonnektIdea."""
    common_headers = {"Accept": "application/json", "X-Authorization": TOOL_AUTH_HEADER}
    return [
        {
            "name": "ik_get_idea",
            "description": (
                "Load one idea's title, problem and solution for an Ideathon pitch draft. "
                "Never returns author identity for anonymous ideas."
            ),
            "method": "GET",
            "base_url": f"{hub_base}/internal/agents/ideas/{{{{idea_id}}}}",
            "headers": common_headers,
            "variables": [{"name": "idea_id", "type": "string", "required": True}],
            "status": "active",
            "returns_untrusted_data": True,
        },
        {
            "name": "ik_ideathon_entries",
            "description": "List the ideas entered in an Ideathon: entry ids, phase, theme and shortlist.",
            "method": "GET",
            "base_url": f"{hub_base}/internal/agents/ideathons/{{{{ideathon_id}}}}/entries",
            "headers": common_headers,
            "variables": [{"name": "ideathon_id", "type": "string", "required": True}],
            "status": "active",
            "returns_untrusted_data": True,
        },
        {
            "name": "ik_search_similar",
            "description": "Find ideas similar to a draft or idea, to group them into themes. Excludes anonymous authors.",
            "method": "POST",
            "base_url": f"{hub_base}/internal/agents/ideas/similar",
            "headers": {**common_headers, "Content-Type": "application/json"},
            "body": {
                "title": "{{title}}",
                "problem": "{{problem}}",
                "tags": "{{tags}}",
                "exclude_idea_ids": "{{exclude_idea_ids}}",
                "limit": "{{limit}}",
            },
            "variables": [
                {"name": "title", "type": "string", "required": True},
                {"name": "problem", "type": "string", "required": True},
                {"name": "tags", "type": "array", "items": "string", "required": False},
                {"name": "exclude_idea_ids", "type": "array", "items": "string", "required": False},
                {"name": "limit", "type": "integer", "required": False},
            ],
            "status": "active",
            "returns_untrusted_data": True,
        },
    ]


def agents() -> list[dict[str, Any]]:
    """The three Ideathon agents. Each reads its prompt from Kompass and inherits its model."""
    prompts = {
        "ideathon-cluster": ("ideakonnekt-ideathon-cluster", ["ik_ideathon_entries", "ik_search_similar"]),
        "ideathon-rank": ("ideakonnekt-ideathon-rank", ["ik_ideathon_entries"]),
        "ideathon-pitch": ("ideakonnekt-ideathon-pitch", ["ik_get_idea", "ik_ideathon_entries"]),
    }
    out = []
    for key in ORDER:
        slug, tool_names = prompts[key]
        out.append(
            {
                "key": key,
                "name": AGENT_NAMES[key],
                "description": {
                    "ideathon-cluster": "Groups ideathon entries into themes, with a label and key terms for each theme.",
                    "ideathon-rank": "Proposes an ordered shortlist of ideathon entries, with scores and reasons.",
                    "ideathon-pitch": "Drafts pitch summaries and handoff problem statements for shortlisted ideas.",
                }[key],
                "prompt_slug": slug,
                "inherit": True,
                "framework": "langgraph",
                "tools": tool_names,
                "accessibility": "private",
                "tags": ["ideakonnekt", "ideathon"],
            }
        )
    return out


# --------------------------------------------------------------------------- #
# team and workflow payloads
# --------------------------------------------------------------------------- #


def team_body(agent_ids: dict[str, str]) -> dict[str, Any]:
    """Sequential team: cluster, then rank, then pitch."""
    nodes = [
        {"id": key, "agent_id": agent_ids[key], "position": {"x": 0, "y": i * 160}}
        for i, key in enumerate(ORDER)
    ]
    edges = [{"id": f"{a}-to-{b}", "source": a, "target": b} for a, b in zip(ORDER, ORDER[1:])]
    return {
        "name": TEAM_NAME,
        "type": "sequential",
        "graph": {"type": "sequential", "nodes": nodes, "edges": edges},
        "accessibility": "private",
        "provenance": "client",
    }


def component_bodies(team_slug: str) -> dict[str, dict[str, Any]]:
    """The four workflow components. Keys are the roles, values are the create bodies."""
    return {
        "init": {
            "name": "Ideathon Input",
            "description": "Ideathon id, stage and weights from the caller.",
            "type": "init",
            "version_id": "1.0.0",
            "status": "active",
            "inputs": {"type": "json"},
        },
        "team": {
            "name": "Ideathon Team",
            "description": "Runs the Cluster -> Rank -> Pitch team.",
            "type": "agent",
            "version_id": "1.0.0",
            "status": "active",
            # ASSUMPTION: the agent component accepts a team slug as agent_id, and forwards the
            # input from the init node. Confirm on the first run.
            "inputs": {
                "input_type": "json",
                "agent_id": team_slug,
                "query": "Run the Ideathon pipeline for the ideathon in the input.",
            },
        },
        "adapter": {
            "name": "Ideathon Pack",
            "description": "Keeps the team output as the ideathon pack.",
            "type": "adapter",
            "version_id": "1.0.0",
            "status": "active",
            # ASSUMPTION: "{{agent_output}}" is how the adapter reads the team's reply.
            "inputs": {
                "transform": [{"key": "ideathon_pack", "values": "{{agent_output}}", "convert_to": "json"}]
            },
        },
        "output": {
            "name": "Ideathon Output",
            "description": "Returns the ideathon pack.",
            "type": "output",
            "version_id": "1.0.0",
            "status": "active",
            # ASSUMPTION: "{{ideathon_pack}}" reads the adapter's key.
            "inputs": {"values": {"ideathon_pack": "{{ideathon_pack}}"}},
        },
    }


def flow_body(component_ids: dict[str, str]) -> dict[str, Any]:
    """Workflow: init -> team -> adapter -> output."""
    order = ["init", "team", "adapter", "output"]
    nodes = [{"id": component_ids[role], "type": role} for role in order]
    edges = [
        {"id": f"{component_ids[a]}-to-{component_ids[b]}", "source": component_ids[a], "target": component_ids[b]}
        for a, b in zip(order, order[1:])
    ]
    return {
        "name": FLOW_NAME,
        "description": "Ideathon pipeline: input, Cluster -> Rank -> Pitch team, pack, output.",
        "status": "active",
        "accessibility": "private",
        "version_id": "1.0.0",
        "flow_graph": {"nodes": nodes, "edges": edges},
    }


# --------------------------------------------------------------------------- #
# HTTP helpers
# --------------------------------------------------------------------------- #


def _data(payload: Any) -> Any:
    return payload.get("data", payload) if isinstance(payload, dict) else payload


def _id_from(response: httpx.Response) -> str:
    data = _data(response.json())
    if not isinstance(data, dict) or not data.get("id"):
        raise RuntimeError(f"no id in response: {response.text[:400]}")
    return str(data["id"])


def _items(payload: Any) -> list[dict[str, Any]]:
    """Find the list of records in a list response, whatever the envelope."""
    data = _data(payload)
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for key in ("items", "tools", "agents", "teams", "results"):
            if isinstance(data.get(key), list):
                return [x for x in data[key] if isinstance(x, dict)]
        for value in data.values():
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    return []


def _post(client: httpx.Client, path: str, body: dict[str, Any]) -> httpx.Response:
    response = client.post(path, json=body)
    if response.status_code >= 400:
        raise RuntimeError(f"POST {path} failed {response.status_code}: {response.text[:600]}")
    return response


def _find_by_name(client: httpx.Client, path: str, name: str) -> dict[str, Any]:
    response = client.get(path)
    if response.status_code >= 400:
        raise RuntimeError(f"GET {path} failed {response.status_code}: {response.text[:400]}")
    for item in _items(response.json()):
        if item.get("name") == name:
            return item
    raise RuntimeError(f"'{name}' not found under {path}. Create it in Kompass first, or pass --create-tools-agents.")


# --------------------------------------------------------------------------- #
# run
# --------------------------------------------------------------------------- #


def _print_plan(create_tools_agents: bool, hub_base: str) -> None:
    print("DRY RUN. Nothing is sent. Use --apply to create.\n")
    if create_tools_agents:
        for t in tools(hub_base):
            print(f"TOOL  POST {AGENTIC_PREFIX}/tool-registry  {t['name']}")
            print(json.dumps(t, indent=2))
        for a in agents():
            print(f"AGENT POST {AGENTIC_PREFIX}/agents  {a['name']}")
    else:
        print("TOOLS  looked up by name: " + ", ".join(TOOL_NAMES))
        print("AGENTS looked up by name: " + ", ".join(AGENT_NAMES.values()))
    print(f"\nTEAM  POST {AGENTIC_PREFIX}/teams  {TEAM_NAME}")
    print(json.dumps(team_body({k: f"<{k} id>" for k in ORDER}), indent=2))
    print(f"\nCOMPONENTS POST {WORKFLOW_PREFIX}/components  (init, team agent, adapter, output)")
    print(json.dumps(component_bodies("<team slug>"), indent=2))
    print(f"\nFLOW  POST {WORKFLOW_PREFIX}/flows  {FLOW_NAME}")
    print(json.dumps(flow_body({r: f"<{r} component id>" for r in ["init", "team", "adapter", "output"]}), indent=2))


def run(apply: bool, create_tools_agents: bool) -> int:
    hub_base = (os.environ.get("HUB_PUBLIC_API_BASE") or "").rstrip("/")
    if create_tools_agents and not hub_base:
        print("HUB_PUBLIC_API_BASE is required with --create-tools-agents.", file=sys.stderr)
        return 2

    if not apply:
        _print_plan(create_tools_agents, hub_base or "<HUB_PUBLIC_API_BASE>")
        return 0

    gateway = os.environ.get("KOMPASS_GATEWAY_URL", DEFAULT_GATEWAY).rstrip("/")
    tenant = os.environ.get("KOMPASS_TENANT_ID", "devtest")
    token = os.environ.get("KOMPASS_ACCESS_TOKEN", "")
    if not token:
        print("KOMPASS_ACCESS_TOKEN is not set.", file=sys.stderr)
        return 2

    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant}
    with httpx.Client(base_url=gateway, headers=headers, timeout=60) as client:
        agent_ids: dict[str, str] = {}
        agent_slugs: dict[str, str] = {}
        if create_tools_agents:
            for t in tools(hub_base):
                _post(client, f"{AGENTIC_PREFIX}/tool-registry", t)
                print("created tool", t["name"])
            for a in agents():
                body = {k: v for k, v in a.items() if k != "key"}
                response = _post(client, f"{AGENTIC_PREFIX}/agents", body)
                agent_ids[a["key"]] = _id_from(response)
                print("created agent", a["name"], agent_ids[a["key"]])
        else:
            for t in TOOL_NAMES:
                found = _find_by_name(client, f"{AGENTIC_PREFIX}/tool-registry", t)
                print("found tool", t, found.get("id"))
            for key, name in AGENT_NAMES.items():
                found = _find_by_name(client, f"{AGENTIC_PREFIX}/agents", name)
                agent_ids[key] = str(found["id"])
                print("found agent", name, agent_ids[key])

        team = _post(client, f"{AGENTIC_PREFIX}/teams", team_body(agent_ids))
        team_data = _data(team.json())
        team_slug = str(team_data.get("slug") or "")
        print("created team", TEAM_NAME, team_data.get("id"), "slug:", team_slug)
        if not team_slug:
            raise RuntimeError("team response has no slug; cannot reference it from the workflow.")

        component_ids: dict[str, str] = {}
        for role, body in component_bodies(team_slug).items():
            response = _post(client, f"{WORKFLOW_PREFIX}/components", body)
            component_ids[role] = _id_from(response)
            print("created component", role, component_ids[role])

        flow = _post(client, f"{WORKFLOW_PREFIX}/flows", flow_body(component_ids))
        print("created flow", FLOW_NAME, _id_from(flow))

    print("\nDone.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="send the requests (default: dry run)")
    parser.add_argument(
        "--create-tools-agents",
        action="store_true",
        help="create the tools and agents too, instead of looking them up by name",
    )
    args = parser.parse_args()
    sys.exit(run(apply=args.apply, create_tools_agents=args.create_tools_agents))


if __name__ == "__main__":
    main()
