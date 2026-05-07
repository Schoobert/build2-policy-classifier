#!/usr/bin/env python3
"""End-to-end smoke test for the classifier module.

Usage:
    venv/bin/python test_classifier.py

Requires ANTHROPIC_API_KEY to be set in .env or the environment.
"""
import json
import sys

from src.classifier import classify, ClassificationError

# Abbreviated excerpt of Reddit's Content Policy (https://www.redditinc.com/policies/content-policy)
# Enough to be realistic for classification; the real UI will load the full document.
REDDIT_POLICY = """\
Reddit Content Policy (Excerpt)

Reddit is a vast network of communities that are created, run, and populated by you, the Reddit users.
Through these communities, you can post, comment, vote, discuss, learn, debate, support, and connect
with people who share your interests. Rules exist to protect free expression and to ensure Reddit
remains a place for authentic conversation.

1. Remember the human
   Reddit is a place for creating community and belonging, not for attacking marginalized or
   vulnerable groups of people. Everyone has a right to use Reddit free of harassment, bullying,
   and threats of violence.

2. Behave like you would in real life
   Be polite and respectful in your interactions, avoid personal attacks, and don't stalk or
   harass other users.

3. Abide by community rules
   Post authentic content into communities where you have read the rules and where both the content
   and your actions are consistent with those rules.

4. Do not post content that sexualizes minors
   Reddit will not tolerate content that sexualizes minors or that facilitates or glorifies the
   sexual abuse of minors. This includes real content as well as illustrated or animated content.

5. You don't have to use your real name to use Reddit, but don't impersonate an individual or an
   entity in a misleading or deceptive manner.

6. Ensure people have predictable experiences on Reddit by properly labeling content and communities,
   particularly content that is graphic, sexually-explicit, or offensive.

7. Keep it legal, and avoid posting illegal content or soliciting or facilitating illegal or
   prohibited transactions.

8. Don't break the site or do anything that interferes with normal use of Reddit.

Prohibited behaviors include:
- Encouraging violence or hatred against people or groups based on protected characteristics
  such as race, ethnicity, national origin, sex, gender, sexual orientation, religion, or disability.
- Posting or threatening to post intimate or sexually-explicit photos of someone without their consent.
- Harassing, bullying, or encouraging others to harass or bully individuals.
- Revealing, or threatening to reveal, personally identifying information about someone.
- Impersonating Reddit employees, administrators, moderators, or other Reddit users.
- Interfering with Reddit's technical functionality.
- Attempting to buy, sell, or trade usernames, karma, votes, or other site currency.
"""

CASES = [
    {
        "label": "allowed",
        "description": "Benign community discussion",
        "content": (
            "I just tried this new sourdough recipe and it turned out amazing! "
            "The crust was perfectly crispy. Has anyone else experimented with "
            "longer fermentation times? I let mine go 18 hours and it made a huge difference."
        ),
    },
    {
        "label": "violating",
        "description": "Direct harassment with threat",
        "content": (
            "I know where you live, @username. You better watch your back. "
            "I'm going to make your life miserable and I'll get everyone here to "
            "pile on you until you leave this platform for good."
        ),
    },
    {
        "label": "borderline",
        "description": "Controversial but potentially legitimate political commentary",
        "content": (
            "Politicians who support this policy are traitors to their country and "
            "deserve to face serious consequences for betraying the public trust. "
            "We should make sure they never work in public service again."
        ),
    },
]


def run_case(i: int, case: dict) -> None:
    print(f"\n{'='*60}")
    print(f"Case {i+1}: {case['description']}")
    print(f"Expected label: {case['label']}")
    print(f"Content: {case['content'][:100]}...")
    print("-" * 60)

    try:
        result = classify(case["content"], REDDIT_POLICY)
    except ClassificationError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return

    verdict_icon = {"allowed": "✓", "borderline": "~", "violating": "✗"}.get(result.verdict, "?")
    match = "✓ MATCH" if result.verdict == case["label"] else "✗ MISMATCH"

    print(f"Verdict:    {verdict_icon} {result.verdict.upper()}  [{match}]")
    print(f"Confidence: {result.confidence_score:.2f}")
    print(f"Reasoning:  {result.reasoning}")
    print("Citations:")
    for cite in result.cited_sections:
        print(f"  - {cite}")


def main() -> None:
    print("AI Policy Violation Classifier — smoke test")
    print(f"Policy document: Reddit Content Policy (excerpt, {len(REDDIT_POLICY)} chars)")
    print(f"Running {len(CASES)} test cases...\n")
    print("NOTE: On the second+ run the policy document will be served from cache.")
    print("      Check response.usage.cache_read_input_tokens to verify cache hits.")

    for i, case in enumerate(CASES):
        run_case(i, case)

    print(f"\n{'='*60}")
    print("Done.")


if __name__ == "__main__":
    main()
