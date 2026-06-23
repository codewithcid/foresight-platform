"""Standalone MCP server: exposes the exact same tool registry
(backend/tools.py) that powers the in-app Supervisor agent, but over the
Model Context Protocol so an external MCP client -- Claude Desktop, another
agent framework, anything that speaks MCP -- can call into Foresight's
causal model, trend forecaster, CRM drafter, explainer, and AI Stylist
directly.

This builds its OWN in-process Foresight instance (synthetic population,
trained causal model, etc.) independent of the live web demo, so it can run
standalone. Run it with:

    python mcp_server.py

Then point an MCP client at it (stdio transport). Example Claude Desktop
config entry:

    "foresight": { "command": "python", "args": ["/path/to/backend/mcp_server.py"] }
"""
from __future__ import annotations

import pandas as pd
from mcp.server.fastmcp import FastMCP

import datagen
import llm
from agent import AgentLoop
from bandit import ThompsonBandit
from causal import UpliftEngine
from context import ShopperRegistry, TrendAnalyzer
from ledger import Ledger
from memory import MemoryStore
from signals import SignalRegistry
from tools import build_tools


def _build_ctx() -> dict:
    customers = datagen.generate_customers()
    demo_personas = datagen.make_demo_personas()
    all_customers = pd.concat([customers, demo_personas], ignore_index=True)

    engine = UpliftEngine(customers)
    engine.train()

    memory = MemoryStore()
    ledger = Ledger()
    bandit = ThompsonBandit()
    signal_registry = SignalRegistry()
    shopper_registry = ShopperRegistry()
    trend_analyzer = TrendAnalyzer(customers, shopper_registry)
    agent_loop = AgentLoop(engine, memory, ledger, all_customers, bandit=bandit, signal_registry=signal_registry)

    return {
        "customers": customers, "all_customers": all_customers, "engine": engine, "memory": memory,
        "ledger": ledger, "agent_loop": agent_loop, "shopper_registry": shopper_registry,
        "trend_analyzer": trend_analyzer, "signal_registry": signal_registry, "bandit": bandit,
    }


def main() -> None:
    print(f"[foresight-mcp] building model... llm={'groq' if llm.has_key() else 'template-fallback'}")
    ctx = _build_ctx()
    tools = build_tools(ctx)

    app = FastMCP(name="foresight", instructions=(
        "Foresight's agent tools for an Indian fashion e-commerce platform: causal uplift "
        "prediction, trend forecasting, occasion-aware CRM campaign drafting, decision "
        "explainability, customer context summarization, AI-stylist outfit composition, and "
        "contextual-bandit status."
    ))
    for tool in tools:
        app.add_tool(tool.fn, name=tool.name, description=tool.description)

    print(f"[foresight-mcp] {len(tools)} tools registered, serving over stdio")
    app.run()


if __name__ == "__main__":
    main()
