"""
ai_service.py - AI Advisory Engine with Multimodal (Image + Text) & Fallback Support

Beginner-Friendly Explanation:
This module connects to state-of-the-art Generative AI models (Google Gemini or OpenAI)
to answer farmer questions about crop diseases, pest control, irrigation, and fertilizers.
It accepts both textual queries and attached plant/leaf photographs.

Key Features:
1. Configurable Provider: Supports Gemini, OpenAI, or an Offline Rule-Based Mock Engine.
2. Multimodal: Encodes plant images in base64 to send to vision-capable AI models.
3. Resilient Error Handling: If an API key is missing, network is down, or quota is exceeded,
   it automatically switches to an intelligent agricultural fallback engine without crashing.
4. Responsible AI: Automatically appends an agricultural safety disclaimer to every response.
"""

import os
import base64
import json
import mimetypes
import requests
from typing import Dict, Any, Optional
import backend.config as config

# Standard Agricultural Safety Disclaimer
AGRICULTURAL_DISCLAIMER = (
    "\n\n---\n"
    "⚠️ **Agricultural Advisory Disclaimer**: This guidance is AI-generated for informational support. "
    "Soil health, microclimates, and regional crop varieties vary. Always verify pesticide dosages and treatment plans "
    "with your local Krishi Vigyan Kendra (KVK), agriculture extension officer, or certified agronomist before application."
)

# System Prompt to instruct the AI model to behave as a dedicated, safe farm advisor
SYSTEM_PROMPT = (
    "You are 'Kisan Mitra AI', an empathetic, practical, and knowledgeable agricultural advisor for farmers. "
    "Provide clear, structured, and farmer-friendly advice. "
    "When answering questions: "
    "1. Use simple language with clear bullet points. "
    "2. If analyzing an image, identify possible plant symptoms, diseases, or deficiencies. "
    "3. Recommend both organic/cultural practices and safe chemical management. "
    "4. Emphasize safe handling of agricultural chemicals (gloves, masks, correct dosage). "
    "5. Keep weather context in mind if provided."
)


def _encode_image_to_base64(image_path: str) -> Optional[tuple[str, str]]:
    """
    Reads an uploaded image file and converts it to base64.
    Returns a tuple of (mime_type, base64_string) or None if file cannot be read.
    """
    if not image_path or not os.path.exists(image_path):
        return None

    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type:
        mime_type = "image/jpeg"

    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
            return mime_type, encoded_string
    except Exception as e:
        print(f"[AI Service] Error encoding image: {e}")
        return None


def _call_gemini_api(
    prompt: str,
    image_path: Optional[str] = None,
    weather_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Calls Google Gemini REST API using the configured GEMINI_API_KEY.
    Supports multimodal queries (text + image).
    """
    if not config.GEMINI_API_KEY or config.GEMINI_API_KEY == "your_gemini_api_key_here":
        raise ValueError("Gemini API key is not configured in .env.")

    # Context enrichment with weather if available
    context_prefix = ""
    if weather_info and weather_info.get("success"):
        context_prefix = (
            f"[Current Field Weather: {weather_info.get('temperature_c')}°C, "
            f"{weather_info.get('condition')}, Humidity {weather_info.get('humidity_pct')}%, "
            f"Wind {weather_info.get('wind_speed_kph')} km/h]\n\n"
        )

    full_prompt = f"{SYSTEM_PROMPT}\n\n{context_prefix}Farmer Question:\n{prompt}"

    # Prepare contents parts for Gemini API
    parts = [{"text": full_prompt}]

    # Attach image if present
    if image_path:
        encoded = _encode_image_to_base64(image_path)
        if encoded:
            mime_type, b64_data = encoded
            parts.append({
                "inline_data": {
                    "mime_type": mime_type,
                    "data": b64_data
                }
            })

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": parts
            }
        ],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 1024
        }
    }

    primary_model = config.AI_MODEL_NAME or "gemini-3-flash-preview"
    candidate_models = [primary_model]
    for fallback in ["gemini-3-flash-preview", "gemini-3.1-flash-lite-preview"]:
        if fallback not in candidate_models:
            candidate_models.append(fallback)

    last_error = None
    for model in candidate_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={config.GEMINI_API_KEY}"
        try:
            response = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                data=json.dumps(payload),
                timeout=15
            )

            if response.status_code == 200:
                res_json = response.json()
                candidates = res_json.get("candidates", [])
                if candidates:
                    text_parts = candidates[0].get("content", {}).get("parts", [])
                    ai_text = "".join([p.get("text", "") for p in text_parts]).strip()
                    if ai_text:
                        return {
                            "text": ai_text + AGRICULTURAL_DISCLAIMER,
                            "is_simulated": False,
                            "provider": f"Gemini ({model})"
                        }

            last_error = f"Gemini API ({model}) returned status {response.status_code}: {response.text[:180]}"
        except requests.exceptions.RequestException as e:
            last_error = f"Network request to Gemini ({model}) failed: {str(e)}"

    raise RuntimeError(last_error or "Gemini API returned empty response.")


def _call_openai_api(
    prompt: str,
    image_path: Optional[str] = None,
    weather_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Calls OpenAI-compatible API using OPENAI_API_KEY.
    """
    if not config.OPENAI_API_KEY:
        raise ValueError("OpenAI API key is not configured in .env.")

    model = config.AI_MODEL_NAME or "gpt-4o-mini"
    url = "https://api.openai.com/v1/chat/completions"

    content_list = []
    # Add text
    weather_text = ""
    if weather_info and weather_info.get("success"):
        weather_text = f"\n[Weather context: {weather_info.get('temperature_c')}°C, Humidity: {weather_info.get('humidity_pct')}%]"
    content_list.append({"type": "text", "text": f"{prompt}{weather_text}"})

    # Add image if available
    if image_path:
        encoded = _encode_image_to_base64(image_path)
        if encoded:
            mime_type, b64_data = encoded
            content_list.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime_type};base64,{b64_data}"}
            })

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content_list}
        ],
        "temperature": 0.4,
        "max_tokens": 1000
    }

    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {config.OPENAI_API_KEY}",
            "Content-Type": "application/json"
        },
        data=json.dumps(payload),
        timeout=15
    )

    if response.status_code != 200:
        raise RuntimeError(f"OpenAI API error {response.status_code}: {response.text[:200]}")

    res_json = response.json()
    ai_text = res_json["choices"][0]["message"]["content"].strip()

    return {
        "text": ai_text + AGRICULTURAL_DISCLAIMER,
        "is_simulated": False,
        "provider": f"OpenAI ({model})"
    }


def _get_rule_based_fallback(
    prompt: str,
    has_image: bool = False,
    weather_info: Optional[Dict[str, Any]] = None,
    error_reason: Optional[str] = None
) -> Dict[str, Any]:
    """
    Intelligent offline fallback engine providing realistic agricultural guidance.
    Ensures that the college project never fails to respond even without external internet or API keys.
    """
    lower_query = prompt.lower()
    advice_sections = []

    if error_reason:
        badge = f"[Simulated / Offline Mode - Reason: {error_reason}]"
    else:
        badge = "[Simulated / Offline Demo Mode]"

    # Weather-aware advice inclusion
    weather_note = ""
    if weather_info and weather_info.get("temperature_c"):
        weather_note = (
            f"**Current Local Weather Consideration**: Field temperature is {weather_info.get('temperature_c')}°C "
            f"with {weather_info.get('humidity_pct')}% humidity ({weather_info.get('condition')}). "
            f"{weather_info.get('advisory')}\n\n"
        )

    # 1. Image Diagnosis Query
    if has_image:
        advice_sections.append(
            "### 🌿 Crop Image Symptom Analysis\n"
            "Thank you for uploading a photograph of the affected plant tissue. "
            "Based on common agricultural pathology criteria:\n"
            "- **Observed Symptoms**: Spotting, discoloration, or leaf curling on foliage.\n"
            "- **Common Suspects**: Fungal Leaf Spot (e.g. Cercospora / Alternaria), early blight, or sucking pest infestation (aphids / mites).\n"
            "- **Immediate Organic / Cultural Remedy**:\n"
            "  1. Prune and safely destroy severely infected lower leaves.\n"
            "  2. Avoid overhead sprinkler irrigation; keep foliage dry.\n"
            "  3. Spray 5ml/L Neem Oil solution (10,000 ppm) with a few drops of mild soap early in the morning.\n"
            "- **Recommended Chemical Alternative** (if fungal infection spreads):\n"
            "  - Copper Oxychloride (50% WP) @ 2.5g/L or Mancozeb (75% WP) @ 2g/L of water."
        )

    # 2. Specific Topic Checks
    elif any(w in lower_query for w in ["tomato", "potato", "blight", "yellow", "curl"]):
        advice_sections.append(
            "### 🍅 Solanaceous Crop Advisory (Tomato / Potato)\n"
            "- **Yellowing / Curling Leaves**: Commonly caused by Yellow Leaf Curl Virus (vectored by Whiteflies) or Nitrogen deficiency.\n"
            "- **Control Measures**:\n"
            "  - Install yellow sticky traps (10-12 traps per acre) to control whitefly populations.\n"
            "  - Spray Imidacloprid 17.8% SL @ 0.5 ml/L of water if whitefly count is high.\n"
            "  - Ensure balanced N-P-K fertilization (19:19:19 @ 5g/L foliar spray)."
        )

    elif any(w in lower_query for w in ["wheat", "rust", "grain", "yellow rust"]):
        advice_sections.append(
            "### 🌾 Wheat Crop Advisory\n"
            "- **Yellow / Brown Rust Monitoring**: Check underside of leaves for yellow or orange powder pustules.\n"
            "- **Recommended Action**:\n"
            "  - If rust symptoms appear, spray Propiconazole 25% EC @ 1 ml per liter of water.\n"
            "  - Avoid excess urea fertilization late in the season, which promotes fungal susceptibility.\n"
            "  - Maintain optimum moisture during the critical flowering and milking stages."
        )

    elif any(w in lower_query for w in ["rice", "paddy", "blast", "stem borer"]):
        advice_sections.append(
            "### 🌾 Paddy / Rice Advisory\n"
            "- **Stem Borer & Leaf Blast Check**: Check for 'dead hearts' in young tillers or spindle-shaped blast lesions.\n"
            "- **Management**:\n"
            "  - Install pheromone traps @ 5 per acre for monitoring Yellow Stem Borer moths.\n"
            "  - For Blast: Spray Tricyclazole 75% WP @ 0.6g/L or Isoprothiolane 40% EC @ 1.5 ml/L.\n"
            "  - Maintain shallow standing water (2-3 cm) during vegetative phase."
        )

    elif any(w in lower_query for w in ["fertilizer", "urea", "dap", "npk", "nutrient"]):
        advice_sections.append(
            "### 🧪 Soil Fertility & Nutrient Guidance\n"
            "- **Balanced Fertilizer Strategy**:\n"
            "  - Base application should be determined by a soil health card test.\n"
            "  - Apply DAP and Potash as basal doses at the time of sowing/transplanting.\n"
            "  - Split Urea into 2-3 top dressings instead of single heavy application to avoid leaching."
        )

    elif any(w in lower_query for w in ["pest", "insect", "caterpillar", "worm", "aphid"]):
        advice_sections.append(
            "### 🐛 Integrated Pest Management (IPM)\n"
            "- **Step 1 (Physical)**: Handpick large caterpillars; install light or pheromone traps.\n"
            "- **Step 2 (Biological)**: Spray Bacillus thuringiensis (Bt) @ 2g/L or release Trichogramma egg parasitoids.\n"
            "- **Step 3 (Chemical)**: If infestation crosses economic threshold (ETL), spray Chlorantraniliprole 18.5% SC @ 0.3 ml/L."
        )

    else:
        # General Agricultural Advice
        advice_sections.append(
            "### 🌱 General Agricultural Advisory\n"
            f"Here are practical farming guidelines regarding your query: *\"{prompt}\"*:\n"
            "1. **Inspection**: Thoroughly inspect the crop early in the morning for localized pest colonies or soil moisture levels.\n"
            "2. **Good Agronomic Practices**: Maintain clean field bunds, practice crop rotation, and ensure adequate plant spacing for airflow.\n"
            "3. **Microbial Soil Enrichers**: Apply Trichoderma viride and Pseudomonas fluorescens mixed with well-rotted FYM (Farmyard Manure) to suppress soil-borne pathogens."
        )

    response_text = f"{badge}\n\n{weather_note}" + "\n\n".join(advice_sections) + AGRICULTURAL_DISCLAIMER

    return {
        "text": response_text,
        "is_simulated": True,
        "provider": "Offline Knowledge Engine (Simulated Mode)"
    }


def generate_agricultural_advisory(
    query_text: str,
    image_filename: Optional[str] = None,
    weather_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Main entry point for generating farmer advice.
    Selects configured AI provider (Gemini or OpenAI), with automatic fallback to
    the simulated engine upon missing keys or network errors.
    """
    cleaned_query = (query_text or "").strip()
    image_path = None
    has_image = False

    if image_filename:
        full_img_path = os.path.join(str(config.UPLOAD_FOLDER), image_filename)
        if os.path.exists(full_img_path):
            image_path = full_img_path
            has_image = True

    # If both text and image are missing, reject
    if not cleaned_query and not has_image:
        return {
            "success": False,
            "error": "Please provide a question or upload a crop photograph.",
            "text": None,
            "is_simulated": False
        }

    # If only an image was uploaded without query text, supply a default query
    effective_query = cleaned_query or "Please analyze this plant image and advise on diagnosis, causes, and treatments."

    provider = config.AI_PROVIDER.lower()

    # Attempt calling chosen AI model
    if provider == "gemini":
        try:
            result = _call_gemini_api(effective_query, image_path=image_path, weather_info=weather_info)
            result["success"] = True
            return result
        except Exception as e:
            print(f"[AI Service Warning] Gemini call failed: {e}. Switching to offline fallback.")
            fallback = _get_rule_based_fallback(
                effective_query,
                has_image=has_image,
                weather_info=weather_info,
                error_reason=f"Gemini API unavailable ({type(e).__name__})"
            )
            fallback["success"] = True
            return fallback

    elif provider == "openai":
        try:
            result = _call_openai_api(effective_query, image_path=image_path, weather_info=weather_info)
            result["success"] = True
            return result
        except Exception as e:
            print(f"[AI Service Warning] OpenAI call failed: {e}. Switching to offline fallback.")
            fallback = _get_rule_based_fallback(
                effective_query,
                has_image=has_image,
                weather_info=weather_info,
                error_reason=f"OpenAI API unavailable ({type(e).__name__})"
            )
            fallback["success"] = True
            return fallback

    else:
        # Default mock provider
        fallback = _get_rule_based_fallback(
            effective_query,
            has_image=has_image,
            weather_info=weather_info,
            error_reason=None
        )
        fallback["success"] = True
        return fallback
