"""Project configuration loader and validator."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator


class CompetitorConfig(BaseModel):
    """A single competitor to analyse."""
    name: str
    website: str
    aliases: list[str] = Field(default_factory=list)
    notes: str = ""


class BudgetConfig(BaseModel):
    """LLM cost budget settings."""
    max_usd: float = 20.0
    alert_at_pct: list[int] = Field(default=[50, 75])
    hard_stop_pct: int = 100


class OutputConfig(BaseModel):
    """Output generation options."""
    generate_battlecards: bool = True
    generate_comparison_pages: bool = True
    generate_docx: bool = True
    brand_colors: dict[str, str] = Field(default_factory=lambda: {
        "primary": "#2A2829",
        "secondary": "#5A7DA3",
    })
    heading_font: str = "Gilda Display"
    body_font: str = "Roboto"


class ProjectConfig(BaseModel):
    """Full project configuration."""
    project_name: str
    target_company: str
    target_website: str
    industry: str
    competitors: list[CompetitorConfig]
    feature_template_path: str = "config/feature_template.json"
    scoring_template_path: str = "config/scoring_template.json"
    budget: BudgetConfig = Field(default_factory=BudgetConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    max_research_retries: int = 3
    parallel_research: bool = True

    @field_validator("competitors")
    @classmethod
    def at_least_one_competitor(cls, v: list) -> list:
        if not v:
            raise ValueError("At least one competitor is required")
        return v


class LLMConfig(BaseModel):
    """LLM provider configuration."""
    provider: str
    model: str
    api_key_env: str
    max_tokens: int = 4096
    temperature: float = 0.3


class LLMRoutingConfig(BaseModel):
    """Maps tasks to LLM providers."""
    content_extraction: LLMConfig
    profile_drafting: LLMConfig
    profile_challenger: LLMConfig
    feature_scoring: LLMConfig
    feature_verification: LLMConfig
    capability_scoring_primary: LLMConfig
    capability_scoring_secondary: LLMConfig
    capability_arbitrator: LLMConfig
    claim_verification: LLMConfig
    editorial: LLMConfig


def load_project_config(path: str | Path) -> ProjectConfig:
    """Load and validate a project config file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    with open(path) as f:
        data = json.load(f)
    return ProjectConfig(**data)


def load_llm_config(path: str | Path) -> LLMRoutingConfig:
    """Load and validate an LLM routing config file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"LLM config not found: {path}")
    with open(path) as f:
        data = json.load(f)
    return LLMRoutingConfig(**data)


def load_json(path: str | Path) -> Any:
    """Load any JSON file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    with open(path) as f:
        return json.load(f)


def resolve_api_key(env_var: str) -> str:
    """Resolve an API key from environment variable."""
    key = os.environ.get(env_var)
    if not key:
        raise EnvironmentError(f"Missing environment variable: {env_var}")
    return key
