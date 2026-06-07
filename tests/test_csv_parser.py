import tempfile
from pathlib import Path

import pytest

from accounting_anomaly.core.csv_parser import CsvProfile, parse_amount, parse_csv


def test_parse_amount_european():
    assert parse_amount("1.234,56", ",", ".") == 1234.56


def test_parse_amount_us():
    assert parse_amount("1,234.56", ".", ",") == 1234.56


def test_parse_amount_negative():
    assert parse_amount("-42,50", ",", ".") == pytest.approx(-42.50)


def test_parse_amount_parentheses():
    assert parse_amount("(100,00)", ",", ".") == pytest.approx(-100.0)


def test_parse_amount_no_thousands():
    assert parse_amount("3,50", ",", "") == pytest.approx(3.50)


def test_parse_csv_basic():
    content = (
        "Date;Description;Amount;Balance\n"
        "01.01.2024;Coffee Shop;-3,50;100,00\n"
        "15.01.2024;Monthly Salary;2000,00;2100,00\n"
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(content)
        tmp = Path(f.name)

    try:
        profile = CsvProfile(
            delimiter=";",
            decimal=",",
            thousands=".",
            skip_rows=1,
            date_col=0,
            date_format="%d.%m.%Y",
            description_col=1,
            amount_col=2,
            balance_col=3,
            encoding="utf-8",
        )
        txs = parse_csv(tmp, profile)
        assert len(txs) == 2

        assert txs[0]["date"] == "2024-01-01"
        assert txs[0]["description"] == "Coffee Shop"
        assert txs[0]["amount"] == pytest.approx(-3.50)
        assert txs[0]["balance"] == pytest.approx(100.0)
        assert txs[0]["month"] == "2024-01"
        assert txs[0]["status"] == "pending"
        assert txs[0]["payee"] == ""

        assert txs[1]["amount"] == pytest.approx(2000.0)
    finally:
        tmp.unlink(missing_ok=True)


def test_parse_csv_with_payee_column():
    content = "Date;Payee;Purpose;Amount\n01.01.2024;ACME GmbH;Office supplies;-42,50\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(content)
        tmp = Path(f.name)

    try:
        profile = CsvProfile(
            delimiter=";",
            decimal=",",
            thousands=".",
            skip_rows=1,
            date_col=0,
            payee_col=1,
            description_col=2,
            amount_col=3,
            encoding="utf-8",
        )
        txs = parse_csv(tmp, profile)
        assert len(txs) == 1
        assert txs[0]["payee"] == "ACME GmbH"
        assert txs[0]["description"] == "Office supplies"
    finally:
        tmp.unlink(missing_ok=True)


def test_parse_csv_skips_empty_rows():
    content = (
        "Date;Description;Amount\n01.01.2024;Coffee;-3,50\n\n   ;;  \n02.01.2024;Rent;-500,00\n"
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(content)
        tmp = Path(f.name)

    try:
        profile = CsvProfile(
            delimiter=";", decimal=",", thousands=".", skip_rows=1, encoding="utf-8"
        )
        txs = parse_csv(tmp, profile)
        assert len(txs) == 2
    finally:
        tmp.unlink(missing_ok=True)
