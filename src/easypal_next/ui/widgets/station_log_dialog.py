"""Station Log viewer dialog."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from easypal_next.core.station_log import read_station_log, station_log_path


class StationLogDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Station Log")
        self.resize(720, 420)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Log file: {station_log_path()}"))

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(["UTC", "Dir", "Call", "Detail", "Path"])
        self._table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._table)

        row = QHBoxLayout()
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.reload)
        row.addWidget(refresh)
        row.addStretch(1)
        layout.addLayout(row)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        buttons.button(QDialogButtonBox.StandardButton.Close).clicked.connect(self.accept)
        layout.addWidget(buttons)
        self.reload()

    def reload(self) -> None:
        entries = read_station_log(limit=500)
        self._table.setRowCount(len(entries))
        for row, entry in enumerate(reversed(entries)):
            self._table.setItem(row, 0, QTableWidgetItem(entry.ts.replace("T", " ")[:19]))
            self._table.setItem(row, 1, QTableWidgetItem(entry.direction))
            self._table.setItem(row, 2, QTableWidgetItem(entry.callsign))
            self._table.setItem(row, 3, QTableWidgetItem(entry.detail))
            self._table.setItem(row, 4, QTableWidgetItem(entry.path))
