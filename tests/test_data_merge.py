from app.data_sources.calendar import CalendarSource
from app.data_sources.news import NewsSource


def test_news_merge_appends_and_deduplicates():
    source = NewsSource('news', 'latest')
    previous = {
        'items': [
            {'url': 'https://example/old', 'title': 'Old', 'summary': 'keep me'},
            {'url': 'https://example/same', 'title': 'Same', 'summary': 'old summary', 'editorial': 'keep'},
        ]
    }
    fetched = {
        'items': [
            {'url': 'https://example/new', 'title': 'New'},
            {'url': 'https://example/same', 'title': 'Same updated', 'summary': 'fresh summary'},
        ],
        'available': True,
    }
    merged = source.merge_payload(previous, fetched)
    assert [item['url'] for item in merged['items']] == [
        'https://example/new',
        'https://example/same',
        'https://example/old',
    ]
    same = next(item for item in merged['items'] if item['url'] == 'https://example/same')
    assert same['summary'] == 'fresh summary'
    assert same['editorial'] == 'keep'


def test_calendar_merge_keeps_missing_old_event_and_updates_existing():
    source = CalendarSource('calendar', 'events')
    previous = {
        'items': [
            {'url': 'https://event/1', 'title': 'Event 1', 'start_date': '2026-09-12', 'note': 'keep'},
            {'url': 'https://event/old', 'title': 'Old event', 'start_date': '2026-09-10'},
        ]
    }
    fetched = {
        'items': [
            {'url': 'https://event/1', 'title': 'Event 1 updated', 'start_date': '2026-09-12'},
            {'url': 'https://event/2', 'title': 'Event 2', 'start_date': '2026-09-13'},
        ],
        'available': True,
    }
    merged = source.merge_payload(previous, fetched)
    urls = {item['url'] for item in merged['items']}
    assert urls == {'https://event/1', 'https://event/2', 'https://event/old'}
    one = next(item for item in merged['items'] if item['url'] == 'https://event/1')
    assert one['title'] == 'Event 1 updated'
    assert one['note'] == 'keep'
