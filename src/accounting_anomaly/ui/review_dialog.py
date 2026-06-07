from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .. import db


class ReviewDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Review Transactions")
        self.setMinimumWidth(520)
        self._queue = db.get_review_queue()
        self._index = 0
        self._reviewed = 0
        self._build_ui()
        self._load_current()
        self._update_nav_state()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        self._progress = QLabel()
        self._progress.setAlignment(Qt.AlignCenter)
        root.addWidget(self._progress)

        form = QFormLayout()
        self._date = QLabel()
        self._description = QLabel()
        self._description.setWordWrap(True)
        self._amount = QLabel()
        self._account = QLabel()
        self._status = QLabel()
        form.addRow("Date:", self._date)
        form.addRow("Payee:", self._description)
        form.addRow("Amount:", self._amount)
        form.addRow("Account:", self._account)
        form.addRow("Status:", self._status)

        self._category = QComboBox()
        self._category.setEditable(True)
        self._category.setInsertPolicy(QComboBox.NoInsert)
        for cat in db.get_known_categories():
            self._category.addItem(cat)
        form.addRow("Category:", self._category)
        root.addLayout(form)

        actions = QHBoxLayout()
        self._approve_btn = QPushButton("Approve (A)")
        self._ignore_btn = QPushButton("Ignore (I)")
        self._anomaly_btn = QPushButton("Anomaly (X)")
        self._skip_btn = QPushButton("Skip")
        self._approve_btn.clicked.connect(lambda: self._apply("approved"))
        self._ignore_btn.clicked.connect(lambda: self._apply("ignored"))
        self._anomaly_btn.clicked.connect(lambda: self._apply("anomaly"))
        self._skip_btn.clicked.connect(self._skip)
        for btn in (self._approve_btn, self._ignore_btn, self._anomaly_btn, self._skip_btn):
            actions.addWidget(btn)
        root.addLayout(actions)

        QShortcut(QKeySequence("A"), self, lambda: self._apply("approved"))
        QShortcut(QKeySequence("I"), self, lambda: self._apply("ignored"))
        QShortcut(QKeySequence("X"), self, lambda: self._apply("anomaly"))

        nav = QDialogButtonBox()
        self._done_btn = nav.addButton("Done", QDialogButtonBox.RejectRole)
        self._done_btn.clicked.connect(self.reject)
        root.addWidget(nav)

    def _load_current(self) -> None:
        if not self._queue:
            self._progress.setText("No transactions need review.")
            for widget in (
                self._date,
                self._description,
                self._amount,
                self._account,
                self._status,
                self._category,
                self._approve_btn,
                self._ignore_btn,
                self._anomaly_btn,
                self._skip_btn,
            ):
                widget.setEnabled(False)
            return

        tx = self._queue[self._index]
        month = tx["month"]
        month_items = [t for t in self._queue if t["month"] == month]
        pos_in_month = month_items.index(tx) + 1
        self._progress.setText(
            f"Month {month} — item {pos_in_month} of {len(month_items)}  "
            f"({self._index + 1}/{len(self._queue)} total)"
        )
        self._date.setText(tx["date"])
        self._description.setText(tx["description"])
        self._amount.setText(f"{tx['amount']:+.2f}")
        self._account.setText(tx.get("account", ""))
        self._status.setText(tx["status"])
        self._category.setCurrentText(tx.get("category", ""))

    def _update_nav_state(self) -> None:
        has_queue = bool(self._queue) and self._index < len(self._queue)
        for btn in (self._approve_btn, self._ignore_btn, self._anomaly_btn, self._skip_btn):
            btn.setEnabled(has_queue)

    def _apply(self, status: str) -> None:
        if not self._queue or self._index >= len(self._queue):
            return
        tx = self._queue[self._index]
        category = self._category.currentText().strip()
        db.update_review(tx["id"], status, category)
        self._reviewed += 1
        self._queue.pop(self._index)
        if self._index >= len(self._queue):
            self._index = max(0, len(self._queue) - 1)
        if not self._queue:
            QMessageBox.information(
                self,
                "Review Complete",
                f"Reviewed {self._reviewed} transaction(s).",
            )
            self.accept()
            return
        self._load_current()
        self._update_nav_state()

    def _skip(self) -> None:
        if not self._queue or self._index >= len(self._queue):
            return
        self._index += 1
        if self._index >= len(self._queue):
            QMessageBox.information(
                self,
                "Review Paused",
                f"Reviewed {self._reviewed} transaction(s). {len(self._queue)} still need review.",
            )
            self.accept()
            return
        self._load_current()

    @property
    def reviewed_count(self) -> int:
        return self._reviewed
