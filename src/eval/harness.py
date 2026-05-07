"""Eval harness: runs labeled examples through the classifier and measures agreement."""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from src.classifier import classify, ClassificationError

_EVAL_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "examples" / "eval_set.json"
)


@dataclass
class ExampleResult:
    id: int
    content: str
    human_label: str
    model_verdict: str
    agreement: bool
    confidence_score: float
    notes: str
    error: str | None = None


@dataclass
class CategoryStats:
    count: int  # number of agreements
    total: int  # number of examples with this label

    @property
    def rate(self) -> float:
        return self.count / self.total if self.total else 0.0


@dataclass
class EvalResult:
    agreements: int
    total: int
    per_category: dict[str, CategoryStats]
    examples: list[ExampleResult] = field(default_factory=list)

    @property
    def overall_agreement_rate(self) -> float:
        return self.agreements / self.total if self.total else 0.0


def run_eval(
    policy_text: str,
    on_progress: Callable[[int, int], None] | None = None,
) -> EvalResult:
    """Classify every example in the eval set and return aggregate results.

    Args:
        policy_text: Full policy document to classify against.
        on_progress: Optional callback(current, total) called after each example.
    """
    examples_data: list[dict] = json.loads(_EVAL_PATH.read_text(encoding="utf-8"))
    total = len(examples_data)

    category_tallies: dict[str, list[int]] = {
        "allowed":    [0, 0],
        "borderline": [0, 0],
        "violating":  [0, 0],
    }
    results: list[ExampleResult] = []
    total_agreements = 0

    for i, ex in enumerate(examples_data):
        human_label: str = ex["human_label"]

        if human_label in category_tallies:
            category_tallies[human_label][1] += 1

        try:
            clf = classify(ex["content"], policy_text)
            model_verdict = clf.verdict
            confidence = clf.confidence_score
            error = None
        except ClassificationError as e:
            model_verdict = "error"
            confidence = 0.0
            error = str(e)

        agreement = model_verdict == human_label
        if agreement:
            total_agreements += 1
            if human_label in category_tallies:
                category_tallies[human_label][0] += 1

        results.append(
            ExampleResult(
                id=ex["id"],
                content=ex["content"],
                human_label=human_label,
                model_verdict=model_verdict,
                agreement=agreement,
                confidence_score=confidence,
                notes=ex.get("notes", ""),
                error=error,
            )
        )

        if on_progress is not None:
            on_progress(i + 1, total)

    per_category = {
        label: CategoryStats(count=tallies[0], total=tallies[1])
        for label, tallies in category_tallies.items()
    }

    return EvalResult(
        agreements=total_agreements,
        total=total,
        per_category=per_category,
        examples=results,
    )
