# Sprint 2: Research Agent

## Goal

Build the Research Agent — the data collection workhorse that systematically gathers competitive intelligence across 10 source categories for each competitor, producing structured claims with source citations.

## Repo

`shinny77/competitor_analysis` — all Sprint 1 foundation code is in place.

## What Exists (Sprint 1)

```
src/
  cli.py                    # Click CLI (init, test-llm, checkpoint, run, cost)
  config.py                 # Pydantic models: ProjectConfig, CompetitorConfig, LLMRoutingConfig
  __main__.py               # python -m src entrypoint
  agents/
    base_agent.py            # Abstract base with run()/execute(), checkpoint-aware retry
  llm/
    router.py                # LLMRouter — task-to-provider dispatch
    cost_tracker.py          # CostTracker with budget alerts
    base_client.py           # BaseLLMClient / LLMResponse
    claude_client.py         # Anthropic Claude
    openai_client.py         # OpenAI GPT-4o
    gemini_client.py         # Google Gemini
    grok_client.py           # xAI Grok
  pipeline/
    checkpoint.py            # CheckpointManager — save/load/list JSON checkpoints
  utils/
    logger.py                # get_logger() + PipelineLogger
    web_fetcher.py           # WebFetcher — URL fetch with retry, HTML→text extraction

config/
  project_example.json       # TIG Freight project with 9 competitors
  llm_config_example.json    # Multi-LLM routing table
  feature_template.json      # 26 features across 5 categories
  scoring_template.json      # 4-dimension scoring framework

prompts/
  profile_generator.md       # (used in Sprint 3)
  feature_scorer.md          # (used in Sprint 3)
  capability_scorer.md       # (used in Sprint 4)
  market_landscape.md        # (used in Sprint 3)
  report_assembly.md         # (used in Sprint 5)
  kill_sheet.md              # (used in Sprint 5)
  battlecard.md              # (used in Sprint 5)
  comparison_page.md         # (used in Sprint 5)
  index_updater.md           # (used in Sprint 5)
```

### Key interfaces to use

```python
# BaseAgent — extend this
from src.agents.base_agent import BaseAgent
# Override: agent_name (str), execute(inputs) -> dict

# LLM calls — use the router
self.router.call("content_extraction", prompt, system="...")          # free text
self.router.call_structured("content_extraction", prompt, schema={})  # JSON output

# Web fetching
from src.utils.web_fetcher import WebFetcher
fetcher = WebFetcher()
result = fetcher.fetch(url)   # -> {url, status, html, text, title, error}

# Checkpoints (handled by BaseAgent.run() automatically)
# Just implement execute() and return your dict — checkpoint saving is automatic

# Logging
self.logger.event("research", "fetch_website", "efmlogistics.com.au")
self.logger.error("research", "fetch_failed", "timeout on page X")
```

---

## Files to Create

```
src/
  agents/
    research_agent.py        # Core Research Agent (extends BaseAgent)
  research/
    __init__.py
    source_fetcher.py        # Orchestrates fetching across 10 source categories
    content_extractor.py     # LLM-powered extraction: raw web content → structured claims
    search_client.py         # Web search integration (Google/Serper/SerpAPI)
    models.py                # Pydantic models: Source, Claim, ResearchResult

prompts/
    content_extraction.md    # System prompt for extracting claims from web content
    claim_structuring.md     # System prompt for structuring raw claims

config/
    source_config.json       # Source taxonomy config (priority, URL patterns, selectors)
```

Estimated: ~700 lines across these files.

---

## Source Taxonomy (10 Categories)

The Research Agent must systematically hit each source type per competitor. Sources are prioritised — 1-4 provide ~80% of useful data.

| Priority | Source Category | Search Strategy |
|----------|----------------|-----------------|
| 1 | Company website (About, Products, Tech, Pricing, Careers, Blog) | Direct URL fetch + crawl subpages |
| 2 | Company LinkedIn page + posts | Search: `"{company}" site:linkedin.com/company` |
| 3 | PE/M&A announcements (law firms, PE sites) | Search: `"{company}" acquisition OR "private equity" OR funding` |
| 4 | Parent company / group sites | Extract from company website, then fetch |
| 5 | Software directories (G2, GetApp, SourceForge, Capterra) | Search: `"{company}" site:g2.com OR site:getapp.com OR site:capterra.com` |
| 6 | Industry publications | Search: `"{company}" site:mhdsupplychain.com.au OR site:freightwaves.com` |
| 7 | Revenue estimators (Growjo, Tracxn, SimilarWeb) | Search: `"{company}" site:growjo.com OR site:tracxn.com` |
| 8 | Google Ads Transparency Centre | Fetch: `https://adstransparency.google.com/?domain={domain}` |
| 9 | News (Google News) | Search: `"{company}" freight OR logistics` (time-limited) |
| 10 | Social/forums (Reddit, Twitter/X) | Search: `"{company}" site:reddit.com OR site:twitter.com` |

---

## Data Models

### Source

```python
class Source(BaseModel):
    source_id: str              # "SRC001"
    url: str
    source_type: str            # One of the 10 categories
    accessed_date: str          # ISO date
    raw_content_summary: str    # First ~500 chars or LLM summary
    status: str                 # "fetched" | "failed" | "blocked" | "empty"
    http_status: int | None
```

### Claim

```python
class Claim(BaseModel):
    claim_id: str               # "CLM001"
    text: str                   # The factual claim
    category: str               # "scale" | "technology" | "ownership" | "gtm" | "financial" | "ai_ml" | "marketing" | "service_model" | "personnel" | "other"
    confidence: str             # "verified_on_source" | "estimated" | "inferred" | "conflicting"
    source_ids: list[str]       # Which sources support this claim
    contradicted_by: list[str]  # Source IDs that contradict (if any)
```

### ResearchResult (output per competitor)

```python
class ResearchResult(BaseModel):
    competitor_name: str
    competitor_website: str
    research_timestamp: str
    sources: list[Source]
    claims: list[Claim]
    source_summary: dict        # Count per source_type: {"company_website": 3, "linkedin": 1, ...}
    coverage_gaps: list[str]    # Source types that yielded no data
    total_claims: int
    llm_calls: int
    cost_usd: float
```

---

## Research Agent Flow

```
For each competitor:
  1. FETCH phase (source_fetcher.py)
     - Fetch company website (homepage + key subpages)
     - Run web searches for sources 2-10
     - Fetch top results for each search
     - Record all Sources with status

  2. EXTRACT phase (content_extractor.py)
     - For each successfully fetched source:
       - Send raw text + system prompt to Claude (content_extraction task)
       - LLM extracts structured claims with categories
       - Assign claim IDs and link to source IDs

  3. DEDUPLICATE phase
     - Merge duplicate claims across sources
     - Flag contradictions (same topic, different facts)
     - Link supporting sources to each claim

  4. OUTPUT
     - Save ResearchResult to research/{competitor_slug}/raw_research.json
     - Checkpoint automatically via BaseAgent
```

---

## Content Extraction Prompt

Create `prompts/content_extraction.md`:

```
You are extracting competitive intelligence claims from a web page.

Input: Raw text content from a web page about a company.

For each factual claim you find, extract:
- claim_text: The specific factual statement
- category: One of [scale, technology, ownership, gtm, financial, ai_ml, marketing, service_model, personnel, other]
- confidence: "verified_on_source" (directly stated) or "inferred" (implied/derived)

Focus on:
- Company size (employees, revenue, shipments, customers)
- Technology (platform name, features, integrations, AI/ML)
- Ownership (PE backing, parent company, acquisitions)
- Go-to-market (service model, pricing, ICP)
- Leadership (key people, roles)

Respond as JSON array of claims. Ignore boilerplate, navigation, and generic marketing fluff.
```

---

## Web Search Integration

The Research Agent needs web search to find sources 2-10. Options (pick one and implement):

### Option A: SerpAPI (recommended)
```
SERPAPI_API_KEY env var
GET https://serpapi.com/search?q={query}&api_key={key}&num=5
```

### Option B: Serper.dev
```
SERPER_API_KEY env var
POST https://google.serper.dev/search
{"q": "{query}", "num": 5}
```

### Option C: Direct Google (fragile, rate-limited)
Not recommended but functional as fallback.

Add the chosen search client config to `config/llm_config_example.json` or a new `config/search_config.json`.

---

## CLI Updates

Add to `src/cli.py`:

```python
@cli.command()
@click.option("--config", "-c", required=True)
@click.option("--competitor", help="Run for single competitor (name)")
@click.option("--dry-run", is_flag=True, help="Show what would be fetched without fetching")
def research(config, competitor, dry_run):
    """Run the research phase for all or one competitor."""
```

---

## Acceptance Criteria

1. `python -m src.cli research --config config/project_example.json --competitor "EFM Logistics"` runs the full 10-source pipeline for one competitor
2. Output saved to `research/efm_logistics/raw_research.json` matching the ResearchResult schema
3. Each claim has a source citation (source_id linking to a Source entry)
4. Sources that fail (404, timeout, blocked) are recorded with status, not silently dropped
5. Coverage gaps are identified (which source categories yielded nothing)
6. Checkpoint saved after completion — rerunning skips completed competitors
7. Cost tracked for all LLM calls during extraction
8. `--dry-run` shows planned fetches without executing
9. `--competitor` flag works for single-competitor runs (useful for debugging)
10. Handles rate limits gracefully (backoff on 429s)

---

## Risks & Notes

- **Web search API cost**: SerpAPI is ~$0.01/search. Budget ~50 searches per competitor = $0.50/competitor, $4.50 for 9 competitors.
- **Website blocking**: Some sites block automated fetching. WebFetcher already has User-Agent spoofing but may need additional handling (JS-rendered pages won't work with requests alone).
- **Content length**: Company websites can be large. Truncate to ~4000 tokens before sending to LLM for extraction.
- **LinkedIn**: Requires authentication for most data. Search results may suffice; direct scraping is unreliable.
- **Parallelism**: Research agents for different competitors can run in parallel (Sprint 6 orchestrator handles this). For Sprint 2, sequential is fine.

---

## Sprint 2 Definition of Done

- [ ] `src/agents/research_agent.py` extends BaseAgent
- [ ] `src/research/source_fetcher.py` fetches across 10 source categories
- [ ] `src/research/content_extractor.py` uses LLM to extract structured claims
- [ ] `src/research/search_client.py` integrates web search API
- [ ] `src/research/models.py` defines Source, Claim, ResearchResult
- [ ] `prompts/content_extraction.md` and `prompts/claim_structuring.md` created
- [ ] CLI `research` command added
- [ ] Single-competitor test run produces valid `raw_research.json`
- [ ] All files committed and pushed to `shinny77/competitor_analysis`
