"""Documents attached to an idea, so reviewers and the scoring AI can read them.

Responsibilities:
- Validate and store uploads (PDF, Markdown, text, DOCX) on the idea.
- Extract readable text once at upload time for the scoring AI.
- List, download and delete documents with author / co-author rules.

Side Effects:
- Writes ``entry_documents`` rows. File bytes live in the database, never in the public uploads folder.
"""

from __future__ import annotations

import io
import uuid
import zipfile
from pathlib import PurePath
from xml.etree import ElementTree

from fastapi import HTTPException, UploadFile
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.entry_scoring import (
    ALLOWED_DOCUMENT_TYPES,
    DOCX_BODY_PART,
    DOCX_PARAGRAPH_TAG,
    DOCX_TEXT_TAG,
    MAX_DOCUMENT_BYTES,
    MAX_DOCUMENTS_PER_IDEA,
    MAX_EXTRACTED_TEXT_CHARS,
)
from app.dependencies.phase23_auth import Actor
from app.models.idea import Idea
from app.models.ideathon import EntryDocument, Ideathon
from app.schemas.entry_scoring import EntryDocumentOut


def extension_of(filename: str) -> str:
    """Lower-case file extension including the dot, or empty."""
    return PurePath(filename or "").suffix.lower()


def _pdf_text(data: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except (PdfReadError, ValueError, KeyError, TypeError):
        return ""


def _docx_text(data: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            root = ElementTree.fromstring(zf.read(DOCX_BODY_PART))
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError):
        return ""
    paragraphs = []
    for para in root.iter(DOCX_PARAGRAPH_TAG):
        text = "".join(node.text or "" for node in para.iter(DOCX_TEXT_TAG))
        if text.strip():
            paragraphs.append(text)
    return "\n".join(paragraphs)


def extract_text(ext: str, data: bytes) -> str:
    """Readable text from a document, trimmed to the stored limit. Empty when unreadable."""
    if ext == ".pdf":
        text = _pdf_text(data)
    elif ext == ".docx":
        text = _docx_text(data)
    else:
        text = data.decode("utf-8", errors="replace")
    return text.strip()[:MAX_EXTRACTED_TEXT_CHARS]


def to_out(doc: EntryDocument) -> EntryDocumentOut:
    """Document metadata for the API (never the bytes)."""
    return EntryDocumentOut(
        id=doc.id,
        idea_id=doc.idea_id,
        filename=doc.filename,
        content_type=doc.content_type,
        size_bytes=doc.size_bytes,
        text_chars=len(doc.extracted_text or ""),
        created_at=doc.created_at,
    )


def _is_author(idea: Idea, actor: Actor) -> bool:
    co_authors = {str(c) for c in (idea.co_author_ids or [])}
    return idea.author_id == actor.id or str(actor.id) in co_authors


class EntryDocumentService:
    """Upload, list, download and delete idea documents."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _idea(self, idea_id: uuid.UUID, actor: Actor) -> Idea:
        idea = await self.session.get(Idea, idea_id)
        if idea is None or (idea.status == "draft" and not _is_author(idea, actor)):
            raise HTTPException(404, "Idea not found.")
        return idea

    async def _require_editable(self, idea: Idea, actor: Actor) -> None:
        if not _is_author(idea, actor):
            raise HTTPException(403, "Only the author or a teammate can change documents.")
        if idea.ideathon_id:
            event = await self.session.get(Ideathon, idea.ideathon_id)
            if event is not None and event.phase != "open":
                raise HTTPException(400, "Documents are locked once submissions close.")

    async def list_documents(self, idea_id: uuid.UUID, actor: Actor) -> list[EntryDocumentOut]:
        """Documents on an idea, oldest first."""
        await self._idea(idea_id, actor)
        rows = (
            await self.session.execute(
                select(EntryDocument)
                .where(EntryDocument.idea_id == idea_id)
                .order_by(EntryDocument.created_at)
            )
        ).scalars().all()
        return [to_out(d) for d in rows]

    async def upload(self, idea_id: uuid.UUID, actor: Actor, file: UploadFile) -> EntryDocumentOut:
        """Validate, extract text and store one document."""
        idea = await self._idea(idea_id, actor)
        await self._require_editable(idea, actor)
        filename = PurePath(file.filename or "").name.strip()
        ext = extension_of(filename)
        if ext not in ALLOWED_DOCUMENT_TYPES:
            raise HTTPException(400, "Documents must be PDF, Markdown, text or Word (.docx).")
        count = (
            await self.session.execute(
                select(func.count()).select_from(EntryDocument).where(EntryDocument.idea_id == idea_id)
            )
        ).scalar_one()
        if count >= MAX_DOCUMENTS_PER_IDEA:
            raise HTTPException(400, f"An idea can have at most {MAX_DOCUMENTS_PER_IDEA} documents.")
        data = await file.read(MAX_DOCUMENT_BYTES + 1)
        if not data:
            raise HTTPException(400, "The file is empty.")
        if len(data) > MAX_DOCUMENT_BYTES:
            raise HTTPException(400, "Each document must be 10 MB or smaller.")
        doc = EntryDocument(
            idea_id=idea.id,
            uploaded_by=actor.id,
            filename=filename[:200],
            content_type=ALLOWED_DOCUMENT_TYPES[ext],
            size_bytes=len(data),
            data=data,
            extracted_text=extract_text(ext, data),
        )
        self.session.add(doc)
        await self.session.commit()
        await self.session.refresh(doc)
        return to_out(doc)

    async def get_file(
        self, idea_id: uuid.UUID, doc_id: uuid.UUID, actor: Actor
    ) -> EntryDocument:
        """The stored document, for download."""
        await self._idea(idea_id, actor)
        doc = await self.session.get(EntryDocument, doc_id)
        if doc is None or doc.idea_id != idea_id:
            raise HTTPException(404, "Document not found.")
        return doc

    async def delete(self, idea_id: uuid.UUID, doc_id: uuid.UUID, actor: Actor) -> None:
        """Remove a document while the entry is still editable."""
        idea = await self._idea(idea_id, actor)
        await self._require_editable(idea, actor)
        doc = await self.session.get(EntryDocument, doc_id)
        if doc is None or doc.idea_id != idea_id:
            raise HTTPException(404, "Document not found.")
        await self.session.delete(doc)
        await self.session.commit()


async def document_texts(session: AsyncSession, idea_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[tuple[str, str]]]:
    """(filename, extracted text) per idea, for the scorer."""
    if not idea_ids:
        return {}
    rows = (
        await session.execute(
            select(EntryDocument.idea_id, EntryDocument.filename, EntryDocument.extracted_text)
            .where(EntryDocument.idea_id.in_(idea_ids))
            .order_by(EntryDocument.created_at)
        )
    ).all()
    out: dict[uuid.UUID, list[tuple[str, str]]] = {}
    for idea_id, filename, text in rows:
        out.setdefault(idea_id, []).append((filename, text or ""))
    return out


async def document_count(session: AsyncSession, idea_id: uuid.UUID) -> int:
    """How many documents an idea has."""
    return int(
        (
            await session.execute(
                select(func.count()).select_from(EntryDocument).where(EntryDocument.idea_id == idea_id)
            )
        ).scalar_one()
    )
