from __future__ import annotations

import sys

import questionary
import rich_click as click
from privy import PrivyAPI
from questionary import Choice, Separator

from cli.constants.config import EXIT_AUTH
from cli.constants.ui import ACCENT, PROMPT_STYLE
from cli.types.enums import AuthMethod, TargetNetwork, TempoChainId
from cli.types.labels import method_label
from cli.types.profiles import (
    ApiKeyProfile,
    ProfileUnion,
    TempoProfile,
    X402KeyProfile,
    X402PrivyProfile,
)
from cli.utils.config import config_manager
from cli.utils.console import err_console
from cli.utils.console import out_console as console


def _ask(prompt: questionary.Question):
    """run a questionary prompt, exit on ctrl-c."""
    result = prompt.ask()
    if result is None:
        raise click.Abort()
    return result


def _prompt_api_key() -> ApiKeyProfile:
    api_key = _ask(questionary.password("API Key:", style=PROMPT_STYLE, qmark="●"))
    return ApiKeyProfile(api_key=api_key)


def _prompt_x402_key() -> X402KeyProfile:
    private_key = _ask(
        questionary.password("EVM Private Key (0x...):", style=PROMPT_STYLE, qmark="●")
    )
    network = _ask(
        questionary.select(
            "Network:",
            choices=[Choice(n.label, value=n) for n in TargetNetwork],
            style=PROMPT_STYLE,
            qmark="●",
            pointer="›",
            instruction="(↑↓ to select)",
        )
    )
    return X402KeyProfile(private_key=private_key, target_network=network)


def _prompt_x402_privy() -> X402PrivyProfile:
    err_console.print(
        "\n  You'll need a Privy account. "
        "Create one at [link]https://dashboard.privy.io[/link]\n"
    )
    app_id = _ask(questionary.text("Privy App ID:", style=PROMPT_STYLE, qmark="●"))
    app_secret = _ask(
        questionary.password("Privy App Secret:", style=PROMPT_STYLE, qmark="●")
    )

    try:
        privy = PrivyAPI(app_id=app_id, app_secret=app_secret)
        wallets = list(privy.wallets.list(chain_type="ethereum"))
    except Exception as exc:
        err_console.print(f"\n  [red]Failed to fetch Privy wallets: {exc}[/red]\n")
        sys.exit(EXIT_AUTH)

    if not wallets:
        err_console.print(
            "\n  [red]No EVM wallets found in this Privy app.[/red]\n"
            "  Create a wallet at [link]https://dashboard.privy.io[/link] first.\n"
        )
        sys.exit(EXIT_AUTH)

    def _wallet_label(w) -> str:
        addr = w.address
        short_addr = f"{addr[:6]}...{addr[-4:]}"
        short_id = f"{w.id[:8]}..."
        return f"{short_addr}  ({short_id})"

    if len(wallets) == 1:
        wallet_id = wallets[0].id
        err_console.print(
            f"  [dim]Wallet:[/dim] {_wallet_label(wallets[0])} (auto-selected)\n"
        )
    else:
        wallet_id = _ask(
            questionary.select(
                "Wallet:",
                choices=[Choice(_wallet_label(w), value=w.id) for w in wallets],
                style=PROMPT_STYLE,
                qmark="●",
                pointer="›",
                instruction="(↑↓ to select)",
            )
        )

    network = _ask(
        questionary.select(
            "Network:",
            choices=[Choice(n.label, value=n) for n in TargetNetwork],
            style=PROMPT_STYLE,
            qmark="●",
            pointer="›",
            instruction="(↑↓ to select)",
        )
    )
    return X402PrivyProfile(
        privy_app_id=app_id,
        privy_app_secret=app_secret,
        privy_wallet_id=wallet_id,
        target_network=network,
    )


def _prompt_tempo() -> TempoProfile:
    private_key = _ask(
        questionary.password("Tempo Private Key:", style=PROMPT_STYLE, qmark="●")
    )
    chain_id = _ask(
        questionary.select(
            "Chain:",
            choices=[Choice(c.label, value=c) for c in TempoChainId],
            style=PROMPT_STYLE,
            qmark="●",
            pointer="›",
            instruction="(↑↓ to select)",
        )
    )
    return TempoProfile(private_key=private_key, chain_id=chain_id)


_SETUP_PROMPTS = {
    "api_key": _prompt_api_key,
    "x402_key": _prompt_x402_key,
    "x402_privy": _prompt_x402_privy,
    "tempo": _prompt_tempo,
}


@click.group()
def auth() -> None:
    """manage authentication profiles for API key, x402, and Tempo access."""


_METHOD_REQUIRED: dict[str, list[str]] = {
    "api_key": ["api_key"],
    "x402_key": ["private_key", "network"],
    "x402_privy": [
        "privy_app_id",
        "privy_app_secret",
        "privy_wallet_id",
        "network",
    ],
    "tempo": ["private_key", "chain_id"],
}


def _build_profile_from_args(
    method: str,
    *,
    api_key: str | None,
    private_key: str | None,
    network: str | None,
    chain_id: str | None,
    privy_app_id: str | None,
    privy_app_secret: str | None,
    privy_wallet_id: str | None,
) -> ProfileUnion:
    """build a profile from CLI args, raising UsageError on missing fields."""
    args = {
        "api_key": api_key,
        "private_key": private_key,
        "network": network,
        "chain_id": chain_id,
        "privy_app_id": privy_app_id,
        "privy_app_secret": privy_app_secret,
        "privy_wallet_id": privy_wallet_id,
    }
    required = _METHOD_REQUIRED[method]
    missing = [k for k in required if not args.get(k)]
    if missing:
        flags = ", ".join(f"--{k.replace('_', '-')}" for k in missing)
        raise click.UsageError(f"--method {method} requires {flags}.")

    if method == "api_key":
        return ApiKeyProfile(api_key=api_key)  # type: ignore[arg-type]
    if method == "x402_key":
        try:
            net = TargetNetwork(network)
        except ValueError:
            valid = ", ".join(m.value for m in TargetNetwork)
            raise click.UsageError(
                f"Invalid --network '{network}'. Choose from: {valid}"
            )
        return X402KeyProfile(
            private_key=private_key,  # type: ignore[arg-type]
            target_network=net,
        )
    if method == "x402_privy":
        try:
            net = TargetNetwork(network)
        except ValueError:
            valid = ", ".join(m.value for m in TargetNetwork)
            raise click.UsageError(
                f"Invalid --network '{network}'. Choose from: {valid}"
            )
        return X402PrivyProfile(
            privy_app_id=privy_app_id,  # type: ignore[arg-type]
            privy_app_secret=privy_app_secret,  # type: ignore[arg-type]
            privy_wallet_id=privy_wallet_id,  # type: ignore[arg-type]
            target_network=net,
        )
    try:
        cid = TempoChainId(chain_id)
    except ValueError:
        valid = ", ".join(m.value for m in TempoChainId)
        raise click.UsageError(f"Invalid --chain-id '{chain_id}'. Choose from: {valid}")
    return TempoProfile(
        private_key=private_key,  # type: ignore[arg-type]
        chain_id=cid,
    )


@auth.command("setup")
@click.option(
    "--method",
    "method",
    type=click.Choice([m.value for m in AuthMethod]),
    default=None,
    help="Auth method (skips interactive wizard).",
)
@click.option("--name", default=None, help="Profile name.")
@click.option(
    "--no-active",
    is_flag=True,
    default=False,
    help="Don't set as active profile.",
)
@click.option("--api-key", default=None, help="API key (for api_key method).")
@click.option(
    "--private-key",
    default=None,
    help="EVM/Tempo private key (for x402_key, tempo).",
)
@click.option(
    "--network",
    default=None,
    help="Target network, e.g. eip155:8453 (for x402_key, x402_privy).",
)
@click.option(
    "--chain-id",
    default=None,
    help="Tempo chain ID, e.g. 4217 (for tempo).",
)
@click.option("--privy-app-id", default=None, help="Privy App ID (for x402_privy).")
@click.option(
    "--privy-app-secret",
    default=None,
    help="Privy App Secret (for x402_privy).",
)
@click.option(
    "--privy-wallet-id",
    default=None,
    help="Privy Wallet ID (for x402_privy).",
)
def auth_setup(
    method: str | None,
    name: str | None,
    no_active: bool,
    api_key: str | None,
    private_key: str | None,
    network: str | None,
    chain_id: str | None,
    privy_app_id: str | None,
    privy_app_secret: str | None,
    privy_wallet_id: str | None,
) -> None:
    """configure authentication (interactive or one-liner).

    run with no arguments for an interactive wizard, or pass --method
    with the required flags for non-interactive setup:

    \b
      allium auth setup
      allium auth setup --method api_key --api-key sk-...
      allium auth setup --method tempo --private-key 0x... --chain-id 4217
    """
    if method:
        profile = _build_profile_from_args(
            method,
            api_key=api_key,
            private_key=private_key,
            network=network,
            chain_id=chain_id,
            privy_app_id=privy_app_id,
            privy_app_secret=privy_app_secret,
            privy_wallet_id=privy_wallet_id,
        )
        profile_name = name or method.replace("_", "-")
        make_active = not no_active
    else:
        profile, profile_name, make_active = _interactive_setup(name)

    config_manager.add_profile(profile_name, profile, set_active=make_active)
    err_console.print(f"\n  [{ACCENT}]✓ Profile '{profile_name}' saved.[/{ACCENT}]")
    if make_active:
        err_console.print(
            f"  [{ACCENT}]✓ Active profile set to '{profile_name}'.[/{ACCENT}]"
        )
    err_console.print()


def _interactive_setup(
    name_override: str | None,
) -> tuple[ProfileUnion, str, bool]:
    """run the interactive setup wizard. returns (profile, name, active)."""
    err_console.print()
    method_key = _ask(
        questionary.select(
            "Authentication method:",
            choices=[
                Separator(""),
                Separator("  Key-based"),
                Separator(""),
                Choice(
                    "  API Key           Standard key from app.allium.so",
                    value="api_key",
                ),
                Separator(""),
                Separator("  Pay-per-call"),
                Separator(""),
                Choice(
                    "  x402 Private Key  USDC on Base (your wallet)",
                    value="x402_key",
                ),
                Choice(
                    "  x402 Privy        USDC via Privy server wallet",
                    value="x402_privy",
                ),
                Choice(
                    "  Tempo MPP         Tempo micropayment protocol",
                    value="tempo",
                ),
            ],
            style=PROMPT_STYLE,
            qmark="●",
            pointer="›",
            instruction="(↑↓ to move, enter to select)",
        )
    )

    err_console.print()
    profile = _SETUP_PROMPTS[method_key]()

    default_name = method_key.replace("_", "-")
    profile_name = name_override or _ask(
        questionary.text(
            "Profile name:",
            default=default_name,
            style=PROMPT_STYLE,
            qmark="●",
        )
    )
    make_active = _ask(
        questionary.confirm(
            "Set as active profile?",
            default=True,
            style=PROMPT_STYLE,
            qmark="●",
        )
    )
    return profile, profile_name, make_active


@auth.command("list")
def auth_list() -> None:
    """show all configured profiles with their auth method and base URL."""
    profiles = config_manager.list_profiles()
    active = config_manager.get_active_profile_name()

    if not profiles:
        err_console.print(
            "\n  No profiles configured. Run [bold]allium auth setup[/bold].\n"
        )
        return

    console.print("\n  [bold]Authentication Profiles[/bold]\n")
    for name, profile in profiles.items():
        is_active = name == active
        bullet = f"[{ACCENT}]●[/{ACCENT}]" if is_active else "[dim]○[/dim]"
        suffix = f" [{ACCENT}](active)[/{ACCENT}]" if is_active else ""
        console.print(f"  {bullet} [bold]{name}[/bold]{suffix}")
        console.print(f"    [dim]Method:[/dim]   {method_label(profile.method)}")

        if hasattr(profile, "target_network"):
            console.print(f"    [dim]Network:[/dim]  {profile.target_network.label}")
        if hasattr(profile, "chain_id"):
            console.print(f"    [dim]Chain:[/dim]    {profile.chain_id.label}")

        console.print(f"    [dim]Base URL:[/dim] {profile.base_url}")
        console.print()


@auth.command("use")
@click.argument("name")
def auth_use(name: str) -> None:
    """switch the active profile used for subsequent commands."""
    try:
        config_manager.set_active_profile(name)
        err_console.print(
            f"\n  [{ACCENT}]✓ Active profile set to '{name}'.[/{ACCENT}]\n"
        )
    except ValueError as e:
        err_console.print(f"\n  [red]{e}[/red]\n")
        sys.exit(EXIT_AUTH)


@auth.command("remove")
@click.argument("name")
def auth_remove(name: str) -> None:
    """remove a saved authentication profile."""
    try:
        config_manager.remove_profile(name)
        err_console.print(f"\n  [{ACCENT}]✓ Profile '{name}' removed.[/{ACCENT}]\n")
    except ValueError as e:
        err_console.print(f"\n  [red]{e}[/red]\n")
        sys.exit(EXIT_AUTH)
