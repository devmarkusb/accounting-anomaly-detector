from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor

STATUS_COLOR: dict[str, QColor] = {
    "pending": QColor("#fff9e6"),
    "approved": QColor("#e8f5e9"),
    "ignored": QColor("#f5f5f5"),
    "anomaly": QColor("#fdecea"),
}

_COLS = ["date", "description", "amount", "balance", "account", "month", "status"]
_HEADERS = ["Date", "Description", "Amount", "Balance", "Account", "Month", "Status"]
_RIGHT_ALIGN = {"amount", "balance"}


class TransactionModel(QAbstractTableModel):
    def __init__(self) -> None:
        super().__init__()
        self._rows: list[dict] = []

    def load(self, rows: list[dict]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(_COLS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return _HEADERS[section]
        return None

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        col = _COLS[index.column()]
        if role == Qt.DisplayRole:
            val = row.get(col)
            if val is None:
                return ""
            if col == "amount":
                return f"{val:+.2f}"
            if col == "balance":
                return f"{val:.2f}"
            return str(val)
        if role == Qt.BackgroundRole:
            return STATUS_COLOR.get(row.get("status", "pending"))
        if role == Qt.TextAlignmentRole and col in _RIGHT_ALIGN:
            return Qt.AlignRight | Qt.AlignVCenter
        if role == Qt.UserRole:
            return row
        return None

    def get_row(self, row_index: int) -> dict:
        return self._rows[row_index]
