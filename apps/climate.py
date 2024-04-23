import appdaemon.plugins.hass.hassapi as hass
from datetime import datetime, time
from enum import Enum, auto

"""
The various states the thermostat can be in.
"""
class ThermostatState(Enum):
    Home = auto(),
    Away = auto(),
    Gone = auto()

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
    night_offset: str
    away_minutes: str
    away_offset: str
    gone_offset: str
    vacation_mode: str
    thermostat: str
    thermostat_state: str
    zone_home: str
    zone_near_home: str
    notify_user: str

    def __init__(self, hass: hass.Hass) -> None:
        self.allison = hass.args["allison"]
        self.owen = hass.args["owen"]
        self.day_time = hass.args["day_time"]
        self.night_time = hass.args["night_time"]
        self.day_temperature = hass.args["day_temperature"]
        self.night_offset = hass.args["night_offset"]
        self.away_minutes = hass.args["climate_away_minutes"]
        self.away_offset = hass.args["climate_away_offset"]
        self.gone_offset = hass.args["climate_gone_offset"]
        self.vacation_mode = hass.args["vacation_mode"]
        self.thermostat = hass.args["thermostat"]
        self.thermostat_state = hass.args["thermostat_state"]
        self.zone_home = hass.args["zone_home"]
        self.zone_near_home = hass.args["zone_near_home"]
        self.notify_user = hass.args["notify_user"]

"""
Due to AppDaemon limitations, we can't listen for zone enter/exit events within this file. To get around
this, we use helper functions in HomeAssistant's built-in Automations area. These automations trigger on
zone events and set the thermostat state, which we are listening on state changes to trigger functions.
HomeAssistant climate helper automations: https://github.com/Owen-Krueger/HomeAssistantConfiguration/blob/main/automation/climate.yaml
"""
class Climate(hass.Hass):

    entities: ClimateEntities
    day_time: time
    day_time_handler: str = None
    night_time: time
    night_time_handler: str = None
    away_state_handler: str = None
    deviation_listener_handler: str = None

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
        self.listen_state(self.on_away_minutes_updated, self.entities.away_minutes, duration = ENTITY_UPDATE_DURATION)

        # Temperature update events
        self.listen_state(self.on_thermostat_state_updated, self.entities.thermostat_state)
        self.listen_state(self.on_person_state_updated, self.entities.allison, new = "home")
        self.listen_state(self.on_person_state_updated, self.entities.owen, new = "home")
        self.away_state_handler = self.listen_state(self.on_person_state_updated, self.entities.owen, old = "home", duration = away_duration_seconds)
        self.day_time_handler = self.run_daily(self.on_schedule_time, self.day_time)
        self.night_time_handler = self.run_daily(self.on_schedule_time, self.night_time)

        # We only want this automation running if people are home. Otherwise, 
        # the temperature probably will be deviating.
        if self.anyone_home(person=True):
            self.update_deviation_handler(True)

    """
    On climate day time set, cancel previous timer and set up a new one for the new time.
    """
    def on_day_time_updated(self, entity: str, attribute: str, old: str, new: str, args) -> None:
        self.cancel_timer(self.day_time_handler)
        self.day_time = self.parse_time(new)
        self.day_time_handler = self.run_daily(self.on_schedule_time, self.day_time)
        self.log(f"day_time updated from {old} to {new}.")

    """
    On climate night time set, cancel previous timer and set up a new one for the new time.
    """
    def on_night_time_updated(self, entity: str, attribute: str, old: str, new: str, args) -> None:
        self.cancel_timer(self.night_time_handler)
        self.night_time = self.parse_time(new)
        self.night_time_handler = self.run_daily(self.on_schedule_time, self.night_time)
        self.log(f"night_time updated from {old} to {new}.")

    """
    On away minutes updated, cancel away state listeners and set up new ones with new time.
    """
    def on_away_minutes_updated(self, entity: str, attribute: str, old: str, new: str, args) -> None:
        self.cancel_listen_state(self.away_state_handler)
        away_duration_seconds = self.get_away_duration_seconds(new)
        self.away_state_handler = self.listen_state(self.on_person_state_updated, self.entities.owen, new = "away", duration = away_duration_seconds)
        self.log(f"away_minutes updated from {old} to {new}.")

    """
    On climate day time or night time, update temperature.
    """
    def on_schedule_time(self, args) -> None:
        state: ThermostatState = ThermostatState[self.get_state(self.entities.thermostat_state)]
        temperature: int = self.set_temperature(state)
        self.notify_user(f"Climate: Temperature set to {temperature}")

    """
    If someone is home or away, set state based on if anybody else is home or not.
    """
    def on_person_state_updated(self, entity: str, attribute: str, old: str, new: str, args) -> None:
        existing_state = ThermostatState[self.get_state(self.entities.thermostat_state)]
        new_state = ThermostatState.Home
        anyone_home = self.anyone_home(person=True)

        if existing_state == ThermostatState.Gone and not anyone_home:
            new_state = ThermostatState.Gone
        elif not anyone_home:
            new_state = ThermostatState.Away

        self.set_state(self.entities.thermostat_state, state = new_state.name)
        self.update_deviation_handler(new_state == ThermostatState.Home)

    """
    On state updated, set temperature based on state.
    """
    def on_thermostat_state_updated(self, entity: str, attribute: str, old: str, new: str, args) -> None:
        temperature: int = self.set_temperature(ThermostatState[new])
        self.notify_user(f"Climate: Temperature set to {temperature}")

    """
    On the current temperature of the thermostat changed, check if it's deviated too much
    from what's currently set at.
    """
    def on_current_temperature_updated(self, entity: str, attribute: str, old: str, new: str, args) -> None:
        previous_temperature = int(old)
        current_temperature = int(new)
        set_temperature = self.get_set_temperature()
        is_heat_mode = self.is_heat_mode()
        temperature_difference = current_temperature - set_temperature
        
        # Don't notify if the temperature is not going in a concerning direction.
        if is_heat_mode and current_temperature <= previous_temperature:
            return
        elif not is_heat_mode and current_temperature >= previous_temperature:
            return

        if is_heat_mode and temperature_difference >= 2:
            self.utils.notify_owen(f"House is too hot! (Current: {current_temperature} Set: {set_temperature})")
        elif not is_heat_mode and temperature_difference <= -2:
            self.utils.notify_owen(f"House is too cold! (Current: {current_temperature} Set: {set_temperature})")

    """
    Sets the temperature of the thermostat based on the state.
    """
    def set_temperature(self, state: ThermostatState) -> int:
        current_temperature: int = self.get_set_temperature()
        new_temperature = self.get_new_temperature(state)
        self.log(f"Temperature update requested. Old: {current_temperature} New: {new_temperature}")

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
    def get_new_temperature(self, state: ThermostatState) -> int:
        day_temperature = self.get_input_number_from_state(self.entities.day_temperature)
        night_offset = self.get_input_number_from_state(self.entities.night_offset)

        if state == ThermostatState.Gone:
            gone_offset = self.get_input_number_from_state(self.entities.gone_offset)
            return day_temperature + self.get_offset(gone_offset)

        temperature = day_temperature if self.is_day() else day_temperature - night_offset
        if state == ThermostatState.Away:
            away_offset = self.get_input_number_from_state(self.entities.away_offset)
            return temperature + self.get_offset(away_offset)

        return temperature

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
        return offset * -1 if self.is_heat_mode() else offset

    """
    Whether on not the thermostat is currently heating or cooling.
    """
    def is_heat_mode(self) -> bool:
        return bool(self.get_state(self.entities.thermostat) == "heat")

    """
    Notify user if notify user boolean is set.
    """
    def notify_user(self, message: str) -> None:
        if self.utils.is_entity_on(self.entities.notify_user):
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

    """
    Gets the currently set temperature for the thermostat.
    """
    def get_set_temperature(self) -> int:
        return int(self.get_state(self.entities.thermostat, attribute = "temperature"))

    """
    Updates the deviation automation handler to be active/inactive dependending on the input.
    """
    def update_deviation_handler(self, active: bool) -> None:
        is_handler_active: bool = self.deviation_listener_handler != None
        if is_handler_active: # Cancel existing handler.
            self.cancel_listen_state(self.deviation_listener_handler)
        
        if active: # Set up a new handler.
            self.deviation_listener_handler = self.listen_state(self.on_current_temperature_updated, self.entities.thermostat, attribute = "current_temperature", duration = 300) if active else None
