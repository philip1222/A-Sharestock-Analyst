import pandas as pd
import pytest

from akshare import cli, registry
from akshare.cli import (
    _frame_text,
    _parse_arg_pairs,
    _parse_kwargs,
    _records_frame,
    _render,
    _resolve,
    main,
)
from akshare.exceptions import InvalidParameterError

FIXTURE = {
    "schema_version": 1,
    "interfaces": [
        {
            "name": "stock_zh_a_hist",
            "module": "akshare.stock.a",
            "category": "stock",
            "documented": True,
            "desc": "东方财富-沪深京 A 股历史行情数据",
            "url": "https://example.com/hist",
            "limit_desc": "单次返回指定区间的日频数据",
            "params": [{"desc": "股票代码", "name": "symbol", "type": "str"}],
            "outputs": [{"desc": "收盘价", "name": "收盘", "type": "float64"}],
            "example": "ak.stock_zh_a_hist(symbol='000001')",
        },
        {
            "name": "fund_open_fund_info_em",
            "module": "akshare.fund.b",
            "category": "fund",
            "documented": True,
            "desc": "东方财富-开放式基金净值",
            "url": None,
            "limit_desc": None,
            "params": [],
            "outputs": [],
            "example": None,
        },
    ],
}


@pytest.fixture(autouse=True)
def _use_fixture(monkeypatch):
    monkeypatch.setattr(registry, "_REGISTRY", FIXTURE)
    yield
    monkeypatch.setattr(registry, "_REGISTRY", None)


# --- 入参解析 ---------------------------------------------------------------


def test_parse_arg_pairs_builds_kwargs():
    assert _parse_arg_pairs(["symbol=000001", "period=daily"]) == {
        "symbol": "000001",
        "period": "daily",
    }


def test_parse_arg_pairs_handles_none_and_empty():
    assert _parse_arg_pairs(None) == {}
    assert _parse_arg_pairs([]) == {}


def test_parse_arg_pairs_keeps_empty_value():
    # adjust= 是 AKShare 里「不复权」的常用写法，不能被当成缺失参数丢掉
    assert _parse_arg_pairs(["adjust="]) == {"adjust": ""}


def test_parse_arg_pairs_splits_on_first_equal_only():
    assert _parse_arg_pairs(["expr=a=b"]) == {"expr": "a=b"}


def test_parse_arg_pairs_never_infers_type():
    # 股票代码的前导 0 一旦被推断成整数就会丢失，这里钉住「一律字符串」
    parsed = _parse_arg_pairs(["symbol=000001", "limit=10"])
    assert parsed["symbol"] == "000001"
    assert parsed["limit"] == "10"


@pytest.mark.parametrize("bad", ["symbol", "=value", " =value"])
def test_parse_arg_pairs_rejects_malformed(bad):
    with pytest.raises(InvalidParameterError):
        _parse_arg_pairs([bad])


def test_parse_kwargs_parses_json_object():
    assert _parse_kwargs('{"limit": 10, "flag": true}') == {
        "limit": 10,
        "flag": True,
    }


def test_parse_kwargs_empty_returns_empty_dict():
    assert _parse_kwargs(None) == {}
    assert _parse_kwargs("") == {}


def test_parse_kwargs_rejects_invalid_json():
    with pytest.raises(InvalidParameterError):
        _parse_kwargs("notjson")


def test_parse_kwargs_rejects_non_object_top_level():
    with pytest.raises(InvalidParameterError) as exc:
        _parse_kwargs("[1, 2]")
    assert "JSON 对象" in str(exc.value)


# --- 接口解析 ---------------------------------------------------------------


def test_resolve_returns_callable(monkeypatch):
    import akshare

    monkeypatch.setattr(akshare, "cli_probe", lambda: None, raising=False)
    assert _resolve("cli_probe") is akshare.cli_probe


def test_resolve_rejects_private_name():
    with pytest.raises(InvalidParameterError):
        _resolve("_load")


def test_resolve_unknown_name_suggests_candidates():
    with pytest.raises(InvalidParameterError) as exc:
        _resolve("stock_zh_a_hisr")
    assert "stock_zh_a_hist" in str(exc.value)


def test_resolve_rejects_non_callable_attribute(monkeypatch):
    # akshare 顶层还挂着 pd 这类非接口对象，不应该被 call 当成接口调用
    import akshare

    monkeypatch.setattr(akshare, "cli_not_callable", 42, raising=False)
    with pytest.raises(InvalidParameterError):
        _resolve("cli_not_callable")


# --- 渲染 -------------------------------------------------------------------

FRAME = pd.DataFrame({"日期": ["20240101", "20240102"], "收盘": [9.11, 9.27]})


def test_frame_text_csv_has_no_index():
    text = _frame_text(FRAME, "csv")
    assert text.splitlines()[0] == "日期,收盘"
    assert text.splitlines()[1] == "20240101,9.11"


def test_frame_text_json_is_records_with_chinese_kept():
    text = _frame_text(FRAME, "json")
    assert '"收盘"' in text
    assert "\\u" not in text


def test_frame_text_table_omits_index():
    lines = _frame_text(FRAME, "table").splitlines()
    assert lines[0].split() == ["日期", "收盘"]


def test_render_truncates_and_reports_note():
    frame = pd.DataFrame({"a": range(50)})
    text, note = _render(frame, "csv", 5)
    assert len(text.splitlines()) == 6  # 表头 + 5 行
    assert "共 50 行" in note


def test_render_head_zero_returns_everything():
    frame = pd.DataFrame({"a": range(50)})
    text, note = _render(frame, "csv", 0)
    assert len(text.splitlines()) == 51
    assert note is None


def test_render_no_note_when_nothing_truncated():
    _, note = _render(FRAME, "table", 20)
    assert note is None


def test_render_converts_series_to_frame():
    text, _ = _render(pd.Series([1, 2], name="值"), "csv", 20)
    assert "值" in text


def test_render_serializes_mapping_as_json():
    text, note = _render({"名称": "平安银行"}, "table", 20)
    assert '"名称": "平安银行"' in text
    assert note is None


def test_render_falls_back_to_str_for_scalar():
    assert _render(42, "table", 20) == ("42", None)


def test_records_frame_puts_name_first():
    frame = _records_frame([{"desc": "股票代码", "name": "symbol", "type": "str"}])
    assert list(frame.columns) == ["name", "type", "desc"]


def test_records_frame_empty_returns_none():
    assert _records_frame([]) is None
    assert _records_frame(None) is None


# --- 子命令 -----------------------------------------------------------------


def test_search_prints_matches(capsys):
    assert main(["search", "历史行情"]) == 0
    assert "stock_zh_a_hist" in capsys.readouterr().out


def test_search_filters_by_category(capsys):
    assert main(["search", "东方财富", "--category", "fund"]) == 0
    out = capsys.readouterr().out
    assert "fund_open_fund_info_em" in out
    assert "stock_zh_a_hist" not in out


def test_search_without_match_warns_on_stderr(capsys):
    assert main(["search", "完全不相关的词"]) == 0
    assert "未匹配到接口" in capsys.readouterr().err


def test_search_negative_limit_exits_nonzero(capsys):
    assert main(["search", "stock", "--limit", "-1"]) == 1
    assert "错误" in capsys.readouterr().err


def test_info_renders_params_and_example(capsys):
    assert main(["info", "stock_zh_a_hist"]) == 0
    out = capsys.readouterr().out
    assert "输入参数" in out
    assert "symbol" in out
    assert "ak.stock_zh_a_hist" in out


def test_info_json_format_emits_raw_record(capsys):
    assert main(["info", "stock_zh_a_hist", "--format", "json"]) == 0
    assert '"module": "akshare.stock.a"' in capsys.readouterr().out


def test_info_unknown_name_exits_nonzero(capsys):
    assert main(["info", "no_such_interface"]) == 1
    assert "错误" in capsys.readouterr().err


def test_categories_lists_counts(capsys):
    assert main(["categories"]) == 0
    out = capsys.readouterr().out
    assert "stock" in out
    assert "fund" in out


def test_call_passes_kwargs_and_prints_frame(monkeypatch, capsys):
    import akshare

    captured = {}

    def fake(**kwargs):
        captured.update(kwargs)
        return FRAME

    monkeypatch.setattr(akshare, "cli_probe", fake, raising=False)
    exit_code = main(
        [
            "call",
            "cli_probe",
            "--kwargs",
            '{"limit": 10}',
            "--arg",
            "symbol=000001",
            "--format",
            "csv",
        ]
    )

    assert exit_code == 0
    assert captured == {"limit": 10, "symbol": "000001"}
    assert "20240101,9.11" in capsys.readouterr().out


def test_call_arg_overrides_kwargs(monkeypatch):
    import akshare

    captured = {}

    def fake(**kwargs):
        captured.update(kwargs)
        return FRAME

    monkeypatch.setattr(akshare, "cli_probe", fake, raising=False)
    main(["call", "cli_probe", "--kwargs", '{"symbol": "1"}', "--arg", "symbol=2"])
    assert captured["symbol"] == "2"


def test_call_truncation_note_goes_to_stderr(monkeypatch, capsys):
    # json/csv 的 stdout 必须只有数据，否则下游 jq 之类的解析会被提示行打断
    import akshare

    monkeypatch.setattr(
        akshare, "cli_probe", lambda: pd.DataFrame({"a": range(50)}), raising=False
    )
    assert main(["call", "cli_probe", "--head", "5", "--format", "json"]) == 0
    captured = capsys.readouterr()
    assert "共 50 行" in captured.err
    assert "共 50 行" not in captured.out


def test_call_reports_parameter_mismatch(monkeypatch, capsys):
    import akshare

    monkeypatch.setattr(akshare, "cli_probe", lambda symbol: FRAME, raising=False)
    assert main(["call", "cli_probe", "--arg", "wrong=1"]) == 1
    assert "参数不匹配" in capsys.readouterr().err


def test_call_unknown_interface_exits_nonzero(capsys):
    assert main(["call", "stock_zh_a_hisr"]) == 1
    assert "stock_zh_a_hist" in capsys.readouterr().err


def test_call_surfaces_upstream_failure_without_traceback(monkeypatch, capsys):
    import akshare

    def boom():
        raise ConnectionError("upstream down")

    monkeypatch.setattr(akshare, "cli_probe", boom, raising=False)
    assert main(["call", "cli_probe"]) == 1
    err = capsys.readouterr().err
    assert "ConnectionError" in err
    assert "Traceback" not in err


def test_keyboard_interrupt_returns_130(monkeypatch, capsys):
    import akshare

    def interrupted():
        raise KeyboardInterrupt

    monkeypatch.setattr(akshare, "cli_probe", interrupted, raising=False)
    assert main(["call", "cli_probe"]) == 130


def test_missing_subcommand_exits_with_usage_error():
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2


def test_default_head_is_applied(monkeypatch, capsys):
    import akshare

    monkeypatch.setattr(
        akshare, "cli_probe", lambda: pd.DataFrame({"a": range(100)}), raising=False
    )
    main(["call", "cli_probe", "--format", "csv"])
    assert len(capsys.readouterr().out.strip().splitlines()) == cli.DEFAULT_HEAD + 1
