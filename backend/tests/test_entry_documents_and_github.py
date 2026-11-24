"""Document text extraction, upload rules, GitHub evidence, and the hackathon link rule."""

from __future__ import annotations

import io
import uuid
import zipfile
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import HTTPException

from app.schemas.ideathon import IdeathonCreate, LinkIdeaRequest
from app.services import entry_document_service as docs
from app.services import github_repo_service as gh
from app.services.ideathon_service import IdeathonService

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _docx(*paragraphs: str) -> bytes:
    body = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paragraphs)
    xml = f'<w:document xmlns:w="{W_NS}"><w:body>{body}</w:body></w:document>'
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("word/document.xml", xml)
    return buf.getvalue()


def test_docx_text_is_extracted_by_paragraph() -> None:
    assert docs.extract_text(".docx", _docx("First line", "Second line")) == "First line\nSecond line"


def test_markdown_and_text_are_decoded() -> None:
    assert docs.extract_text(".md", "# Title\nBody".encode()) == "# Title\nBody"


def test_unreadable_files_give_empty_text() -> None:
    assert docs.extract_text(".docx", b"not a zip") == ""
    assert docs.extract_text(".pdf", b"not a pdf") == ""


def test_extension_is_lower_cased() -> None:
    assert docs.extension_of("Design.PDF") == ".pdf"
    assert docs.extension_of("noext") == ""


def _idea(author: uuid.UUID, **extra: Any) -> SimpleNamespace:
    base = {"id": uuid.uuid4(), "author_id": author, "co_author_ids": [], "status": "submitted",
            "ideathon_id": None}
    base.update(extra)
    return SimpleNamespace(**base)


def _upload(name: str, data: bytes) -> SimpleNamespace:
    return SimpleNamespace(filename=name, read=AsyncMock(return_value=data))


def _doc_service(idea: SimpleNamespace, count: int = 0) -> docs.EntryDocumentService:
    session = SimpleNamespace(
        get=AsyncMock(return_value=idea),
        execute=AsyncMock(return_value=SimpleNamespace(scalar_one=lambda: count)),
        add=lambda _row: None,
        commit=AsyncMock(),
        refresh=AsyncMock(),
    )
    return docs.EntryDocumentService(session)  # type: ignore[arg-type]


async def test_non_author_cannot_upload() -> None:
    idea = _idea(uuid.uuid4())
    actor = SimpleNamespace(id=uuid.uuid4())
    with pytest.raises(HTTPException) as exc:
        await _doc_service(idea).upload(idea.id, actor, _upload("a.md", b"x"))  # type: ignore[arg-type]
    assert exc.value.status_code == 403


async def test_wrong_type_is_rejected() -> None:
    me = uuid.uuid4()
    idea = _idea(me)
    with pytest.raises(HTTPException) as exc:
        await _doc_service(idea).upload(idea.id, SimpleNamespace(id=me), _upload("a.exe", b"x"))  # type: ignore[arg-type]
    assert exc.value.status_code == 400


async def test_document_limit_is_enforced() -> None:
    me = uuid.uuid4()
    idea = _idea(me)
    with pytest.raises(HTTPException) as exc:
        await _doc_service(idea, count=5).upload(idea.id, SimpleNamespace(id=me), _upload("a.md", b"x"))  # type: ignore[arg-type]
    assert "at most 5" in str(exc.value.detail)


async def test_oversized_file_is_rejected() -> None:
    me = uuid.uuid4()
    idea = _idea(me)
    big = b"x" * (10 * 1024 * 1024 + 1)
    with pytest.raises(HTTPException) as exc:
        await _doc_service(idea).upload(idea.id, SimpleNamespace(id=me), _upload("a.md", big))  # type: ignore[arg-type]
    assert "10 MB" in str(exc.value.detail)


def test_repo_slug_parsing() -> None:
    assert gh.repo_slug("https://github.com/acme/tool/") == "acme/tool"
    assert gh.repo_slug("https://github.com/acme/tool.git") == "acme/tool"
    assert gh.repo_slug("https://gitlab.com/acme/tool") is None
    assert gh.repo_slug(None) is None


async def test_missing_link_gives_missing_snapshot() -> None:
    snap = await gh.fetch_snapshot(None)
    assert snap.status == "missing"


def test_summary_detects_tests_and_ci_without_owner() -> None:
    ev = gh.summarise({"name": "tool", "pushed_at": "2026-11-01"}, {"Python": 1200}, "readme",
                      ["src/a.py", "tests/test_a.py", ".github/workflows/ci.yml"], 7)
    assert ev["has_tests"] and ev["has_ci"]
    assert ev["file_count"] == 3 and ev["recent_commits"] == 7
    assert "owner" not in ev


async def test_github_errors_become_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Not Found"}, request=request)

    real_client = httpx.AsyncClient

    def fake_client(**kwargs: Any) -> httpx.AsyncClient:
        return real_client(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(gh.httpx, "AsyncClient", fake_client)
    snap = await gh.fetch_snapshot("https://github.com/acme/private")
    assert snap.status == "unreachable"
    assert "404" in snap.evidence["reason"]


async def test_github_success_builds_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/languages"):
            return httpx.Response(200, json={"TypeScript": 900}, request=request)
        if "/git/trees/" in path:
            return httpx.Response(200, json={"tree": [{"path": "src/a.ts", "type": "blob"},
                                                      {"path": "src", "type": "tree"}]}, request=request)
        if path.endswith("/commits"):
            return httpx.Response(200, json=[{}, {}, {}], request=request)
        if path.endswith("/readme"):
            return httpx.Response(200, text="Hello project", request=request)
        return httpx.Response(200, json={"name": "tool", "default_branch": "main"}, request=request)

    real_client = httpx.AsyncClient

    def fake_client(**kwargs: Any) -> httpx.AsyncClient:
        return real_client(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(gh.httpx, "AsyncClient", fake_client)
    snap = await gh.fetch_snapshot("https://github.com/acme/tool")
    assert snap.status == "ok"
    assert snap.readme == "Hello project"
    assert snap.paths == ["src/a.ts"]
    assert snap.evidence["recent_commits"] == 3


def test_event_kind_defaults_to_ideathon() -> None:
    body = IdeathonCreate(
        title="Spring event", theme="Support", challenges=["Reduce ticket triage time for agents."],
        sponsor_id=uuid.uuid4(), start_at="2026-12-01T00:00:00Z", end_at="2026-12-10T00:00:00Z",
    )
    assert body.kind == "ideathon"


def _link_service(kind: str, github_url: str | None, doc_count: int,
                  monkeypatch: pytest.MonkeyPatch) -> tuple[IdeathonService, Any, Any]:
    me = uuid.uuid4()
    it = SimpleNamespace(id=uuid.uuid4(), phase="open", kind=kind)
    idea = SimpleNamespace(id=uuid.uuid4(), author_id=me, co_author_ids=[], status="submitted",
                           title="Entry", github_url=github_url)
    svc = IdeathonService.__new__(IdeathonService)
    svc.repo = SimpleNamespace(get=AsyncMock(return_value=it), entry_for_idea=AsyncMock(return_value=None))
    svc.spine = SimpleNamespace(get_idea=AsyncMock(return_value=idea), set_idea_ideathon=AsyncMock())
    svc.session = SimpleNamespace(add=lambda _row: None, commit=AsyncMock())
    monkeypatch.setattr("app.services.ideathon_service.document_count", AsyncMock(return_value=doc_count))
    return svc, idea, SimpleNamespace(id=me)


async def test_hackathon_entry_needs_github(monkeypatch: pytest.MonkeyPatch) -> None:
    svc, idea, actor = _link_service("hackathon", None, 1, monkeypatch)
    with pytest.raises(HTTPException) as exc:
        await svc.link_idea(uuid.uuid4(), LinkIdeaRequest(idea_id=idea.id), actor)
    assert "GitHub" in str(exc.value.detail)


async def test_hackathon_entry_needs_documentation(monkeypatch: pytest.MonkeyPatch) -> None:
    svc, idea, actor = _link_service("hackathon", "https://github.com/a/b", 0, monkeypatch)
    with pytest.raises(HTTPException) as exc:
        await svc.link_idea(uuid.uuid4(), LinkIdeaRequest(idea_id=idea.id), actor)
    assert "documentation" in str(exc.value.detail)


async def test_complete_hackathon_entry_links(monkeypatch: pytest.MonkeyPatch) -> None:
    svc, idea, actor = _link_service("hackathon", "https://github.com/a/b", 1, monkeypatch)
    assert await svc.link_idea(uuid.uuid4(), LinkIdeaRequest(idea_id=idea.id), actor) == {"title": "Entry"}


async def test_ideathon_entry_needs_neither(monkeypatch: pytest.MonkeyPatch) -> None:
    svc, idea, actor = _link_service("ideathon", None, 0, monkeypatch)
    assert await svc.link_idea(uuid.uuid4(), LinkIdeaRequest(idea_id=idea.id), actor) == {"title": "Entry"}
