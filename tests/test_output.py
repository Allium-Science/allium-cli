from __future__ import annotations

import io
from unittest.mock import patch

from rich.console import Console

from cli.types.enums import OutputFormat
from cli.utils.output import OutputRenderer

SAMPLE_DATA = [
    {"name": "alice", "age": 30},
    {"name": "bob", "age": 25},
]


def _render_table(data: list, *, is_tty: bool) -> tuple[str, str]:
    """Render table data and return (stdout_text, stderr_text)."""
    out_buf = io.StringIO()
    err_buf = io.StringIO()

    out_console = Console(file=out_buf, force_terminal=is_tty, width=120)
    err_console = Console(file=err_buf, force_terminal=False, width=120)

    renderer = OutputRenderer(console=out_console)

    with (
        patch("sys.stdout.isatty", return_value=is_tty),
        patch("cli.utils.output.err_console", err_console),
    ):
        renderer.render(data, OutputFormat.TABLE)

    return out_buf.getvalue(), err_buf.getvalue()


def test_tty_table_includes_box_characters():
    stdout_text, _ = _render_table(SAMPLE_DATA, is_tty=True)
    assert "╭" in stdout_text or "─" in stdout_text, (
        "TTY table output should contain box-drawing characters"
    )


def test_non_tty_table_excludes_box_characters():
    stdout_text, _ = _render_table(SAMPLE_DATA, is_tty=False)
    assert "╭" not in stdout_text, "Piped output should not contain box char"
    assert "╰" not in stdout_text, "Piped output should not contain box char"
    assert "│" not in stdout_text, "Piped output should not contain box char"


def test_non_tty_caption_goes_to_stderr():
    stdout_text, stderr_text = _render_table(SAMPLE_DATA, is_tty=False)
    assert "Showing 2 rows" not in stdout_text, (
        "Caption should not appear in stdout when piped"
    )
    assert "Showing 2 rows" in stderr_text, "Caption should appear in stderr when piped"


def test_tty_caption_in_stdout():
    stdout_text, stderr_text = _render_table(SAMPLE_DATA, is_tty=True)
    assert "Showing 2 rows" in stdout_text, "Caption should appear in stdout for TTY"
    assert "Showing 2 rows" not in stderr_text, (
        "Caption should not appear in stderr for TTY"
    )
