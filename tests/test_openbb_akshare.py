import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest
import requests

EXT = Path(__file__).resolve().parents[1] / "extensions" / "openbb_akshare"
sys.path.insert(0, str(EXT))

from openbb_akshare.sources import (  # noqa: E402
    fetch_history_rows,
    first_successful,
    history_rows,
    is_network_failure,
    quote_rows,
)
from openbb_akshare.symbols import (  # noqa: E402
    bare_symbol,
    exchange_of,
    prefixed_symbol,
)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("000001", "000001"),
        ("sz000001", "000001"),
        ("SZ000001", "000001"),
        ("600000", "600000"),
        ("sh600000", "600000"),
        ("430047", "430047"),
    ],
)
def test_bare_symbol_accepts_common_forms(raw, expected):
    assert bare_symbol(raw) == expected


def test_bare_symbol_rejects_garbage():
    with pytest.raises(ValueError):
        bare_symbol("AAPL")


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("000001", "sz000001"),
        ("600000", "sh600000"),
        ("688001", "sh688001"),
        ("430047", "bj430047"),
        ("SH600000", "sh600000"),
    ],
)
def test_prefixed_symbol_adds_market(raw, expected):
    assert prefixed_symbol(raw) == expected


def test_exchange_of_maps_market():
    assert exchange_of("000001") == "SZSE"
    assert exchange_of("600000") == "SSE"
    assert exchange_of("430047") == "BSE"


def test_history_rows_maps_eastmoney_columns_and_converts_lots():
    frame = pd.DataFrame(
        {
            "日期": [date(2024, 1, 4)],
            "开盘": [9.19],
            "收盘": [9.11],
            "最高": [9.19],
            "最低": [9.08],
            "成交量": [8641.94],
            "成交额": [7.874701e8],
            "涨跌幅": [-0.98],
            "涨跌额": [-0.09],
        }
    )
    rows = history_rows(frame, source="eastmoney", symbol="000001")
    assert len(rows) == 1
    row = rows[0]
    assert row["date"] == date(2024, 1, 4)
    assert row["open"] == 9.19
    assert row["close"] == 9.11
    assert row["volume"] == pytest.approx(864194.0)
    assert row["change_percent"] == pytest.approx(-0.0098)
    assert row["source"] == "eastmoney"
    assert row["symbol"] == "000001"


def test_history_rows_keeps_tencent_share_volume():
    frame = pd.DataFrame(
        {
            "date": [date(2024, 1, 4)],
            "open": [9.19],
            "close": [9.11],
            "high": [9.19],
            "low": [9.08],
            "volume": [864194.0],
            "amount": [787470100.0],
        }
    )
    rows = history_rows(frame, source="tencent", symbol="000001")
    assert rows[0]["volume"] == pytest.approx(864194.0)
    assert rows[0]["source"] == "tencent"


def test_quote_rows_accepts_prefixed_codes():
    frame = pd.DataFrame(
        {
            "代码": ["sz000001", "sh600000"],
            "名称": ["平安银行", "浦发银行"],
            "最新价": [11.57, 8.11],
            "涨跌幅": [1.94, 0.50],
        }
    )
    rows = quote_rows(frame, source="sina", symbol="000001")
    assert len(rows) == 1
    assert rows[0]["symbol"] == "000001"
    assert rows[0]["last_price"] == 11.57


def test_quote_rows_filters_and_normalizes_percent():
    frame = pd.DataFrame(
        {
            "代码": ["600000", "000001"],
            "名称": ["浦发银行", "平安银行"],
            "最新价": [8.11, 9.21],
            "涨跌幅": [1.76, 0.33],
            "今开": [8.10, 9.16],
            "昨收": [7.95, 9.18],
        }
    )
    rows = quote_rows(frame, source="eastmoney", symbol="000001")
    assert len(rows) == 1
    assert rows[0]["last_price"] == 9.21
    assert rows[0]["close"] == 9.21
    assert rows[0]["change_percent"] == pytest.approx(0.0033)
    assert rows[0]["exchange"] == "SZSE"
    assert rows[0]["asset_type"] == "stock"


def test_is_network_failure_recognizes_proxy_and_nested_cause():
    assert is_network_failure(requests.exceptions.ProxyError("proxy"))
    nested = RuntimeError("wrap")
    nested.__cause__ = ConnectionError("upstream")
    assert is_network_failure(nested)
    assert not is_network_failure(ValueError("bad symbol"))


def test_first_successful_skips_network_errors():
    calls = []

    def boom():
        calls.append("em")
        raise requests.exceptions.ProxyError("blocked")

    def ok():
        calls.append("tx")
        return pd.DataFrame({"date": [date(2024, 1, 2)], "close": [9.21]})

    source, frame = first_successful([("eastmoney", boom), ("tencent", ok)])
    assert source == "tencent"
    assert list(frame["close"]) == [9.21]
    assert calls == ["em", "tx"]


def test_first_successful_does_not_swallow_value_error():
    def bad():
        raise ValueError("sina hfq factor not available")

    with pytest.raises(ValueError):
        first_successful([("sina", bad)])


def test_first_successful_raises_after_all_network_failures():
    def boom():
        raise requests.exceptions.ConnectionError("down")

    with pytest.raises(RuntimeError) as exc:
        first_successful([("eastmoney", boom), ("tencent", boom)])
    assert "eastmoney" in str(exc.value)
    assert "tencent" in str(exc.value)


def test_fetch_history_rows_uses_injected_callers():
    def em(**kwargs):
        raise requests.exceptions.ProxyError("kline blocked")

    def tx(**kwargs):
        assert kwargs["symbol"] == "sz000001"
        assert kwargs["start_date"] == "20240101"
        return pd.DataFrame(
            {
                "date": [date(2024, 1, 2)],
                "open": [9.39],
                "close": [9.21],
                "high": [9.42],
                "low": [9.21],
                "volume": [1158366.0],
                "amount": [1075742300.0],
            }
        )

    rows = fetch_history_rows(
        symbol="000001",
        start="20240101",
        end="20240131",
        callers={"eastmoney": em, "tencent": tx, "sina": em},
    )
    assert rows[0]["source"] == "tencent"
    assert rows[0]["close"] == 9.21


def test_weekly_history_does_not_fall_back_to_daily_sources():
    def em(**kwargs):
        assert kwargs["period"] == "weekly"
        raise requests.exceptions.ProxyError("kline blocked")

    def should_not_run(**kwargs):
        raise AssertionError("daily fallback must not run for weekly")

    with pytest.raises(RuntimeError):
        fetch_history_rows(
            symbol="000001",
            start="20240101",
            end="20240131",
            period="weekly",
            callers={
                "eastmoney": em,
                "tencent": should_not_run,
                "sina": should_not_run,
            },
        )
