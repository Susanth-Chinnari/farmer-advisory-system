"""
test_auth.py - Automated Tests for Authentication & Password Security

Tests Covered:
1. Register a valid user.
2. Reject duplicate usernames.
3. Reject weak/short passwords (< 6 characters).
4. Verify passwords are cryptographically hashed and never stored as plain text.
5. Successful login with correct credentials.
6. Failed login with wrong password.
7. User session check (/api/auth/me) and logout.
"""

from backend.database import get_user_by_username


def test_register_success(client):
    """Test successful farmer registration."""
    res = client.post('/api/auth/register', json={
        'username': 'rajesh_kumar',
        'password': 'StrongPassword123',
        'full_name': 'Rajesh Kumar',
        'location': 'Punjab,IN'
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data['success'] is True
    assert data['user']['username'] == 'rajesh_kumar'


def test_password_is_hashed_in_database(client):
    """Verify that the database stores a salted cryptographic hash, NOT plain text."""
    plain_password = 'SecretFarmPassword99'
    client.post('/api/auth/register', json={
        'username': 'secure_farmer',
        'password': plain_password,
        'full_name': 'Secure Farmer',
        'location': 'Delhi,IN'
    })

    user_row = get_user_by_username('secure_farmer')
    assert user_row is not None
    # Password must not equal plain text
    assert user_row['password_hash'] != plain_password
    # Password must have hash prefix (e.g. scrypt: or pbkdf2:)
    assert any(user_row['password_hash'].startswith(p) for p in ['scrypt:', 'pbkdf2:'])


def test_register_duplicate_username(client):
    """Test rejection when username is already taken."""
    payload = {
        'username': 'duplicate_user',
        'password': 'Password123',
        'full_name': 'First User'
    }
    res1 = client.post('/api/auth/register', json=payload)
    assert res1.status_code == 201

    # Attempt to register identical username
    res2 = client.post('/api/auth/register', json=payload)
    assert res2.status_code == 409
    data = res2.get_json()
    assert data['success'] is False
    assert 'already taken' in data['error'].lower()


def test_register_short_password(client):
    """Test rejection when password is less than 6 characters."""
    res = client.post('/api/auth/register', json={
        'username': 'short_pwd_user',
        'password': '123',
        'full_name': 'Short Password'
    })
    assert res.status_code == 400
    data = res.get_json()
    assert data['success'] is False
    assert 'at least 6 characters' in data['error']


def test_login_success_and_failure(client):
    """Test login with valid vs invalid passwords."""
    client.post('/api/auth/register', json={
        'username': 'login_tester',
        'password': 'CorrectPassword1',
        'full_name': 'Login Tester'
    })

    # Wrong password
    bad_res = client.post('/api/auth/login', json={
        'username': 'login_tester',
        'password': 'WrongPassword9'
    })
    assert bad_res.status_code == 401

    # Correct password
    good_res = client.post('/api/auth/login', json={
        'username': 'login_tester',
        'password': 'CorrectPassword1'
    })
    assert good_res.status_code == 200
    assert good_res.get_json()['success'] is True


def test_logout_and_session(auth_client):
    """Test /api/auth/me endpoint and logout clearing."""
    me_res = auth_client.get('/api/auth/me')
    assert me_res.status_code == 200
    assert me_res.get_json()['authenticated'] is True

    # Logout
    logout_res = auth_client.post('/api/auth/logout')
    assert logout_res.status_code == 200

    # Check session again
    me_after = auth_client.get('/api/auth/me')
    assert me_after.get_json()['authenticated'] is False
