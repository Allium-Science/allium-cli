#!/bin/sh
set -eu

if [ "$(git rev-parse --abbrev-ref HEAD)" != "main" ]; then
    echo "error: must be on main branch" >&2
    exit 1
fi

if [ -n "$(git status --porcelain)" ]; then
    echo "error: working tree is dirty" >&2
    exit 1
fi

git pull origin main --ff-only

cz bump

git push origin main --tags
