# Competitive Intelligence Platform

Multi-agent system for automated competitor research, analysis, and report generation.

## Overview

Automates the production of competitive intelligence reports using a 5-agent pipeline with multi-LLM orchestration (Claude, GPT-4, Gemini, Grok). Back-engineered from a proven 82-page competitor analysis methodology.

## Architecture

```
CLI Input (config.json)
       |
       v
  ORCHESTRATOR (Pipeline Manager)
       |
  +----+----+----+
  v    v    v    v
RESEARCH AGENTS (1 per competitor, parallel)
       |
  +----+----+
  v         v
ANALYST    SCORING
AGENT      AGENT
  |         |
  +----+----+
       v
  OUTPUT AGENT (Report + DOCX)
```

## Quick Start

```bash
# Install
pip install -e .

# Configure
cp .env.example .env
# Edit .env with your API keys

# Initialise project
python -m src.cli init --config config/project_example.json

# Test LLM connectivity
python -m src.cli test-llm

# Run analysis (Sprint 6+)
python -m src.cli run --config config/project_example.json
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `init --config FILE` | Validate config and create output directories |
| `test-llm` | Test connectivity to all 4 LLM providers |
| `checkpoint --save/--load/--list/--clear` | Manage pipeline checkpoints |
| `run --config FILE` | Run full analysis pipeline |
| `cost` | Show cost tracking summary |
| `version` | Show version info |

## Project Structure

```
src/
  cli.py                  # Click-based CLI
  config.py               # Pydantic config models
  agents/
    base_agent.py          # Abstract base with retry/checkpoint
  llm/
    router.py              # Task-to-LLM routing
    cost_tracker.py        # Budget management
    claude_client.py       # Anthropic
    openai_client.py       # OpenAI
    gemini_client.py       # Google
    grok_client.py         # xAI
  pipeline/
    checkpoint.py          # JSON checkpoint system
  utils/
    logger.py              # Structured logging
    web_fetcher.py         # URL fetching with retry

config/
  project_example.json     # Example project config
  llm_config_example.json  # LLM routing config
  feature_template.json    # Feature matrix categories
  scoring_template.json    # 4-dimension scoring framework

prompts/
  profile_generator.md     # Competitor profile prompt
  feature_scorer.md        # Feature matrix scoring
  capability_scorer.md     # 0-10 dimension scoring
  market_landscape.md      # Market overview synthesis
  report_assembly.md       # Editorial/assembly
  kill_sheet.md            # Sales kill sheet
  battlecard.md            # One-page battlecard
  comparison_page.md       # Marketing comparison page
  index_updater.md         # Artefact index management
```

## Sprint Plan

| Sprint | Focus | Status |
|--------|-------|--------|
| S0 | Architecture | Done |
| S1 | Foundation (CLI, config, LLM clients, checkpoints) | Done |
| S2 | Research Agent (web fetching, content extraction) | Planned |
| S3 | Analyst Agent (profiles, feature matrix, market landscape) | Planned |
| S4 | Scoring Agent (dual-LLM 4-dimension assessment) | Planned |
| S5 | Output Agent (report assembly, DOCX export) | Planned |
| S6 | Orchestrator + Integration (pipeline wiring) | Planned |
| S7 | TIG Freight test run | Planned |

## LLM Routing

| Task | Primary | Secondary | Rationale |
|------|---------|-----------|-----------|
| Content extraction | Claude | - | Best structured extraction |
| Profile drafting | Claude | Grok (challenger) | Adversarial review |
| Feature matrix | Claude | Gemini (verification) | Fact-check |
| Capability scoring | Claude + GPT-4 | Grok (arbitrator) | Dual-score prevents bias |
| Claim verification | Gemini | Claude (fallback) | Fast grounding |
| Editorial/assembly | Claude | - | Long-form coherence |

## Cost Estimates

~$10-16 per full run (9 competitors). Budget cap configurable with alerts at 50%, 75%, and hard stop at 100%.

## License

Private — shinny77
