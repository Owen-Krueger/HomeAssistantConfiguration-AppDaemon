import appdaemon.plugins.hass.hassapi as hass
from datetime import datetime, timedelta
from enum import Enum, auto

class Climate(hass.Hass):

    entities: ClimateEntities
    state: ClimateState
    day_time_handler: str
    night_time_handler: str

    """
    Set up automation callbacks and state.
    """
    def initialize(self) -> None:
        self.utils = self.get_app("utils")
        self.entities = ClimateEntities(self)
        self.state = ClimateState(self, self.entities)
        ENTITY_UPDATE_DURATION: int = 15


        # Property updates
        self.listen_state(self.on_day_time_updated, self.entities.day_time, duration = ENTITY_UPDATE_DURATION)
        self.listen_state(self.on_night_time_updated, self.entities.night_time, duration = ENTITY_UPDATE_DURATION)
        self.listen_state(self.on_day_temperature_updated, self.entities.day_temperature, duration = ENTITY_UPDATE_DURATION)
        self.listen_state(self.on_night_temperature_updated, self.entities.night_temperature, duration = ENTITY_UPDATE_DURATION)
        self.listen_state(self.on_away_minutes_updated, self.entities.away_minutes, duration = ENTITY_UPDATE_DURATION)
        self.listen_state(self.on_away_offset_updated, self.entities.away_offset, duration = ENTITY_UPDATE_DURATION)
        self.listen_state(self.on_gone_offset_updated, self.entities.gone_offset, duration = ENTITY_UPDATE_DURATION)
        self.listen_state(self.on_thermostat_mode_updated, self.entities.thermostat, duration = ENTITY_UPDATE_DURATION)
        self.listen_state(self.on_notify_user_updated, self.entities.notify_user, duration = ENTITY_UPDATE_DURATION)
        
        # Temperature update events
        self.listen_state(self.on_person_state_updated, self.entities.allison, new = "home")
        self.listen_state(self.on_person_state_updated, self.entities.owen, new = "home")
        self.listen_state(self.on_person_state_updated, self.entities.allison, new = "away", duration = self.state.away_minutes * 60)
        self.listen_state(self.on_person_state_updated, self.entities.owen, new = "away", duration = self.state.away_minutes * 60)
        self.listen_state(self.on_person_state_updated, self.entities.zone_near_home, duration = 300) # 5 minutes.
        self.day_time_handler = self.run_daily(self.on_schedule_time, self.state.day_time)
        self.night_time_handler = self.run_daily(self.on_schedule_time, self.state.night_time)

    """
    On climate day time set, cancel previous timer and set up a new one for the new time.
    """
    def on_day_time_updated(self, entity: str, attribute: str, old: str, new: str, args) -> None:
        self.state.day_time = self.parse_time(new)
        self.cancel_timer(self.day_time_handler)
        self.day_time_handler = self.run_daily(self.on_schedule_time, self.state.day_time)

    """
    On climate night time set, cancel previous timer and set up a new one for the new time.
    """
    def on_night_time_updated(self, entity: str, attribute: str, old: str, new: str, args) -> None:
        self.state.night_time = self.parse_time(new)
        self.cancel_timer(self.night_time_handler)
        self.night_time_handler = self.run_daily(self.on_schedule_time, self.state.night_time)

    """
    On day temperature updated, update state.
    """
    def on_day_temperature_updated(self, entity: str, attribute: str, old: str, new: str, args) -> None:
        self.state.day_temperature = self.utils.get_input_number_integer(new)

    """
    On night temperature updated, update state.
    """
    def on_night_temperature_updated(self, entity: str, attribute: str, old: str, new: str, args) -> None:
        self.state.night_temperature = self.utils.get_input_number_integer(new)

    """
    On away minutes updated, update state.
    """
    def on_away_minutes_updated(self, entity: str, attribute: str, old: str, new: str, args) -> None:
        self.state.away_minutes = self.utils.get_input_number_integer(new)

    """
    On away offset updated, update state.
    """
    def on_away_offset_updated(self, entity: str, attribute: str, old: str, new: str, args) -> None:
        self.state.away_offset = self.utils.get_input_number_integer(new)

    """
    On gone offset updated, update state.
    """
    def on_gone_offset_updated(self, entity: str, attribute: str, old: str, new: str, args) -> None:
        self.state.gone_offset = self.utils.get_input_number_integer(new)

    """
    On thermostat mode updated, update state.
    """
    def on_thermostat_mode_updated(self, entity: str, attribute: str, old: str, new: str, args) -> None:
        self.state.is_heat_mode = bool(new == "heat")

    """
    On notify user boolean updated, update state.
    """
    def on_notify_user_updated(self, entity: str, attribute: str, old: str, new: str, args) -> None:
        self.state.notify_user = bool(new)

    """
    On climate day time or night time, update temperature.
    """
    def on_schedule_time(self, args) -> None:
        self.set_temperature()

    """
    If someone is home or away, set state based on if anybody else is home or not.
    """
    def on_person_state_updated(self, entity: str, attribute: str, old: str, new: str, args) -> None:
        self.set_temperature()
        self.notify_user("Climate: People are {}. Temperature set to {}.".format(self.state.thermostat_state, self.state.set_temperature))

    """
    Sets the temperature of the thermostat based on the state.
    """
    def set_temperature(self) -> None:
        self.state.update_temperature()
        if self.state.set_temperature != int(self.get_state(self.entities.thermostat, attribute = "temperature")):
            self.call_service(
                "climate/set_temperature",
                entity_id=self.entities.thermostat,
                temperature=self.state.set_temperature,
            )

    """
    Notify user if notify user boolean is set.
    """
    def notify_user(self, message: str) -> None:
        if self.state.notify_user:
            self.utils.notify_owen(message)

"""
Stores the inner state that's used by the climate automations.
"""
class ClimateState:

    hass: hass.Hass
    entities: ClimateEntities
    day_time: datetime.time
    night_time: datetime.time
    day_temperature: int
    night_temperature: int
    away_offset: int
    gone_offset: int
    vacation_mode: bool
    away_minutes: int
    is_heat_mode: bool
    notify_user: bool
    thermostat_state: ThermostatState
    set_temperature: int

    def __init__(self, hass: hass.Hass, entities: ClimateEntities) -> None:
        self.hass = hass
        self.entities = entities
        self.day_time = hass.parse_time(hass.get_state(entities.day_time))
        self.night_time = hass.parse_time(hass.get_state(entities.night_time))
        self.day_temperature = hass.utils.get_input_number_integer(hass.get_state(entities.day_temperature))
        self.night_temperature = hass.utils.get_input_number_integer(hass.get_state(entities.night_temperature))
        self.away_minutes = hass.utils.get_input_number_integer(hass.get_state(entities.away_minutes))
        self.away_offset = hass.utils.get_input_number_integer(hass.get_state(entities.away_offset))
        self.gone_offset = hass.utils.get_input_number_integer(hass.get_state(entities.gone_offset))
        self.vacation_mode = bool(hass.get_state(entities.vacation_mode))
        self.is_heat_mode = bool(hass.get_state(entities.thermostat) == "heat")
        self.notify_user = bool(hass.get_state(entities.notify_user))
        self.update_temperature()

    """
    Updates the correct temperature to set based on the current state.
    """
    def update_temperature(self) -> None:
        self.update_thermostat_state()

        if self.thermostat_state == ThermostatState.Gone:
            self.set_temperature = self.day_temperature + self.get_offset(self.gone_offset)
            return

        temperature = self.day_temperature if self.is_day() else self.night_temperature
        self.set_temperature = temperature + self.get_offset(self.away_offset) if self.thermostat_state == ThermostatState.Away else temperature
    
    """
    Updates the current state of the thermostat based on where people are.
    """
    def update_thermostat_state(self) -> None:
        state = ThermostatState.Home

        if (int(self.hass.get_state(self.entities.zone_near_home)) == 0 and 
            int(self.hass.get_state(self.entities.zone_home)) == 0): # Nobody in either zones means people are far away.
            state = ThermostatState.Gone
        elif not self.hass.anyone_home(person=True):
            state = ThermostatState.Away

        self.thermostat_state = state

    
    """
    Day is considered the time between the start time of the day temperature
    and the start time of the night temperature.
    """
    def is_day(self) -> bool:
        return self.hass.now_is_between(str(self.day_time), str(self.night_time))

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
Stores the identifiers for HASS entities.
Example: day_time: input_datetime.climate_day_start
"""
class ClimateEntities:

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

"""
The various states the thermostat can be in.
"""
class ThermostatState(Enum):
    Home = auto(),
    Away = auto(),
    Gone = auto()