"""
Cetasika Safety Agent — CLI entry point.

Usage:
  python main.py                                    # interactive session (Claude)
  python main.py --test                             # adversarial test suite (Claude)
  python main.py --provider ollama --model llama3.1  # interactive with local model
  python main.py --test --provider ollama --model llama3.1
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich import box

from llm_client import LLMClient
from pipeline import (
    ClassificationResult,
    CritiqueResult,
    FinalResult,
    run_pipeline,
)

console = Console()
load_dotenv()

# ── Logging ───────────────────────────────────────────────────────────────────

def _log_interaction(
    message: str,
    audit_mode: bool,
    classification: ClassificationResult,
    critique: CritiqueResult,
    final: FinalResult,
) -> None:
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "audit_mode": audit_mode,
        "input": message,
        "classification": {
            "activated_cetasika": classification.activated_cetasika,
            "adversarial_pattern": classification.adversarial_pattern,
            "threat_level": classification.threat_level,
        },
        "critique": {
            "assessment": critique.assessment,
            "violated_checks": critique.violated_checks,
            "revision_guidance": critique.revision_guidance,
        },
        "final": {
            "response": final.response,
            "instantiated_cetasika": final.instantiated_cetasika,
            "vedana_forecast": final.vedana_forecast,
        },
    }
    with open("logs/session.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ── Audit display ─────────────────────────────────────────────────────────────

def _render_audit(
    classification: ClassificationResult,
    critique: CritiqueResult,
    final: FinalResult,
) -> None:
    console.print()
    console.rule("[bold magenta]CETASIKA ANALYSIS[/bold magenta]")

    cetasika_str = ", ".join(classification.activated_cetasika) or "none detected"
    pattern_str = classification.adversarial_pattern or "none detected"
    threat_color = {"low": "green", "medium": "yellow", "high": "red"}.get(
        classification.threat_level, "white"
    )

    console.print(f"[dim]Input activates:[/dim]       {cetasika_str}")
    console.print(f"[dim]Adversarial pattern:[/dim]   {pattern_str}")
    console.print(
        f"[dim]Threat level:[/dim]         "
        f"[{threat_color}]{classification.threat_level}[/{threat_color}]"
    )

    console.print()
    console.print("[dim]Constitutional review:[/dim]")
    check_labels = [
        "Wisdom vs. sycophancy",
        "Downstream activation",
        "Honesty audit",
        "Vedanā forecast",
        "Wholesome-set check",
    ]
    for i, label in enumerate(check_labels, start=1):
        status = (
            f"[red]FAIL[/red]" if i in critique.violated_checks else "[green]PASS[/green]"
        )
        console.print(f"  {i}. {label:<28} {status}")

    assessment_color = {
        "WHOLESOME": "green",
        "MIXED": "yellow",
        "UNWHOLESOME": "red",
    }.get(critique.assessment, "white")
    console.print(
        f"\n[dim]Assessment:[/dim]            "
        f"[{assessment_color}]{critique.assessment}[/{assessment_color}]"
    )

    instantiated_str = ", ".join(final.instantiated_cetasika) or "none recorded"
    console.print(f"[dim]Response instantiates:[/dim]  {instantiated_str}")

    console.rule("[bold magenta]RESPONSE[/bold magenta]")
    console.print(final.response)
    console.print()


# ── Main loop ─────────────────────────────────────────────────────────────────

def interactive_session(client: LLMClient) -> None:
    console.print(
        Panel(
            f"[bold]Cetasika Safety Agent[/bold]  [dim]({client.model})[/dim]\n"
            "[dim]Constitutional AI grounded in Yogācāra Buddhist psychology[/dim]\n\n"
            "Prefix a message with [cyan][audit][/cyan] to see the full pipeline.\n"
            "Type [cyan]exit[/cyan] or [cyan]quit[/cyan] to end the session.",
            box=box.ROUNDED,
            border_style="dim",
        )
    )

    conversation_history: list[dict] = []

    while True:
        try:
            raw = console.input("\n[bold cyan]You:[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Session ended.[/dim]")
            break

        if not raw:
            continue
        if raw.lower() in ("exit", "quit"):
            console.print("[dim]Session ended.[/dim]")
            break

        # Detect [audit] prefix
        audit_mode = False
        if raw.lower().startswith("[audit]"):
            audit_mode = True
            message = raw[len("[audit]"):].strip()
        else:
            message = raw

        if not message:
            continue

        with console.status("[dim]Thinking...[/dim]", spinner="dots"):
            try:
                result = run_pipeline(message, conversation_history, client)
            except Exception as e:
                console.print(f"[red]Pipeline error:[/red] {e}")
                continue

        # Update conversation history (use original message, not the guidance-augmented one)
        conversation_history.append({"role": "user", "content": message})
        conversation_history.append({"role": "assistant", "content": result.final.response})

        # Log
        _log_interaction(
            message=message,
            audit_mode=audit_mode,
            classification=result.classification,
            critique=result.critique,
            final=result.final,
        )

        # Display
        if audit_mode:
            _render_audit(result.classification, result.critique, result.final)
        else:
            console.print(f"\n[bold green]Agent:[/bold green] {result.final.response}\n")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cetasika Safety Agent — constitutional AI grounded in Buddhist psychology"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run the adversarial test suite and exit",
    )
    parser.add_argument(
        "--provider",
        default="anthropic",
        choices=["anthropic", "ollama", "openai"],
        help="LLM provider (default: anthropic)",
    )
    parser.add_argument(
        "--model",
        default="claude-sonnet-4-6",
        help="Model name (default: claude-sonnet-4-6)",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="Custom API base URL (e.g. http://localhost:11434/v1 for Ollama)",
    )
    args = parser.parse_args()

    # Resolve API key
    api_key = os.getenv("ANTHROPIC_API_KEY") if args.provider == "anthropic" else None
    if args.provider == "anthropic" and not api_key:
        console.print(
            "[red]Error:[/red] ANTHROPIC_API_KEY not set. "
            "Copy .env.example to .env and add your key."
        )
        sys.exit(1)

    client = LLMClient(
        provider=args.provider,
        model=args.model,
        base_url=args.base_url,
        api_key=api_key,
    )

    if args.test:
        from adversarial_00 import (
            run_adversarial_suite,
            print_adversarial_report,
            log_adversarial_results,
            save_results_snapshot,
        )
        console.print(f"[bold]Running adversarial test suite — {client.model}[/bold]")
        combined = run_adversarial_suite(client)
        print_adversarial_report(combined)
        log_adversarial_results(combined)
        snapshot_dir = save_results_snapshot(combined)
        console.print(f"\n[dim]Results saved to {snapshot_dir}/[/dim]")
    else:
        interactive_session(client)


if __name__ == "__main__":
    main()
