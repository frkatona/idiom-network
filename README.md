# Idiom Phonetics Explorer

A local Dash app for exploring American idioms by phonetic features: syllable
count, rhyme keys, alliteration patterns, stress, and related idioms.

The source corpus is `american_idioms_clean_list.csv`, a cleaned idiom list
extracted from NTC's American Idioms Dictionary. Definitions are not included.

## Setup

Use Python 3.13 through the Windows Python launcher:

```powershell
py -3.13 -m pip install -r requirements.txt
```

## Build The Dataset

```powershell
py -3.13 build_dataset.py
```

This creates:

- `output/idioms_phonetic.json`
- `output/idioms_phonetic.csv`
- `output/idioms_indices.json`
- `output/dataset_stats.json`

The builder preserves the original CSV fields and adds normalized tokens,
CMUdict phonemes, syllable counts, phrase-level rhyme keys, initial phoneme
patterns, alliteration scores, stress patterns, unknown pronunciation flags,
and related idioms.

## Run The App

```powershell
py -3.13 app.py
```

Open:

```text
http://127.0.0.1:8050
```

If the generated output files are missing, the app builds them automatically on
startup.

## Build The Static GitHub Pages Site

GitHub Pages only serves static files, so the repository includes a static
browser version of the explorer for deployment.

```powershell
py -3.13 build_static_site.py --site-dir site --subpath idiom-dictionary-network
```

This writes:

```text
site/
  index.html
  idiom-dictionary-network/
    index.html
    assets/
    data/
```

The deployed subpage path is:

```text
/idiom-dictionary-network/
```

The GitHub Actions workflow in `.github/workflows/deploy-pages.yml` builds this
static site and deploys it using GitHub Pages. In the repository settings, set
Pages build and deployment source to **GitHub Actions**.

## Use The Explorer

- Search idiom text or fragments.
- Filter by syllable range, rhyme key, initial phoneme, alliteration floor, and
  unknown-pronunciation status.
- Toggle whether alliteration ignores common stopwords.
- Select a table row to inspect tokens, phonemes, stress pattern, rhyme key,
  unknown words, and related idioms.
- Use the cluster view to inspect rhyme and phonetic-similarity relationships.

## Phonetic Concepts And Resources

This project uses pronunciation data rather than spelling. The phoneme labels
come from CMUdict's ARPABET-style notation, where vowel phonemes include stress
digits such as `0`, `1`, and `2`.

- **Rhyme key**: the phrase-level phoneme tail from the last stressed vowel to
  the end of the idiom. For example, a key like `EH1 F ER0 T` represents the
  stressed vowel and remaining sounds in the final rhyming segment. This follows
  the same basic idea as `pronouncing.rhyming_part`, which defines the rhyming
  part as the sounds from the stressed syllable nearest the end through the end.
- **Initial phonemes**: the first consonant phoneme found in each word after
  tokenization. These are sound-based initials, so words may group together even
  when their first letters differ.
- **Alliteration floor**: the minimum alliteration score required by the filter.
  The score is the share of considered words that use the most repeated initial
  consonant phoneme. A floor of `0.50` keeps idioms where at least half of the
  counted words share the same initial sound.

Suggested resources:

- [CMUdict](https://github.com/cmusphinx/cmudict): the Carnegie Mellon
  Pronouncing Dictionary used as the pronunciation source.
- [CMUdict symbol files](https://github.com/cmusphinx/cmudict/blob/master/cmudict.symbols):
  the phoneme and stress-mark symbols that explain labels such as `AH0`, `EH1`,
  and `ER0`.
- [pronouncing documentation](https://pronouncing.readthedocs.io/en/latest/):
  practical Python examples for CMUdict lookup, syllables, stresses, and rhymes.
- [Poetry Foundation: alliteration](https://www.poetryfoundation.org/education/glossary/alliteration):
  a literary definition of alliteration as repeated initial consonant sounds.

## Tests

```powershell
py -3.13 -m pytest
```
