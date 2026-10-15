"""
auth.py - Authentication and User Security Module

Beginner-Friendly Explanation:
Storing passwords in plain text is a serious security vulnerability.
If an attacker accesses the database, they could steal everyone's password.
Instead, we use "one-way hashing" with a random salt via werkzeug.security:
1. When a user registers:
   password -> generate_password_hash(password) -> $scrypt$... or $pbkdf2$...
2. When a user logs in:
   check_password_hash(stored_hash, candidate_password) -> True or False
The original password can never be recovered from the hash.

This module also manages user sessions (logging in and logging out)
using Flask's tamper-proof signed session cookies.
"""

from functools import wraps
from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from backend.database import create_user, get_user_by_username, get_user_by_id

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


def login_required(f):
    """
    Decorator to protect routes that require a logged-in farmer.
    If the user has not logged in, returns a 401 Unauthorized JSON response.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({
                'success': False,
                'error': 'Authentication required. Please log in first.'
            }), 401
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Registers a new farmer account.
    Expects JSON: { "username": "...", "password": "...", "full_name": "...", "location": "..." }
    """
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip().lower()
    password = data.get('password') or ''
    full_name = (data.get('full_name') or '').strip()
    location = (data.get('location') or 'Delhi,IN').strip()

    # Validation: Check required fields
    if not username:
        return jsonify({'success': False, 'error': 'Username is required.'}), 400
    if len(username) < 3 or len(username) > 30:
        return jsonify({'success': False, 'error': 'Username must be between 3 and 30 characters.'}), 400
    if not username.replace('_', '').isalnum():
        return jsonify({'success': False, 'error': 'Username can only contain letters, numbers, and underscores.'}), 400

    if not password:
        return jsonify({'success': False, 'error': 'Password is required.'}), 400
    if len(password) < 6:
        return jsonify({'success': False, 'error': 'Password must be at least 6 characters long.'}), 400

    if not full_name:
        return jsonify({'success': False, 'error': 'Full name is required.'}), 400

    # Check if username is already taken
    existing = get_user_by_username(username)
    if existing:
        return jsonify({'success': False, 'error': f'Username "{username}" is already taken. Please choose another.'}), 409

    # Hash the password securely
    password_hash = generate_password_hash(password, method='scrypt')

    try:
        user_id = create_user(
            username=username,
            password_hash=password_hash,
            full_name=full_name,
            location=location
        )
    except Exception as e:
        return jsonify({'success': False, 'error': f'Failed to create account: {str(e)}'}), 500

    # Automatically log the user in by populating Flask session
    session['user_id'] = user_id
    session['username'] = username
    session['full_name'] = full_name
    session['location'] = location

    return jsonify({
        'success': True,
        'message': f'Welcome, {full_name}! Your account has been registered.',
        'user': {
            'id': user_id,
            'username': username,
            'full_name': full_name,
            'location': location
        }
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Logs in an existing farmer.
    Expects JSON: { "username": "...", "password": "..." }
    """
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip().lower()
    password = data.get('password') or ''

    if not username or not password:
        return jsonify({'success': False, 'error': 'Both username and password are required.'}), 400

    user = get_user_by_username(username)
    if not user:
        # Use generic error message to prevent user enumeration
        return jsonify({'success': False, 'error': 'Invalid username or password.'}), 401

    # Verify password against stored hash
    if not check_password_hash(user['password_hash'], password):
        return jsonify({'success': False, 'error': 'Invalid username or password.'}), 401

    # Populate session
    session['user_id'] = user['id']
    session['username'] = user['username']
    session['full_name'] = user['full_name']
    session['location'] = user['location']

    return jsonify({
        'success': True,
        'message': f'Welcome back, {user["full_name"]}!',
        'user': {
            'id': user['id'],
            'username': user['username'],
            'full_name': user['full_name'],
            'location': user['location']
        }
    }), 200


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Clears the active farmer session."""
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully.'}), 200


@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    """Returns currently authenticated farmer details or null if unauthenticated."""
    if 'user_id' not in session:
        return jsonify({'authenticated': False, 'user': None}), 200

    user = get_user_by_id(session['user_id'])
    if not user:
        session.clear()
        return jsonify({'authenticated': False, 'user': None}), 200

    return jsonify({
        'authenticated': True,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'full_name': user['full_name'],
            'location': user['location']
        }
    }), 200
