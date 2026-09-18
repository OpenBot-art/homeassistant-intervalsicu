"""Constants for the Intervals.icu integration."""

DOMAIN = "intervals_icu"

CONF_ATHLETE_ID = "athlete_id"
CONF_API_KEY = "api_key"

API_BASE_URL = "https://intervals.icu/api/v1"

DEFAULT_SCAN_INTERVAL = 7200  # 2 hours

# Number of days of activity history to request from the API.
ACTIVITY_LOOKBACK_DAYS = 30

# Upper bound on activity records fetched per poll. The sensors only ever read
# the single latest activity, so a small window is enough; the 30-day lookback
# exists to tolerate rest weeks where the newest record is older than a week.
ACTIVITY_LIMIT = 10

# Number of days of upcoming planned events to poll for the sensors.
EVENT_LOOKAHEAD_DAYS = 7

# Sensor keys that have been renamed. Maps the old key to the new key so
# entity unique IDs can be migrated without losing history. Keep this in
# sync with ``async_migrate_entry``.
RENAMED_SENSOR_KEYS = {
    "hrv_rmssd": "hrv_sdnn",
}
