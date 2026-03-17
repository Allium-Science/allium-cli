#!/usr/bin/env bash

uv run ruff check --fix .
uv run ruff format .
