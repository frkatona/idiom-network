Build a searchable and analyzable dataset of American idioms that supports exploration of:

syllable count,
rhyme relationships (phonetic, not spelling-based), and
alliteration (initial phoneme patterns)

The input corpus is a cleaned idiom list (~7.4k entries) extracted from NTC’s American Idioms Dictionary
Definitions are not required.

The final system should support:

filtering idioms by phonetic features
grouping idioms by rhyme/alliteration
computing similarity relationships between idioms
optionally visualizing idiom clusters
Core Design Principles
Phonetics over spelling
Use pronunciation (CMUdict), not orthography
Phrase-level analysis
Not just word-level; operate on entire idioms
Deterministic + fallback
Use dictionary lookup first, heuristics second
Pipeline architecture
Raw → normalized → phonetic → features → index
Ideal Task Order
Phase 1 — Input + normalization

Goal: clean, canonical idiom strings

Tasks
Load idiom list (TXT or CSV)
Normalize each idiom:
lowercase
strip punctuation (but preserve apostrophes optionally)
standardize whitespace
Tokenize into words
Store:
{
  "idiom": "...",
  "tokens": [...]
}
Edge handling
remove empty or malformed entries
optionally keep original + normalized versions
Phase 2 — Pronunciation mapping

Goal: map words → phonemes

Tools
CMU Pronouncing Dictionary
Python library: pronouncing (recommended)
Tasks
For each word:
lookup pronunciation(s)
select primary pronunciation
Handle unknown words:
fallback heuristic (simple syllable estimator)
mark as unknown_pronunciation = true
Output structure
{
  "phonemes_by_word": [
    ["AH0", "B", "IY1", "L"],
    ...
  ]
}
Phase 3 — Feature extraction

Goal: compute phonetic features per idiom

3.1 Syllable count
count digits in CMU phonemes (0/1/2 markers)
sum across words
"syllable_count": 6
3.2 Rhyme key

Define rhyme as:

from last stressed vowel → end

Example:

"dozen" → AH1 Z AH0 N

Tasks:

find last stressed vowel (1 or 2)
slice phoneme sequence from that point
"rhyme_key": "AH1 Z AH0 N"
3.3 Alliteration features

Focus on initial phoneme, not first letter

Tasks:

extract first consonant phoneme per word
ignore stopwords optionally (configurable)

Compute:

list of initial sounds
repetition score (e.g., frequency of most common)
"initial_phonemes": ["D", "D", "D"],
"alliteration_score": 0.75
3.4 Stress pattern (optional but powerful)
binary pattern of stressed syllables
"stress_pattern": [0,1,0,1]
Phase 4 — Data model assembly

Combine into unified structure:

{
  "idiom": "a dime a dozen",
  "tokens": [...],
  "syllable_count": 6,
  "phonemes": [...],
  "rhyme_key": "...",
  "initial_phonemes": [...],
  "alliteration_score": ...,
  "unknown_words": [...]
}

Export:

CSV (for inspection)
JSON (for app use)
Phase 5 — Search + indexing
Build indices for:
syllable_count → idioms
rhyme_key → idioms
initial_phoneme → idioms
Implement queries:
idioms with N syllables
idioms that rhyme with X
idioms with strong alliteration
combinations:
same syllable count + rhyme
alliteration + length constraint
Phase 6 — Similarity / relationships

Define similarity metrics:

Option A (simple)
shared rhyme
similar syllable count
overlapping phoneme sets
Option B (stronger)
phoneme edit distance
cosine similarity on phoneme n-grams

Output:

"related_idioms": [...]
Phase 7 — Visualization (optional but high value)
Options
Network graph
nodes = idioms
edges:
same rhyme
high alliteration similarity
Scatter plot
x = syllable count
y = rhyme cluster ID
UI filters
sliders for syllables
toggle for alliteration strength
search box
Key Libraries

Recommended Python stack:

pandas
pronouncing
numpy
networkx (for graph)
rapidfuzz (optional search)
plotly (optional visualization)
Known Challenges
CMUdict missing entries (proper nouns, rare words)
multi-pronunciation ambiguity
idioms with punctuation/variants
deciding how to treat stopwords in alliteration
Suggested Milestones
Clean idiom dataset (done)
Phoneme mapping working for 90%+ entries
Syllable + rhyme extraction validated
Basic search working
Similarity + grouping
Visualization layer
Stretch Goals
semantic clustering (embeddings)
frequency weighting (common vs rare idioms)
rhythm/meter classification
“generate similar-sounding idioms” tool