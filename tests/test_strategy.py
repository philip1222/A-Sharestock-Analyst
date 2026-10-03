import pandas as pd

from research.strategy import code_from_name, main, missing_books
from research.strategy_rules import evaluate


def _rising(n: int = 40, amount: float = 50_000_000) -> pd.DataFrame:
    close = pd.Series([10 + i * 0.05 for i in range(n)])
    return pd.DataFrame(
        {
            "date": pd.bdate_range("2024-01-02", periods=n),
            "close": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "volume": 1_000_000,
            "amount": amount,
        }
    )


def _valuation() -> dict:
    return {"pe_ttm": 8.0, "pe_percentile": 0.3, "pb": 0.7, "pb_percentile": 0.4}


def test_uptrend_with_valuation_can_buy():
    out = evaluate(
        _rising(),
        symbol="000001",
        asof="2024-03-01",
        valuation=_valuation(),
        references_ready=True,
    )
    assert out["action"] == "买入"
    assert out["confidence"] == "中"
    assert out["windows"]["1"]["trading_days"] == 1
    assert out["windows"]["30"]["return"] > 0
    assert out["plan"]["status"] == "active"
    assert out["plan"]["take_profit"] > out["plan"]["entry"] > out["plan"]["stop"]
    assert "不构成下单指令" in out["disclaimer"]


def test_downtrend_is_avoid():
    frame = _rising()
    frame["close"] = frame["close"].iloc[::-1].to_numpy()
    frame["high"] = frame["close"] * 1.01
    frame["low"] = frame["close"] * 0.99
    out = evaluate(
        frame,
        symbol="000001",
        asof="2024-03-01",
        valuation=_valuation(),
        references_ready=True,
    )
    assert out["action"] == "回避"
    assert out["trend"]["structure"] == "下行"


def test_missing_valuation_stays_watch():
    out = evaluate(
        _rising(),
        symbol="000001",
        asof="2024-03-01",
        valuation=None,
        references_ready=True,
    )
    assert out["action"] == "观察"
    assert "市盈率(TTM)" in out["missing"]
    assert out["plan"]["status"] == "reference_only"


def test_missing_books_do_not_change_action():
    out = evaluate(
        _rising(),
        symbol="000001",
        asof="2024-03-01",
        valuation=_valuation(),
        references_ready=False,
    )
    assert out["action"] == "买入"
    assert out["data"]["books_on_disk"] is False


def test_thin_liquidity_is_avoid():
    out = evaluate(
        _rising(amount=1_000),
        symbol="000001",
        asof="2024-03-01",
        valuation=_valuation(),
        references_ready=True,
    )
    assert out["action"] == "回避"
    assert any("成交额" in item for item in out["vetoes"])


def test_short_history_has_no_plan():
    out = evaluate(
        _rising(n=10),
        symbol="000001",
        asof="2024-03-01",
        valuation=_valuation(),
        references_ready=True,
    )
    assert out["action"] == "观察"
    assert out["plan"] is None
    assert out["windows"] == {}


def test_datetime_index_fills_window_dates():
    frame = _rising().set_index("date")
    out = evaluate(
        frame,
        symbol="000001",
        asof="2024-03-01",
        valuation=_valuation(),
        references_ready=True,
    )
    assert out["windows"]["1"]["end"] is not None
    assert out["path"][-1]["date"] == out["windows"]["1"]["end"]


def test_unique_chinese_name_resolves_to_code():
    table = pd.DataFrame({"code": ["000001", "000002"], "name": ["平安银行", "万科A"]})
    assert code_from_name("平安银行", table) == "000001"


def test_ambiguous_name_raises():
    table = pd.DataFrame(
        {"code": ["600000", "600001"], "name": ["浦发银行", "浦发转债"]}
    )
    try:
        code_from_name("浦发", table)
    except ValueError as exc:
        assert "多只股票" in str(exc)
    else:
        raise AssertionError("ambiguous name should fail")


def test_unknown_symbol_exits_2(capsys):
    assert main(["--symbol", "AAPL"]) == 2
    assert "无法识别" in capsys.readouterr().err


def test_missing_books_lists_expected_names(tmp_path):
    absent = missing_books(tmp_path)
    assert len(absent) == 18
    assert absent[0].startswith("L1_01_")
