"""Documents attached to an idea (hackathon / ideathon documentation the AI reads)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, File, Response, UploadFile

from app.db.session_deps import DbSession
from app.dependencies.phase23_auth import RequireActor
from app.schemas.entry_scoring import EntryDocumentOut
from app.services.entry_document_service import EntryDocumentService

router = APIRouter(prefix="/ideas", tags=["idea-documents"])


@router.get("/{idea_id}/documents", response_model=list[EntryDocumentOut], summary="List documents")
async def list_documents(
    idea_id: uuid.UUID, session: DbSession, actor: RequireActor
) -> list[EntryDocumentOut]:
    """Documents attached to an idea, oldest first."""
    return await EntryDocumentService(session).list_documents(idea_id, actor)


@router.post("/{idea_id}/documents", response_model=EntryDocumentOut, summary="Upload a document")
async def upload_document(
    idea_id: uuid.UUID,
    session: DbSession,
    actor: RequireActor,
    file: UploadFile = File(..., description="PDF, Markdown, text or .docx, up to 10 MB"),
) -> EntryDocumentOut:
    """Author or teammate uploads one document."""
    return await EntryDocumentService(session).upload(idea_id, actor, file)


@router.get("/{idea_id}/documents/{doc_id}/download", summary="Download a document")
async def download_document(
    idea_id: uuid.UUID, doc_id: uuid.UUID, session: DbSession, actor: RequireActor
) -> Response:
    """The original file."""
    doc = await EntryDocumentService(session).get_file(idea_id, doc_id, actor)
    safe_name = doc.filename.replace('"', "")
    return Response(
        content=doc.data,
        media_type=doc.content_type,
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )


@router.delete("/{idea_id}/documents/{doc_id}", summary="Delete a document")
async def delete_document(
    idea_id: uuid.UUID, doc_id: uuid.UUID, session: DbSession, actor: RequireActor
) -> dict[str, bool]:
    """Author or teammate removes a document while the entry is editable."""
    await EntryDocumentService(session).delete(idea_id, doc_id, actor)
    return {"ok": True}
