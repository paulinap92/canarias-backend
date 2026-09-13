from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def test_places_get_local_shape():
    r=client.get('/api/regions/canarias/places?island=tenerife'); assert r.status_code==200; d=r.json(); assert d['type']=='FeatureCollection' and 'status' in d
def test_generic_reads_same_snapshot():
    a=client.get('/api/regions/canarias/places?island=tenerife').json(); b=client.get('/api/regions/canarias/data/explore/places?island=tenerife').json(); assert a['features']==b['features']
def test_news_get_local(): assert isinstance(client.get('/api/regions/canarias/news').json(),list)
def test_calendar_get_local():
    d=client.get('/api/regions/canarias/events?island=tenerife&month=2026-09').json(); assert d['island']=='tenerife' and 'items' in d
def test_live_get_local(): assert 'status' in client.get('/api/regions/canarias/live/weather?island=tenerife').json()

def test_seeded_tenerife_places_are_not_empty():
    data = client.get('/api/regions/canarias/places?island=tenerife&limit=500').json()
    assert data['features']
    assert any(f.get('properties', {}).get('category') in {'town', 'village'} for f in data['features'])


def test_seeded_tenerife_beaches_are_not_empty():
    data = client.get('/api/regions/canarias/beaches?island=tenerife&limit=300').json()
    assert data['features']


def test_empty_weather_snapshot_keeps_frontend_compatible_points_shape():
    data = client.get('/api/regions/canarias/live/weather?island=tenerife').json()
    assert isinstance(data.get('points'), list)
    assert 'status' in data


def test_empty_air_quality_snapshot_keeps_frontend_compatible_points_shape():
    data = client.get('/api/regions/canarias/live/air-quality?island=tenerife').json()
    assert isinstance(data.get('points'), list)


def test_empty_tides_snapshot_keeps_frontend_compatible_points_shape():
    data = client.get('/api/regions/canarias/live/tides?island=tenerife').json()
    assert isinstance(data.get('points'), list)


def test_flora_is_exposed_and_capability_is_enabled():
    flora = client.get('/api/regions/canarias/flora?island=tenerife').json()
    caps = client.get('/api/regions/canarias/islands/tenerife/capabilities').json()
    assert flora['type'] == 'FeatureCollection'
    assert caps['features']['flora'] is True


def test_live_config_files_live_under_live_config_folder():
    from app.services.open_meteo_live import (
        AIR_POINTS_FILE,
        COASTAL_POINTS_FILE,
        WEATHER_POINTS_FILE,
    )
    for path in (WEATHER_POINTS_FILE, AIR_POINTS_FILE, COASTAL_POINTS_FILE):
        assert path.exists()
        assert path.parent.name == 'config'
        assert path.parent.parent.name == 'live'


def test_marine_is_island_snapshot_not_island_centre_point():
    data = client.get('/api/regions/canarias/live/marine?island=tenerife').json()
    assert data['island'] == 'tenerife'
    assert isinstance(data.get('points'), list)
    assert 'latitude' not in data
    assert 'longitude' not in data


def test_tenerife_marine_config_uses_multiple_coastal_points():
    import json
    from app.services.open_meteo_live import COASTAL_POINTS_FILE
    points = [p for p in json.loads(COASTAL_POINTS_FILE.read_text(encoding='utf-8')) if p['island'] == 'tenerife']
    assert len(points) >= 4
    teide = (28.2724, -16.6425)
    assert all((round(float(p['latitude']), 4), round(float(p['longitude']), 4)) != teide for p in points)


def test_news_uses_official_portada_feed():
    from app.services.news import NEWS_RSS_URL
    assert NEWS_RSS_URL == 'https://www3.gobiernodecanarias.org/noticias/feed'
