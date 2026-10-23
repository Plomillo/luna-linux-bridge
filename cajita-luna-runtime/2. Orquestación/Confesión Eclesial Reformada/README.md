---
dataset_info:
- config_name: default
  features:
  - name: translation_id
    dtype: string
  - name: translation
    dtype: string
  - name: language
    dtype: string
  - name: book_number
    dtype: int32
  - name: book
    dtype: string
  - name: book_abbr
    dtype: string
  - name: chapter
    dtype: int32
  - name: verse
    dtype: string
  - name: verse_number
    dtype: int32
  - name: verse_suffix
    dtype: string
  - name: verse_id
    dtype: string
  - name: text
    dtype: string
  splits:
  - name: train
    num_examples: 30997
  num_rows: 30997
configs:
- config_name: default
  data_files: data/data.parquet
---

# Reina-Valera (1909)

## Description

The Reina-Valera Bible is the first complete translation of the Bible into Spanish, first published in 1569 by Casiodoro de Reina, with a revision by Cipriano de Valera in 1602. This 1909 edition is a significant revision that became the standard Spanish Protestant Bible. The translation was made from the original Hebrew and Greek texts. The Reina-Valera has had a profound influence on Spanish-speaking Protestantism and is one of the most widely used Spanish Bible translations. It includes the Protestant canon (66 books).

## Dataset Structure

Each row represents one Bible verse.

| Column | Type | Description |
|--------|------|-------------|
| `translation_id` | string | Translation identifier |
| `translation` | string | Full translation name |
| `language` | string | Language code |
| `book_number` | int32 | Book number (1-66) |
| `book` | string | Book name |
| `book_abbr` | string | Book abbreviation |
| `chapter` | int32 | Chapter number |
| `verse` | string | Verse number (may include suffixes like `13a`) |
| `verse_number` | int32 | Numeric part of verse |
| `verse_suffix` | string | Verse suffix (e.g. `a`, `b`) or null |
| `verse_id` | string | Unique verse identifier (`{book_abbr}_{chapter}_{verse}`) |
| `text` | string | Verse text |

## Statistics

- **Books:** 66
- **Verses:** 30997
- **Language:** Spanish
- **Format:** Parquet (ZSTD compressed)
- **File size:** 2.10 MB

## Usage

```python
from datasets import load_dataset

dataset = load_dataset("k-mktr/reina_valera_es", split="train")
print(dataset[0])
# {'translation_id': 'reina_valera_es', 'book': '...', 'chapter': 1, 'verse': '1', 'text': '...'}
```

## License

Public domain (1909 revision, copyright expired).
