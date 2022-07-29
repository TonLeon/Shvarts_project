from flask import Flask, render_template, request, jsonify
import pymongo
import json
import re

app = Flask(__name__)
def get_poems_titles():
    client = pymongo.MongoClient('mongodb://admin:solaerice@142.93.242.162')
    db = client['admin']
    all_collections = db.list_collection_names()
    
    all_titles = []
    all_duplicates = []
    all_non_dup_id_2_next_nondup = {}
    all_non_dup_id_2_previous_nondup = {}
    
    for collection in all_collections:
        if collection.startswith('Shvarts'):
            collection = db['{}'.format(collection)]
            titles = [title for title in collection.find({"root": []})]
            all_titles = all_titles + titles
            
            duplicates = [title for title in collection.find({"root": {'$ne':[]}})]
            all_duplicates = all_duplicates + duplicates
            
    titles = sorted(all_titles, key = lambda x: x['meta']['date_written'] if isinstance(x['meta']['date_written'], int) 
       else int(re.findall('\d{4}', str(x['meta']['date_written']))[0]))
            
    non_dup_id_2_next_nondup = {titles[i]['ID']: titles[i + 1]['ID'] for i in range(len(titles) - 1)}
    all_non_dup_id_2_next_nondup.update(non_dup_id_2_next_nondup)

    non_dup_id_2_previous_nondup = {titles[i]['ID']: titles[i - 1]['ID'] for i in range(1, len(titles))}
    all_non_dup_id_2_previous_nondup.update(non_dup_id_2_previous_nondup)
            
    return all_titles, all_duplicates, all_non_dup_id_2_next_nondup, all_non_dup_id_2_previous_nondup


def get_poems_texts(ID):
    client = pymongo.MongoClient('mongodb://admin:solaerice@142.93.242.162')
    db = client['admin']
    all_collections = db.list_collection_names()
    
    all_counts = []
    all_poem_texts = []
    all_duplicates = []
    
    
    for collection in all_collections:
        if collection.startswith('Shvarts'):
            collection = db['{}'.format(collection)]
            count = collection.count_documents({})
            all_counts.append(count)
            
            poem_texts = [text for text in collection.find({"poem_text": {"$exists": True}, "ID":ID})] #вот тут словарь в списке
            all_poem_texts = all_poem_texts + poem_texts
            
            duplicates = [title for title in collection.find({"root": {'$ne':[]}})]
            all_duplicates = all_duplicates + duplicates
            
    return all_poem_texts, all_duplicates, all_counts 


# Для сборников

def get_collection_titles(name_of_db):
    client = pymongo.MongoClient('mongodb://admin:solaerice@142.93.242.162')
    db = client['admin']
    collection= db[name_of_db]
    titles = [title for title in collection.find({"root": []})]
    duplicates = [title for title in collection.find({"root": {'$ne':[]}})]
    non_dup_id_2_next_nondup = {titles[i]['ID']: titles[i + 1]['ID'] for i in range(len(titles) - 1)}
    non_dup_id_2_previous_nondup = {titles[i]['ID']: titles[i - 1]['ID'] for i in range(1, len(titles))}
    return titles, duplicates, non_dup_id_2_next_nondup, non_dup_id_2_previous_nondup


def get_collection_texts(ID, name_of_db):
    client = pymongo.MongoClient('mongodb://admin:solaerice@142.93.242.162')
    db = client['admin']
    collection = db[name_of_db]
    count = collection.count_documents({})
    poem_texts = [text for text in collection.find({"poem_text": {"$exists": True}, "ID":ID})] #вот тут словарь в списке
    duplicates = [title for title in collection.find({"root": {'$ne':[]}})]
    return poem_texts, duplicates, count 

# Функция для поиска по всем коллекциям
def search_result(word):
    client = pymongo.MongoClient('mongodb://admin:solaerice@142.93.242.162')
    db = client['admin']
    all_collections = db.list_collection_names()
    
    all_texts = []
    
    for collection in all_collections:
        if collection.startswith('Shvarts'):
            collection = db['{}'.format(collection)]
            texts_in_collection = [text for text in collection.find({"$text": {"$search": word}, "root": []}, 
                     projection={'_id':False}).sort('meta.date_written')]
            all_texts = all_texts + texts_in_collection

    poems = []

    for text in all_texts:
        lst = []
        lst.append(text.get('ID'))
        lst.append(text.get('title'))
        lst.append(text.get('meta').get('edition'))
        lst.append(text.get('meta').get('date_written'))
        poems.append(lst)

    return sorted(poems, key=lambda x: x[1])

# Вывод всех текстов
def show_all_poems():
    client = pymongo.MongoClient('mongodb://admin:solaerice@142.93.242.162')
    db = client['admin']
    all_collections = db.list_collection_names()
    
    all_texts = []
    
    for collection in all_collections:
        if collection.startswith('Shvarts'):
            collection = db['{}'.format(collection)]
            for text in collection.find({"root": []}).sort('meta.date_written', pymongo.ASCENDING):
                all_texts.append(text)

    poems = []

    for text in all_texts:
        lst = []
        lst.append(text.get('ID'))
        lst.append(text.get('title'))
        lst.append(text.get('meta').get('date_written'))
        poems.append(lst)
        
    poems = sorted(poems, key=lambda x: x[2] if isinstance(x[2], int) else int(re.findall('\d{4}', str(x[2]))[0]))

    return poems

#Функция для фильтрации стихов на странице произведений по десятилетиям
def filter_poems_by_year(name_of_db, start_year, end_year):
    client = pymongo.MongoClient('mongodb://admin:solaerice@142.93.242.162')
    db = client['admin']
    collection = db[name_of_db]
    texts_of_exact_period = []
    for text in collection.find({'meta.date_written':{'$gte':start_year, '$lte':end_year}, "root": []}).sort('meta.date_written', pymongo.ASCENDING):
        texts_of_exact_period.append(text)

    poems = []

    for text in texts_of_exact_period:
        lst = []
        lst.append(text.get('ID'))
        lst.append(text.get('title'))
        lst.append(text.get('meta').get('date_written'))
        poems.append(lst)

    return poems

@app.route('/')
def base():
    return render_template('index.html', page_name="shvarts")

@app.route('/about/')
def index():
    return render_template('index.html', page_name='project')

# Выведение названия стихов на странце произведений
@app.route('/list_of_texts/')
def get_list_of_texts():
	titles, duplicates, _, _ = get_poems_titles()
	return render_template('titles.html', page_name='list_of_texts', 
							titles=titles, duplicates=duplicates)

# Выведение текста произведения после нажатия
@app.route('/texts_<int:ID>/')
def get_text_sixties(ID):
    _, _, non_dup_id_2_next_nondup, non_dup_id_2_previous_nondup = get_poems_titles()
    previous_id = non_dup_id_2_previous_nondup[ID] if ID in non_dup_id_2_previous_nondup.keys() else None
    next_id = non_dup_id_2_next_nondup[ID] if ID in non_dup_id_2_next_nondup.keys() else None
    poem_texts, duplicates, _ = get_poems_texts(ID)
    return render_template('text.html', page_name='texts', 
							poem_texts=poem_texts, duplicates=duplicates, next_id=next_id, previous_id=previous_id)

@app.route('/show_all_poems')
def all_poems():
    try:
        result = show_all_poems()
        return jsonify(result=result)
    except Exception as e:
        return str(e)


# Фильтрация 60-х годов
@app.route('/filter_poems_by_period_sixties')
def filter_poems_sixties():
    try:
        result = filter_poems_by_year('Shvarts_60', 1960, 1969)
        return jsonify(result=result)
    except Exception as e:
        return str(e)


# Фильтрация 80-х годов
@app.route('/filter_poems_by_period_eighties')
def filter_poems_eighties():
    try:
        result = filter_poems_by_year('Shvarts_80', 1980, 1989)
        return jsonify(result=result)
    except Exception as e:
        return str(e)

# Фильтрация 90-х годов
@app.route('/filter_poems_by_period_nineties')
def filter_poems_nineties():
    try:
        result = filter_poems_by_year('Shvarts_90', 1990, 1999)
        return jsonify(result=result)
    except Exception as e:
        return str(e)

# Печатные издания

@app.route('/printed_edition/') #сейчас это работает только для Зеленой тетради
def get_list_of_texts_from_printed_editions():
	titles, duplicates, _, _ = get_collection_titles('Shvarts_ZT')
	return render_template('printed_edition.html', page_name='texts_from_printed_editions', 
							titles=titles, duplicates=duplicates)

@app.route('/texts_ZT_<int:ID>/')
def get_ZT_text(ID):
    poem_texts, duplicates, count = get_collection_texts(ID, 'Shvarts_ZT')
    titles, _, _, _ = get_collection_titles('Shvarts_ZT')
    return render_template('text_from_printed_edition.html', page_name='texts', 
							poem_texts=poem_texts, duplicates=duplicates, count=count, titles=titles)

# Поиск
@app.route('/background_process', methods=['GET', 'POST', 'DELETE', 'PATCH'])
def background_process():
    try:
        word = request.args.get('search', 'text', type=str)
        result = search_result(word)
        print(result)
        return jsonify(result=result)
    except Exception as e:
        return str(e)

#Фотоархив
@app.route('/contrib/')
def photos():
    return render_template('contrib.html', page_name='photos')

#Пустая страница
@app.route('/other/')
def other():
    return render_template('other.html', page_name='other')

#Библиотека
@app.route('/bibl/')
def bibl():
    return render_template('bibl.html', page_name="bibl")

# Сравнение текстов
@app.route('/comparison_<int:ID>/')
def compare_poems(ID):
    poem_texts, duplicates, _ = get_poems_texts(ID)
    return render_template('comparison.html', poem_texts=poem_texts, duplicates=duplicates)

#Что-то непонятное
@app.route('/trial/')
def trial():
    return render_template('trial.html', page_name="trial")

if __name__=='__main__':
	app.run(debug=True)