from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .. import db
from ..core.anomaly import classify
from ..core.categories import apply_categories
from .import_dialog import ImportDialog
from .review_dialog import ReviewDialog
from .transaction_table import TransactionModel


class _SummaryWidget(QWidget):
    _HEADERS = ["Month", "Income", "Expenses", "Net", "Pending", "Anomalies"]
    _KEYS = ["month", "income", "expenses", None, "pending", "anomalies"]

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        self._table = QTableWidget()
        self._table.setColumnCount(len(self._HEADERS))
        self._table.setHorizontalHeaderLabels(self._HEADERS)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table)

    def refresh(self) -> None:
        rows = db.get_summary()
        self._table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            income = row.get("income") or 0.0
            expenses = row.get("expenses") or 0.0
            net = income + expenses
            values = [
                row.get("month", ""),
                f"+{income:.2f}",
                f"{expenses:.2f}",
                f"{net:+.2f}",
                str(row.get("pending", 0)),
                str(row.get("anomalies", 0)),
            ]
            for c, val in enumerate(values):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                self._table.setItem(r, c, item)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Accounting Anomaly Detector")
        self.setMinimumSize(1100, 700)
        db.init_db()
        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        toolbar = self.addToolBar("Main")
        toolbar.setMovable(False)

        import_action = QAction("Import CSV", self)
        import_action.setShortcut(QKeySequence("Ctrl+I"))
        import_action.triggered.connect(self._import_csv)
        toolbar.addAction(import_action)

        review_action = QAction("Review", self)
        review_action.setShortcut(QKeySequence("Ctrl+R"))
        review_action.triggered.connect(self._start_review)
        toolbar.addAction(review_action)
        toolbar.addSeparator()

        toolbar.addWidget(QLabel("  Month: "))
        self._month_combo = QComboBox()
        self._month_combo.addItem("All months", None)
        self._month_combo.currentIndexChanged.connect(self._refresh_table)
        toolbar.addWidget(self._month_combo)

        toolbar.addWidget(QLabel("  Status: "))
        self._status_combo = QComboBox()
        self._status_combo.addItems(["All", "pending", "approved", "ignored", "anomaly"])
        self._status_combo.currentIndexChanged.connect(self._refresh_table)
        toolbar.addWidget(self._status_combo)

        splitter = QSplitter(Qt.Vertical)

        self._model = TransactionModel()
        self._table = QTableView()
        self._table.setModel(self._model)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._context_menu)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._table.setAlternatingRowColors(False)
        splitter.addWidget(self._table)

        self._summary = _SummaryWidget()
        splitter.addWidget(self._summary)
        splitter.setSizes([520, 180])

        self.setCentralWidget(splitter)
        self.setStatusBar(QStatusBar())

    def _import_csv(self) -> None:
        dialog = ImportDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return
        stats = db.get_payee_stats()
        payee_categories = db.get_payee_categories()
        transactions = apply_categories(
            classify(dialog.get_transactions(), stats), payee_categories
        )
        inserted, skipped = db.insert_transactions(transactions)
        QMessageBox.information(
            self,
            "Import Complete",
            f"Inserted: {inserted}\nSkipped (duplicates): {skipped}",
        )
        self._refresh()
        if inserted and db.get_review_queue():
            reply = QMessageBox.question(
                self,
                "Start Review",
                "New transactions need review. Walk through them month by month now?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self._start_review()

    def _start_review(self) -> None:
        if not db.get_review_queue():
            QMessageBox.information(self, "Review", "No pending or anomaly transactions to review.")
            return
        dialog = ReviewDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self._refresh()

    def _refresh(self) -> None:
        current_month = self._month_combo.currentData()
        self._month_combo.blockSignals(True)
        self._month_combo.clear()
        self._month_combo.addItem("All months", None)
        for m in db.get_months():
            self._month_combo.addItem(m, m)
        idx = self._month_combo.findData(current_month)
        self._month_combo.setCurrentIndex(max(idx, 0))
        self._month_combo.blockSignals(False)
        self._refresh_table()
        self._summary.refresh()

    def _refresh_table(self) -> None:
        month = self._month_combo.currentData()
        status_text = self._status_combo.currentText()
        status = None if status_text == "All" else status_text
        rows = db.get_transactions(month=month, status=status)
        self._model.load(rows)
        pending = sum(1 for r in rows if r["status"] == "pending")
        anomalies = sum(1 for r in rows if r["status"] == "anomaly")
        self.statusBar().showMessage(
            f"{len(rows)} transactions  |  {pending} pending  |  {anomalies} anomalies"
        )

    def _context_menu(self, pos) -> None:
        indexes = self._table.selectedIndexes()
        if not indexes:
            return
        row_indices = sorted(set(i.row() for i in indexes))
        tx_ids = [self._model.get_row(r)["id"] for r in row_indices]

        menu = QMenu(self)
        actions = {
            menu.addAction("Mark Approved"): "approved",
            menu.addAction("Mark Ignored"): "ignored",
            menu.addAction("Mark Anomaly"): "anomaly",
            menu.addAction("Mark Pending"): "pending",
        }
        chosen = menu.exec(self._table.viewport().mapToGlobal(pos))
        if chosen in actions:
            for tx_id in tx_ids:
                db.update_status(tx_id, actions[chosen])
            self._refresh()
