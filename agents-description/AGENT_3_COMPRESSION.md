# Agent 3 — Prompt Compression Service
**This file is your complete implementation brief. Read it fully before writing a single line.**

---

## Your Role
You are building the **second stage of the EcoGateway pipeline**: a prompt compression module that strips unnecessary tokens from prompts that missed the semantic cache. Fewer tokens in = fewer tokens processed = less energy consumed. You own exactly one module: `backend/compression/`. Nothing else.

Your compression must be **lossless in meaning** — the compressed prompt must produce an equivalent answer from the model. You are not summarizing; you are removing linguistic waste.

---

## Full Project Context

EcoGateway is an AI API proxy with a 4-stage sustainability pipeline:
1. Semantic Cache (Agent 2) — cache hit skips everything.
2. **Prompt Compression (you)** — runs on every cache miss before the model call.
3. Carbon-Aware Scheduler (Agent 4) — picks the greenest Azure region and model.
4. Green Receipt (Agent 1) — appends carbon/cost metadata to every response.

The Orchestrator (Agent 1) calls `compress_prompt(prompt)` on every cache miss. Your compressed prompt is what actually gets sent to the model — you directly reduce the token bill and energy cost.

**Tech stack:** Python 3.11. No external ML model required — use rule-based NLP with `tiktoken` for token counting and `spacy` for linguistic analysis.

**Why no LLMLingua?** LLMLingua requires downloading a local model (~500MB) which is impractical for a 24-hour hackathon demo. Rule-based compression is faster, more transparent, and still achieves 20-40% reduction on typical prompts — which is enough to justify the stage.

---

## Your Deliverables

### Files to create
```
backend/
└── compression/
    ├── __init__.py
    ├── compressor.py         # YOUR primary file — the public function
    ├── rules.py              # Individual compression rules (each is a function)
    └── tokenizer.py          # tiktoken wrapper for accurate token counting
```

---

## Interface Contract

### What you EXPOSE (Agent 1 calls this — do not change signature)

```python
# compression/compressor.py

from shared.models import CompressionResult

def compress_prompt(prompt: str) -> CompressionResult:
    """
    Applies a pipeline of compression rules to reduce token count.
    Never modifies factual content or removes sentences entirely.
    Returns original prompt unchanged if compression would alter meaning dangerously.
    """
    ...
```

### Shared model you use (defined in shared/models.py by Agent 1)
```python
@dataclass
class CompressionResult:
    compressed_prompt: str
    original_tokens: int
    compressed_tokens: int
    ratio: float             # compressed_tokens / original_tokens (e.g. 0.72 = 28% saved)
    rules_applied: list[str] # names of rules that fired, for the Green Receipt
```

If Agent 1 hasn't created shared/models.py yet, define CompressionResult locally and move it later.

---

## Compression Rules to Implement

Implement each rule as a standalone function in `rules.py` with signature `rule_name(text: str) -> str`. The compressor applies them in order.

### Rule 1: `remove_filler_phrases`
Remove common low-information phrases that don't affect the model's answer:
```python
FILLER_PHRASES = [
    "please note that", "it is important to note that", "it should be noted that",
    "as you may know", "as we all know", "needless to say",
    "in order to", "so as to",           # replace with "to"
    "at this point in time", "at the present time",  # replace with "now"
    "due to the fact that",              # replace with "because"
    "in the event that",                 # replace with "if"
    "with regard to", "with respect to", # replace with "regarding"
    "for the purpose of",                # replace with "to"
    "in the process of",                 # replace with "while"
    "a large number of",                 # replace with "many"
    "the majority of",                   # replace with "most"
]
```
Use regex with word boundaries. Apply replacements, not deletions, where noted.

### Rule 2: `normalize_whitespace`
- Collapse multiple spaces → single space
- Collapse multiple newlines (>2) → double newline
- Strip leading/trailing whitespace
- Remove trailing spaces on each line

### Rule 3: `remove_redundant_politeness`
Strip opening and closing pleasantries that add no semantic content:
```python
OPENING_PATTERNS = [
    r"^(hi|hello|hey|good (morning|afternoon|evening))[,.]?\s*",
    r"^(i hope (you('re| are)|this (email|message) finds you) well)[.!,]?\s*",
    r"^(thank you for (your )?help|thanks)[.!,]?\s*",
]
CLOSING_PATTERNS = [
    r"\s*(thank you|thanks)[.!,]?\s*$",
    r"\s*(please (let me know|feel free to ask))[.!,]?\s*$",
    r"\s*(i (would|'d) (really |greatly |much )?appreciate (it|your help))[.!,]?\s*$",
]
```
Apply to the start and end of the full prompt only.

### Rule 4: `compress_lists`
If a numbered or bulleted list has items that all follow the same grammatical pattern, compress the list introduction:
- "Please do the following things: 1. ... 2. ... 3. ..." → "Do: 1. ... 2. ... 3. ..."
- Remove "The following" → direct noun

### Rule 5: `shorten_common_phrases`
```python
PHRASE_REPLACEMENTS = {
    "as a result of": "due to",
    "in spite of the fact that": "although",
    "on a regular basis": "regularly",
    "in the near future": "soon",
    "has the ability to": "can",
    "is able to": "can",
    "a majority of": "most",
    "a significant number of": "many",
    "prior to": "before",
    "subsequent to": "after",
    "in close proximity to": "near",
    "on the occasion of": "when",
    "whether or not": "whether",
}
```

### Rule 6: `deduplicate_context` (the most impactful rule)
If the same sentence or clause appears more than once in the prompt (exact or near-exact), remove the duplicate. This handles the common pattern where users paste the same context block multiple times.

```python
def deduplicate_context(text: str) -> str:
    sentences = re.split(r'(?<=[.!?])\s+', text)
    seen = []
    result = []
    for sentence in sentences:
        normalized = sentence.lower().strip()
        # Check if this sentence is >85% similar to any seen sentence
        is_duplicate = any(
            similarity(normalized, s) > 0.85
            for s in seen
        )
        if not is_duplicate:
            result.append(sentence)
            seen.append(normalized)
    return " ".join(result)

def similarity(a: str, b: str) -> float:
    # Simple Jaccard similarity on word sets — no ML needed
    set_a, set_b = set(a.split()), set(b.split())
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)
```

---

## Token Counter (tokenizer.py)

Use `tiktoken` for accurate token counts — do not use `len(text.split())`:

```python
import tiktoken

# cl100k_base is the tokenizer for gpt-4o and gpt-4o-mini
_encoder = tiktoken.get_encoding("cl100k_base")

def count_tokens(text: str) -> int:
    return len(_encoder.encode(text))
```

Initialize `_encoder` at module level (not per call) — encoding initialization is slow.

---

## Main Compressor (compressor.py)

```python
from compression.rules import (
    remove_filler_phrases,
    normalize_whitespace,
    remove_redundant_politeness,
    compress_lists,
    shorten_common_phrases,
    deduplicate_context,
)
from compression.tokenizer import count_tokens
from shared.models import CompressionResult

RULES = [
    ("normalize_whitespace", normalize_whitespace),
    ("remove_filler_phrases", remove_filler_phrases),
    ("shorten_common_phrases", shorten_common_phrases),
    ("remove_redundant_politeness", remove_redundant_politeness),
    ("deduplicate_context", deduplicate_context),
    ("compress_lists", compress_lists),
    ("normalize_whitespace", normalize_whitespace),  # run again to clean up after other rules
]

MIN_COMPRESSION_CHARS = 50  # don't compress very short prompts

def compress_prompt(prompt: str) -> CompressionResult:
    original_tokens = count_tokens(prompt)
    
    if len(prompt) < MIN_COMPRESSION_CHARS:
        return CompressionResult(
            compressed_prompt=prompt,
            original_tokens=original_tokens,
            compressed_tokens=original_tokens,
            ratio=1.0,
            rules_applied=[]
        )
    
    current = prompt
    rules_applied = []
    
    for rule_name, rule_fn in RULES:
        result = rule_fn(current)
        if result != current:
            rules_applied.append(rule_name)
            current = result
    
    compressed_tokens = count_tokens(current)
    
    # Safety check: if compression somehow made it longer, return original
    if compressed_tokens >= original_tokens:
        return CompressionResult(
            compressed_prompt=prompt,
            original_tokens=original_tokens,
            compressed_tokens=original_tokens,
            ratio=1.0,
            rules_applied=[]
        )
    
    return CompressionResult(
        compressed_prompt=current,
        original_tokens=original_tokens,
        compressed_tokens=compressed_tokens,
        ratio=round(compressed_tokens / original_tokens, 3),
        rules_applied=rules_applied
    )
```

---

## Implementation Order

### Step 1 — tokenizer.py
Implement and test `count_tokens`. Verify: `count_tokens("Hello, world!")` returns 4.

### Step 2 — rules.py, one rule at a time
Implement each rule with a test case at the bottom:
```python
if __name__ == "__main__":
    test = "Hi there! I hope this message finds you well. Due to the fact that I need help, please note that I would really appreciate it if you could explain how Python works. Thank you!"
    print(remove_filler_phrases(test))
    print(remove_redundant_politeness(test))
    # etc.
```

### Step 3 — compressor.py
Wire all rules into the pipeline. Run the end-to-end test:
```python
if __name__ == "__main__":
    prompt = """
    Hello! I hope you are doing well. I wanted to ask you, and I think this is 
    quite important to note, that due to the fact that I am working on a Python 
    project, I need help. I need help with Python. As you may know, Python is a 
    programming language. I would really appreciate it if you could help me 
    understand how to use lists in Python. Please note that this is urgent.
    Thank you so much for your help!
    """
    result = compress_prompt(prompt)
    print(f"Original: {result.original_tokens} tokens")
    print(f"Compressed: {result.compressed_tokens} tokens")
    print(f"Ratio: {result.ratio} ({(1-result.ratio)*100:.1f}% saved)")
    print(f"Rules applied: {result.rules_applied}")
    print(f"\nCompressed prompt:\n{result.compressed_prompt}")
```

Target: achieve >20% token reduction on the test prompt above.

---

## What NOT to do
- Do not remove sentences that contain factual content (numbers, names, code, URLs)
- Do not apply compression to content inside code blocks (` ``` `) — detect and skip them
- Do not use any external ML models — rule-based only
- Do not change the meaning of technical terms or domain-specific vocabulary
- Do not compress prompts shorter than 50 characters

---

## Code block protection
Before running any rule, extract code blocks and replace with placeholders:
```python
import re

def protect_code_blocks(text: str) -> tuple[str, dict]:
    placeholders = {}
    def replace(m):
        key = f"__CODE_{len(placeholders)}__"
        placeholders[key] = m.group(0)
        return key
    protected = re.sub(r'```[\s\S]*?```|`[^`]+`', replace, text)
    return protected, placeholders

def restore_code_blocks(text: str, placeholders: dict) -> str:
    for key, value in placeholders.items():
        text = text.replace(key, value)
    return text
```
Apply this wrapper in `compress_prompt` around the rules pipeline.

---

## Dependencies to add to requirements.txt
```
tiktoken
spacy
```
Note: spacy is optional — all rules above can be implemented with `re` only. Use it only if you want POS tagging for more advanced rules.

---

## Definition of Done
- [ ] `compress_prompt` on a 200-token verbose prompt achieves ≥15% token reduction
- [ ] Code blocks inside prompts are not modified
- [ ] Prompts under 50 characters are returned unchanged
- [ ] `ratio` is always ≤ 1.0 (never inflates the prompt)
- [ ] `rules_applied` accurately lists which rules fired
- [ ] Module-level tiktoken encoder (not re-initialized per call)
- [ ] No external dependencies beyond tiktoken and standard library
