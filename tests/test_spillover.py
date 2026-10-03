from datetime import date

import numpy as np
import pandas as pd
import pytest

from research.conclude import main
from research.models.diebold_yilmaz import _var_ols, connectedness
from research.models.spillover_dy import conclude_panel
from research.panel import align_panel, complete_cases


def _driven_frame(positive: bool) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    n = 240
    us = np.zeros(n)
    vix = np.zeros(n)
    stock = np.zeros(n)
    for step in range(1, n):
        us[step] = rng.normal()
        vix[step] = rng.normal()
        stock[step] = 0.9 * us[step - 1] - 0.8 * vix[step - 1] + 0.02 * rng.normal()
    bump = 4.0 if positive else -4.0
    us[-5:] += bump
    vix[-5:] -= bump
    index = pd.bdate_range("2023-01-02", periods=n)
    return pd.DataFrame({"a_share": stock, "us_equity": us, "vix": vix}, index=index)


def test_var_recovers_exact_ar1_coefficient():
    values = np.zeros(80)
    values[0] = 1.0
    for step in range(1, len(values)):
        values[step] = 0.5 * values[step - 1]
    beta, _, _, _ = _var_ols(values.reshape(-1, 1), 1)
    assert beta[1, 0] == pytest.approx(0.5, abs=1e-8)
    assert beta[0, 0] == pytest.approx(0.0, abs=1e-8)


def test_independent_series_have_low_spillover():
    rng = np.random.default_rng(2)
    frame = pd.DataFrame(
        rng.normal(size=(300, 3)),
        columns=["a_share", "us_equity", "vix"],
        index=pd.bdate_range("2023-01-02", periods=300),
    )
    result = connectedness(frame)
    assert result is not None
    assert result.spillover_index < 35
    assert np.allclose(result.theta.sum(axis=1), 1.0)


def test_positive_external_shocks_lean_positive():
    out = conclude_panel("000001", "2024-06-03", _driven_frame(True))
    assert out.stance == "偏多"
    assert out.score > 0.15
    shares = {item["id"]: item["detail"]["fevd_share"] for item in out.used}
    assert shares["us_equity"] > 0.2
    assert "不构成交易建议" in out.disclaimer


def test_flipped_shocks_lean_negative():
    out = conclude_panel("000001", "2024-06-03", _driven_frame(False))
    assert out.stance == "偏空"
    assert out.score < -0.15


def test_short_panel_stays_neutral():
    frame = _driven_frame(True).head(20)
    out = conclude_panel("000001", "2024-06-03", frame)
    assert out.stance == "中性"
    assert out.score == 0.0
    assert out.confidence == 0.0
    assert out.used == []


def test_prior_us_return_aligns_to_next_a_share_session():
    a_share = pd.Series(
        [10.0, 10.0, 10.0, 10.0],
        index=pd.to_datetime(["2024-01-08", "2024-01-09", "2024-01-10", "2024-01-11"]),
    )
    us = pd.Series(
        [100.0, 110.0, 121.0],
        index=pd.to_datetime(["2024-01-05", "2024-01-08", "2024-01-09"]),
    )
    frame = align_panel(a_share, {"us_equity": us})
    assert frame.loc[pd.Timestamp("2024-01-09"), "us_equity"] == pytest.approx(0.1)
    assert frame.loc[pd.Timestamp("2024-01-10"), "us_equity"] == pytest.approx(0.1)


def test_sparse_column_is_dropped():
    index = pd.bdate_range("2023-01-02", periods=80)
    frame = pd.DataFrame(
        {
            "a_share": 1.0,
            "us_equity": 1.0,
            "northbound": np.nan,
        },
        index=index,
    )
    frame.loc[index[:10], "northbound"] = 1.0
    kept, dropped = complete_cases(frame)
    assert dropped == ["northbound"]
    assert list(kept.columns) == ["a_share", "us_equity"]


def test_cli_uses_injected_panel(monkeypatch, capsys):
    monkeypatch.setattr("research.conclude.FACTORS", [])
    frame = _driven_frame(True)

    def _panel(symbol, asof):
        assert symbol == "000001"
        assert asof == date(2024, 6, 3)
        return frame, []

    monkeypatch.setattr("research.models.spillover_dy.load_panel", _panel)
    assert (
        main(
            [
                "--symbol",
                "000001",
                "--model",
                "spillover_dy",
                "--asof",
                "2024-06-03",
            ]
        )
        == 0
    )
    assert "spillover_dy" in capsys.readouterr().out
