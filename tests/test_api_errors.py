"""
test_api_errors.py - Automated Tests for Error Handling, Validation, and Safety

Tests Covered:
1. Reject unauthenticated queries with 401.
2. Reject completely empty queries with 400.
3. Handle weather fetching gracefully with fallback simulation.
4. Verify agricultural advisory safety disclaimer is always appended.
5. Verify 404 on accessing non-existent conversation.
"""

from backend.ai_service import AGRICULTURAL_DISCLAIMER


def test_unauthenticated_query_rejected(client):
    """Test that requests from unauthenticated clients return 401."""
    res = client.post('/api/query', json={'query': 'How to control aphids?'})
    assert res.status_code == 401
    data = res.get_json()
    assert data['success'] is False
    assert 'Please log in' in data['error']


def test_empty_query_rejected(auth_client):
    """Test that queries with neither text nor image are rejected with 400."""
    res = auth_client.post('/api/query', json={'query': '   '})
    assert res.status_code == 400
    data = res.get_json()
    assert data['success'] is False
    assert 'Please provide a question' in data['error']


def test_weather_endpoint_fallback(client):
    """Test that weather endpoint returns valid structured data even without external API key."""
    res = client.get('/api/weather?city=Jaipur,IN')
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert 'temperature_c' in data
    assert 'humidity_pct' in data
    assert 'advisory' in data
    assert isinstance(data['is_simulated'], bool)


def test_advisory_contains_mandatory_disclaimer(auth_client):
    """Verify that every AI response includes the agricultural safety disclaimer."""
    res = auth_client.post('/api/query', json={
        'query': 'What is the dosage of urea fertilizer for wheat crop?'
    })
    assert res.status_code == 200
    data = res.get_json()
    ai_text = data['assistant_message']['text']
    # Must contain warning keywords
    assert "Agricultural Advisory Disclaimer" in ai_text
    assert "Krishi Vigyan Kendra" in ai_text


def test_nonexistent_conversation_returns_404(auth_client):
    """Test that requesting an invalid or deleted conversation ID returns 404."""
    res = auth_client.get('/api/conversations/99999')
    assert res.status_code == 404
    data = res.get_json()
    assert data['success'] is False
