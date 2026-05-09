"""
rules.py — Reguli individuale de compresie pentru proiect.

Fiecare regulă este o funcție cu semnatura: rule_name(text: str) -> str
Regulile sunt apelate in ordine din compressor.py.

IMPORTANT: niciuna dintre reguli nu trebuie sa schimbe sensul textului.
"""

import re

_DIACRITICS = str.maketrans({
	'ă': 'a', 'â': 'a', 'î': 'i', 'ș': 's', 'ț': 't',
	'Ă': 'A', 'Â': 'A', 'Î': 'I', 'Ș': 'S', 'Ț': 'T',
	# variante cu cedila (unicode vechi, mai apar in text copiat)
	'ş': 's', 'ţ': 't', 'Ş': 'S', 'Ţ': 'T',
})


def strip_diacritics(text: str) -> str:
	return text.translate(_DIACRITICS)


EN_FILLER_DELETIONS = [
	r"\bplease note that\b",
	r"\bit is important to note that\b",
	r"\bit should be noted that\b",
	r"\bit is worth noting that\b",
	r"\bit is worth mentioning that\b",
	r"\bas you may (already )?know\b",
	r"\bas we (all )?know\b",
	r"\bneedless to say\b",
	r"\bit goes without saying( that)?\b",
	r"\bfor what it'?s worth\b",
	r"\bat the end of the day\b",
	r"\bin my (humble )?opinion\b",
	r"\bif you ask me\b",
	r"\bto be (perfectly )?honest\b",
	r"\bto tell (you )?the truth\b",
	r"\bbasically\b",
	r"\bessentially\b",
	r"\bliterally\b",
	r"\bactually\b",
	r"\bquite frankly\b",
	r"\bI (just )?wanted to (ask you|mention|bring up|flag)[,.]?\s*",
	r"\band I think (this is|it is|it's) (quite |very )?(important to note|worth noting|worth mentioning)[,.]?\s*(that\s+)?",
	r"\bI think (this is|it is|it's) (quite |very )?(important to note|worth noting|worth mentioning)[,.]?\s*(that\s+)?",
]

RO_FILLER_DELETIONS = [
	r"\bva rog sa retineti ca\b",
	r"\bte rog sa retii ca\b",
	r"\bvreau sa retineti ca\b",
	r"\bvreau sa retii ca\b",
	r"\bas vrea sa retii ca\b",
	r"\bas vrea sa retineti ca\b",
	r"\bam dori sa retii ca\b",
	r"\bam dori sa retineti ca\b",
	r"\btin sa mentionez ca\b",
	r"\btin sa precizez ca\b",
	r"\beste important sa mentionam ca\b",
	r"\beste important de mentionat ca\b",
	r"\btrebuie mentionat ca\b",
	r"\bmerita mentionat ca\b",
	r"\bdupa cum bine stiti\b",
	r"\bdupa cum stiti\b",
	r"\bdupa cum bine stim\b",
	r"\bdupa cum stim\b",
	r"\bdupa cum stii\b",
	r"\bfara nicio indoiala\b",
	r"\bfara indoiala\b",
	r"\bnu mai e nevoie sa spun\b",
	r"\bnu mai e nevoie sa mentionez\b",
	r"\bde altfel\b",
	r"\bde fapt\b",
	r"\bpur si simplu\b",
	r"\bca sa fiu sincer\b",
	r"\bca sa fiu onest\b",
	r"\bsincer sa fiu\b",
	r"\bca sa spun drept\b",
	r"\bca sa spun adevarul\b",
	r"\bin opinia mea\b",
	r"\bdupa parerea mea\b",
	r"\bla finalul zilei\b",
	r"\bin esenta\b",
]


# =============================================================================
#  SECTIUNEA 2 — DICTIONARE: FRAZE CARE SE INLOCUIESC (replacements)
# =============================================================================
#  Cheia = pattern-ul cautat (regex), valoarea = ce punem in loc.
#  Toate au flag IGNORECASE cand sunt aplicate, deci nu te complici cu majuscule.

EN_FILLER_REPLACEMENTS = {
	# ─── timp ───
	r"\bat this point in time\b": "now",
	r"\bat the present time\b": "now",
	r"\bat the current time\b": "now",
	r"\bin the near future\b": "soon",
	r"\bin the not too distant future\b": "soon",
	r"\bon a regular basis\b": "regularly",
	r"\bon a daily basis\b": "daily",
	r"\bprior to\b": "before",
	r"\bsubsequent to\b": "after",
	r"\bin advance of\b": "before",

	# ─── cauzalitate ───
	r"\bdue to the fact that\b": "because",
	r"\bowing to the fact that\b": "because",
	r"\bfor the (simple )?reason that\b": "because",
	r"\bas a result of\b": "due to",
	r"\bas a consequence of\b": "due to",
	r"\bin spite of the fact that\b": "although",
	r"\bdespite the fact that\b": "although",
	r"\bregardless of the fact that\b": "although",

	# ─── conditionale ───
	r"\bin the event that\b": "if",
	r"\bin the case (that|of)\b": "if",
	r"\bunder circumstances in which\b": "if",
	r"\bwhether or not\b": "whether",

	# ─── scop / mod ───
	r"\bin order to\b": "to",
	r"\bso as to\b": "to",
	r"\bfor the purpose of\b": "to",
	r"\bwith the intention of\b": "to",
	r"\bin the process of\b": "while",
	r"\bin the course of\b": "during",

	# ─── referinta ───
	r"\bwith regard to\b": "regarding",
	r"\bwith respect to\b": "regarding",
	r"\bin reference to\b": "regarding",
	r"\bin relation to\b": "regarding",

	# ─── cantitate ───
	r"\ba large number of\b": "many",
	r"\ba great number of\b": "many",
	r"\ba significant number of\b": "many",
	r"\ba small number of\b": "few",
	r"\bthe majority of\b": "most",
	r"\ba majority of\b": "most",
	r"\ba minority of\b": "few",
	r"\ba great deal of\b": "much",
	r"\ba large amount of\b": "much",

	# ─── capabilitate ───
	r"\bhas the ability to\b": "can",
	r"\bhave the ability to\b": "can",
	r"\bis able to\b": "can",
	r"\bare able to\b": "can",
	r"\bhas the capacity to\b": "can",
	r"\bis in a position to\b": "can",

	# ─── spatiu ───
	r"\bin close proximity to\b": "near",
	r"\bin the vicinity of\b": "near",

	# ─── altele ───
	r"\bon the occasion of\b": "when",
	r"\bin the absence of\b": "without",
	r"\bin terms of\b": "for",
	r"\bin connection with\b": "about",
	r"\bin (the )?light of\b": "given",
	r"\bin view of the fact that\b": "since",
	r"\ba sufficient (number|amount) of\b": "enough",
}

RO_FILLER_REPLACEMENTS = {
	# ─── timp ───
	r"\bla momentul actual\b": "acum",
	r"\bla momentul de fata\b": "acum",
	r"\bin acest moment\b": "acum",
	r"\bin momentul de fata\b": "acum",
	r"\bin perioada actuala\b": "acum",
	r"\bin perioada imediat urmatoare\b": "curand",
	r"\bin viitorul apropiat\b": "curand",
	r"\bin mod regulat\b": "regulat",
	r"\bin mod frecvent\b": "frecvent",
	r"\bpe baza zilnica\b": "zilnic",
	r"\bpe baza regulata\b": "regulat",
	r"\binainte de a\b": "inainte sa",

	# ─── cauzalitate ───
	r"\bdin cauza faptului ca\b": "fiindca",
	r"\bdatorita faptului ca\b": "fiindca",
	r"\bca urmare a faptului ca\b": "fiindca",
	r"\bpentru motivul ca\b": "fiindca",
	r"\bpentru simplul motiv ca\b": "fiindca",
	r"\bca rezultat al\b": "din cauza",
	r"\bca o consecinta a\b": "din cauza",
	r"\bin pofida faptului ca\b": "desi",
	r"\bin ciuda faptului ca\b": "desi",
	r"\bcu toate ca\b": "desi",
	r"\bavand in vedere faptul ca\b": "deoarece",
	r"\bin lumina faptului ca\b": "deoarece",
	r"\btinand cont de faptul ca\b": "deoarece",

	# ─── conditionale ───
	r"\bin cazul in care\b": "daca",
	r"\bin situatia in care\b": "daca",
	r"\bin eventualitatea in care\b": "daca",
	r"\bindiferent daca\b": "daca",

	# ─── scop / mod ───
	r"\bin vederea\b": "pentru",
	r"\bin scopul de a\b": "pentru a",
	r"\bin scopul realizarii\b": "pentru",
	r"\bcu scopul de a\b": "pentru a",
	r"\bcu intentia de a\b": "pentru a",
	r"\bin procesul de\b": "in timp ce",
	r"\bpe parcursul\b": "in timpul",
	r"\bin decursul\b": "in timpul",

	# ─── referinta ───
	r"\bcu privire la\b": "despre",
	r"\bin ceea ce priveste\b": "despre",
	r"\bin legatura cu\b": "despre",
	r"\breferitor la\b": "despre",
	r"\bin raport cu\b": "fata de",
	r"\bin comparatie cu\b": "fata de",

	# ─── cantitate ───
	r"\bun numar mare de\b": "multi",
	r"\bun numar semnificativ de\b": "multi",
	r"\bun numar important de\b": "multi",
	r"\bun numar mic de\b": "putini",
	r"\bo mare parte din\b": "majoritatea",
	r"\bo mare parte a\b": "majoritatea",
	r"\bo buna parte din\b": "mare parte din",
	r"\bo cantitate mare de\b": "mult",
	r"\bo cantitate semnificativa de\b": "mult",
	r"\bun procent mare de\b": "multi",
	r"\bun procent insemnat de\b": "multi",

	# ─── capabilitate ───
	r"\bare capacitatea de a\b": "poate",
	r"\bau capacitatea de a\b": "pot",
	r"\bare posibilitatea de a\b": "poate",
	r"\bau posibilitatea de a\b": "pot",
	r"\bare abilitatea de a\b": "poate",
	r"\bau abilitatea de a\b": "pot",
	r"\beste capabil sa\b": "poate",
	r"\beste capabila sa\b": "poate",
	r"\bsunt capabili sa\b": "pot",
	r"\bsunt capabile sa\b": "pot",
	r"\beste in masura sa\b": "poate",

	# ─── spatiu ───
	r"\bin apropierea\b": "langa",
	r"\bin imediata apropiere a\b": "langa",
	r"\bin vecinatatea\b": "langa",
	r"\bin proximitatea\b": "langa",

	# ─── altele ───
	r"\bcu ocazia\b": "cand",
	r"\bin absenta\b": "fara",
	r"\bin lipsa\b": "fara",
	r"\bin termeni de\b": "pentru",
	r"\bdin punct de vedere al\b": "ca",
	r"\bdin punct de vedere\b": "ca",
	r"\bo cantitate suficienta de\b": "destul",
	r"\bun numar suficient de\b": "destui",
}


# =============================================================================
#  SECTIUNEA 3 — POLITETE LA INCEPUT / SFARSIT (opening / closing)
# =============================================================================
#  Aceste pattern-uri folosesc anchor-uri ^ (inceput) si $ (sfarsit).
#  Se aplica DOAR pe marginile promptului, nu in interior.

EN_OPENING_PATTERNS = [
	r"^(hi|hello|hey|greetings)( there)?[,.!]?\s*",
	r"^good (morning|afternoon|evening)[,.!]?\s*",
	r"^i hope (you('re| are)|this (email|message) finds you) (doing )?well[.!,]?\s*",
	r"^i hope (you('re| are) )?having a (great|good|nice) (day|week)[.!,]?\s*",
	r"^thank(s| you)( so much)?( in advance)?( for (your )?(help|time))?[.!,]?\s*",
	r"^(sorry|apologies) (for|to) (bother|disturb|interrupt)( you)?[.!,]?\s*",
	r"^(just )?(quick|brief) (question|note)[.!,:]?\s*",
]

EN_CLOSING_PATTERNS = [
	r"\s*thank(s| you)( so much)?( in advance)?( for (your )?(help|time))?[.!,]?\s*$",
	r"\s*please (let me know|feel free to ask|don'?t hesitate)[^.!?]*[.!,]?\s*$",
	r"\s*i (would|'d) (really |greatly |much )?appreciate (it|your help|any help)[^.!?]*[.!,]?\s*$",
	r"\s*looking forward to (your reply|hearing (from you|back))[.!,]?\s*$",
	r"\s*(best|kind) regards[.!,]?\s*$",
	r"\s*(cheers|sincerely|best)[.!,]?\s*$",
	r"\s*hope (this|that) helps[.!,]?\s*$",
	r"\s*any (help|advice|input) (is|would be) (appreciated|welcome)[.!,]?\s*$",
]

RO_OPENING_PATTERNS = [
	r"^(salut|buna|servus|noroc)( ziua| dimineata| seara)?[,.!]?\s*",
	r"^buna (ziua|dimineata|seara)[,.!]?\s*",
	r"^sper ca (esti|sunteti) bine[.!,]?\s*",
	r"^sper ca (te|va) gaseste (acest mesaj )?bine[.!,]?\s*",
	r"^sper ca ai (avut )?o (zi|saptamana) (buna|frumoasa)[.!,]?\s*",
	r"^as aprecia (mult |enorm |foarte mult |tare mult )?(daca|ca)\b[^.!?]*[.!?]\s*",
	r"^as dori (mult |enorm |foarte mult )?(daca|ca|sa)\b[^.!?]*[.!?]\s*",
	r"^te[-\s]?as ruga (mult |frumos )?(daca|ca|sa)\b[^.!?]*[.!?]\s*",
	r"^multumesc (mult |anticipat |mult anticipat |frumos )?(pentru (ajutor|timp))?[.!,]?\s*",
	r"^(scuze|imi (cer|pare) rau)( pentru deranj)?[.!,]?\s*",
	r"^(o |doar o )?(scurta |rapida )?(intrebare|nelamurire)[.!,:]?\s*",
]

RO_CLOSING_PATTERNS = [
	r"\s*multumesc (mult |anticipat |frumos |foarte mult )?(pentru (ajutor|timp|rabdare))?[.!,]?\s*$",
	r"\s*va multumesc[^.!?]*[.!,]?\s*$",
	r"\s*as aprecia (mult |foarte mult |enorm )?(orice ajutor|ajutorul (tau|dumneavoastra))?[.!,]?\s*$",
	r"\s*orice (ajutor|sfat|sugestie) (e|este|ar fi) (binevenit|apreciat)a?[.!,]?\s*$",
	r"\s*astept (cu interes )?raspunsul (tau|dumneavoastra)[.!,]?\s*$",
	r"\s*sper ca (asta |aceasta )?ajuta[.!,]?\s*$",
	r"\s*(toate cele bune|cu drag|cu stima|cu respect)[.!,]?\s*$",
	r"\s*(numai bine|o zi (buna|frumoasa))[.!,]?\s*$",
]


# =============================================================================
#  SECTIUNEA 4 — DICTIONARE COMBINATE (EN + RO)
# =============================================================================
#  Folosim {**dict1, **dict2} = dict unpacking. Combina doua dictionare intr-unul.

ALL_DELETIONS = EN_FILLER_DELETIONS + RO_FILLER_DELETIONS
ALL_REPLACEMENTS = {**EN_FILLER_REPLACEMENTS, **RO_FILLER_REPLACEMENTS}
ALL_OPENINGS = EN_OPENING_PATTERNS + RO_OPENING_PATTERNS
ALL_CLOSINGS = EN_CLOSING_PATTERNS + RO_CLOSING_PATTERNS


def normalize_whitespace(text: str) -> str:
	text = re.sub(r'[ \t]+', ' ', text)
	text = re.sub(r'\n{3,}', '\n\n', text)
	text = re.sub(r' +\n', '\n', text)
	return text.strip()



def remove_filler_phrases(text: str) -> str:
	for pattern, replacement in ALL_REPLACEMENTS.items():
		text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
	for pattern in ALL_DELETIONS:
		text = re.sub(pattern, '', text, flags=re.IGNORECASE)
	return text


def remove_redundant_politeness(text: str) -> str:
	for pattern in ALL_OPENINGS:
		text = re.sub(pattern, '', text, flags=re.IGNORECASE)
	for pattern in ALL_CLOSINGS:
		text = re.sub(pattern, '', text, flags=re.IGNORECASE)
	return text


_LIST_INTRO = re.compile(
	r'\b(please\s+)?(do\s+)?the\s+following(\s+things?|\s+steps?|\s+items?)?\s*:',
	re.IGNORECASE,
)

def compress_lists(text: str) -> str:
	return _LIST_INTRO.sub('Do:', text)


def _jaccard(a: str, b: str) -> float:
	sa, sb = set(a.split()), set(b.split())
	if not sa or not sb:
		return 0.0
	return len(sa & sb) / len(sa | sb)


def deduplicate_context(text: str) -> str:
	sentences = re.split(r'(?<=[.!?])\s+', text)
	seen: list[str] = []
	result: list[str] = []
	for sentence in sentences:
		normalized = sentence.lower().strip()
		if not any(_jaccard(normalized, s) > 0.85 for s in seen):
			result.append(sentence)
			seen.append(normalized)
	return ' '.join(result)


def fix_artifacts(text: str) -> str:
	# Virgula orfana dupa punct: ". , Cuvant" → ". Cuvant"
	text = re.sub(r'([.!?] ),\s*', r'\1', text)
	# Virgula orfana la inceput de string: ", Cuvant" → "Cuvant"
	text = re.sub(r'^[,;]\s*', '', text)
	# Capitalizeaza prima litera dupa punct/semn de exclamare/intrebare
	text = re.sub(r'([.!?]\s+)([a-z])', lambda m: m.group(1) + m.group(2).upper(), text)
	# Capitalizeaza prima litera din tot textul
	if text and text[0].islower():
		text = text[0].upper() + text[1:]
	return text


# =============================================================================
#  SECTIUNEA 8 — TESTE RAPIDE (ruleaza cu: python rules.py)
# =============================================================================

if __name__ == "__main__":
	print("=" * 70)
	print("TEST 1 — strip_diacritics")
	print("=" * 70)
	test_diac = "Salut, înțeleg că ești ocupat. Mulțumesc!"
	print(f"INPUT : {test_diac}")
	print(f"OUTPUT: {strip_diacritics(test_diac)}")

	print("\n" + "=" * 70)
	print("TEST 2 — normalize_whitespace")
	print("=" * 70)
	test_ws = "  Salut    lume   \n\n\n\n  Cum  esti?   "
	print(f"INPUT : {repr(test_ws)}")
	print(f"OUTPUT: {repr(normalize_whitespace(test_ws))}")

	print("\n" + "=" * 70)
	print("TEST 3 — remove_filler_phrases (RO)")
	print("=" * 70)
	test_ro = (
		"Datorita faptului ca am nevoie de ajutor, va rog sa retineti ca "
		"in cazul in care aveti timp, in mod regulat verific emailul."
	)
	print(f"INPUT : {test_ro}")
	print(f"OUTPUT: {remove_filler_phrases(test_ro)}")

	print("\n" + "=" * 70)
	print("TEST 4 — remove_filler_phrases (EN)")
	print("=" * 70)
	test_en = (
		"Due to the fact that I need help, please note that in the event "
		"that you have time, I check email on a regular basis."
	)
	print(f"INPUT : {test_en}")
	print(f"OUTPUT: {remove_filler_phrases(test_en)}")

	print("\n" + "=" * 70)
	print("TEST 5 — remove_redundant_politeness")
	print("=" * 70)
	test_pol = (
		"Salut! Sper ca esti bine. Am o intrebare despre Python. "
		"Multumesc anticipat pentru ajutor!"
	)
	print(f"INPUT : {test_pol}")
	print(f"OUTPUT: {remove_redundant_politeness(test_pol)}")

	print("\n" + "=" * 70)
	print("TEST 6 — pipeline complet (toate regulile aplicate)")
	print("=" * 70)
	test_full = (
		"Salut! Sper ca esti bine. As aprecia mult daca, in cazul in care ai timp, "
		"ai putea sa ma ajuti. Datorita faptului ca lucrez la un proiect Python, "
		"as vrea sa retii ca am nevoie de ajutor cu listele. "
		"Multumesc anticipat pentru ajutor!"
	)
	print(f"INPUT :\n{test_full}\n")
	step1 = strip_diacritics(test_full)
	step2 = normalize_whitespace(step1)
	step3 = remove_filler_phrases(step2)
	step4 = remove_redundant_politeness(step3)
	step5 = normalize_whitespace(step4)  # cleanup final dupa stergeri
	print(f"OUTPUT:\n{step5}")
	print(f"\nReducere caractere: {len(test_full)} → {len(step5)} "
		  f"({(1 - len(step5)/len(test_full))*100:.1f}% mai scurt)")