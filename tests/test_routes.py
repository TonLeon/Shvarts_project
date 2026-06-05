"""Route smoke tests. Require the local MongoDB to be running
(docker start mongodb) — see CLAUDE.md."""
import pytest

from app import app, EDITIONS, get_files_by_edition, get_poems_titles


@pytest.fixture
def client():
    app.testing = True
    with app.test_client() as c:
        yield c


@pytest.mark.parametrize('url', ['/', '/about/', '/contrib/', '/other/', '/bibl/', '/trial/'])
def test_static_pages(client, url):
    assert client.get(url).status_code == 200


def test_list_of_texts(client):
    response = client.get('/list_of_texts/')
    assert response.status_code == 200


def test_poem_page(client):
    titles, _, _, _ = get_poems_titles()
    ID = titles[0]['ID']
    response = client.get('/texts_{}/'.format(ID))
    assert response.status_code == 200
    assert titles[0]['title'].encode() in response.data


def test_comparison_page(client):
    titles, _, _, _ = get_poems_titles()
    assert client.get('/comparison_{}/'.format(titles[0]['ID'])).status_code == 200


@pytest.mark.parametrize('slug', sorted(EDITIONS))
def test_edition_index(client, slug):
    response = client.get('/edition/{}/'.format(slug))
    assert response.status_code == 200
    assert EDITIONS[slug]['title'].encode() in response.data


@pytest.mark.parametrize('slug', sorted(EDITIONS))
def test_edition_text_page(client, slug):
    files, _, _, _, count = get_files_by_edition(EDITIONS[slug]['match'])
    assert count > 0, 'edition {} matches no poems'.format(slug)
    response = client.get('/edition/{}/text_{}/'.format(slug, files[0]['ID']))
    assert response.status_code == 200


@pytest.mark.parametrize('slug', sorted(EDITIONS))
def test_legacy_edition_urls_redirect(client, slug):
    response = client.get('/{}/'.format(slug))
    assert response.status_code == 301
    assert response.headers['Location'].endswith('/edition/{}/'.format(slug))

    response = client.get('/{}_text_5/'.format(slug))
    assert response.status_code == 301
    assert response.headers['Location'].endswith('/edition/{}/text_5/'.format(slug))


def result_ids(poems):
    return {p['ID'] for p in poems}


def test_search_finds_titles_and_texts(client):
    from app import search_poems
    # by title, declined form
    assert 'мигрени'.encode() in client.get('/list_of_texts/?q=мигрень').data.lower()
    assert 'Найдено'.encode() in client.get('/list_of_texts/?q=мигрень').data
    # case-insensitive + declension: ДЕРЕВО finds деревьев
    assert result_ids(search_poems('ДЕРЕВО')) == result_ids(search_poems('деревьев'))


def test_search_treats_yo_and_ye_alike():
    from app import search_poems
    assert result_ids(search_poems('чёрный')) == result_ids(search_poems('черный'))
    assert result_ids(search_poems('слёзы')) == result_ids(search_poems('слезы'))


def test_lemmas_not_stems():
    from app import query_lemmas
    # гора and горит share a stem but no lemma — must not cross-match
    assert not query_lemmas('гора') & query_lemmas('горит')
    # the homonym горе legitimately covers both горе and гора
    assert {'горе', 'гора'} <= query_lemmas('горе')
    # suppletive verb forms resolve to one lemma
    assert query_lemmas('шёл') & query_lemmas('идти')


def test_year_filter(client):
    from app import search_poems
    poems = search_poems(year_from=1970, year_to=1979)
    assert poems
    assert all(1970 <= p['year'] <= 1979 for p in poems)
    response = client.get('/list_of_texts/?year_from=1970&year_to=1979')
    assert response.status_code == 200
    assert str(len(poems)).encode() in response.data


def test_edition_filter(client):
    from app import search_poems
    for slug in EDITIONS:
        assert search_poems(edition_slug=slug), 'edition filter {} empty'.format(slug)
    assert client.get('/list_of_texts/?edition=zel_tet').status_code == 200


def test_search_no_results_message(client):
    response = client.get('/list_of_texts/?q=кзылординский')
    assert 'ничего не найдено'.encode() in response.data


def test_search_shows_kwic_snippet(client):
    response = client.get('/list_of_texts/?q=дерево')
    assert b'<mark>' in response.data


def test_search_covers_variants_with_edition_note(client):
    # «томная вода» exists only in the Звезда 2001 variant of
    # «Антропологическое страноведение», not in its canonical text
    from app import search_poems
    hits = [p for p in search_poems('томная') if p.get('variants')]
    assert hits, 'variant-only hit not surfaced'
    assert any('Звезда' in v['edition'] for p in hits for v in p['variants'])
    assert 'в варианте'.encode() in client.get('/list_of_texts/?q=томная').data


def test_pagination(client):
    page1 = client.get('/list_of_texts/?page=1')
    page2 = client.get('/list_of_texts/?page=2')
    assert page1.status_code == page2.status_code == 200
    assert page1.data != page2.data
    assert 'aria-label="Страницы списка"'.encode() in page1.data
    # out-of-range pages clamp instead of erroring
    assert client.get('/list_of_texts/?page=999').status_code == 200


@pytest.mark.parametrize('url', [
    '/texts_999999/',
    '/comparison_999999/',
    '/edition/no_such_edition/',
    '/edition/zel_tet/text_999999/',
])
def test_unknown_resources_404(client, url):
    assert client.get(url).status_code == 404
