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

## Tests

```powershell
py -3.13 -m pytest
```
