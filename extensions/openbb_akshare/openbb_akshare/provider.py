#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026/10/3
Desc: OpenBB Provider 实例，仅在安装了 openbb-core 时加载
"""

from openbb_core.provider.abstract.provider import Provider

from openbb_akshare.models.equity_historical import AkshareEquityHistoricalFetcher
from openbb_akshare.models.equity_quote import AkshareEquityQuoteFetcher

akshare_provider = Provider(
    name="akshare",
    description="China A-share data via the local AKShare interfaces.",
    website="https://akshare.akfamily.xyz/",
    fetcher_dict={
        "AkshareEquityHistorical": AkshareEquityHistoricalFetcher,
        "AkshareEquityQuote": AkshareEquityQuoteFetcher,
    },
)
