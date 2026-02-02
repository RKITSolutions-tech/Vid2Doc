def test_purge_modal_present():
    from app import app
    client = app.test_client()
    r = client.get('/audio-failures')
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert 'open-purge-modal' in html
    assert 'purge-modal' in html
    assert 'purge-form' in html
