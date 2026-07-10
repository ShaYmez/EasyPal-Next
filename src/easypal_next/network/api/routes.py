"""FastAPI REST routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from easypal_next import __version__
from easypal_next.network.api.schemas import (
    GalleryItemResponse,
    StatusResponse,
    TransferProgressResponse,
)
from easypal_next.network.gallery_store import GalleryStore

router = APIRouter(prefix="/api/v1")


def create_router(gallery: GalleryStore, get_state, get_progress, abort_transfer) -> APIRouter:
    @router.get("/status", response_model=StatusResponse)
    def status() -> StatusResponse:
        state, callsign, modem_mode = get_state()
        return StatusResponse(
            version=__version__,
            session_state=state,
            callsign=callsign,
            modem_mode=modem_mode,
        )

    @router.get("/transfer/progress", response_model=TransferProgressResponse)
    def transfer_progress() -> TransferProgressResponse:
        progress = get_progress()
        return TransferProgressResponse(
            pct=progress.pct,
            bytes_done=progress.bytes_done,
            bytes_total=progress.bytes_total,
        )

    @router.post("/transfer/abort")
    def transfer_abort() -> dict[str, str]:
        abort_transfer()
        return {"status": "aborted"}

    @router.get("/gallery", response_model=list[GalleryItemResponse])
    def gallery_list() -> list[GalleryItemResponse]:
        return [
            GalleryItemResponse(
                id=entry.id,
                callsign=entry.callsign,
                created_at=entry.created_at,
                direction=entry.direction,
                thumb_url=f"/api/v1/gallery/{entry.id}/thumb",
                image_url=f"/api/v1/gallery/{entry.id}",
            )
            for entry in gallery.list_entries()
        ]

    @router.get("/gallery/{image_id}")
    def gallery_image(image_id: str):
        entry = gallery.get_entry(image_id)
        if entry is None:
            raise HTTPException(status_code=404, detail="Image not found")
        path = Path(entry.path)
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Image file missing")
        return FileResponse(path)

    @router.get("/gallery/{image_id}/thumb")
    def gallery_thumb(image_id: str):
        entry = gallery.get_entry(image_id)
        if entry is None:
            raise HTTPException(status_code=404, detail="Thumbnail not found")
        path = Path(entry.thumb_path)
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Thumbnail file missing")
        return FileResponse(path, media_type="image/jpeg")

    return router
