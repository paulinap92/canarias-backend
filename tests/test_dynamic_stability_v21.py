from fastapi.testclient import TestClient

from app.main import app
from app.services.volcanic import parse_volcanic_reports

client = TestClient(app)


def test_seismic_declares_ten_day_window_and_source():
    data = client.get('/api/regions/canarias/seismic?island=tenerife').json()
    assert data['window_days'] == 10
    assert data['source'] == 'IGN'
    assert 'get10dias' in data['source_url']


def test_alerts_endpoint_can_be_scoped_to_island_snapshot():
    response = client.get('/api/regions/canarias/alerts?island=tenerife')
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_volcanic_parser_keeps_multiple_reports():
    html = '''
    <h3>Julio 2026</h3>
    <h2><a href="/julio">Actividad volcánica en Canarias</a></h2>
    <p>Durante el mes se han localizado un total de 724 terremotos. La magnitud máxima fue 3,5.</p>
    <p>No muestran deformaciones significativas del terreno.</p>
    <h3>Junio 2026</h3>
    <h2><a href="/junio">Actividad volcánica en Canarias</a></h2>
    <p>Durante el mes se han localizado un total de 474 terremotos. La magnitud máxima fue 3,8.</p>
    '''
    reports = parse_volcanic_reports(html)
    assert len(reports) == 2
    assert reports[0]['period'] == 'Julio 2026'
    assert reports[0]['earthquakes_total'] == 724
    assert reports[0]['max_magnitude'] == 3.5
    assert reports[0]['significant_deformation_detected'] is False
    assert reports[1]['period'] == 'Junio 2026'


def test_volcanic_uses_one_archipelago_snapshot_for_any_island():
    from app.data_sources.live import VolcanicSource
    source = VolcanicSource('live', 'volcanic')
    assert source.path(island='tenerife').name == 'canarias.json'
    assert source.path(island='gran-canaria').name == 'canarias.json'
