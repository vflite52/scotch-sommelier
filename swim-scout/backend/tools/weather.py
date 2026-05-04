"""Weather and water condition tools using Open-Meteo and USGS NWIS APIs."""
import httpx

LOCATIONS: dict[str, dict] = {
    "lake tahoe": {"lat": 39.0968, "lon": -120.0324, "display": "Lake Tahoe, CA/NV"},
    "lake whatcom": {"lat": 48.7519, "lon": -122.3793, "display": "Lake Whatcom, WA"},
    "puget sound": {"lat": 47.6062, "lon": -122.3321, "display": "Puget Sound, WA"},
    "crater lake": {"lat": 42.9446, "lon": -122.1090, "display": "Crater Lake, OR"},
    "flathead lake": {"lat": 47.8600, "lon": -114.1500, "display": "Flathead Lake, MT"},
    "lake del valle": {"lat": 37.6019, "lon": -121.7097, "display": "Lake Del Valle, CA", "lakemonster_id": 3275},
    "sf bay aquatic park": {"lat": 37.8081, "lon": -122.4161, "display": "SF Bay Aquatic Park, CA"},
    "foster city": {"lat": 37.5585, "lon": -122.2711, "display": "Foster City Lagoon, CA"},
    "santa cruz pier": {"lat": 36.9583, "lon": -122.0174, "display": "Santa Cruz Pier, CA"},
    "coyote point": {"lat": 37.5916, "lon": -122.3186, "display": "Coyote Point, San Mateo, CA"},
    "donner lake": {"lat": 39.3229, "lon": -120.2344, "display": "Donner Lake, CA", "lakemonster_id": 327},
    "waikiki beach": {"lat": 21.2793, "lon": -157.8294, "display": "Waikiki Beach, HI"},
}

WMO_CODES: dict[int, str] = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Icy fog", 51: "Light drizzle", 53: "Moderate drizzle",
    55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
    95: "Thunderstorm", 96: "Thunderstorm w/ hail", 99: "Thunderstorm w/ heavy hail",
}


def resolve_location(location: str) -> dict | None:
    return LOCATIONS.get(location.lower().strip())


def get_supported_locations() -> list[str]:
    return [v["display"] for v in LOCATIONS.values()]


def get_location_options() -> list[dict]:
    return [{"key": k, "display": v["display"]} for k, v in LOCATIONS.items()]


async def get_weather_conditions(location: str) -> dict:
    coords = resolve_location(location)
    if not coords:
        return {"error": f"Unknown location '{location}'. Supported: {', '.join(LOCATIONS)}"}

    params = {
        "latitude": coords["lat"],
        "longitude": coords["lon"],
        "current": "temperature_2m,wind_speed_10m,wind_direction_10m,wind_gusts_10m,precipitation,weather_code,cloud_cover",
        "wind_speed_unit": "mph",
        "temperature_unit": "fahrenheit",
        "timezone": "auto",
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()

        cur = data["current"]
        weather_code = cur.get("weather_code", 0)
        return {
            "location": coords["display"],
            "air_temp_f": round(cur["temperature_2m"], 1),
            "wind_speed_mph": round(cur["wind_speed_10m"], 1),
            "wind_gusts_mph": round(cur.get("wind_gusts_10m", 0), 1),
            "wind_direction_deg": cur["wind_direction_10m"],
            "precipitation_mm": cur["precipitation"],
            "cloud_cover_pct": cur.get("cloud_cover", 0),
            "weather_description": WMO_CODES.get(weather_code, f"Code {weather_code}"),
            "observation_time": cur["time"],
        }
    except httpx.HTTPError as e:
        return {"error": f"Weather API error: {e}"}


async def _usgs_water_temp(lat: float, lon: float, display: str) -> dict | None:
    """Try USGS NWIS. Returns a result dict on success, None if no sensor found."""
    params = {
        "format": "json",
        "bBox": f"{lon - 0.4:.4f},{lat - 0.4:.4f},{lon + 0.4:.4f},{lat + 0.4:.4f}",
        "parameterCd": "00010",
        "siteStatus": "active",
        "period": "PT6H",
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://waterservices.usgs.gov/nwis/iv/", params=params, timeout=15.0)
            resp.raise_for_status()
            data = resp.json()

        time_series = data.get("value", {}).get("timeSeries", [])
        if not time_series:
            return None

        ts = time_series[0]
        values = ts.get("values", [{}])[0].get("value", [])
        if not values:
            return None

        temp_c = float(values[-1]["value"])
        # USGS uses -999999 as a sentinel for missing/invalid readings
        if temp_c < -100:
            return None

        return {
            "location": display,
            "water_temp_c": round(temp_c, 1),
            "water_temp_f": round(temp_c * 9 / 5 + 32, 1),
            "observation_time": values[-1]["dateTime"],
            "usgs_site": ts.get("sourceInfo", {}).get("siteName", "Unknown site"),
            "source": "USGS NWIS",
        }
    except Exception:
        return None


async def _lakemonster_water_temp(lake_id: int, display: str) -> dict | None:
    """Fallback to Lake Monster API. Returns a result dict on success, None on failure."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://lakemonster.com/api/lakes/{lake_id}",
                timeout=10.0,
                follow_redirects=True,
            )
            resp.raise_for_status()
            data = resp.json()

        raw_temp = data.get("waterTemp")
        if raw_temp is None:
            return None

        temp_f = float(raw_temp)
        temp_c = round((temp_f - 32) * 5 / 9, 1)

        # Most recent entry in temp_graph gives a timestamped reading
        graph = data.get("temp_graph") or []
        observation_time = graph[-1].get("time") if graph else None

        return {
            "location": display,
            "water_temp_f": round(temp_f, 1),
            "water_temp_c": temp_c,
            "observation_time": observation_time,
            "source": "Lake Monster",
        }
    except Exception:
        return None


async def get_water_temperature(location: str) -> dict:
    coords = resolve_location(location)
    if not coords:
        return {"error": f"Unknown location: {location}"}

    display = coords["display"]

    # Primary: USGS NWIS
    result = await _usgs_water_temp(coords["lat"], coords["lon"], display)
    if result:
        return result

    # Fallback: Lake Monster (if an ID is registered for this location)
    lake_id = coords.get("lakemonster_id")
    if lake_id:
        result = await _lakemonster_water_temp(lake_id, display)
        if result:
            return result

    return {
        "location": display,
        "water_temp_f": None,
        "note": "No water temperature data available from USGS or Lake Monster.",
    }
