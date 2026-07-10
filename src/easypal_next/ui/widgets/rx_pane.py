"""RX image pane with thumbnail grid."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QGridLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from easypal_next.network.gallery_store import GalleryEntry, GalleryStore


class RxPane(QWidget):
    image_selected = Signal(str)

    def __init__(self, gallery: GalleryStore, parent=None) -> None:
        super().__init__(parent)
        self._gallery = gallery
        self._preview = QLabel("No image received")
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setMinimumHeight(240)
        self._preview.setStyleSheet("border: 1px solid #444; background: #1a1a1a; color: #ccc;")

        self._grid_widget = QWidget()
        self._grid = QGridLayout(self._grid_widget)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._grid_widget)
        scroll.setMaximumHeight(160)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Received images"))
        layout.addWidget(self._preview, stretch=2)
        layout.addWidget(scroll, stretch=1)

        self.refresh()

    def refresh(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        entries = self._gallery.list_entries()
        if not entries:
            self._preview.setText("No image received")
            self._preview.setPixmap(QPixmap())
            return

        latest = entries[0]
        self._show_entry(latest)

        for index, entry in enumerate(entries[:12]):
            thumb = QLabel()
            thumb.setFixedSize(72, 72)
            thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            thumb.setStyleSheet("border: 1px solid #333;")
            path = Path(entry.thumb_path)
            if path.is_file():
                pix = QPixmap(str(path)).scaled(68, 68, Qt.AspectRatioMode.KeepAspectRatio)
                thumb.setPixmap(pix)
            else:
                thumb.setText("?")
            thumb.mousePressEvent = lambda _e, ent=entry: self._show_entry(ent)  # type: ignore[method-assign]
            self._grid.addWidget(thumb, index // 6, index % 6)

    def add_entry(self, entry_id: str) -> None:
        entry = self._gallery.get_entry(entry_id)
        if entry:
            self._show_entry(entry)
        self.refresh()

    def _show_entry(self, entry: GalleryEntry) -> None:
        path = Path(entry.path)
        if path.is_file():
            pix = QPixmap(str(path))
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
        self._preview.setText(entry.path)
