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


@pytest.mark.parametrize('url', [
    '/show_all_poems',
    '/filter_poems_by_period_sixties',
    '/filter_poems_by_period_seventies',
    '/filter_poems_by_period_eighties',
    '/filter_poems_by_period_nineties',
    '/filter_poems_by_period_millenial',
])
def test_json_endpoints(client, url):
    response = client.get(url)
    assert response.status_code == 200
    assert isinstance(response.get_json()['result'], list)
    assert len(response.get_json()['result']) > 0


def test_search(client):
    response = client.get('/background_process?search=луна')
    assert response.status_code == 200
    assert isinstance(response.get_json()['result'], list)


def test_empty_search_returns_no_results(client):
    response = client.get('/background_process?search=')
    assert response.status_code == 200
    assert response.get_json()['result'] == []


@pytest.mark.parametrize('url', [
    '/texts_999999/',
    '/comparison_999999/',
    '/edition/no_such_edition/',
    '/edition/zel_tet/text_999999/',
])
def test_unknown_resources_404(client, url):
    assert client.get(url).status_code == 404
