from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..core.csv_parser import CsvProfile, load_profiles, parse_csv, read_raw, save_profiles


class _ProfileEditor(QWidget):
    def __init__(self, profile: CsvProfile) -> None:
        super().__init__()
        layout = QFormLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.name = QLineEdit(profile.name)
        self.delimiter = QLineEdit(profile.delimiter)
        self.decimal = QLineEdit(profile.decimal)
        self.thousands = QLineEdit(profile.thousands)
        self.skip = QSpinBox()
        self.skip.setRange(0, 20)
        self.skip.setValue(profile.skip_rows)
        self.date_col = QSpinBox()
        self.date_col.setRange(0, 99)
        self.date_col.setValue(profile.date_col)
        self.date_fmt = QLineEdit(profile.date_format)
        self.desc_col = QSpinBox()
        self.desc_col.setRange(0, 99)
        self.desc_col.setValue(profile.description_col)
        self.amount_col = QSpinBox()
        self.amount_col.setRange(0, 99)
        self.amount_col.setValue(profile.amount_col)
        self.balance_col = QSpinBox()
        self.balance_col.setRange(-1, 99)
        self.balance_col.setValue(profile.balance_col)
        self.account = QLineEdit(profile.account)
        self.encoding = QLineEdit(profile.encoding)

        layout.addRow("Profile name:", self.name)
        layout.addRow("CSV delimiter:", self.delimiter)
        layout.addRow("Decimal separator:", self.decimal)
        layout.addRow("Thousands separator:", self.thousands)
        layout.addRow("Header rows to skip:", self.skip)
        layout.addRow("Date column index:", self.date_col)
        layout.addRow("Date format (strptime):", self.date_fmt)
        layout.addRow("Description column index:", self.desc_col)
        layout.addRow("Amount column index:", self.amount_col)
        layout.addRow("Balance column index (−1 = none):", self.balance_col)
        layout.addRow("Account label:", self.account)
        layout.addRow("File encoding:", self.encoding)

    def apply(self, profile: CsvProfile) -> None:
        profile.name = self.name.text().strip() or "Default"
        profile.delimiter = self.delimiter.text() or ";"
        profile.decimal = self.decimal.text() or ","
        profile.thousands = self.thousands.text()
        profile.skip_rows = self.skip.value()
        profile.date_col = self.date_col.value()
        profile.date_format = self.date_fmt.text().strip() or "%d.%m.%Y"
        profile.description_col = self.desc_col.value()
        profile.amount_col = self.amount_col.value()
        profile.balance_col = self.balance_col.value()
        profile.account = self.account.text().strip()
        profile.encoding = self.encoding.text().strip() or "utf-8-sig"

    def load(self, profile: CsvProfile) -> None:
        self.name.setText(profile.name)
        self.delimiter.setText(profile.delimiter)
        self.decimal.setText(profile.decimal)
        self.thousands.setText(profile.thousands)
        self.skip.setValue(profile.skip_rows)
        self.date_col.setValue(profile.date_col)
        self.date_fmt.setText(profile.date_format)
        self.desc_col.setValue(profile.description_col)
        self.amount_col.setValue(profile.amount_col)
        self.balance_col.setValue(profile.balance_col)
        self.account.setText(profile.account)
        self.encoding.setText(profile.encoding)

    def get_profile(self) -> CsvProfile:
        p = CsvProfile()
        self.apply(p)
        return p


class ImportDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Import CSV")
        self.setMinimumSize(860, 640)

        self._profiles = load_profiles()
        self._path: Path | None = None
        self._parsed: list[dict] = []

        root = QVBoxLayout(self)

        # --- file picker ---
        file_box = QGroupBox("CSV File")
        fl = QHBoxLayout(file_box)
        self._path_label = QLabel("No file selected")
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        fl.addWidget(self._path_label, 1)
        fl.addWidget(browse)
        root.addWidget(file_box)

        # --- profile area ---
        prof_box = QGroupBox("Import Profile")
        pl = QVBoxLayout(prof_box)
        sel_row = QHBoxLayout()
        self._prof_combo = QComboBox()
        for p in self._profiles:
            self._prof_combo.addItem(p.name)
        self._prof_combo.currentIndexChanged.connect(self._on_profile_switch)
        add_btn = QPushButton("New Profile")
        add_btn.clicked.connect(self._new_profile)
        save_btn = QPushButton("Save Profile")
        save_btn.clicked.connect(self._save_profile)
        sel_row.addWidget(QLabel("Profile:"))
        sel_row.addWidget(self._prof_combo, 1)
        sel_row.addWidget(add_btn)
        sel_row.addWidget(save_btn)
        pl.addLayout(sel_row)
        self._editor = _ProfileEditor(self._profiles[0])
        pl.addWidget(self._editor)
        root.addWidget(prof_box)

        # --- preview tabs ---
        tabs = QTabWidget()
        self._raw_table = _make_table()
        self._preview_table = _make_table()
        tabs.addTab(self._raw_table, "Raw CSV")
        tabs.addTab(self._preview_table, "Parsed Preview")
        root.addWidget(tabs, 1)

        # --- buttons ---
        preview_btn = QPushButton("Preview")
        preview_btn.clicked.connect(self._do_preview)
        root.addWidget(preview_btn)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    # ------------------------------------------------------------------ slots

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select CSV", "", "CSV files (*.csv *.txt);;All files (*)"
        )
        if path:
            self._path = Path(path)
            self._path_label.setText(path)
            self._refresh_raw()

    def _on_profile_switch(self, idx: int) -> None:
        if 0 <= idx < len(self._profiles):
            self._editor.load(self._profiles[idx])

    def _new_profile(self) -> None:
        p = CsvProfile(name=f"Profile {len(self._profiles) + 1}")
        self._profiles.append(p)
        self._prof_combo.addItem(p.name)
        self._prof_combo.setCurrentIndex(len(self._profiles) - 1)

    def _save_profile(self) -> None:
        idx = self._prof_combo.currentIndex()
        self._editor.apply(self._profiles[idx])
        self._prof_combo.setItemText(idx, self._profiles[idx].name)
        save_profiles(self._profiles)

    def _refresh_raw(self) -> None:
        if not self._path:
            return
        try:
            profile = self._editor.get_profile()
            header, rows = read_raw(self._path, profile)
            display = ([header] if header else []) + rows[:100]
            ncols = max((len(r) for r in display), default=0)
            self._raw_table.setRowCount(len(display))
            self._raw_table.setColumnCount(ncols)
            for r, row in enumerate(display):
                for c, cell in enumerate(row):
                    self._raw_table.setItem(r, c, QTableWidgetItem(cell))
        except Exception as exc:
            QMessageBox.warning(self, "Read error", str(exc))

    def _do_preview(self) -> None:
        if not self._path:
            QMessageBox.information(self, "No file", "Select a CSV file first.")
            return
        self._refresh_raw()
        try:
            profile = self._editor.get_profile()
            txs = parse_csv(self._path, profile)
            headers = ["Date", "Description", "Amount", "Balance", "Account", "Month"]
            keys = ["date", "description", "amount", "balance", "account", "month"]
            self._preview_table.setColumnCount(len(headers))
            self._preview_table.setHorizontalHeaderLabels(headers)
            self._preview_table.setRowCount(len(txs))
            for r, tx in enumerate(txs):
                for c, key in enumerate(keys):
                    val = tx.get(key)
                    if key == "amount" and val is not None:
                        text = f"{val:+.2f}"
                    elif key == "balance" and val is not None:
                        text = f"{val:.2f}"
                    else:
                        text = str(val) if val is not None else ""
                    self._preview_table.setItem(r, c, QTableWidgetItem(text))
            self._parsed = txs
        except Exception as exc:
            QMessageBox.warning(self, "Parse error", str(exc))

    def _accept(self) -> None:
        if not self._parsed:
            self._do_preview()
        if not self._parsed:
            QMessageBox.warning(self, "Nothing to import", "No transactions were parsed.")
            return
        self.accept()

    def get_transactions(self) -> list[dict]:
        return self._parsed


def _make_table() -> QTableWidget:
    t = QTableWidget()
    t.setEditTriggers(QTableWidget.NoEditTriggers)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    return t
