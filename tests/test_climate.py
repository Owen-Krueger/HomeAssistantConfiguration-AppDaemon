from unittest import mock
from appdaemon_testing.pytest import automation_fixture
from apps.climate import Climate, ClimateEntities

def test_day_time_updated(hass_driver, climate: Climate):
    listen_state = hass_driver.get_mock("listen_state")


@automation_fixture(
    Climate,
    args={
        "allison": "person.allison",
        "climate_away_minutes": "input_number.climate_away_minutes",
        "climate_away_offset": "input_number.climate_away_offset",
        "climate_gone_offset": "input_number.climate_gone_offset",
        "day_temperature": "input_number.climate_day_temp",
        "day_time": "input_datetime.climate_day_start",
        "night_temperature": "input_number.climate_night_temp",
        "night_time": "input_datetime.climate_night_start",
        "notify_user": "input_boolean.climate_notify_user",
        "owen": "person.owen",
        "thermostat": "climate.kitchen_thermostat",
        "vacation_mode": "input_boolean.mode_vacation",
        "zone_home": "zone.home",
        "zone_near_home": "zone.near_home"
    }
)

def climate() -> Climate:
    pass