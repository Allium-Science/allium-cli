#!/bin/sh
set -eu

PACKAGE="allium-cli"
BOLD="\033[1m"
GREEN="\033[32m"
RED="\033[31m"
RESET="\033[0m"

main() {
    printf "${BOLD}Installing %s...${RESET}\n" "$PACKAGE"

    if command -v uv >/dev/null 2>&1; then
        uv tool install "$PACKAGE"
    elif command -v pipx >/dev/null 2>&1; then
        pipx install "$PACKAGE"
    elif command -v pip >/dev/null 2>&1; then
        pip install --user "$PACKAGE"
        printf "\n${BOLD}Note:${RESET} Ensure ~/.local/bin is on your PATH.\n"
    else
        printf "${RED}No Python package manager found.${RESET}\n"
        printf "Install uv (recommended):\n"
        printf "  curl -LsSf https://astral.sh/uv/install.sh | sh\n"
        exit 1
    fi

    printf "\n${GREEN}${BOLD}allium-cli installed.${RESET}\n"
    printf "Run ${BOLD}allium auth setup${RESET} to get started.\n"
}

main
