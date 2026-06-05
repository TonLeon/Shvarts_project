"""Build the search_text field and its full-text index.

Search must cover titles as well as poem texts, ignore case, match
declensions (ДЕРЕВО finds деревьев — Mongo's Russian stemmer does this),
and treat ё/е as the same letter (the corpus mixes both spellings).
Mongo's stemmer handles the first two; ё/е needs normalization, hence
this shadow field.

Run after any corpus re-ingest from the notebook:
    python scripts/build_search_index.py
"""
import os
import pymongo

client = pymongo.MongoClient(os.environ.get('MONGO_URI', 'mongodb://localhost:27017'))
db = client[os.environ.get('MONGO_DB', 'admin')]


def normalize(s):
    return (s or '').replace('ё', 'е').replace('Ё', 'Е')


for name in db.list_collection_names():
    if not name.startswith('Shvarts'):
        continue
    collection = db[name]
    updated = 0
    for doc in collection.find({}, {'title': 1, 'head': 1, 'epigraph': 1,
                                    'dedication': 1, 'poem_text': 1}):
        parts = [doc.get('title'), doc.get('head'), doc.get('epigraph'),
                 doc.get('dedication'), doc.get('poem_text')]
        search_text = normalize(' '.join(p for p in parts if p))
        collection.update_one({'_id': doc['_id']},
                              {'$set': {'search_text': search_text}})
        updated += 1

    # Replace the old poem_text-only index with one over search_text.
    for index_name, info in collection.index_information().items():
        if '_fts' in dict(info['key']):
            collection.drop_index(index_name)
    collection.create_index([('search_text', 'text')],
                            default_language='russian',
                            name='search_text_russian')
    print(f'{name}: {updated} docs, index rebuilt')

print('done')
