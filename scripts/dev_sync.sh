#!/bin/sh
# 在任意机器上复现本仓库环境：安装锁定依赖、注册 OpenBB 扩展、挂上 pull 后自动同步的 hook。
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
if command -v git >/dev/null 2>&1 && git -C "$ROOT" rev-parse --show-toplevel >/dev/null 2>&1; then
    ROOT=$(git -C "$ROOT" rev-parse --show-toplevel)
fi
cd "$ROOT"

export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

if ! command -v uv >/dev/null 2>&1; then
    echo "dev_sync: 未找到 uv，请先安装 https://docs.astral.sh/uv/" >&2
    exit 1
fi

if [ -d "$ROOT/.git" ] && [ -d "$ROOT/.githooks" ]; then
    mkdir -p "$ROOT/.git/hooks"
    for hook in post-merge post-checkout; do
        src="$ROOT/.githooks/$hook"
        dst="$ROOT/.git/hooks/$hook"
        if [ -f "$src" ]; then
            cp "$src" "$dst"
            chmod +x "$dst"
        fi
    done
fi

uv sync
uv run openbb-build
