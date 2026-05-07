# AI Policy Violation Classifier

## Project Purpose

A portfolio project that classifies user-submitted content against a policy document using Claude. Given a content snippet and a policy, the classifier returns a structured JSON judgment — `allowed`, `borderline`, or `violating` — with citations to specific policy sections and a confidence score. A built-in evaluation harness measures agreement rate against human-labeled examples.

## Tech Stack

| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| LLM | Claude (claude-sonnet-4-20250514) via `anthropic` SDK |
| UI | Streamlit |
| Data validation | Pydantic |
| Config | python-dotenv |

## File Structure

```
build2-policy-classifier/
├── src/
│   ├── classifier/     # Core classification logic and prompt construction
│   ├── eval/           # Evaluation harness: runs labeled examples, reports metrics
│   └── ui/             # Streamlit app entry point and page components
├── data/
│   ├── policies/       # Policy documents (e.g. Reddit Content Policy text)
│   └── examples/       # Labeled eval examples (JSON/JSONL)
├── tests/              # Unit and integration tests
├── .env.example        # Required environment variables (no real values)
├── requirements.txt
└── CLAUDE.md
```

## Key Design Constraints

- **Structured output only.** The classifier must return a Pydantic-validated model every call; free-form strings are not acceptable outputs from the core classifier module.
- **Citations required.** Every judgment must reference at least one specific policy section by name/number. Judgments without citations are invalid.
- **Confidence score.** Float in [0.0, 1.0]; must accompany every judgment.
- **No real secrets committed.** API keys live in `.env` (gitignored). Use `.env.example` as the template.
- **Model pinned.** Use `claude-sonnet-4-20250514` explicitly; do not use alias strings like `claude-sonnet-4-5`.
- **Prompt caching.** The policy document is long and static per session — use Anthropic prompt caching (cache-control breakpoints) on the policy content to reduce latency and cost.
- **Eval harness is separate from UI.** The eval script (`src/eval/`) runs headlessly and writes results to `results/`; it does not import Streamlit.
- **20-30 labeled examples minimum** for the eval set, covering all three verdict categories.

## Environment Variables

See `.env.example`. The only required variable is `ANTHROPIC_API_KEY`.
