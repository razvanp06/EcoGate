from .rules import (
	strip_diacritics,
	normalize_whitespace,
	remove_filler_phrases,
	remove_redundant_politeness,
	compress_lists,
	deduplicate_context,
	fix_artifacts,
)
import sys
import os
import re
from .tokenizer import count_tokens
from shared.models import CompressionResult

MIN_COMPRESSION_CHARS = 50

def _protect_code_blocks(text: str) -> tuple[str, dict[str, str]]:
	placeholders: dict[str, str] = {}

	def replace(m: re.Match) -> str:
		key = f"__CODE_{len(placeholders)}__"
		placeholders[key] = m.group(0)
		return key
	
	protected = re.sub(r'```[\s\S]*?```|`[^`]+`', replace, text)
	return protected, placeholders

def _restore_code_blocks(text: str, placeholders: dict) -> str:
	for key, value in placeholders.items():
		text = text.replace(key, value)
	return text

RULES = [
	("strip_diacritics", strip_diacritics),
	("normalize_whitespace", normalize_whitespace),
	("remove_filler_phrases", remove_filler_phrases),
	("remove_redundant_politeness", remove_redundant_politeness),
	("deduplicate_context", deduplicate_context),
	("compress_lists", compress_lists),
	("fix_artifacts", fix_artifacts),
	("normalize_whitespace", normalize_whitespace),
]

def compress_prompt(prompt: str) -> CompressionResult:
	original_tokens = count_tokens(prompt)

	if len(prompt) < MIN_COMPRESSION_CHARS:
		return CompressionResult(
			compressed_prompt = prompt,
			original_tokens = original_tokens,
			compressed_tokens = original_tokens,
			ratio = 1.0,
			rules_applied = []
		)

	current, placeholders = _protect_code_blocks(prompt)
	rules_applied: list[str] = []

	for rule_name, rule_fn in RULES:
		result = rule_fn(current)
		if result != current:
			rules_applied.append(rule_name)
			current = result

	current = _restore_code_blocks(current, placeholders)
	compressed_tokens = count_tokens(current)

	if compressed_tokens >= original_tokens:
		return CompressionResult(
			compressed_prompt=prompt,
			original_tokens=original_tokens,
			compressed_tokens=original_tokens,
			ratio=1.0,
			rules_applied=[],
		)
	
	return CompressionResult(
	compressed_prompt=current,
	original_tokens=original_tokens,
	compressed_tokens=compressed_tokens,
	ratio=round(compressed_tokens / original_tokens, 3),
	rules_applied=rules_applied,
)


if __name__ == "__main__":
    prompt = (
        "Hello! I hope you are doing well. I wanted to ask you, and I think this is "
        "quite important to note, that due to the fact that I am working on a Python "
        "project, I need help. I need help with Python. As you may know, Python is a "
        "programming language. I would really appreciate it if you could help me "
        "understand how to use lists in Python. Please note that this is urgent. "
        "Thank you so much for your help!"
    )
    result = compress_prompt(prompt)
    print(f"Original:   {result.original_tokens} tokens")
    print(f"Compressed: {result.compressed_tokens} tokens")
    print(f"Ratio:      {result.ratio} ({(1 - result.ratio) * 100:.1f}% saved)")
    print(f"Rules:      {result.rules_applied}")
    print(f"\nCompressed:\n{result.compressed_prompt}")
