"""CLI entry point for agentify-example-tau-bench."""

import asyncio

import typer
from agentify_tau_bench.green_agent import start_green_agent
from agentify_tau_bench.launcher import launch_evaluation
from agentify_tau_bench.white_agent import start_white_agent
from pydantic_settings import BaseSettings


class TaubenchSettings(BaseSettings):
    role: str = "unspecified"
    host: str = "127.0.0.1"
    agent_port: int = 9000


app = typer.Typer(help="Agentified Tau-Bench - Standardized agent assessment framework")


@app.command()
def green(
    host: str = typer.Option("0.0.0.0", "--host", help="Host to bind to"),
    port: int = typer.Option(8080, "--port", help="Port to bind to"),
    card_url: str = typer.Option(None, "--card-url", help="Public URL for agent card"),
):
    """Start the green agent (assessment manager)."""
    if card_url:
        import os
        os.environ["AGENT_URL"] = card_url
    start_green_agent(host=host, port=port)


@app.command()
def white(
    host: str = typer.Option("0.0.0.0", "--host", help="Host to bind to"),
    port: int = typer.Option(9002, "--port", help="Port to bind to"),
    card_url: str = typer.Option(None, "--card-url", help="Public URL for agent card"),
):
    """Start the white agent (target being tested)."""
    if card_url:
        import os
        os.environ["AGENT_URL"] = card_url
    start_white_agent(host=host, port=port)


@app.command()
def launch():
    """Launch the complete evaluation workflow."""
    asyncio.run(launch_evaluation())


@app.command()
def run():
    settings = TaubenchSettings()
    if settings.role == "green":
        start_green_agent(host=settings.host, port=settings.agent_port)
    elif settings.role == "white":
        start_white_agent(host=settings.host, port=settings.agent_port)
    else:
        raise ValueError(f"Unknown role: {settings.role}")
    return


if __name__ == "__main__":
    app()
