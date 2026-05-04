"""Water safety and algae bloom checking tools using EPA and USGS APIs."""
import csv
import io
import httpx
from datetime import datetime, timedelta, timezone

LOCATIONS: dict[str, dict] = {
    "lake tahoe": {"lat": 39.0968, "lon": -120.0324, "display": "Lake Tahoe, CA/NV", "huc": "18020129"},
    "lake whatcom": {"lat": 48.7519, "lon": -122.3793, "display": "Lake Whatcom, WA", "huc": "17110019"},
    "puget sound": {"lat": 47.6062, "lon": -122.3321, "display": "Puget Sound, WA", "huc": "17110019"},
    "crater lake": {"lat": 42.9446, "lon": -122.1090, "display": "Crater Lake, OR", "huc": "17070304"},
    "flathead lake": {"lat": 47.8600, "lon": -114.1500, "display": "Flathead Lake, MT", "huc": "17010207"},
    "lake del valle": {"lat": 37.6019, "lon": -121.7097, "display": "Lake Del Valle, CA", "huc": "18050001"},
    "sf bay aquatic park": {"lat": 37.8081, "lon": -122.4161, "display": "SF Bay Aquatic Park, CA", "huc": "18050003"},
    "foster city": {"lat": 37.5585, "lon": -122.2711, "display": "Foster City Lagoon, CA", "huc": "18050003"},
    "santa cruz pier": {"lat": 36.9583, "lon": -122.0174, "display": "Santa Cruz Pier, CA", "huc": "18060001"},
    "coyote point": {"lat": 37.5916, "lon": -122.3186, "display": "Coyote Point, San Mateo, CA", "huc": "18050003"},
    "donner lake": {"lat": 39.3229, "lon": -120.2344, "display": "Donner Lake, CA", "huc": "18020128"},
    "waikiki beach": {"lat": 21.2793, "lon": -157.8294, "display": "Waikiki Beach, HI", "huc": "20060000"},
}


def resolve_location(location: str) -> dict | None:
    return LOCATIONS.get(location.lower().strip())


async def check_algae_bloom_alerts(location: str) -> dict:
    """Check EPA Water Quality Portal for recent cyanobacteria reports (last 30 days)."""
    coords = resolve_location(location)
    if not coords:
        return {"error": f"Unknown location: {location}"}

    start_date = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%m-%d-%Y")
    params = {
        "huc": coords["huc"],
        "characteristicName": "Cyanobacteria",
        "startDateLo": start_date,
        "mimeType": "csv",
        "zip": "no",
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://www.waterqualitydata.us/data/Result/search",
                params=params,
                headers={"Accept": "text/csv"},
                timeout=20.0,
            )
            resp.raise_for_status()

        rows = list(csv.DictReader(io.StringIO(resp.text)))

        if not rows:
            return {
                "location": coords["display"],
                "algae_alert": False,
                "report_count": 0,
                "period": "Last 30 days",
                "source": "EPA Water Quality Portal",
                "note": "No cyanobacteria reports found.",
            }

        detections = [
            {
                "value": r.get("ResultMeasureValue", ""),
                "unit": r.get("ResultMeasure/MeasureUnitCode", ""),
                "date": r.get("ActivityStartDate", ""),
                "site": r.get("MonitoringLocationName", ""),
            }
            for r in rows[:10]
            if r.get("ResultMeasureValue")
        ]

        return {
            "location": coords["display"],
            "algae_alert": len(detections) > 0,
            "report_count": len(rows),
            "recent_detections": detections[:5],
            "period": "Last 30 days",
            "source": "EPA Water Quality Portal",
        }

    except httpx.HTTPError as e:
        return {
            "location": coords["display"],
            "error": f"Water quality API unavailable: {e}",
            "note": "Could not retrieve algae data. Check your state health dept for advisories.",
        }


async def check_water_quality(location: str) -> dict:
    """Check USGS sensors for pH and dissolved oxygen near the location."""
    coords = resolve_location(location)
    if not coords:
        return {"error": f"Unknown location: {location}"}

    lat, lon = coords["lat"], coords["lon"]
    params = {
        "format": "json",
        "bBox": f"{lon - 0.4:.4f},{lat - 0.4:.4f},{lon + 0.4:.4f},{lat + 0.4:.4f}",
        "parameterCd": "00400,00300",  # pH, dissolved oxygen
        "siteStatus": "active",
        "period": "P1D",
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://waterservices.usgs.gov/nwis/iv/", params=params, timeout=15.0)
            resp.raise_for_status()
            data = resp.json()

        time_series = data.get("value", {}).get("timeSeries", [])
        if not time_series:
            return {
                "location": coords["display"],
                "ph": None,
                "dissolved_oxygen_mg_l": None,
                "note": "No USGS water quality sensors found near this location.",
            }

        quality: dict = {"location": coords["display"]}
        for ts in time_series:
            param = ts.get("variable", {}).get("variableCode", [{}])[0].get("value", "")
            values = ts.get("values", [{}])[0].get("value", [])
            if values:
                val = float(values[-1]["value"])
                if param == "00400":
                    quality["ph"] = round(val, 2)
                elif param == "00300":
                    quality["dissolved_oxygen_mg_l"] = round(val, 2)

        concerns = []
        ph = quality.get("ph")
        do = quality.get("dissolved_oxygen_mg_l")
        if ph is not None and (ph < 6.5 or ph > 9.0):
            concerns.append(f"pH out of safe range: {ph}")
        if do is not None and do < 5.0:
            concerns.append(f"Low dissolved oxygen: {do} mg/L")

        quality["concerns"] = concerns
        quality["safe"] = len(concerns) == 0
        quality["source"] = "USGS NWIS"
        return quality

    except httpx.HTTPError as e:
        return {"location": coords["display"], "error": f"USGS API error: {e}"}
