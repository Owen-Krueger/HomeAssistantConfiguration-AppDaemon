import appdaemon.plugins.hass.hassapi as hass
from datetime import datetime, time
from enum import Enum, auto

"""
Stores the identifiers for HASS entities.
Example: day_time: input_datetime.climate_day_start
"""
class ClimateEntities:

    allison: str
    owen: str
    day_time: str
    night_time: str
    day_temperature: str
    night_temperature: str
    away_minutes: str
    away_offset: str
    gone_offset: str
    vacation_mode: str
    thermostat: str
    zone_home: str
    zone_near_home: str
    notify_user: str

    def __init__(self, hass: hass.Hass) -> None:
        self.allison = hass.args["allison"]
        self.owen = hass.args["owen"]
        self.day_time = hass.args["day_time"]
        self.night_time = hass.args["night_time"]
        self.day_temperature = hass.args["day_temperature"]
        self.night_temperature = hass.args["night_temperature"]
        self.away_minutes = hass.args["climate_away_minutes"]
        self.away_offset = hass.args["climate_away_offset"]
        self.gone_offset = hass.args["climate_gone_offset"]
        self.vacation_mode = hass.args["vacation_mode"]
        self.thermostat = hass.args["thermostat"]
        self.zone_home = hass.args["zone_home"]
        self.zone_near_home = hass.args["zone_near_home"]
        self.notify_user = hass.args["notify_user"]

"""
The various states the thermostat can be in.
"""
class ThermostatState(Enum):
    Home = auto(),
    Away = auto(),
    Gone = auto()

class Climate(hass.Hass):

    entities: ClimateEntities
    day_time: time
    day_time_handler: str
    night_time: time
    night_time_handler: str
    allison_away_state_handler: str
    owen_away_state_handler: str
    thermostat_state: ThermostatState

    """
    Set up automation callbacks and state.
    """
    def initialize(self) -> None:
        self.utils = self.get_app("utils")
        self.entities = ClimateEntities(self)
        self.day_time = self.parse_time(self.get_state(self.entities.day_time))
        self.night_time = self.parse_time(self.get_state(self.entities.night_time))
        ENTITY_UPDATE_DURATION: int = 15
        away_duration_seconds: int = self.get_away_duration_seconds(self.get_state(self.entities.away_minutes))

        # Property updates
        self.listen_state(self.on_day_time_updated, self.entities.day_time, duration = ENTITY_UPDATE_DURATION)
        self.listen_state(self.on_night_time_updated, self.entities.night_time, duration = ENTITY_UPDATE_DURATION)
        
        # Temperature update events
        self.listen_state(self.on_person_state_updated, self.entities.allison, new = "home")
        self.listen_state(self.on_person_state_updated, self.entities.owen, new = "home")
        self.allison_away_state_handler = self.listen_state(self.on_person_state_updated, self.entities.allison, new = "away", duration = away_duration_seconds)
        self.owen_away_state_handler = self.listen_state(self.on_person_state_updated, self.entities.owen, new = "away", duration = away_duration_seconds)
        self.listen_state(self.on_person_state_updated, self.entities.zone_near_home, duration = 300) # 5 minutes.
        self.day_time_handler = self.run_daily(self.on_schedule_time, self.day_time)
        self.night_time_handler = self.run_daily(self.on_schedule_time, self.night_time)

    """
    On climate day time set, cancel previous timer and set up a new one for the new time.
    """
    def on_day_time_updated(self, entity: str, attribute: str, old: str, new: str, args) -> None:
        self.cancel_timer(self.day_time_handler)
        self.day_time = self.parse_time(new)
        self.day_time_handler = self.run_daily(self.on_schedule_time, self.day_time)
        self.log("day_time updated from {} to {}.".format(old, new))

    """
    On climate night time set, cancel previous timer and set up a new one for the new time.
    """
    def on_night_time_updated(self, entity: str, attribute: str, old: str, new: str, args) -> None:
        self.cancel_timer(self.night_time_handler)
        self.night_time = self.parse_time(new)
        self.night_time_handler = self.run_daily(self.on_schedule_time, self.night_time)
        self.log("night_time updated from {} to {}.".format(old, new))

    """
    On away minutes updated, cancel away state listeners and set up new ones with new time.
    """
    def on_away_minutes_updated(self, entity: str, attribute: str, old: str, new: str, args) -> None:
        self.cancel_listen_state(self.allison_away_state_handler)
        self.cancel_listen_state(self.owen_away_state_handler)
        away_duration_seconds = self.get_away_duration_seconds(new)
        self.allison_away_state_handler = self.listen_state(self.on_person_state_updated, self.entities.allison, new = "away", duration = away_duration_seconds)
        self.owen_away_state_handler = self.listen_state(self.on_person_state_updated, self.entities.owen, new = "away", duration = away_duration_seconds)
        self.log("away_minutes updated from {} to {}.".format(old, new))

    """
    On climate day time or night time, update temperature.
    """
    def on_schedule_time(self, args) -> None:
        temperature: int = self.set_temperature()
        self.notify_user("Climate: Temperature set to {}".format(temperature))

    """
    If someone is home or away, set state based on if anybody else is home or not.
    """
    def on_person_state_updated(self, entity: str, attribute: str, old: str, new: str, args) -> None:
        temperature: int = self.set_temperature()
        self.notify_user("Climate: People are {}. Temperature set to {}.".format(self.thermostat_state.name, temperature))

    """
    Sets the temperature of the thermostat based on the state.
    """
    def set_temperature(self) -> int:
        current_temperature: int = int(self.get_state(self.entities.thermostat, attribute = "temperature"))
        new_temperature = self.get_new_temperature()

        self.log("Temperature update requested. Old: {} New: {}".format(current_temperature, new_temperature))

        if current_temperature != new_temperature:
            self.call_service(
                "climate/set_temperature",
                entity_id=self.entities.thermostat,
                temperature=new_temperature,
            )
        
        return new_temperature

    """
    Updates the correct temperature to set based on the current state.
    """
    def get_new_temperature(self) -> int:
        self.update_thermostat_state()
        day_temperature = self.get_input_number_from_state(self.entities.day_temperature)
        night_temperature = self.get_input_number_from_state(self.entities.night_temperature)

        if self.thermostat_state == ThermostatState.Gone:
            gone_offset = self.get_input_number_from_state(self.entities.gone_offset)
            return day_temperature + self.get_offset(gone_offset)

        temperature = day_temperature if self.is_day() else night_temperature
        if self.thermostat_state == ThermostatState.Away:
            away_offset = self.get_input_number_from_state(self.entities.away_offset)
            return temperature + self.get_offset(away_offset)

        return temperature
    
    """
    Updates the current state of the thermostat based on where people are.
    """
    def update_thermostat_state(self) -> None:
        state = ThermostatState.Home

        if (int(self.get_state(self.entities.zone_near_home)) == 0 and 
            int(self.get_state(self.entities.zone_home)) == 0): # Nobody in either zones means people are far away.
            state = ThermostatState.Gone
        elif not self.anyone_home(person=True):
            state = ThermostatState.Away

        self.thermostat_state = state

    """
    Day is considered the time between the start time of the day temperature
    and the start time of the night temperature.
    """
    def is_day(self) -> bool:
        # Subtract 5 seconds from the user set day time to get rid of an edge case where
        # the automation running fast could result in `now_is_between` returning false.
        day_time = self.utils.add_seconds(self.day_time, -5)
        return self.now_is_between(str(day_time), str(self.night_time))

    """
    Gets the correct offset, based on if the thermostat is in heat or cool mode.
    If mode is heat, we want to be cooler, so we multiply the offset by -1.
    If mode is cool, we want to be hotter, so the offset stays as is.
    Example: Offset = 5
    Heat: -5
    Cool: 5
    """
    def get_offset(self, offset: int) -> int:
        return offset * -1 if self.is_heat_mode else offset

    """
    Notify user if notify user boolean is set.
    """
    def notify_user(self, message: str) -> None:
        if bool(self.get_state(self.entities.notify_user)):
            self.utils.notify_owen(message)

    """
    Converts state string to an integer (minutes) and multiplies to get seconds
    needed for AppDaemon durations.
    """
    def get_away_duration_seconds(self, state: str) -> int:
        return self.utils.get_input_number_integer(state) * 60

    """
    Gets the integer representation of the state of the input entity.
    """
    def get_input_number_from_state(self, entity_id: str) -> int:
        return self.utils.get_input_number_integer(self.get_state(entity_id))