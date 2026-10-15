"""
routes.py - Core REST API Endpoints & Request Handling

Beginner-Friendly Explanation:
This file defines the URLs (endpoints) that the frontend connects to.
It validates all incoming data (file uploads, text queries, JSON payloads)
and delegates tasks to the auth, weather, database, and AI modules.
"""

import os
import uuid
from typing import Optional, Tuple, Dict, Any
from flask import Blueprint, request, jsonify, session, send_from_directory, current_app
from werkzeug.utils import secure_filename
from PIL import Image

import backend.config as config
from backend.auth import login_required
from backend.database import (
    create_conversation,
    get_user_conversations,
    get_conversation_by_id,
    update_conversation_title,
    add_message,
    get_conversation_messages,
    delete_conversation,
    get_user_by_id
)
from backend.weather_service import fetch_weather
from backend.ai_service import generate_agricultural_advisory

api_bp = Blueprint('api', __name__, url_prefix='/api')


def _validate_and_save_image(file_obj) -> tuple[Optional[str], Optional[str]]:
    """
    Validates an uploaded image file:
    1. Checks filename and extension against whitelist.
    2. Validates image integrity using Pillow (to block disguised malicious files).
    3. Saves with a cryptographically safe, unique filename.
    Returns: (saved_filename, error_message)
    """
    if not file_obj or file_obj.filename == '':
        return None, None

    raw_filename = file_obj.filename
    if not config.allowed_file(raw_filename):
        return None, "Invalid file format. Allowed formats: PNG, JPG, JPEG, WEBP."

    # Validate actual image content using Pillow
    try:
        # Open and verify file header without decoding the entire image
        img = Image.open(file_obj)
        img.verify()
        # Reset file pointer after verify()
        file_obj.seek(0)
    except Exception:
        return None, "The uploaded file is not a valid or readable image."

    # Create safe unique filename
    safe_base = secure_filename(raw_filename)
    extension = safe_base.rsplit('.', 1)[1].lower() if '.' in safe_base else 'jpg'
    unique_name = f"{uuid.uuid4().hex[:12]}_{safe_base}"
    save_path = os.path.join(str(config.UPLOAD_FOLDER), unique_name)

    try:
        file_obj.save(save_path)
        return unique_name, None
    except Exception as e:
        return None, f"Failed to save uploaded file: {str(e)}"


# ---------------------------------------------------------------------------
# Weather API
# ---------------------------------------------------------------------------
@api_bp.route('/weather', methods=['GET'])
def get_weather():
    """
    Returns current weather data and agricultural suggestions.
    Query parameter: ?city=Delhi,IN (optional)
    """
    user_city = request.args.get('city')
    # If not provided in URL query, check user's saved location in session
    if not user_city and 'user_id' in session:
        user = get_user_by_id(session['user_id'])
        if user and user['location']:
            user_city = user['location']

    weather_data = fetch_weather(user_city or config.DEFAULT_CITY)
    return jsonify(weather_data), 200


# ---------------------------------------------------------------------------
# Farmer Advisory Query API
# ---------------------------------------------------------------------------
@api_bp.route('/query', methods=['POST'])
def process_query():
    """
    Processes a farmer query. Supports text, voice transcript, and image attachment.
    Can be called via multipart/form-data or application/json.
    """
    # 1. Check Authentication (Guest or Logged In)
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({
            'success': False,
            'error': 'Please log in or continue as guest to consult the advisor.'
        }), 401

    # 2. Extract inputs from form-data or JSON
    query_text = ""
    conv_id_raw = None
    city_override = None
    uploaded_file = None

    if request.content_type and 'multipart/form-data' in request.content_type:
        query_text = request.form.get('query', '').strip()
        conv_id_raw = request.form.get('conversation_id')
        city_override = request.form.get('city')
        uploaded_file = request.files.get('image')
    else:
        json_data = request.get_json(silent=True) or {}
        query_text = (json_data.get('query') or '').strip()
        conv_id_raw = json_data.get('conversation_id')
        city_override = json_data.get('city')

    # 3. Validate image upload if present
    saved_image_name = None
    if uploaded_file and uploaded_file.filename:
        saved_image_name, img_err = _validate_and_save_image(uploaded_file)
        if img_err:
            return jsonify({'success': False, 'error': img_err}), 400

    # 4. Check that at least one query component exists
    if not query_text and not saved_image_name:
        return jsonify({
            'success': False,
            'error': 'Please provide a question or upload a plant picture for diagnosis.'
        }), 400

    # 5. Fetch weather context for smarter farming recommendations
    weather_info = fetch_weather(city_override)

    # 6. Retrieve or Create Conversation
    conversation_id = None
    if conv_id_raw:
        try:
            cid = int(conv_id_raw)
            existing_conv = get_conversation_by_id(cid, user_id)
            if existing_conv:
                conversation_id = cid
        except (ValueError, TypeError):
            pass

    if not conversation_id:
        # Generate initial title from query text or image tag
        default_title = query_text[:40] if query_text else "Crop Photo Diagnosis"
        conversation_id = create_conversation(user_id, default_title)

    # 7. Store user message in database
    display_user_text = query_text or "[Uploaded crop photograph for diagnosis]"
    user_msg_id = add_message(
        conversation_id=conversation_id,
        sender='user',
        text=display_user_text,
        image_filename=saved_image_name,
        weather_snapshot=weather_info,
        is_simulated=False
    )

    # 8. Generate AI Response
    ai_result = generate_agricultural_advisory(
        query_text=query_text,
        image_filename=saved_image_name,
        weather_info=weather_info
    )

    if not ai_result.get('success'):
        return jsonify({
            'success': False,
            'error': ai_result.get('error', 'Failed to generate advisory. Please try again.')
        }), 500

    ai_reply_text = ai_result.get('text', '')
    is_simulated = ai_result.get('is_simulated', False)

    # 9. Store assistant message in database
    ai_msg_id = add_message(
        conversation_id=conversation_id,
        sender='assistant',
        text=ai_reply_text,
        image_filename=None,
        weather_snapshot=weather_info,
        is_simulated=is_simulated
    )

    return jsonify({
        'success': True,
        'conversation_id': conversation_id,
        'user_message': {
            'id': user_msg_id,
            'sender': 'user',
            'text': display_user_text,
            'image_filename': saved_image_name,
            'weather_snapshot': weather_info
        },
        'assistant_message': {
            'id': ai_msg_id,
            'sender': 'assistant',
            'text': ai_reply_text,
            'is_simulated': is_simulated,
            'provider': ai_result.get('provider')
        },
        'weather': weather_info
    }), 200


# ---------------------------------------------------------------------------
# Conversation History Management
# ---------------------------------------------------------------------------
@api_bp.route('/conversations', methods=['GET'])
@login_required
def list_conversations():
    """Lists all consultation conversations for the current farmer."""
    user_id = session['user_id']
    conversations = get_user_conversations(user_id)
    return jsonify({'success': True, 'conversations': conversations}), 200


@api_bp.route('/conversations', methods=['POST'])
@login_required
def new_conversation():
    """Creates a new empty consultation thread."""
    user_id = session['user_id']
    data = request.get_json(silent=True) or {}
    title = (data.get('title') or 'New Consultation').strip()
    conv_id = create_conversation(user_id, title)
    return jsonify({'success': True, 'conversation_id': conv_id, 'title': title}), 201


@api_bp.route('/conversations/<int:conversation_id>', methods=['GET'])
@login_required
def get_conversation_history(conversation_id: int):
    """Retrieves all message history for a specific conversation."""
    user_id = session['user_id']
    conv = get_conversation_by_id(conversation_id, user_id)
    if not conv:
        return jsonify({'success': False, 'error': 'Conversation not found.'}), 404

    messages = get_conversation_messages(conversation_id)
    return jsonify({
        'success': True,
        'conversation': dict(conv),
        'messages': messages
    }), 200


@api_bp.route('/conversations/<int:conversation_id>', methods=['DELETE'])
@login_required
def remove_conversation(conversation_id: int):
    """Deletes a conversation and its messages."""
    user_id = session['user_id']
    deleted = delete_conversation(conversation_id, user_id)
    if not deleted:
        return jsonify({'success': False, 'error': 'Conversation not found or already deleted.'}), 404
    return jsonify({'success': True, 'message': 'Conversation deleted successfully.'}), 200


# ---------------------------------------------------------------------------
# Guest Quick-Login Helper for College Demo / Viva
# ---------------------------------------------------------------------------
@api_bp.route('/guest-login', methods=['POST'])
def guest_login():
    """
    Creates or logs in a temporary Guest Farmer for effortless college demonstrations.
    Allows testing features immediately without manually registering.
    """
    from backend.database import get_user_by_username, create_user
    from werkzeug.security import generate_password_hash

    guest_user = get_user_by_username('demo_farmer')
    if not guest_user:
        pwd_hash = generate_password_hash('DemoFarmer@123', method='scrypt')
        user_id = create_user(
            username='demo_farmer',
            password_hash=pwd_hash,
            full_name='Kisan Demo (Guest)',
            location='Delhi,IN'
        )
    else:
        user_id = guest_user['id']

    session['user_id'] = user_id
    session['username'] = 'demo_farmer'
    session['full_name'] = 'Kisan Demo (Guest)'
    session['location'] = 'Delhi,IN'

    return jsonify({
        'success': True,
        'message': 'Logged in as Demo Farmer.',
        'user': {
            'id': user_id,
            'username': 'demo_farmer',
            'full_name': 'Kisan Demo (Guest)',
            'location': 'Delhi,IN'
        }
    }), 200
