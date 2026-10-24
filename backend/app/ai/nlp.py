"""Shared NLTK text helpers: tokenizing, stemming, fuzzy phrase matching, key terms.

Uses only NLTK parts that need no downloaded corpora, so setup stays `pip install`.
"""

import unicodedata
from collections import Counter

from nltk import edit_distance
from nltk.stem import SnowballStemmer
from nltk.tokenize import RegexpTokenizer

_STEMMER = SnowballStemmer("english")
_TOKENIZER = RegexpTokenizer(r"[a-z0-9]+")

# shortcut: small built-in English list instead of nltk.corpus.stopwords, which needs a download.
# "no"/"not" are kept as content words: "no water" and "not working" are complaints.
STOPWORDS = frozenset("""
a about above after again all also am an and any are as at be been before being below between both but by can
could did do does doing down during each few for from further had has have having he her here hers him his how i
if in into is it its itself just me more most my of off on once only or other our out over own please
same she should so some such than that the their them then there these they this those through to too under until
up very was we were what when where which while who whom why will with would you your yours get got still keep
keeps kept every since many much one two near inside outside today yesterday days day week weeks
""".split())

FUZZY_MIN_LEN = 6  # shorter words ("bus", "but") are too close to each other to fuzzy-match safely


def normalize(value):
    value = unicodedata.normalize("NFKC", value).casefold()
    value = value.translate(str.maketrans({c: " " for c in "-_/‐‑‒–—―"}))
    return " ".join(value.split())


def tokens(text):
    return _TOKENIZER.tokenize(normalize(text))


def stem(word):
    return _STEMMER.stem(word)


def content_stems(text):
    """Stems of the non-stopword tokens, in order."""
    return [stem(w) for w in tokens(text) if w not in STOPWORDS]


def _same(word, target):
    if word == target:
        return True
    if min(len(word), len(target)) < FUZZY_MIN_LEN:
        return False
    # stems of misspellings drift further ("projecter" -> "project"), so long words get 2 edits
    return edit_distance(word, target) <= (2 if max(len(word), len(target)) >= 8 else 1)


def phrase_stems(phrase):
    words = [w for w in tokens(phrase) if w not in STOPWORDS] or tokens(phrase)
    return [stem(w) for w in words]


def has_phrase(text_stems, phrase):
    """True when every stem of `phrase` occurs, in any order, within a short window of the text.

    Stemming and the window let "taps are leaking" match "leaking tap"; edit distance 1
    on long words tolerates typos such as "projecter".
    """
    wanted = phrase_stems(phrase)
    if not wanted:
        return False
    window = len(wanted) + 2
    for start in range(len(text_stems)):
        span = text_stems[start:start + window]
        if all(any(_same(w, target) for w in span) for target in wanted):
            return True
    return False


def key_terms(texts, limit=5, min_docs=2):
    """Most widespread content words across texts, counted once per text.

    Returns [(word, number_of_texts)], using the most common surface form of each stem.
    """
    doc_freq, surface = Counter(), {}
    for text in texts:
        seen = set()
        for word in tokens(text):
            if word in STOPWORDS or len(word) < 3 or word.isdigit():
                continue
            s = stem(word)
            surface.setdefault(s, Counter())[word] += 1
            seen.add(s)
        doc_freq.update(seen)
    ranked = sorted((item for item in doc_freq.items() if item[1] >= min_docs), key=lambda kv: (-kv[1], kv[0]))
    return [(surface[s].most_common(1)[0][0], n) for s, n in ranked[:limit]]

