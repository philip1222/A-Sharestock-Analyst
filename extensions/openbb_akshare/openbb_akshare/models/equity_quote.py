#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026/10/3
Desc: A 股快照 Fetcher
"""

from typing import Any

from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.equity_quote import (
    EquityQuoteData,
    EquityQuoteQueryParams,
)
from openbb_core.provider.utils.errors import EmptyDataError
from pydantic import Field

from openbb_akshare.sources import fetch_quote_rows
from openbb_akshare.symbols import bare_symbol


class AkshareEquityQuoteQueryParams(EquityQuoteQueryParams):
    """A 股快照查询。"""


class AkshareEquityQuoteData(EquityQuoteData):
    """A 股快照一行。"""

    source: str | None = Field(
        default=None, description="实际命中的数据源：eastmoney / sina。"
    )
    amount: float | None = Field(default=None, description="成交额，单位元。")


class AkshareEquityQuoteFetcher(
    Fetcher[AkshareEquityQuoteQueryParams, list[AkshareEquityQuoteData]]
):
    """A 股快照。"""

    require_credentials = False

    @staticmethod
    def transform_query(params: dict[str, Any]) -> AkshareEquityQuoteQueryParams:
        """校验入参。"""
        query = AkshareEquityQuoteQueryParams(**params)
        bare_symbol(query.symbol)
        return query

    @staticmethod
    def extract_data(
        query: AkshareEquityQuoteQueryParams,
        credentials: dict[str, str] | None,
        **kwargs: Any,
    ) -> list[dict]:
        """取全市场快照再按代码过滤。"""
        return fetch_quote_rows(symbol=query.symbol)

    @staticmethod
    def transform_data(
        query: AkshareEquityQuoteQueryParams,
        data: list[dict],
        **kwargs: Any,
    ) -> list[AkshareEquityQuoteData]:
        """校验行。"""
        if not data:
            raise EmptyDataError(
                f"未取到 {query.symbol} 的快照，请核对代码与上游可用性。"
            )
        return [AkshareEquityQuoteData.model_validate(row) for row in data]
