"""Constants for entry documents, GitHub evidence, rubric scoring and idea AI review."""

from __future__ import annotations

# --- Event kinds ---
EVENT_KINDS: tuple[str, ...] = ("ideathon", "hackathon")
HACKATHON_KIND: str = "hackathon"

# --- Entry documents ---
MAX_DOCUMENT_BYTES: int = 10 * 1024 * 1024
MAX_DOCUMENTS_PER_IDEA: int = 5
MAX_EXTRACTED_TEXT_CHARS: int = 60_000
ALLOWED_DOCUMENT_TYPES: dict[str, str] = {
    ".pdf": "application/pdf",
    ".md": "text/markdown",
    ".txt": "text/plain",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
DOCX_BODY_PART: str = "word/document.xml"
DOCX_TEXT_TAG: str = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"
DOCX_PARAGRAPH_TAG: str = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"

# --- GitHub evidence (public REST API, no token) ---
GITHUB_API_BASE: str = "https://api.github.com/repos"
GITHUB_HTTP_TIMEOUT: float = 10.0
GITHUB_USER_AGENT: str = "IdeaKonnekt-entry-scoring"
GITHUB_README_MAX_CHARS: int = 12_000
GITHUB_MAX_PARALLEL: int = 4
GITHUB_TEST_MARKERS: tuple[str, ...] = ("test/", "tests/", "__tests__/", "spec/", ".test.", "_test.", ".spec.")
GITHUB_CI_MARKERS: tuple[str, ...] = (".github/workflows/", ".gitlab-ci.yml", "bitbucket-pipelines.yml", "jenkinsfile")
GITHUB_STATUS_OK: str = "ok"
GITHUB_STATUS_MISSING: str = "missing"
GITHUB_STATUS_UNREACHABLE: str = "unreachable"

# --- Rubric (docs/IDEATHON_SCORING_RUBRIC.md) ---
RUBRIC_VERSION: str = "2026-11-v1"
RUBRIC_CRITERIA: tuple[str, ...] = ("relevance", "feasibility", "impact", "originality")
SCORE_MIN: float = 0.0
SCORE_MAX: float = 10.0
SCORER_ENGINE_LOCAL: str = "local-rubric-scorer"
SCORER_ENGINE_KOMPASS: str = "kompass:ideathon-rank"
EFFORT_FEASIBILITY: dict[str, float] = {"S": 3.0, "M": 2.0, "L": 1.0, "XL": 0.0}
MIN_SCORABLE_TEXT_CHARS: int = 20
# An entry that does not answer the challenge cannot rank on its other criteria alone.
RELEVANCE_GATE_MIN: float = 3.0
RELEVANCE_GATE_OVERALL_CAP: float = 4.0
# Context sent to the Kompass Rank agent (keeps the run input a sensible size).
RANK_DOC_EXCERPT_CHARS: int = 3000
RANK_DOCS_TOTAL_CHARS: int = 6000
RANK_README_EXCERPT_CHARS: int = 3000
DOC_TEXT_FOR_SCORING_CHARS: int = 20_000
SCORING_STOPWORDS: frozenset[str] = frozenset(
    {
        "the", "and", "for", "with", "that", "this", "from", "into", "our", "your", "are",
        "was", "were", "will", "can", "how", "what", "who", "why", "when", "use", "using",
        "make", "more", "less", "than", "they", "them", "their", "its", "has", "have", "not",
        "but", "all", "any", "each", "per", "via", "out", "new", "get", "set", "one", "two",
    }
)
METRIC_UNIT_WORDS: tuple[str, ...] = (
    "%", "percent", "hours", "hour", "days", "day", "minutes", "weeks", "per", "rate",
    "count", "number", "time", "cost", "nps", "score",
)

# --- Idea AI review (runs after submit) ---
AI_REVIEW_ENGINE_LOCAL: str = "local-idea-review"
COMPANY_CONTEXT_SETTING_KEY: str = "company_context"
FIT_STRONG_MIN_THEMES: int = 2
FIT_PARTIAL_MIN_THEMES: int = 1
MIN_FIELD_CHARS: dict[str, int] = {
    "problem": 80,
    "solution": 80,
    "beneficiaries": 15,
    "success_metrics": 15,
}
AI_REVIEW_FIELD_HINTS: dict[str, tuple[str, str]] = {
    "problem": ("Problem", "Describe who feels the pain, how often, and what it costs today"),
    "solution": ("Solution", "Say what would change and how a first version would work"),
    "beneficiaries": ("Who benefits", "Name the team, role or customer group that gains"),
    "success_metrics": ("Success metrics", "Add one measure with a unit and today's baseline"),
}
