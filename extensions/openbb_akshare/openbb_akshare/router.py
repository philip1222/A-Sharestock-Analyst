#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026/10/3
Desc: OpenBB 路由，暴露 A 股日线与快照
"""

from openbb_core.app.model.command_context import CommandContext
from openbb_core.app.model.example import APIEx
from openbb_core.app.model.obbject import OBBject
from openbb_core.app.provider_interface import (
    ExtraParams,
    ProviderChoices,
    StandardParams,
)
from openbb_core.app.query import Query
from openbb_core.app.router import Router

router = Router(prefix="", description="AKShare China-market data.")


@router.command(
    model="AkshareEquityHistorical",
    examples=[
        APIEx(
            parameters={
                "symbol": "000001",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "provider": "akshare",
            }
        )
    ],
)
async def historical(
    cc: CommandContext,
    provider_choices: ProviderChoices,
    standard_params: StandardParams,
    extra_params: ExtraParams,
) -> OBBject:
    """A 股历史行情。东方财富 K 线失败时自动换腾讯或新浪日线。"""
    return await OBBject.from_query(Query(**locals()))


@router.command(
    model="AkshareEquityQuote",
    examples=[APIEx(parameters={"symbol": "000001", "provider": "akshare"})],
)
async def quote(
    cc: CommandContext,
    provider_choices: ProviderChoices,
    standard_params: StandardParams,
    extra_params: ExtraParams,
) -> OBBject:
    """A 股最新快照。"""
    return await OBBject.from_query(Query(**locals()))
