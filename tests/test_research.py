from datetime import date

import pandas as pd

from research.conclude import build, main
from research.factors.a_share_flow import evaluate as flow_evaluate
from research.factors.a_share_tape import evaluate as tape_evaluate
from research.factors.commodity import evaluate as commodity_evaluate
from research.factors.fx import evaluate as fx_evaluate
from research.factors.us_risk import evaluate as risk_evaluate
from research.models.rules_v1 import run
from research.types import FactorContext, FactorResult


def _result(
    fid: str, weight: float, status: str = "ok", direction: float | None = 0.0
) -> FactorResult:
    return FactorResult(
        id=fid,
        name=fid,
        weight=weight,
        rationale="测试",
        status=status,
        direction=direction if status == "ok" else None,
    )


def test_rules_all_factors_lean_positive():
    factors = [
        _result("a", 1.0, direction=1.0),
        _result("b", 1.0, direction=1.0),
    ]
    out = run("000001", "2024-01-10", factors)
    assert out.stance == "偏多"
    assert out.score == 1.0
    assert out.confidence == 1.0
    assert out.skipped == []
    assert "不构成交易建议" in out.disclaimer


def test_rules_renormalize_when_a_factor_is_missing():
    factors = [
        _result("heavy", 1.5, status="missing"),
        _result("light", 1.0, direction=-1.0),
    ]
    out = run("000001", "2024-01-10", factors)
    assert out.score == -1.0
    assert out.stance == "偏空"
    assert out.confidence == round(1.0 / 2.5, 4)
    assert [item["id"] for item in out.skipped] == ["heavy"]


def test_rules_neutral_band_and_empty():
    mixed = [_result("a", 1.0, direction=0.1), _result("b", 1.0, direction=-0.1)]
    assert run("000001", "2024-01-10", mixed).stance == "中性"
    empty = run("000001", "2024-01-10", [_result("a", 1.0, status="missing")])
    assert empty.stance == "中性"
    assert empty.score == 0.0
    assert empty.confidence == 0.0


def test_unknown_symbol_exits_2(capsys):
    assert main(["--symbol", "AAPL"]) == 2
    assert "无法识别" in capsys.readouterr().err


def test_unknown_model_exits_2(capsys):
    assert main(["--symbol", "000001", "--model", "nope"]) == 2
    assert "未知模型" in capsys.readouterr().err


def test_tape_direction_from_injected_frame():
    frame = pd.DataFrame({"close": [10.0, 10.8], "source": ["tencent", "tencent"]})
    result = tape_evaluate(FactorContext("000001", date(2024, 1, 10)), frame)
    assert result.status == "ok"
    assert result.direction == 1.0
    assert result.detail["lookback_return"] == 0.08


def test_flow_sums_latest_northbound():
    frame = pd.DataFrame(
        {
            "交易日": ["2024-01-09", "2024-01-10", "2024-01-10"],
            "板块": ["沪股通", "沪股通", "深股通"],
            "资金净流入": [100.0, 30.0, 20.0],
        }
    )
    result = flow_evaluate(FactorContext("000001", date(2024, 1, 10)), frame)
    assert result.status == "ok"
    assert result.detail["net_inflow_yi"] == 50.0
    assert result.direction == 1.0


def test_fx_dollar_strength_is_negative_for_a_share():
    frame = pd.DataFrame({"央行中间价": [700.0, 714.0]})
    result = fx_evaluate(FactorContext("000001", date(2024, 1, 10)), frame)
    assert result.direction == -1.0


def test_commodity_rise_is_positive():
    frame = pd.DataFrame(
        {
            "date": ["2024-01-02", "2024-01-10"],
            "close": [100.0, 106.0],
        }
    )
    result = commodity_evaluate(FactorContext("000001", date(2024, 1, 10)), frame)
    assert result.direction == 1.0


def test_vix_above_20_is_negative():
    frame = pd.DataFrame({"close": [30.0]})
    result = risk_evaluate(FactorContext("000001", date(2024, 1, 10)), frame)
    assert result.direction == -1.0
    assert result.source == "cboe"


def test_build_uses_registered_factors(monkeypatch):
    class Stub:
        def evaluate(self, ctx):
            return _result("stub", 1.0, direction=0.5)

    monkeypatch.setattr("research.conclude.FACTORS", [Stub()])
    payload = build("sz000001", date(2024, 1, 10), "rules_v1")
    assert payload["symbol"] == "000001"
    assert payload["model"] == "rules_v1"
    assert payload["used"][0]["id"] == "stub"
