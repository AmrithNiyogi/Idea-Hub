"""AI Newsletter categories and story validation thresholds."""

from __future__ import annotations

from datetime import timedelta

# (slug, label) — ordered as shown in the UI; first is the default.
NEWS_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("ai", "Artificial Intelligence"),
    ("ai-business", "AI in Business"),
    ("ai-sports", "AI in Sports"),
    ("ai-healthcare", "AI in Healthcare"),
    ("ai-finance", "AI in Finance"),
    ("ai-policy", "AI Policy & Safety"),
    ("ai-tools", "AI Tools & Launches"),
    ("ai-research", "AI Research"),
)

NEWS_CATEGORY_LABELS: dict[str, str] = dict(NEWS_CATEGORIES)
NEWS_DEFAULT_CATEGORY: str = NEWS_CATEGORIES[0][0]

# Stored results older than this are served as stale and refreshed.
NEWS_STALE_AFTER: timedelta = timedelta(hours=6)
# Stories published before this window are dropped.
NEWS_MAX_AGE: timedelta = timedelta(days=7)
# Stories scoring below this AI-relevance (0..1) are dropped.
NEWS_MIN_AI_RELEVANCE: float = 0.5
NEWS_MAX_ITEMS: int = 8

# Categories backed by a live source; every other category uses placeholder data.
NEWS_SOURCE_SAMPLE: str = "sample"
NEWS_CATEGORY_SOURCES: dict[str, str] = {
    "ai-research": "arxiv",
    "ai-tools": "github",
}

NEWS_HTTP_TIMEOUT: float = 20.0
NEWS_USER_AGENT: str = "IdeaKonnekt-Newsletter/1.0"

ARXIV_API_URL: str = "https://export.arxiv.org/api/query"
# arXiv asks clients to leave about 3 seconds between requests.
ARXIV_REQUEST_GAP_SECONDS: float = 3.0
ARXIV_STORY_FETCH: int = 25
ARXIV_SUMMARY_MAX_CHARS: int = 280
# (arXiv category, label); also used for the weekly paper counts.
ARXIV_TOPICS: tuple[tuple[str, str], ...] = (
    ("cs.AI", "Artificial intelligence"),
    ("cs.LG", "Machine learning"),
    ("cs.CL", "Language and NLP"),
    ("cs.CV", "Computer vision"),
    ("cs.RO", "Robotics"),
    ("cs.MA", "Multi-agent systems"),
)

GITHUB_SEARCH_URL: str = "https://api.github.com/search/repositories"
GITHUB_TOPICS: tuple[str, ...] = ("llm", "ai-agents", "generative-ai")
GITHUB_LOOKBACK: timedelta = timedelta(days=7)
GITHUB_PER_TOPIC: int = 10

NEWS_TRENDING_REPOS: int = 6
NEWS_TOP_TOPICS: int = 8
# A theme must appear in at least this many stories to be listed.
NEWS_TOPIC_MIN_STORIES: int = 2
NEWS_TOPIC_STOPWORDS: frozenset[str] = frozenset(
    (
        "a about after all also an and any are as at be been but by can could for "
        "from has have how in into is it its more most new not of on one or our over "
        "than that the their they this to up us use used using via was we were what "
        "when which who will with you your ai model models first paper announces "
        "launches releases adds says open study report week year years today"
    ).split()
)
