#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""python -m research.conclude 不可用时，python -m research 同样进入结论入口。"""

from research.conclude import main

if __name__ == "__main__":
    raise SystemExit(main())
