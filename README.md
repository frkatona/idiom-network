# Idiom Phonetics Explorer

A static web app for exploring American idioms by phonetic features: syllable
count, rhyme keys, alliteration patterns, stress, and related idioms.

The source corpus is `american_idioms_clean_list.csv`, a cleaned idiom list
extracted from NTC's American Idioms Dictionary. Definitions are not included.

## Deployment

The `docs/` directory contains the complete static site. Pushing to `main`
triggers GitHub Actions to deploy it to GitHub Pages — no build step required.

The deployed subpage path is `/idiom-dictionary-network/`.

## Use The Explorer

- Search idiom text or fragments. The search supports fuzzy matching for
  approximate queries.
- Filter by syllable range, rhyme key, initial phoneme, alliteration floor, and
  unknown-pronunciation status.
- Toggle whether alliteration ignores common stopwords.
- Click a sortable column header to reorder the results table.
- Select a table row to inspect tokens, phonemes, stress pattern, rhyme key,
  unknown words, and related idioms.
- Use the network graph to inspect rhyme and phonetic-similarity relationships
  between idioms.

## Rebuilding The Dataset

The Python scripts are only needed when the source corpus or phonetic analysis
logic changes. They are **not** required for deployment.

### Setup

```powershell
py -3.13 -m pip install -r requirements.txt
```

### Regenerate data and rebuild the site

```powershell
py -3.13 build_dataset.py
py -3.13 app.py
```

This reads `american_idioms_clean_list.csv`, runs CMUdict pronunciation
analysis via the `pronouncing` library, computes phonetic features and
similarity relationships, and writes the deployable site to `docs/`.

### Run tests

```powershell
py -3.13 -m pytest
```

## Phonetic Concepts And Resources

This project uses pronunciation data rather than spelling. The phoneme labels
come from CMUdict's ARPABET-style notation, where vowel phonemes include stress
digits such as `0`, `1`, and `2`.

- **Rhyme key**: the phrase-level phoneme tail from the last stressed vowel to
  the end of the idiom.
- **Initial phonemes**: the first consonant phoneme found in each word after
  tokenization. These are sound-based initials, so words may group together even
  when their first letters differ.
- **Alliteration floor**: the minimum alliteration score required by the filter.
  The score is the share of considered words that use the most repeated initial
  consonant phoneme.

Suggested resources:

- [CMUdict](https://github.com/cmusphinx/cmudict)
- [pronouncing documentation](https://pronouncing.readthedocs.io/en/latest/)
- [Poetry Foundation: alliteration](https://www.poetryfoundation.org/education/glossary/alliteration)

## Todo

- [x] added wildcards '*' and '?' (multiple and single replacements, resp.) for filters
- [ ] Source and method for adding additional idioms and adding a label for the type of phrase's origin
- [ ] Cluster view improved usability
- [ ] Fix how placeholder words are accounted for in syllable and alliteration calculations
