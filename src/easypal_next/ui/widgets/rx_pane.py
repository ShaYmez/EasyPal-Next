"""Gallery pane with TX/RX thumbnails and preview."""

from __future__ import annotations

from pathlib import Path

from PIL import Image
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from easypal_next.network.gallery_store import IMAGE_SUFFIXES, GalleryEntry, GalleryStore

_THUMB_SIZE = 64


def _pil_to_pixmap(image_path: Path, size: int) -> QPixmap:
    with Image.open(image_path) as img:
        rgb = img.convert("RGBA")
        data = rgb.tobytes("raw", "RGBA")
        qimg = QImage(data, rgb.width, rgb.height, QImage.Format.Format_RGBA8888)
        return QPixmap.fromImage(qimg).scaled(
            size,
            size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )


def _load_thumb_pixmap(entry: GalleryEntry, size: int = _THUMB_SIZE) -> QPixmap:
    thumb_path = Path(entry.thumb_path)
    if thumb_path.is_file():
        pix = QPixmap(str(thumb_path))
        if not pix.isNull():
            return pix.scaled(
                size,
                size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        try:
            return _pil_to_pixmap(thumb_path, size)
        except OSError:
            pass
    full = Path(entry.path)
    if full.is_file():
        if full.suffix.lower() in IMAGE_SUFFIXES:
            pix = QPixmap(str(full))
            if not pix.isNull():
                return pix.scaled(
                    size,
                    size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            try:
                return _pil_to_pixmap(full, size)
            except OSError:
                pass
    return QPixmap()


class RxPane(QWidget):
    image_selected = Signal(str)

    def __init__(self, gallery: GalleryStore, parent=None) -> None:
        super().__init__(parent)
        self._gallery = gallery
        self._filter = QComboBox()
        self._filter.addItem("All", None)
        self._filter.addItem("Received", "rx")
        self._filter.addItem("Transmitted", "tx")
        self._filter.currentIndexChanged.connect(lambda _: self.refresh())

        self._preview = QLabel("No image received")
        self._preview.setObjectName("galleryPreview")
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setMinimumHeight(80)
        self._preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._thumb_list = QListWidget()
        self._thumb_list.setViewMode(QListWidget.ViewMode.IconMode)
        self._thumb_list.setFlow(QListWidget.Flow.LeftToRight)
        self._thumb_list.setWrapping(False)
        self._thumb_list.setMovement(QListWidget.Movement.Static)
        self._thumb_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._thumb_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._thumb_list.setIconSize(QSize(_THUMB_SIZE, _THUMB_SIZE))
        self._thumb_list.setFixedHeight(_THUMB_SIZE + 8)
        self._thumb_list.currentItemChanged.connect(self._on_thumb_selected)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Show:"))
        filter_row.addWidget(self._filter)
        filter_row.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        layout.addLayout(filter_row)
        layout.addWidget(self._preview, stretch=1)
        layout.addWidget(self._thumb_list)

        self.refresh()

    def refresh(self) -> None:
        self._thumb_list.clear()
        direction = self._filter.currentData()
        entries = self._gallery.list_entries(direction=direction)
        if not entries:
            self._preview.setText("No gallery entries")
            self._preview.setPixmap(QPixmap())
            return

        self._show_entry(entries[0])

        for entry in entries[:10]:
            pix = _load_thumb_pixmap(entry)
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, entry.id)
            if not pix.isNull():
                item.setIcon(pix)
            else:
                item.setText(entry.direction.upper())
            tip = f"{entry.direction.upper()} · {Path(entry.path).name}"
            item.setToolTip(tip)
            self._thumb_list.addItem(item)

    def add_entry(self, entry_id: str) -> None:
        entry = self._gallery.get_entry(entry_id)
        if entry:
            self._show_entry(entry)
        self.refresh()

    def _on_thumb_selected(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        if current is None:
            return
        entry_id = current.data(Qt.ItemDataRole.UserRole)
        if entry_id:
            entry = self._gallery.get_entry(str(entry_id))
            if entry:
                self._show_entry(entry)

    def _show_entry(self, entry: GalleryEntry) -> None:
        path = Path(entry.path)
        if path.suffix.lower() in IMAGE_SUFFIXES and path.is_file():
            pix = QPixmap(str(path))
            if pix.isNull():
                try:
                    pix = _pil_to_pixmap(path, 512)
                except OSError:
                    pix = QPixmap()
            if not pix.isNull():
                scaled = pix.scaled(
                    self._preview.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self._preview.setPixmap(scaled)
                self._preview.setText("")
                self.image_selected.emit(str(path))
                return
        self._preview.setPixmap(QPixmap())
        self._preview.setText(f"[{entry.direction.upper()}] {path.name}")
