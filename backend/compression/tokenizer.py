import tiktoken

_encoder = tiktoken.get_encoding("clk100k_base")

def count_token(text: str) -> int:
	return len(_encoder.encode(text))