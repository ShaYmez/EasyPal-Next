"""REST API DTOs."""

from __future__ import annotations

from pydantic import BaseModel


class StatusResponse(BaseModel):
    version: str
    session_state: str
    callsign: str
    modem_mode: str


class GalleryItemResponse(BaseModel):
    id: str
    callsign: str
    created_at: str
    direction: str
    thumb_url: str
    image_url: str


class TransferProgressResponse(BaseModel):
    pct: float
    bytes_done: int
    bytes_total: int
