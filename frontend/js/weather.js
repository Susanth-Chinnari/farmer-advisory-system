/**
 * weather.js - Weather Information and Agricultural Advisory Display
 *
 * Beginner-Friendly Explanation:
 * Fetches weather metrics from the backend (/api/weather) and populates the weather card.
 * If the user has a preferred city, it passes ?city=... to the endpoint.
 * Clearly badges live vs simulated data so examiners know when fallback mode is active.
 */

async function loadWeather(city = null) {
  const weatherCard = document.getElementById('weather-bar');
  if (!weatherCard) return;

  const tempElem = document.getElementById('weather-temp');
  const condElem = document.getElementById('weather-cond');
  const humidElem = document.getElementById('weather-humid');
  const windElem = document.getElementById('weather-wind');
  const badgeElem = document.getElementById('weather-badge');
  const advElem = document.getElementById('weather-advisory');
  const cityElem = document.getElementById('weather-city');

  try {
    const url = city ? `/api/weather?city=${encodeURIComponent(city)}` : '/api/weather';
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Weather API returned HTTP ${response.status}`);
    }

    const data = await response.json();

    if (tempElem) tempElem.textContent = `${data.temperature_c}°C`;
    if (condElem) condElem.textContent = data.condition || 'Clear';
    if (humidElem) humidElem.textContent = `${data.humidity_pct}%`;
    if (windElem) windElem.textContent = `${data.wind_speed_kph} km/h`;
    if (cityElem) cityElem.textContent = data.city || 'Delhi';
    if (advElem) advElem.textContent = data.advisory || 'Normal weather for routine farm tasks.';

    if (badgeElem) {
      badgeElem.textContent = data.status_badge || (data.is_simulated ? 'Simulated' : 'Live');
      badgeElem.className = 'weather-badge ' + (data.is_simulated ? 'badge-simulated' : 'badge-live');
      badgeElem.title = data.notice || (data.is_simulated ? 'Offline demo mode' : 'Real-time OpenWeatherMap data');
    }
  } catch (error) {
    console.warn("Unable to load weather:", error);
    if (advElem) advElem.textContent = "Weather service temporarily offline. Standard farming guidelines apply.";
    if (badgeElem) {
      badgeElem.textContent = "Offline";
      badgeElem.className = "weather-badge badge-simulated";
    }
  }
}
