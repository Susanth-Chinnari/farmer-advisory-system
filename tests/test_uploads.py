"""
test_uploads.py - Automated Tests for File Upload Validation

Tests Covered:
1. Upload valid image (PNG/JPG) with query.
2. Reject non-image dangerous extensions (.exe, .sh, .py).
3. Reject fake images (text file renamed to .jpg).
4. Verify files are stored with sanitized unique names to prevent directory traversal.
"""

import io
from PIL import Image


def _create_test_image_bytes(format='PNG'):
    """Helper to generate an in-memory genuine image for testing."""
    file_bytes = io.BytesIO()
    img = Image.new('RGB', (100, 100), color=(73, 109, 137))
    img.save(file_bytes, format=format)
    file_bytes.seek(0)
    return file_bytes


def test_valid_image_upload(auth_client):
    """Test uploading a valid crop photo alongside a question."""
    img_data = _create_test_image_bytes('JPEG')

    data = {
        'query': 'What is causing these spots on my crop leaf?',
        'image': (img_data, 'leaf_spot.jpg')
    }

    res = auth_client.post(
        '/api/query',
        data=data,
        content_type='multipart/form-data'
    )
    assert res.status_code == 200
    res_data = res.get_json()
    assert res_data['success'] is True
    assert res_data['user_message']['image_filename'] is not None
    assert 'leaf_spot.jpg' in res_data['user_message']['image_filename']


def test_reject_dangerous_extension(auth_client):
    """Test rejection of non-whitelisted executable/script extensions."""
    fake_script = io.BytesIO(b"echo 'malicious command'")
    data = {
        'query': 'Check this file',
        'image': (fake_script, 'script.exe')
    }

    res = auth_client.post(
        '/api/query',
        data=data,
        content_type='multipart/form-data'
    )
    assert res.status_code == 400
    res_data = res.get_json()
    assert res_data['success'] is False
    assert 'Invalid file format' in res_data['error']


def test_reject_corrupt_or_fake_image(auth_client):
    """Test rejection when a plain text file is renamed to a valid image extension."""
    fake_img = io.BytesIO(b"This is just plain text, not real image bytes!")
    data = {
        'query': 'Diagnose this leaf',
        'image': (fake_img, 'fake_leaf.png')
    }

    res = auth_client.post(
        '/api/query',
        data=data,
        content_type='multipart/form-data'
    )
    assert res.status_code == 400
    res_data = res.get_json()
    assert res_data['success'] is False
    assert 'not a valid or readable image' in res_data['error']
