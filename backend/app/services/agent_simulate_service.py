# pylint: disable=too-many-lines  # cohesive module; splitting is a separate refactor
"""Local simulated agent turns for Submit assist, help, and author optimizer.

No network, no LLM, no secrets. Used while ``SIMULATE_AGENTS`` is true.
Submit assist is conversational (brainstorm, refine, patch fields) — not a
one-field wizard. Author optimizer is a separate post-submit persona.
Kompass can replace these handlers later via ``AgentGateway`` without changing
router contracts.
"""

from __future__ import annotations

import re
from typing import Any, Optional

from app.config.settings import settings

ENGINE = "mock-heuristic-v1"

# Soft completeness hints (not a forced wizard order).
SUBMIT_FIELDS: list[tuple[str, str, int]] = [
    ("title", "Give your idea a short, specific title (under 120 characters).", 8),
    (
        "problem",
        "Who is affected, what goes wrong, and how often?",
        20,
    ),
    ("solution", "What would you build or change?", 20),
    (
        "beneficiaries",
        "Who benefits — teams, roles, or customers, with rough numbers?",
        12,
    ),
    (
        "success_metrics",
        "What does success look like? Prefer a number: from X to Y by when.",
        12,
    ),
    (
        "tags",
        "Suggest up to 4 short tags (comma or space separated), e.g. tooling, onboarding.",
        1,
    ),
    (
        "effort",
        "Rough effort: reply with S (days), M (weeks), L (a quarter), or XL (multi-quarter).",
        1,
    ),
]

FIELD_LABELS = {
    "title": "title",
    "problem": "problem",
    "solution": "solution",
    "beneficiaries": "beneficiaries",
    "success_metrics": "success metrics",
    "tags": "tags",
    "effort": "effort",
    "category_slug": "category",
}

# Deterministic starter ideas for blank-draft brainstorming.
_STARTERS: list[dict[str, Any]] = [
    {
        "keys": ("onboard", "new hire", "joiners", "ramp"),
        "category_slug": "process",
        "title": "Self-serve onboarding checklist for new joiners",
        "problem": (
            "New joiners wait days for accounts and tribal knowledge. Managers "
            "rebuild the same checklist in chat every cohort, and ramps slip by "
            "about a week."
        ),
        "solution": (
            "A living onboarding checklist with owners, due days, and links to "
            "docs — auto-assigned on day one, with a manager view of blockers."
        ),
        "beneficiaries": "New joiners (~8–12/quarter) and their managers",
        "success_metrics": "Time-to-first-PR from 14 days to under 7 within two cohorts",
        "tags": ["onboarding", "process", "people"],
        "effort": "M",
    },
    {
        "keys": ("incident", "runbook", "outage", "sre", "postmortem"),
        "category_slug": "tech",
        "title": "Auto-draft incident runbooks from chat timelines",
        "problem": (
            "After each incident an SRE spends three to four hours turning the "
            "chat timeline into a runbook; about half of incidents never get one."
        ),
        "solution": (
            "Pull the incident channel transcript, draft a structured runbook "
            "(symptoms, steps, owners), and open it for a five-minute human edit."
        ),
        "beneficiaries": "SRE and on-call engineers (~20 people)",
        "success_metrics": "Runbook coverage from ~50% to 90% of Sev-1/2 within a quarter",
        "tags": ["sre", "incidents", "tooling"],
        "effort": "L",
    },
    {
        "keys": ("cost", "spend", "budget", "cloud", "staging"),
        "category_slug": "tech",
        "title": "Sleep unused staging environments outside work hours",
        "problem": (
            "Staging stacks stay up nights and weekends. Cloud spend on idle "
            "environments is roughly a third of the non-prod bill."
        ),
        "solution": (
            "Schedule sleep/wake for non-prod with a one-click wake command and "
            "an override label for long-running tests."
        ),
        "beneficiaries": "Platform and product engineering teams",
        "success_metrics": "Cut non-prod idle spend 30% within 60 days without blocking releases",
        "tags": ["cloud", "cost", "platform"],
        "effort": "M",
    },
    {
        "keys": ("sales", "support", "customer", "ticket", "escalat"),
        "category_slug": "business",
        "title": "Ask-the-roadmap assistant for sales and support",
        "problem": (
            "Sales and support answer roadmap questions from memory or ping PMs. "
            "Answers drift and confidential items sometimes leak into chat."
        ),
        "solution": (
            "An internal assistant grounded on the published roadmap and decision "
            "notes; it cites sources and declines anything marked confidential."
        ),
        "beneficiaries": "Sales, CS, and support (~40 people)",
        "success_metrics": "Halve PM pings about public roadmap questions in 90 days",
        "tags": ["sales-enablement", "knowledge-base", "agents"],
        "effort": "M",
    },
    {
        "keys": ("meeting", "handoff", "approval", "process", "workflow"),
        "category_slug": "process",
        "title": "Replace status meetings with a weekly async digest",
        "problem": (
            "Weekly status meetings run 45 minutes for updates that fit in a "
            "paragraph. Attendance is uneven and decisions get rehashed."
        ),
        "solution": (
            "A Friday async digest template (wins, risks, asks) with a 48-hour "
            "comment window; reserve live time only for blocked decisions."
        ),
        "beneficiaries": "Cross-functional delivery teams (~6 squads)",
        "success_metrics": "Drop recurring status meeting time 50% in one quarter",
        "tags": ["meetings", "async", "process"],
        "effort": "S",
    },
]

_DEFAULT_STARTER = {
    "category_slug": "innovation",
    "title": "Prototype an internal idea-shaping chat for authors",
    "problem": (
        "People with half-formed ideas stall on the blank submit form. Drafts "
        "stay empty or get abandoned before reviewers ever see them."
    ),
    "solution": (
        "A conversational assist that brainstorms a starter draft, then refines "
        "title, problem, solution, tags, and metrics in to-and-fro turns."
    ),
    "beneficiaries": "Anyone submitting ideas (contributors across teams)",
    "success_metrics": "Raise draft→submit conversion 20% within two months",
    "tags": ["innovation", "agents", "submit"],
    "effort": "M",
}

HELP_FAQ: list[dict[str, Any]] = [
    {
        "id": "submit",
        "keywords": ("submit", "draft", "new idea", "create idea", "write an idea"),
        "reply": (
            "To submit an idea: open Submit in the sidebar (or My ideas → New). "
            "Chat with the Submit assistant to brainstorm from scratch or refine "
            "fields, or fill the draft form yourself. Save a draft anytime, then "
            "Submit idea. The assistant is Simulated until Kompass is wired."
        ),
        "links": [{"label": "Submit an idea", "href": "/submit"}],
    },
    {
        "id": "review",
        "keywords": ("review", "score", "decide", "accept", "park", "decline", "queue"),
        "reply": (
            "Reviewers open Review for their panel queue, pick up an idea, score "
            "Impact / Effort / Alignment (1–5), then record a decision with a "
            "written reason (≥20 characters). A Simulated Review Intelligence "
            "brief can suggest scores — you confirm before saving."
        ),
        "links": [{"label": "Review queue", "href": "/review"}],
    },
    {
        "id": "roles",
        "keywords": ("role", "reviewer", "admin", "contributor", "leadership", "permission"),
        "reply": (
            "Common roles: contributor (submit & discuss), reviewer (score & decide "
            "on a panel), leadership (approvals / hours), admin (platform settings, "
            "users, categories). Your account can hold more than one role."
        ),
        "links": [{"label": "Home", "href": "/"}],
    },
    {
        "id": "explore",
        "keywords": ("explore", "find", "search", "browse", "follow"),
        "reply": (
            "Explore lists submitted ideas you can open, follow, comment on, and "
            "vote for. Use filters and search to find similar work before you submit."
        ),
        "links": [{"label": "Explore", "href": "/explore"}],
    },
    {
        "id": "agents",
        "keywords": ("agent", "kompass", "simulated", "ai", "assistant"),
        "reply": (
            "Idea Hub agents are Simulated today — local heuristics, labelled "
            "Simulated in the UI. Live Kompass agents will plug in later through "
            "the same AgentGateway seam. Agents propose; humans decide. They never "
            "write scores or decisions of record."
        ),
        "links": [{"label": "Agent hub", "href": "/agents"}],
    },
    {
        "id": "sso_mfa",
        "keywords": (
            "sso",
            "microsoft",
            "entra",
            "mfa",
            "totp",
            "password",
            "login",
            "otp",
            "2fa",
        ),
        "reply": (
            "Sign-in options depend on admin policy: email + password with a "
            "one-time code (OTP), optional authenticator MFA (TOTP), and Microsoft "
            "Entra SSO when enabled. Idea Hub never asks you to paste secrets into "
            "chat. Manage MFA under Account settings when available."
        ),
        "links": [
            {"label": "Log in", "href": "/login"},
            {"label": "Account settings", "href": "/settings"},
        ],
    },
    {
        "id": "admin",
        "keywords": ("admin", "category", "panel", "timeline", "users", "platform"),
        "reply": (
            "Admins use Admin to manage users/roles, categories, review panels, "
            "and timelines. Only accounts with the admin role see that nav item."
        ),
        "links": [{"label": "Admin", "href": "/admin"}],
    },
    {
        "id": "ideathons",
        "keywords": ("ideathon", "challenge", "contest"),
        "reply": (
            "Ideathons are time-boxed challenges. Enter from Ideathons while a "
            "round is open — entries are ordinary ideas with the normal review path."
        ),
        "links": [{"label": "Ideathons", "href": "/ideathons"}],
    },
]

_SECRETISH = re.compile(
    r"(?i)(password|secret|api[_-]?key|token|otp|bearer|authorization)\s*[:=]\s*\S+"
)

_CAT_SLUGS = {
    "tech": ("tech", "engineering", "infra", "platform", "tooling", "code"),
    "business": ("business", "revenue", "sales", "pricing", "customer", "gtm"),
    "process": ("process", "workflow", "meeting", "handoff", "ops", "people"),
    "innovation": ("innovation", "ai", "agent", "llm", "prototype", "kompass"),
}


def simulation_mode() -> bool:
    """Return True when local stubs should handle agent UX."""
    return bool(settings.SIMULATE_AGENTS)


def _meta() -> dict[str, Any]:
    return {
        "simulated": True,
        "engine": ENGINE,
        "mode": "simulate" if simulation_mode() else "kompass-pending",
        "notice": "Simulated — Kompass soon",
    }


def _draft_get(draft: dict[str, Any], key: str) -> str:
    aliases = {
        "success_metrics": ("success_metrics", "success"),
    }
    for k in aliases.get(key, (key,)):
        val = draft.get(k)
        if val is not None:
            if isinstance(val, list):
                return " ".join(str(x) for x in val).strip()
            return str(val).strip()
    return ""


def _field_complete(draft: dict[str, Any], key: str, min_len: int) -> bool:
    if key == "tags":
        tags = draft.get("tags") or []
        if isinstance(tags, list):
            return len(tags) >= 1
        return bool(str(tags).strip())
    if key == "effort":
        return str(draft.get("effort") or "").upper() in {"S", "M", "L", "XL"}
    return len(_draft_get(draft, key)) >= min_len


def next_submit_field(draft: dict[str, Any]) -> Optional[tuple[str, str, int]]:
    for key, prompt, min_len in SUBMIT_FIELDS:
        if not _field_complete(draft, key, min_len):
            return key, prompt, min_len
    return None


def _draft_empty(draft: dict[str, Any]) -> bool:
    """True when the client has no meaningful draft text yet."""
    for key, _, min_len in SUBMIT_FIELDS:
        if key in ("tags", "effort"):
            continue
        if _field_complete(draft, key, min_len):
            return False
    if _draft_get(draft, "title"):
        return False
    return True


def _parse_tags(text: str) -> list[str]:
    parts = re.split(r"[,;\n]+|\s{2,}", text)
    out: list[str] = []
    for p in parts:
        tag = re.sub(r"[^a-z0-9\- ]", "", p.strip().lower()).replace(" ", "-")
        if tag and tag not in out:
            out.append(tag[:30])
        if len(out) >= 4:
            break
    if not out and text.strip():
        tag = re.sub(r"[^a-z0-9\- ]", "", text.strip().lower()).replace(" ", "-")
        if tag:
            out.append(tag[:30])
    return out[:4]


def _parse_effort(text: str) -> Optional[str]:
    m = re.search(r"\b(XL|S|M|L)\b", text.upper())
    return m.group(1) if m else None


def _scrub(text: str) -> str:
    """Strip secret-like assignments from user text before echoing."""
    return _SECRETISH.sub("[redacted]", text.strip())


def _patch_labels(patches: dict[str, Any]) -> str:
    names = [FIELD_LABELS.get(k, k.replace("_", " ")) for k in patches]
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]


def _turn(
    *,
    reply: str,
    patches: Optional[dict[str, Any]] = None,
    awaiting_field: Optional[str] = None,
    field_prompt: Optional[str] = None,
    done: bool = False,
) -> dict[str, Any]:
    return {
        **_meta(),
        "reply": reply,
        "patches": patches or {},
        "awaiting_field": awaiting_field,
        "field_prompt": field_prompt,
        "done": done,
    }


def _pick_starter(topic: str) -> dict[str, Any]:
    low = topic.lower()
    for starter in _STARTERS:
        if any(k in low for k in starter["keys"]):
            return {k: v for k, v in starter.items() if k != "keys"}
    if low.strip():
        # Topic-flavoured default: weave the user's words into title/problem.
        topic_clean = re.sub(r"\s+", " ", topic.strip())[:80]
        base = dict(_DEFAULT_STARTER)
        base["title"] = f"Improve {topic_clean}"[:120]
        base["problem"] = (
            f"Teams keep hitting friction around “{topic_clean}”. Today it is "
            "handled ad hoc, so time is lost and quality varies."
        )
        base["solution"] = (
            f"A focused change that makes “{topic_clean}” clearer, faster, and "
            "measurable — starting with a small prototype."
        )
        base["tags"] = _parse_tags(topic_clean) or list(base["tags"])
        return base
    return dict(_DEFAULT_STARTER)


def _starter_patches(starter: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": starter["title"],
        "problem": starter["problem"],
        "solution": starter["solution"],
        "beneficiaries": starter["beneficiaries"],
        "success_metrics": starter["success_metrics"],
        "tags": list(starter["tags"]),
        "effort": starter["effort"],
        "category_slug": starter["category_slug"],
    }


def _detect_category_slug(text: str) -> Optional[str]:
    low = text.lower()
    for slug, keys in _CAT_SLUGS.items():
        if any(k in low for k in keys):
            return slug
    return None


def _shorten_title(title: str) -> str:
    t = re.sub(r"\s+", " ", title.strip())
    # Drop soft lead-ins
    t = re.sub(
        r"^(a |an |the |proposal (to|for) |idea (to|for) )",
        "",
        t,
        flags=re.I,
    )
    if len(t) <= 48:
        return t[:120]
    # Prefer cutting at a separator
    for sep in (" — ", " - ", ": ", ", "):
        if sep in t:
            head = t.split(sep, 1)[0].strip()
            if 12 <= len(head) <= 60:
                return head[:120]
    words = t.split()
    clipped = " ".join(words[:6]).rstrip(",.;:")
    return (clipped or t[:48]).strip()[:120]


def _enrich_metrics(draft: dict[str, Any]) -> str:
    existing = _draft_get(draft, "success_metrics")
    title = _draft_get(draft, "title") or "this idea"
    if existing and re.search(r"\d", existing):
        return existing
    if existing:
        return f"{existing.rstrip('.')}. Target: improve the key metric 20% within 90 days."
    return (
        f"For “{title[:40]}”: move the primary metric from baseline X to Y "
        "within 90 days (define X/Y with the owner)."
    )


def _enrich_beneficiaries(draft: dict[str, Any]) -> str:
    existing = _draft_get(draft, "beneficiaries")
    if existing and re.search(r"\d", existing):
        return existing
    if existing:
        return f"{existing.rstrip('.')} (~estimate headcount or % of users)."
    return "Primary users of this workflow, plus their managers (~order-of-magnitude headcount)."


def _refine_problem(text: str) -> str:
    t = text.strip()
    if len(t) >= 40:
        return t
    return (
        f"{t.rstrip('.')} — who is affected, how often it happens, and what it "
        "costs in time or quality."
    )


def _refine_solution(text: str) -> str:
    t = text.strip()
    if len(t) >= 40:
        return t
    return (
        f"{t.rstrip('.')}. Start with a thin slice: one workflow, clear owners, "
        "and a way to measure before/after."
    )


def _is_brainstorm(msg: str) -> bool:
    low = msg.lower()
    cues = (
        "brainstorm",
        "from scratch",
        "no idea",
        "don't know",
        "dont know",
        "need an idea",
        "give me an idea",
        "suggest an idea",
        "propose an idea",
        "help me think",
        "blank",
        "start over",
        "starter",
        "inspire",
    )
    return any(c in low for c in cues) or low in {"idea", "help", "hi", "hello", "hey"}


def _intent_shorten_title(msg: str) -> bool:
    low = msg.lower()
    return (
        "title" in low
        and any(w in low for w in ("short", "shorter", "tighten", "concise", "trim"))
    ) or "shorter title" in low or "shorten the title" in low or "shorten title" in low


def _intent_metrics(msg: str) -> bool:
    low = msg.lower()
    return any(
        w in low
        for w in ("metric", "metrics", "success", "kpi", "measure", "measurable")
    )


def _intent_tags(msg: str) -> bool:
    low = msg.lower()
    return bool(re.search(r"\btags?\b", low))


def _intent_effort(msg: str) -> bool:
    low = msg.lower()
    return "effort" in low or bool(re.search(r"\b(size|t-shirt|tshirt)\b", low))


def _intent_category(msg: str) -> bool:
    low = msg.lower()
    return "categor" in low or bool(_detect_category_slug(low) and "make it" in low)


def _intent_beneficiaries(msg: str) -> bool:
    low = msg.lower()
    return any(w in low for w in ("beneficiar", "who benefits", "audience", "users"))


_REFINE_WORDS: tuple[str, ...] = ("improve", "rewrite", "refine", "expand", "add")


def _asks_refine(msg: str) -> bool:
    """True when the chat message asks to improve or rewrite existing copy."""
    lowered = msg.lower()
    return any(word in lowered for word in _REFINE_WORDS)


def _intent_problem(msg: str) -> bool:
    low = msg.lower()
    return any(
        w in low
        for w in ("problem", "pain", "issue", "friction", "who is affected")
    )


def _intent_solution(msg: str) -> bool:
    low = msg.lower()
    return any(w in low for w in ("solution", "propose", "build", "fix", "approach"))


def _intent_improve_all(msg: str) -> bool:
    low = msg.lower()
    return any(
        w in low
        for w in ("improve", "polish", "refine", "strengthen", "rewrite", "better")
    )


def _apply_legacy_field(
    target: str, msg: str, draft: dict[str, Any]
) -> Optional[dict[str, Any]]:
    """Map a free-form reply onto one field when awaiting_field is set."""
    if target == "tags":
        tags = _parse_tags(msg)
        return {"tags": tags} if tags else None
    if target == "effort":
        eff = _parse_effort(msg)
        return {"effort": eff} if eff else None
    if target == "title":
        return {"title": msg[:120]}
    if target in {
        "problem",
        "solution",
        "beneficiaries",
        "success_metrics",
    }:
        return {target: msg}
    return None


def _conversational_refine(
    draft: dict[str, Any], msg: str
) -> Optional[dict[str, Any]]:
    """Return a turn for mid-draft refine intents, or None if no intent matched."""
    patches: dict[str, Any] = {}

    if _intent_shorten_title(msg):
        title = _draft_get(draft, "title")
        if not title:
            return _turn(
                reply=(
                    "There is no title yet. Tell me the idea in a sentence and I "
                    "will draft one — or say “brainstorm” for a starter idea."
                ),
            )
        patches["title"] = _shorten_title(title)
        return _turn(
            reply=(
                f"Shortened the title to “{patches['title']}”. Say if you want it "
                "punchier, or ask me to tweak problem, metrics, or tags next."
            ),
            patches=patches,
        )

    if _intent_category(msg) or (
        _detect_category_slug(msg)
        and any(w in msg.lower() for w in ("categor", "make it", "change to", "set "))
    ):
        slug = _detect_category_slug(msg)
        if slug:
            patches["category_slug"] = slug
            return _turn(
                reply=(
                    f"Set category to **{slug}**. You can still pick another on the "
                    "draft form."
                ),
                patches=patches,
            )
        return _turn(
            reply=(
                "Which category — tech, business, process, or innovation? "
                "Or pick it on the form."
            ),
            awaiting_field=None,
        )

    if _intent_metrics(msg):
        patches["success_metrics"] = _enrich_metrics(draft)
        return _turn(
            reply=(
                "Updated success metrics with a measurable target. Adjust the "
                "numbers on the form when you know the real baseline."
            ),
            patches=patches,
        )

    if _intent_beneficiaries(msg):
        patches["beneficiaries"] = _enrich_beneficiaries(draft)
        return _turn(
            reply="Updated who benefits — add a rough headcount if you have one.",
            patches=patches,
        )

    if _intent_tags(msg):
        # Explicit tag list in the message, or invent from draft text
        tags = _parse_tags(msg)
        if len(tags) <= 1 and "tag" in msg.lower():
            # User said "add tags" / "better tags" without listing them
            blob = " ".join(
                [
                    _draft_get(draft, "title"),
                    _draft_get(draft, "problem"),
                    _draft_get(draft, "solution"),
                ]
            )
            tags = _parse_tags(blob) or ["innovation", "process"]
        if tags:
            patches["tags"] = tags
            return _turn(
                reply=f"Updated tags: {', '.join(tags)}.",
                patches=patches,
            )

    if _intent_effort(msg):
        eff = _parse_effort(msg)
        if eff:
            patches["effort"] = eff
            return _turn(
                reply=f"Set rough effort to **{eff}**.",
                patches=patches,
            )
        return _turn(
            reply="Rough effort — reply with S, M, L, or XL (days → multi-quarter).",
            awaiting_field="effort",
            field_prompt=SUBMIT_FIELDS[-1][1],
        )

    if _intent_problem(msg) and _asks_refine(msg):
        base = _draft_get(draft, "problem") or msg
        # If message is mostly instruction, refine existing; else treat as new copy
        if len(msg) > 60 and not msg.lower().startswith(
            ("improve", "rewrite", "refine", "expand", "add")
        ):
            patches["problem"] = msg
        else:
            patches["problem"] = _refine_problem(base)
        return _turn(
            reply="Updated the problem statement. Want the solution tightened next?",
            patches=patches,
        )

    if _intent_solution(msg) and _asks_refine(msg):
        base = _draft_get(draft, "solution") or msg
        if len(msg) > 60 and not msg.lower().startswith(
            ("improve", "rewrite", "refine", "expand", "add")
        ):
            patches["solution"] = msg
        else:
            patches["solution"] = _refine_solution(base)
        return _turn(
            reply="Updated the proposed solution. Ask for metrics or tags anytime.",
            patches=patches,
        )

    # Direct title replace: "title: …" or "rename to …"
    m_title = re.match(
        r"(?i)^(?:title\s*[:=]\s*|rename(?:\s+to)?\s+|call it\s+)(.+)$", msg
    )
    if m_title:
        patches["title"] = m_title.group(1).strip()[:120]
        return _turn(
            reply=f"Updated title to “{patches['title']}”.",
            patches=patches,
        )

    if _intent_improve_all(msg) and not _draft_empty(draft):
        if _draft_get(draft, "title"):
            patches["title"] = _shorten_title(_draft_get(draft, "title"))
        if _draft_get(draft, "problem"):
            patches["problem"] = _refine_problem(_draft_get(draft, "problem"))
        if _draft_get(draft, "solution"):
            patches["solution"] = _refine_solution(_draft_get(draft, "solution"))
        patches["success_metrics"] = _enrich_metrics({**draft, **patches})
        patches["beneficiaries"] = _enrich_beneficiaries({**draft, **patches})
        blob = " ".join(
            [
                str(patches.get("title") or _draft_get(draft, "title")),
                str(patches.get("problem") or _draft_get(draft, "problem")),
            ]
        )
        tags = _parse_tags(blob)
        if tags:
            patches["tags"] = tags
        return _turn(
            reply=(
                f"Polished the draft ({_patch_labels(patches)}). Keep chatting to "
                "nudge any field, or edit the form directly."
            ),
            patches=patches,
        )

    return None


def submit_assist_turn(
    *,
    draft: dict[str, Any],
    message: str,
    awaiting_field: Optional[str] = None,
) -> dict[str, Any]:
    """Handle one conversational Submit-assist turn and optionally propose patches.

    Behaviour (simulated heuristics):
    - Empty draft + empty message → brainstorm opener (no forced field wizard).
    - Empty / thin draft + brainstorm or topic → starter idea ``patches``.
    - Mid-draft refine phrases → targeted ``field_patches`` (title, metrics, …).
    - Legacy ``awaiting_field`` still accepts a direct answer for that field.
    - Client should auto-apply ``patches``; this service never persists.

    Args:
        draft: Current form values from the client (not persisted here).
        message: Latest user chat text (may be empty for the opening prompt).
        awaiting_field: Optional soft focus from a prior turn (not required).

    Returns:
        Simulated turn payload with ``reply``, ``patches``, ``awaiting_field``,
        ``done``, and engine metadata. Never includes secrets.
    """
    draft = dict(draft or {})
    msg = _scrub(message or "")

    # --- Opening: blank form ---
    if not msg and _draft_empty(draft):
        return _turn(
            reply=(
                "I am the Submit assistant (**Simulated — Kompass soon**). "
                "Treat this like a normal chat — blank form is fine.\n\n"
                "Tell me a problem area (onboarding, incidents, cloud cost, "
                "sales…), say **brainstorm** for a starter idea, or paste a "
                "rough thought. I will update the draft as we go; you can edit "
                "the form anytime."
            ),
            awaiting_field=None,
            field_prompt=None,
            done=False,
        )

    # --- Opening with existing draft ---
    if not msg:
        nxt = next_submit_field(draft)
        title = _draft_get(draft, "title")
        if nxt:
            return _turn(
                reply=(
                    f"I see a draft{f' titled “{title}”' if title else ''}. "
                    "Ask me to shorten the title, add metrics, change category, "
                    "refine tags, or polish the whole thing — or just describe "
                    "what to change."
                ),
                awaiting_field=nxt[0],
                field_prompt=nxt[1],
                done=False,
            )
        return _turn(
            reply=(
                "Your draft looks filled in. Ask me to tighten anything "
                "(title, problem, metrics, tags…), or edit the form yourself "
                "and hit Save draft / Submit."
            ),
            awaiting_field=None,
            done=True,
        )

    # --- Soft awaiting_field answer (compat with older clients) ---
    if awaiting_field:
        field_patches = _apply_legacy_field(awaiting_field, msg, draft)
        if field_patches:
            merged = {**draft, **field_patches}
            nxt = next_submit_field(merged)
            label = FIELD_LABELS.get(awaiting_field, awaiting_field)
            if nxt:
                return _turn(
                    reply=(
                        f"Updated **{label}**. Next you might flesh out "
                        f"**{FIELD_LABELS.get(nxt[0], nxt[0])}** — or ask me "
                        "anything else."
                    ),
                    patches=field_patches,
                    awaiting_field=nxt[0],
                    field_prompt=nxt[1],
                    done=False,
                )
            return _turn(
                reply=(
                    f"Updated **{label}**. Draft looks complete — tweak on the "
                    "form or ask for another polish."
                ),
                patches=field_patches,
                awaiting_field=None,
                done=True,
            )

    # --- Mid-draft conversational refine ---
    refined = _conversational_refine(draft, msg)
    if refined is not None:
        return refined

    # --- Brainstorm / starter from empty or near-empty ---
    if _draft_empty(draft) and (_is_brainstorm(msg) or len(msg) >= 8):
        starter = _pick_starter(msg if not _is_brainstorm(msg) else "")
        if _is_brainstorm(msg):
            residual = msg
            for cue in (
                "brainstorm",
                "from scratch",
                "give me an idea",
                "suggest an idea",
                "propose an idea",
                "need an idea",
                "help me think",
                "starter",
                "inspire me",
                "inspire",
            ):
                residual = re.sub(re.escape(cue), " ", residual, flags=re.I)
            residual = residual.strip(" .,!")
            if len(residual) >= 4:
                starter = _pick_starter(residual)
        patches = _starter_patches(starter)
        return _turn(
            reply=(
                f"Here is a starter: **{patches['title']}**. I applied it to the "
                f"draft ({_patch_labels(patches)}). Tell me what to change — "
                "shorter title, stronger metrics, different category, or a whole "
                "new direction."
            ),
            patches=patches,
            awaiting_field=None,
            done=False,
        )

    # --- Free-form: treat longer messages as problem/solution paste ---
    if len(msg) >= 40 and _draft_empty(draft):
        starter = _pick_starter(msg)
        patches = _starter_patches(starter)
        patches["problem"] = msg if len(msg) > len(str(patches["problem"])) else patches["problem"]
        return _turn(
            reply=(
                f"Took that as the problem space and drafted **{patches['title']}** "
                f"({_patch_labels(patches)}). What should we refine first?"
            ),
            patches=patches,
        )

    if len(msg) >= 24:
        # Heuristic: assign to the weakest incomplete field, else problem
        nxt = next_submit_field(draft)
        target = nxt[0] if nxt else "problem"
        if target == "tags":
            patches = {"tags": _parse_tags(msg)}
        elif target == "effort":
            eff = _parse_effort(msg)
            patches = {"effort": eff} if eff else {"problem": msg}
            target = "effort" if eff else "problem"
        elif target == "title":
            patches = {"title": msg[:120]}
        else:
            patches = {target: msg}
        return _turn(
            reply=(
                f"Updated **{FIELD_LABELS.get(target, target)}** from your note. "
                "Keep chatting — e.g. “make the title shorter” or “add metrics”."
            ),
            patches=patches,
            awaiting_field=None,
        )

    # --- Short unclear nudge ---
    hints = []
    if _draft_get(draft, "title"):
        hints.append("“make the title shorter”")
    else:
        hints.append("“brainstorm onboarding”")
    hints.append("“add metrics”")
    hints.append("“change category to tech”")
    return _turn(
        reply=(
            "I can brainstorm from scratch or refine the draft. Try "
            + ", ".join(hints)
            + " — or write the change in plain language."
        ),
        awaiting_field=awaiting_field,
    )


def help_turn(*, message: str) -> dict[str, Any]:
    """Answer a basic Idea Hub FAQ question from a local intent map.

    Args:
        message: User question text.

    Returns:
        Simulated help reply with optional deep links. Never echoes secrets.
    """
    msg = _scrub(message or "")
    low = msg.lower()
    best: Optional[dict[str, Any]] = None
    best_hits = 0
    for entry in HELP_FAQ:
        hits = sum(1 for kw in entry["keywords"] if kw in low)
        if hits > best_hits:
            best_hits = hits
            best = entry

    if best and best_hits > 0:
        return {
            "simulated": True,
            "engine": ENGINE,
            "mode": "simulate" if simulation_mode() else "kompass-pending",
            "topic": best["id"],
            "reply": best["reply"],
            "links": list(best["links"]),
            "notice": "Simulated — Kompass soon",
        }

    return {
        "simulated": True,
        "engine": ENGINE,
        "mode": "simulate" if simulation_mode() else "kompass-pending",
        "topic": "fallback",
        "reply": (
            "I can help with Submit, Review, roles, Explore, Ideathons, Admin, "
            "agents (Simulated), and high-level SSO/MFA sign-in. Ask about one of "
            "those — I do not need or store passwords or OTP codes."
        ),
        "links": [
            {"label": "Submit", "href": "/submit"},
            {"label": "Review", "href": "/review"},
            {"label": "Explore", "href": "/explore"},
            {"label": "Agent hub", "href": "/agents"},
        ],
        "notice": "Simulated — Kompass soon",
    }


def _idea_field(idea: dict[str, Any], key: str) -> str:
    if key == "success_metrics":
        return str(idea.get("success_metrics") or idea.get("success") or "").strip()
    if key == "tags":
        tags = idea.get("tags") or []
        if isinstance(tags, list):
            return ", ".join(str(t) for t in tags)
        return str(tags).strip()
    if key == "category":
        return str(
            idea.get("category")
            or idea.get("category_slug")
            or idea.get("category_id")
            or ""
        ).strip()
    return str(idea.get(key) or "").strip()


def _weak_fields(idea: dict[str, Any]) -> list[str]:
    weak: list[str] = []
    title = _idea_field(idea, "title")
    if len(title) < 12:
        weak.append("title")
    problem = _idea_field(idea, "problem")
    if len(problem) < 60 or not re.search(r"\b(who|team|user|customer)\b", problem, re.I):
        weak.append("problem")
    solution = _idea_field(idea, "solution")
    if len(solution) < 40:
        weak.append("solution")
    beneficiaries = _idea_field(idea, "beneficiaries")
    if len(beneficiaries) < 20:
        weak.append("beneficiaries")
    metrics = _idea_field(idea, "success_metrics")
    if len(metrics) < 20 or not re.search(r"\d", metrics):
        weak.append("success_metrics")
    tags = idea.get("tags") or []
    if isinstance(tags, list):
        if len(tags) < 2:
            weak.append("tags")
    elif not str(tags).strip():
        weak.append("tags")
    return weak


def _expand_problem(idea: dict[str, Any]) -> str:
    base = _idea_field(idea, "problem") or _idea_field(idea, "title")
    if not base:
        return (
            "Who is affected, what breaks, and how often? "
            "Today: ___ people / ___ times per week. Cost: ___."
        )
    if len(base) >= 120 and re.search(r"\d", base):
        return base
    suffix = (
        " Who feels this most (role/team)? How often each week? "
        "What is the cost in time or quality today?"
    )
    if base.endswith("?"):
        return f"{base.rstrip()}{suffix}"
    return f"{base.rstrip('.')}." + suffix


def _expand_metrics(idea: dict[str, Any]) -> str:
    base = _idea_field(idea, "success_metrics")
    if base and re.search(r"\d", base) and len(base) >= 24:
        return base
    title = _idea_field(idea, "title") or "this change"
    return (
        f"For “{title[:60]}”: reduce median cycle time from 10 days to 4 days "
        f"within 8 weeks (baseline measured this month)."
    )


def _suggest_tags(idea: dict[str, Any]) -> list[str]:
    existing = idea.get("tags") or []
    if not isinstance(existing, list):
        existing = _parse_tags(str(existing))
    blob = " ".join(
        _idea_field(idea, k) for k in ("title", "problem", "solution", "beneficiaries")
    )
    words = re.findall(r"[a-z]{4,}", blob.lower())
    stop = {
        "this",
        "that",
        "with",
        "from",
        "have",
        "will",
        "would",
        "could",
        "about",
        "their",
        "there",
        "which",
        "when",
        "into",
        "idea",
        "team",
        "teams",
    }
    out: list[str] = [str(t) for t in existing if t]
    for w in words:
        if w in stop or w in out:
            continue
        out.append(w[:30])
        if len(out) >= 4:
            break
    if not out:
        out = ["tooling", "productivity"]
    return out[:4]


def _optimize_patches(idea: dict[str, Any], message: str) -> dict[str, Any]:
    """Build field_patches from intent keywords + weak-field heuristics."""
    low = (message or "").lower()
    weak = _weak_fields(idea)
    patches: dict[str, Any] = {}

    wants_all = not low or any(
        k in low
        for k in (
            "optimize",
            "improve",
            "sharpen",
            "clarity",
            "all",
            "everything",
            "review my",
            "help me",
        )
    )
    wants_problem = "problem" in low or "framing" in low or "pain" in low
    wants_metrics = any(k in low for k in ("metric", "success", "kpi", "measure"))
    wants_tags = "tag" in low
    wants_title = "title" in low or "rename" in low
    wants_solution = "solution" in low or "approach" in low
    wants_beneficiaries = "beneficiar" in low or "who benefits" in low
    wants_effort = "effort" in low or "sizing" in low

    targeted = any(
        (
            wants_problem,
            wants_metrics,
            wants_tags,
            wants_title,
            wants_solution,
            wants_beneficiaries,
            wants_effort,
        )
    )

    def include(field: str, forced: bool) -> bool:
        return forced or (wants_all and field in weak) or (not targeted and field in weak)

    if include("problem", wants_problem):
        patches["problem"] = _expand_problem(idea)
    if include("success_metrics", wants_metrics):
        patches["success_metrics"] = _expand_metrics(idea)
    if include("tags", wants_tags):
        patches["tags"] = _suggest_tags(idea)
    if include("title", wants_title):
        title = _idea_field(idea, "title")
        if title and len(title) < 80:
            patches["title"] = title.rstrip(".")
        elif not title:
            patches["title"] = "Clarify the outcome in the title"
    if include("solution", wants_solution):
        sol = _idea_field(idea, "solution")
        if len(sol) < 40:
            patches["solution"] = (
                (sol.rstrip(".") + ". " if sol else "")
                + "What we would build or change: ___. "
                "First milestone in 2 weeks: ___."
            ).strip()
    if include("beneficiaries", wants_beneficiaries):
        ben = _idea_field(idea, "beneficiaries")
        if len(ben) < 20:
            patches["beneficiaries"] = (
                (ben + " — " if ben else "")
                + "Primary: ___ role/team (~N people). Secondary: ___."
            ).strip(" —")
    if include("effort", wants_effort):
        cur = str(idea.get("effort") or "").upper()
        if cur not in {"S", "M", "L", "XL"}:
            patches["effort"] = "M"

    return patches


def idea_optimize_turn(
    *,
    idea: dict[str, Any],
    message: str,
    messages: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Propose author-side field improvements for an existing idea.

    Distinct from Review Intelligence (scores / decision lean) and from the
    one-shot ``idea-enhancement`` roster agent. Proposes only — never persists.

    Args:
        idea: Current idea fields (id, title, problem, solution, tags, …).
        message: Latest author chat text (empty opens with a critique).
        messages: Optional prior turns (ignored by the heuristic; reserved for
            Kompass chat history).

    Returns:
        Simulated turn with ``reply`` and ``field_patches``. Never includes secrets.

    Side Effects:
        None.
    """
    _ = messages  # reserved for Kompass multi-turn context
    idea = dict(idea or {})
    msg = _scrub(message or "")
    weak = _weak_fields(idea)
    patches = _optimize_patches(idea, msg) if msg or weak else {}

    if not msg:
        if weak:
            focus = ", ".join(w.replace("_", " ") for w in weak[:3])
            reply = (
                "I am the author Idea Optimizer (Simulated — Kompass soon). "
                "I suggest clearer framing, metrics, and tags — you apply each "
                "patch. I do not score or decide like Review Intelligence.\n\n"
                f"Weak spots right now: **{focus}**. "
                "Ask me to improve problem, metrics, tags, or say “optimize all”."
            )
        else:
            reply = (
                "I am the author Idea Optimizer (Simulated — Kompass soon). "
                "Your fields look reasonably complete. Ask for a sharper title, "
                "problem framing, measurable success metrics, or better tags."
            )
        return {
            "simulated": True,
            "engine": ENGINE,
            "mode": "simulate" if simulation_mode() else "kompass-pending",
            "reply": reply,
            "field_patches": {},
            "focus_fields": weak,
            "notice": "Simulated — Kompass soon",
        }

    if not patches:
        reply = (
            "I did not find a concrete edit for that ask. Try: “sharpen the "
            "problem”, “add a metric”, “suggest tags”, or “optimize all”."
        )
    else:
        keys = ", ".join(k.replace("_", " ") for k in patches)
        reply = (
            f"Proposed updates for **{keys}**. Click Apply on a chip to stage "
            "the edit — nothing is saved until you confirm through the idea "
            "update path. Ask for another pass anytime."
        )

    return {
        "simulated": True,
        "engine": ENGINE,
        "mode": "simulate" if simulation_mode() else "kompass-pending",
        "reply": reply,
        "field_patches": patches,
        "focus_fields": weak,
        "notice": "Simulated — Kompass soon",
    }
