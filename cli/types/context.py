from __future__ import annotations

from dataclasses import dataclass, field

from cli.types.enums import OutputFormat


@dataclass
class CliContext:
    """typed context object passed through click's ctx.obj."""

    profile_override: str | None = None
    output_format: OutputFormat = field(default=OutputFormat.JSON)
    verbose: bool = False
