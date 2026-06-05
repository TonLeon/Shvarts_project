"""Build the lemmatized search fields and the full-text index.

Search must cover titles as well as poem texts, ignore case, match
declensions without over-matching (гора must find горы/гор but NOT
горит, which merely shares a stem), treat ё/е as the same letter, and
keep genuine homonyms (горе finds both горе and гора — both readings
are real). A stemmer can't do this; pymorphy2 lemmatization can: every
token is replaced by the set of its possible dictionary forms.

Each document gets a search_lemmas field — all normal forms of all
words in title/head/epigraph/dedication/poem_text, ё→е-normalized —
indexed with default_language 'none' (lemmas need no further stemming).
Queries are lemmatized the same way in app.py.

Run after any corpus re-ingest from the notebook:
    python scripts/build_search_index.py
"""
import os
import re

import pymongo
import pymorphy2

client = pymongo.MongoClient(os.environ.get('MONGO_URI', 'mongodb://localhost:27017'))
db = client[os.environ.get('MONGO_DB', 'admin')]

morph = pymorphy2.MorphAnalyzer()
WORD = re.compile(r'[А-Яа-яЁёA-Za-z-]+')


def normalize(s):
    return (s or '').replace('ё', 'е').replace('Ё', 'Е')


def lemmas_of(text):
    out = set()
    for word in WORD.findall(text or ''):
        for parse in morph.parse(word.lower()):
            out.add(normalize(parse.normal_form))
    return out


for name in db.list_collection_names():
    if not name.startswith('Shvarts'):
        continue
    collection = db[name]
    updated = 0
    for doc in collection.find({}, {'title': 1, 'head': 1, 'epigraph': 1,
                                    'dedication': 1, 'poem_text': 1}):
        parts = ' '.join(doc.get(f) or '' for f in
                         ('title', 'head', 'epigraph', 'dedication', 'poem_text'))
        collection.update_one(
            {'_id': doc['_id']},
            {'$set': {'search_lemmas': ' '.join(sorted(lemmas_of(parts)))}})
        updated += 1

    # Replace any previous text index with one over the lemma field.
    for index_name, info in collection.index_information().items():
        if '_fts' in dict(info['key']):
            collection.drop_index(index_name)
    collection.create_index([('search_lemmas', 'text')],
                            default_language='none',
                            name='search_lemmas_text')
    print(f'{name}: {updated} docs, index rebuilt')

print('done')
