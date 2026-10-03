#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026/10/3
Desc: 命令行入口，提供接口检索、元数据查询与接口调用能力
"""

import argparse
import json
import sys
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import pandas as pd

from akshare.exceptions import AkshareException, InvalidParameterError
from akshare.registry import interface_info, list_categories, search

FORMATS = ("table", "json", "csv")
DEFAULT_HEAD = 20


def _dumps(payload: Any) -> str:
    """
    统一的 JSON 序列化口径，保留中文原文而非转义码点。

    :param payload: 可序列化对象
    :return: JSON 文本
    :rtype: str
    """
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)


def _parse_arg_pairs(pairs: Optional[Sequence[str]]) -> Dict[str, str]:
    """
    解析 ``--arg key=value`` 形式的参数。

    值一律按字符串处理：股票代码一类的入参以 0 开头时若做类型推断会被
    转成整数而丢掉前导 0，需要非字符串类型时请改用 ``--kwargs``。

    :param pairs: 原始 ``key=value`` 字符串序列
    :return: 关键字参数
    :rtype: dict
    :raises InvalidParameterError: 当缺少 ``=`` 或键为空时
    """
    result: Dict[str, str] = {}
    for item in pairs or []:
        if "=" not in item:
            raise InvalidParameterError(f"--arg 需要 key=value 形式，收到 {item!r}")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise InvalidParameterError(f"--arg 的键不能为空，收到 {item!r}")
        result[key] = value
    return result


def _parse_kwargs(raw: Optional[str]) -> Dict[str, Any]:
    """
    解析 ``--kwargs`` 传入的 JSON 对象。

    :param raw: JSON 文本
    :return: 关键字参数
    :rtype: dict
    :raises InvalidParameterError: 当 JSON 非法或顶层不是对象时
    """
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except ValueError as e:
        raise InvalidParameterError(f"--kwargs 不是合法 JSON: {e}")
    if not isinstance(parsed, dict):
        raise InvalidParameterError(
            f"--kwargs 顶层必须是 JSON 对象，收到 {type(parsed).__name__}"
        )
    return parsed


def _suggest(name: str) -> str:
    """
    为拼错的接口名给出最接近的候选。

    :param name: 用户输入的接口名
    :return: 顿号分隔的候选名，无候选时返回 "无"
    :rtype: str
    """
    try:
        candidates = list(search(name, limit=3)["接口名"])
    except AkshareException:
        return "无"
    return "、".join(candidates) if candidates else "无"


def _resolve(name: str) -> Callable[..., Any]:
    """
    把接口名解析为顶层包上的可调用对象。

    :param name: 接口名，如 "stock_zh_a_hist"
    :return: 接口函数
    :rtype: callable
    :raises InvalidParameterError: 当接口不存在或不可调用时
    """
    if name.startswith("_"):
        raise InvalidParameterError(f"{name} 不是公开接口")
    import akshare

    func = getattr(akshare, name, None)
    if func is None or not callable(func):
        raise InvalidParameterError(f"未知接口 {name}，最接近的候选: {_suggest(name)}")
    return func


def _frame_text(frame: pd.DataFrame, fmt: str) -> str:
    """
    按指定格式渲染 DataFrame。

    :param frame: 待渲染数据
    :param fmt: 输出格式，取值见 FORMATS
    :return: 渲染结果
    :rtype: str
    """
    if fmt == "csv":
        return frame.to_csv(index=False).rstrip("\n")
    if fmt == "json":
        payload = json.loads(
            frame.to_json(orient="records", force_ascii=False, date_format="iso")
        )
        return _dumps(payload)
    with pd.option_context("display.max_columns", None, "display.width", 200):
        return frame.to_string(index=False)


def _render(result: Any, fmt: str, head: int) -> Tuple[str, Optional[str]]:
    """
    渲染接口返回值，并在发生截断时给出提示。

    非表格返回值（dict/list/标量）一律按 JSON 渲染，不受 fmt 影响。

    :param result: 接口返回值
    :param fmt: 输出格式
    :param head: 最多展示的行数，<=0 表示全量
    :return: (渲染文本, 截断提示)
    :rtype: tuple
    """
    if isinstance(result, pd.Series):
        result = result.to_frame()
    if not isinstance(result, pd.DataFrame):
        if isinstance(result, (dict, list)):
            return _dumps(result), None
        return str(result), None

    total = len(result)
    shown = result if head <= 0 else result.head(head)
    note = None
    if len(shown) < total:
        note = f"共 {total} 行，已显示前 {len(shown)} 行（--head 0 查看全量）"
    return _frame_text(shown, fmt), note


def _records_frame(records: Optional[List[Dict]]) -> Optional[pd.DataFrame]:
    """
    把 registry 中的 params/outputs 列表转成 DataFrame。

    :param records: 参数或输出列表
    :return: 转换结果，列表为空时返回 None
    :rtype: pandas.DataFrame or None
    """
    if not records:
        return None
    frame = pd.DataFrame(records)
    # registry JSON 里的键序是 desc 在先，直接展示会把最该先看的接口名挤到右边
    preferred = [name for name in ("name", "type", "desc") if name in frame.columns]
    rest = [name for name in frame.columns if name not in preferred]
    return frame[preferred + rest]


def _info_text(info: Dict) -> str:
    """
    把接口元数据渲染成人类可读文本。

    :param info: interface_info 的返回值
    :return: 渲染结果
    :rtype: str
    """
    lines = [
        f"接口名: {info['name']}",
        f"类目: {info['category']}",
        f"模块: {info['module']}",
        f"描述: {info.get('desc') or '-'}",
        f"有无文档: {info['documented']}",
    ]
    if info.get("url"):
        lines.append(f"链接: {info['url']}")
    if info.get("limit_desc"):
        lines.append(f"限量: {info['limit_desc']}")

    params = _records_frame(info.get("params"))
    if params is not None:
        lines += ["", "输入参数:", _frame_text(params, "table")]
    outputs = _records_frame(info.get("outputs"))
    if outputs is not None:
        lines += ["", "输出参数:", _frame_text(outputs, "table")]
    if info.get("example"):
        lines += ["", "示例:", str(info["example"])]
    return "\n".join(lines)


def _cmd_search(args: argparse.Namespace) -> int:
    """
    执行 search 子命令。

    :param args: 已解析的命令行参数
    :return: 退出码
    :rtype: int
    """
    frame = search(
        args.query,
        limit=args.limit,
        category=args.category,
        documented_only=args.documented_only,
    )
    if frame.empty:
        print(f"未匹配到接口: {args.query}", file=sys.stderr)
    print(_frame_text(frame, args.format))
    return 0


def _cmd_info(args: argparse.Namespace) -> int:
    """
    执行 info 子命令。

    :param args: 已解析的命令行参数
    :return: 退出码
    :rtype: int
    """
    info = interface_info(args.name)
    print(_dumps(info) if args.format == "json" else _info_text(info))
    return 0


def _cmd_categories(args: argparse.Namespace) -> int:
    """
    执行 categories 子命令。

    :param args: 已解析的命令行参数
    :return: 退出码
    :rtype: int
    """
    print(_frame_text(list_categories(), args.format))
    return 0


def _cmd_call(args: argparse.Namespace) -> int:
    """
    执行 call 子命令。

    :param args: 已解析的命令行参数
    :return: 退出码
    :rtype: int
    """
    kwargs = _parse_kwargs(args.kwargs)
    kwargs.update(_parse_arg_pairs(args.arg))
    func = _resolve(args.name)
    try:
        result = func(**kwargs)
    except TypeError as e:
        raise InvalidParameterError(
            f"{args.name} 参数不匹配: {e}；可用 akshare info {args.name} 查看入参"
        )
    text, note = _render(result, args.format, args.head)
    print(text)
    if note:
        print(note, file=sys.stderr)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    """
    构造命令行解析器。

    :return: 解析器
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog="akshare",
        description="AKShare 命令行入口：检索接口、查看元数据并直接取数",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    search_parser = subparsers.add_parser("search", help="离线检索接口")
    search_parser.add_argument("query", help="查询词，如 'A股 历史行情'")
    search_parser.add_argument(
        "--limit", type=int, default=10, help="返回条数上限，默认 10"
    )
    search_parser.add_argument("--category", default=None, help="限定类目，如 stock")
    search_parser.add_argument(
        "--documented-only", action="store_true", help="仅返回有文档的接口"
    )
    search_parser.add_argument(
        "--format", choices=FORMATS, default="table", help="输出格式，默认 table"
    )
    search_parser.set_defaults(func=_cmd_search)

    info_parser = subparsers.add_parser("info", help="查看接口入参与输出")
    info_parser.add_argument("name", help="接口名，如 stock_zh_a_hist")
    info_parser.add_argument(
        "--format", choices=("table", "json"), default="table", help="输出格式"
    )
    info_parser.set_defaults(func=_cmd_info)

    categories_parser = subparsers.add_parser("categories", help="列出全部类目")
    categories_parser.add_argument(
        "--format", choices=FORMATS, default="table", help="输出格式，默认 table"
    )
    categories_parser.set_defaults(func=_cmd_categories)

    call_parser = subparsers.add_parser("call", help="调用接口并打印结果")
    call_parser.add_argument("name", help="接口名，如 stock_zh_a_hist")
    call_parser.add_argument(
        "--kwargs", default=None, help="JSON 对象形式的入参，支持非字符串类型"
    )
    call_parser.add_argument(
        "--arg",
        action="append",
        metavar="KEY=VALUE",
        help="字符串入参，可重复；值不做类型推断",
    )
    call_parser.add_argument(
        "--head",
        type=int,
        default=DEFAULT_HEAD,
        help=f"最多展示的行数，默认 {DEFAULT_HEAD}，0 表示全量",
    )
    call_parser.add_argument(
        "--format", choices=FORMATS, default="table", help="输出格式，默认 table"
    )
    call_parser.set_defaults(func=_cmd_call)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """
    命令行主入口。

    :param argv: 命令行参数，默认取 sys.argv[1:]
    :return: 退出码
    :rtype: int
    """
    args = _build_parser().parse_args(argv)
    try:
        return args.func(args)
    except AkshareException as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("已中断", file=sys.stderr)
        return 130
    except Exception as e:  # 上游站点改版等运行期故障
        print(f"调用失败: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
