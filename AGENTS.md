# A-share data workflow

This repository is the AKShare source tree. When a user asks for factual
A-share market data, use the local `tools/stock_query.py` command before
answering. Do not claim that data was fetched unless the command succeeded.

## Terminal and interpreter discovery

1. Run `git rev-parse --show-toplevel` to locate the project root. Do not rely
   on the terminal's current directory.
2. Prefer the project interpreter at `<root>/.venv/bin/python` on macOS/Linux,
   or `<root>/.venv/Scripts/python.exe` on Windows. If neither exists, locate a
   Python 3.11+ interpreter. Never use Python 3.9 or older for this project.
3. If no compatible environment exists, report the exact setup command rather
   than silently substituting a system Python.

## Query commands

Run the script with its absolute path after finding `<root>`.

```sh
# Historical daily prices (last 30 calendar days by default)
<python> <root>/tools/stock_query.py history --symbol 000001

# Latest available quote
<python> <root>/tools/stock_query.py quote --symbol 000001

# Basic company information
<python> <root>/tools/stock_query.py info --symbol 000001
```

For historical requests, convert dates to `YYYYMMDD`; use `--period weekly` or
`monthly` when asked, and use `--adjust qfq` for forward-adjusted prices unless
the user specifies otherwise. Use `--csv <path>` only when a file is requested.

The script accesses third-party data sources and is for research only. State the
retrieval time and source limitations; do not give trading instructions.
