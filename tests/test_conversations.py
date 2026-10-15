"""
test_conversations.py - Automated Tests for Conversation Persistence & Privacy

Tests Covered:
1. Creating consultation conversations.
2. Persisting question and answer message pairs.
3. Fetching message history for a conversation thread.
4. Privacy isolation: User A cannot read or delete User B's consultations.
5. Deleting a conversation cascades deletion to its messages.
"""

from backend.database import get_conversation_messages


def test_conversation_flow(auth_client):
    """Test full query-response flow and history persistence."""
    # 1. Ask first question
    res1 = auth_client.post('/api/query', json={
        'query': 'How much water does wheat crop need during flowering stage?'
    })
    assert res1.status_code == 200
    data1 = res1.get_json()
    conv_id = data1['conversation_id']
    assert conv_id is not None

    # 2. Ask follow-up question in the same conversation
    res2 = auth_client.post('/api/query', json={
        'query': 'What if the temperature suddenly rises?',
        'conversation_id': conv_id
    })
    assert res2.status_code == 200

    # 3. Retrieve conversation history
    res_history = auth_client.get(f'/api/conversations/{conv_id}')
    assert res_history.status_code == 200
    history_data = res_history.get_json()
    assert history_data['success'] is True
    # Should have 4 messages: 2 from user, 2 from assistant
    assert len(history_data['messages']) == 4
    assert history_data['messages'][0]['sender'] == 'user'
    assert history_data['messages'][1]['sender'] == 'assistant'


def test_conversation_privacy_isolation(client):
    """Test that conversations are strictly private to the user who created them."""
    # Register Farmer A
    client.post('/api/auth/register', json={
        'username': 'farmer_a',
        'password': 'Password123',
        'full_name': 'Farmer A'
    })
    # Farmer A asks question
    res_a = client.post('/api/query', json={'query': 'Farmer A secret crop question'})
    conv_id_a = res_a.get_json()['conversation_id']

    # Logout Farmer A
    client.post('/api/auth/logout')

    # Register Farmer B
    client.post('/api/auth/register', json={
        'username': 'farmer_b',
        'password': 'Password123',
        'full_name': 'Farmer B'
    })

    # Farmer B attempts to access Farmer A's conversation
    forbidden_res = client.get(f'/api/conversations/{conv_id_a}')
    assert forbidden_res.status_code == 404

    # Farmer B attempts to delete Farmer A's conversation
    del_res = client.delete(f'/api/conversations/{conv_id_a}')
    assert del_res.status_code == 404


def test_delete_conversation(auth_client):
    """Test deleting a conversation removes it and cascades message deletion."""
    res = auth_client.post('/api/query', json={'query': 'Temporary test question'})
    conv_id = res.get_json()['conversation_id']

    # Delete conversation
    del_res = auth_client.delete(f'/api/conversations/{conv_id}')
    assert del_res.status_code == 200
    assert del_res.get_json()['success'] is True

    # Confirm conversation is gone
    check_res = auth_client.get(f'/api/conversations/{conv_id}')
    assert check_res.status_code == 404

    # Confirm messages were cascade deleted from database
    remaining_messages = get_conversation_messages(conv_id)
    assert len(remaining_messages) == 0
