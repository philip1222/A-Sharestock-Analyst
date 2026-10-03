#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026/10/3
Desc: A 股历史行情 Fetcher，东方财富失败时自动换腾讯 / 新浪
"""

from datetime import date as dateType
from typing import Any, Literal

from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.equity_historical import (
    EquityHistoricalData,
    EquityHistoricalQueryParams,
)
from openbb_core.provider.utils.errors import EmptyDataError
from pydantic import Field

from openbb_akshare.sources import fetch_history_rows
from openbb_akshare.symbols import bare_symbol


class AkshareEquityHistoricalQueryParams(EquityHistoricalQueryParams):
    """A 股历史行情查询。"""

    period: Literal["daily", "weekly", "monthly"] = Field(
        default="daily",
        description="K 线周期。周线 / 月线仅东方财富提供，该源失败时不会回退到日线源。",
    )
    adjust: Literal["", "qfq", "hfq"] = Field(
        default="",
        description="复权：空字符串不复权，qfq 前复权，hfq 后复权。",
    )


class AkshareEquityHistoricalData(EquityHistoricalData):
    """A 股历史行情一行。"""

    symbol: str | None = Field(default=None, description="6 位 A 股代码。")
    source: str | None = Field(
        default=None, description="实际命中的数据源：eastmoney / tencent / sina。"
    )
    amount: float | None = Field(default=None, description="成交额，单位元。")
    change: float | None = Field(default=None, description="涨跌额。")
    change_percent: float | None = Field(
        default=None,
        description="涨跌幅，归一化小数（0.0176 表示 1.76%）。",
        json_schema_extra={"x-unit_measurement": "percent", "x-frontend_multiply": 100},
    )
    turnover: float | None = Field(default=None, description="换手率，若源提供。")


class AkshareEquityHistoricalFetcher(
    Fetcher[AkshareEquityHistoricalQueryParams, list[AkshareEquityHistoricalData]]
):
    """A 股历史行情。"""

    require_credentials = False

    @staticmethod
    def transform_query(params: dict[str, Any]) -> AkshareEquityHistoricalQueryParams:
        """校验入参。"""
        query = AkshareEquityHistoricalQueryParams(**params)
        bare_symbol(query.symbol)
        return query

    @staticmethod
    def extract_data(
        query: AkshareEquityHistoricalQueryParams,
        credentials: dict[str, str] | None,
        **kwargs: Any,
    ) -> list[dict]:
        """按换源顺序取数。"""
        start = (query.start_date or dateType(1990, 1, 1)).strftime("%Y%m%d")
        end = (query.end_date or dateType.today()).strftime("%Y%m%d")
        return fetch_history_rows(
            symbol=query.symbol,
            start=start,
            end=end,
            period=query.period,
            adjust=query.adjust,
        )

    @staticmethod
    def transform_data(
        query: AkshareEquityHistoricalQueryParams,
        data: list[dict],
        **kwargs: Any,
    ) -> list[AkshareEquityHistoricalData]:
        """校验行。"""
        if not data:
            raise EmptyDataError(
                f"未取到 {query.symbol} 的历史行情，请核对代码、日期区间与上游可用性。"
            )
        return [AkshareEquityHistoricalData.model_validate(row) for row in data]
