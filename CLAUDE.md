# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A digital scholarly archive of Elena Shvarts's poetry (Елена Шварц, 1948–2010): a Flask + MongoDB web app for browsing ~430 canonical poems (~1,285 documents counting variant printings) chronologically or by published collection, comparing textual variants of the same poem, and lemma-aware full-text search. UI text is Russian. Production lives at https://eshvarts.com/ (DigitalOcean droplet 142.93.242.162, nginx + uWSGI) — currently down at the DB level and awaiting redeploy (Phase 4 below).

## Running locally

The database is a local Docker container that must be started first:

```bash
docker start mongodb          # mongo:4.0.4, port 27017, no auth
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
FLASK_APP=app .venv/bin/flask run
```

Connection is configured by env vars `MONGO_URI` (default `mongodb://localhost:27017`) and `MONGO_DB` (default `admin` — yes, the data really lives in the `admin` database).

Tests (require the Docker DB to be up): `pip install -r requirements-dev.txt && python -m pytest tests/`. The suite smoke-tests every route, legacy-URL redirects, 404s, and pins the search semantics (declensions, ё/е, lemma-vs-stem precision, variant notes, pagination, year validation).

Backup/restore: `docker exec mongodb mongodump --db admin --archive > backup.archive`. Verified backups live in `~/Documents/Shvarts_backups/`.

## Architecture

**Data pipeline (one-way):** TEI XML files in `static/data/` (one per poem, with `teiHeader` bibliography metadata) → parsed by `Shvarts_MongoDB_main.ipynb` → MongoDB collections → **`scripts/build_search_index.py` must be rerun after any re-ingest** (it builds the `search_lemmas` field and the text index). The XML files are the source of truth for corpus changes; the app only reads Mongo.

**MongoDB layout:** poems split by decade of writing into collections `Shvarts_60/70/80/90/20` (=2000s). Queries iterate all `Shvarts*` collections and merge in Python (the corpus is small; this is fine). Document fields that matter:
- `ID` (int) — app-level key used in all URLs; unique across collections
- `poem_text` — plain text with newlines (cycles: HTML rendered via `Markup`)
- `genre` — `"cycle"` gets whole-cycle rendering
- `meta.date_written` — int year or a string containing one (`written_year()` parses)
- `meta.edition` — free-text bibliography string; edition pages match it by substring via the `EDITIONS` dict in app.py
- `root` / `children` — variant linkage: `root: []` = canonical; non-empty `root` points to the canonical doc; canonical's `children` lists its variants' `_id`s. Powers the comparison view and variant-aware search
- `search_lemmas` — generated; all pymorphy2 normal forms of the text's words, ё→е-normalized, text-indexed with language `none`

**Search** (`search_poems` in app.py): queries are lemmatized with pymorphy2 (same dictionary logic as the index), so гора matches горы but not горит, homonyms keep all readings, шёл finds идти. All documents are searched, variants included; hits fold into their canonical poem, and variant lines that don't occur in the canonical text render with «— в варианте: <edition>». KWIC lines (up to 3 + counter) highlight hits via the shared `word_lemmas()`. Year filter validates against `YEAR_MIN/YEAR_MAX` (1962–2010) — out-of-range shows a styled error (JS popup + server-rendered fallback).

**Routes:** `/list_of_texts/` (catalog: `q`, `year_from`, `year_to`, `edition`, `page` GET params — citable URLs, no JS required), `/texts_<ID>/`, `/edition/<slug>/` + `/edition/<slug>/text_<ID>/` (driven by `EDITIONS`; pre-2026 per-edition URLs 301-redirect — keep those, they're cited), `/comparison_<ID>/`, plus static pages. `/contrib/` builds its photo grid by scanning `static/photo` (NN.jpg thumb ↔ 0NN.jpg full pairs).

**Frontend:** one stylesheet (`static/css/shvarts.css`, design tokens at the top: warm paper palette, wine accent), two fonts (EB Garamond = literature, PT Mono = apparatus/UI — keep this two-voice rule), one small `static/js/site.js` (comparison diff, gallery lightbox, year-validation popup; everything else works without JS). No Bootstrap, no jQuery. The Оглавление drawer on edition pages is a native `<details>` overlay.

## Modernization status (2026)

Phases 0–3 are **done**: slim deps, env-var DB config, consolidated routes/templates, 404s, test suite, full redesign (typography, search+filters, drawer, galleries, comparison), legacy frontend stack deleted.

**Phase 4 (pending): deploy.** Blocked on recovering SSH/DigitalOcean console access to the droplet; its mongod is down (production DB pages 500). Deploy steps when access returns: restore DB from backup (or re-dump local), run `scripts/build_search_index.py` there, install slim requirements, set `MONGO_URI`/`MONGO_DB` for uWSGI, deploy code, rotate the old leaked Mongo password (it's in git history).

## Gotchas

- Old MongoDB credentials are burned into git history; rotate before ever re-exposing Mongo publicly.
- Rerun `scripts/build_search_index.py` after any corpus change, or search silently misses new/edited texts.
- Poem rendering relies on `<pre>`/preserved whitespace; line breaks are semantically significant (it's poetry). `pre-wrap` is set so long lines wrap.
- The error message for out-of-range years exists in two places by design (app.py `YEAR_ERROR` for no-JS, site.js for the popup) — keep the wording in sync.
