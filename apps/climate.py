import appdaemon.plugins.hass.hassapi as hass
from datetime import time
from enum import Enum, auto
import importlib

try:
    Person = importlib.import_module("utils.person").Person
except ModuleNotFoundError:
    Person = importlib.import_module("person").Person


class ThermostatState(Enum):
    """
    The various states the thermostat can be in.
    """

    Home = auto()
    Away = auto()
    Gone = auto()


class ClimateEntities:
    """
    Stores the identifiers for HASS entities.
    Example: day_time: input_datetime.climate_day_start
    """

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
    notify_time: str
    notify_location: str
    bedroom_fan: str
    bedroom_temperature: str

    def __init__(self, hass_instance: hass.Hass) -> None:
        self.allison = hass_instance.args["allison"]
        self.owen = hass_instance.args["owen"]
        self.day_time = hass_instance.args["day_time"]
        self.night_time = hass_instance.args["night_time"]
        self.day_temperature = hass_instance.args["day_temperature"]
        self.night_offset = hass_instance.args["night_offset"]
        self.away_minutes = hass_instance.args["climate_away_minutes"]
        self.away_offset = hass_instance.args["climate_away_offset"]
        self.gone_offset = hass_instance.args["climate_gone_offset"]
        self.vacation_mode = hass_instance.args["vacation_mode"]
        self.thermostat = hass_instance.args["thermostat"]
        self.thermostat_state = hass_instance.args["thermostat_state"]
        self.zone_home = hass_instance.args["zone_home"]
        self.zone_near_home = hass_instance.args["zone_near_home"]
        self.notify_time = hass_instance.args["notify_time"]
        self.notify_location = hass_instance.args["notify_location"]
        self.bedroom_fan = hass_instance.args["bedroom_fan"]
        self.bedroom_temperature = hass_instance.args["bedroom_temperature"]


class Climate(hass.Hass):
    """
    Due to AppDaemon limitations, we can't listen for zone enter/exit events within this file. To get around
    this, we use helper functions in HomeAssistant's built-in Automations area. These automations trigger on
    zone events and set the thermostat state, which we are listening on state changes to trigger functions.
    HomeAssistant climate helper automations: https://github.com/Owen-Krueger/HomeAssistantConfiguration/blob/main/automation/climate.yaml
    """

    entities: ClimateEntities
    day_time: time
    day_time_handler: str = None
    night_time: time
    night_time_handler: str = None
    away_state_handler: str = None

    def initialize(self) -> None:
        """
        Set up automation callbacks and state.
        """

        self.notification_utils = self.get_app("notification_utils")
        self.utils = self.get_app("utils")
        self.entities = ClimateEntities(self)
        self.day_time = self.parse_time(self.get_state(self.entities.day_time))
        self.night_time = self.parse_time(self.get_state(self.entities.night_time))
        entity_update_duration: int = 15
        away_duration_seconds: int = self.get_away_duration_seconds(self.get_state(self.entities.away_minutes))
        # Property updates
        self.listen_state(self.on_day_time_updated, self.entities.day_time, duration=entity_update_duration)
        self.listen_state(self.on_night_time_updated, self.entities.night_time, duration=entity_update_duration)
        self.listen_state(self.on_away_minutes_updated, self.entities.away_minutes,
                          duration=entity_update_duration)

        # Temperature update events
        self.listen_state(self.on_thermostat_state_updated, self.entities.thermostat_state)
        self.listen_state(self.on_person_state_updated, self.entities.allison, new="home")
        self.listen_state(self.on_person_state_updated, self.entities.owen, new="home")
        self.away_state_handler = self.listen_state(self.on_person_state_updated, self.entities.owen,
                                                    old="home", duration=away_duration_seconds)
        self.day_time_handler = self.run_daily(self.on_schedule_time, self.day_time)
        self.night_time_handler = self.run_daily(self.on_schedule_time, self.night_time)
        self.listen_state(self.on_current_temperature_updated, self.entities.thermostat,
                          attribute="current_temperature", duration=300)

    def on_day_time_updated(self, entity: str, attribute: str, old: str, new: str, args) -> None:
        """
        On climate day time set, cancel previous timer and set up a new one for the new time.
        """

        self.cancel_timer(self.day_time_handler)
        self.day_time = self.parse_time(new)
        self.day_time_handler = self.run_daily(self.on_schedule_time, self.day_time)
        self.log(f"day_time updated from {old} to {new}.")

    def on_night_time_updated(self, entity: str, attribute: str, old: str, new: str, args) -> None:
        """
        On climate nighttime set, cancel previous timer and set up a new one for the new time.
        """

        self.cancel_timer(self.night_time_handler)
        self.night_time = self.parse_time(new)
        self.night_time_handler = self.run_daily(self.on_schedule_time, self.night_time)
        self.log(f"night_time updated from {old} to {new}.")

    def on_away_minutes_updated(self, entity: str, attribute: str, old: str, new: str, args) -> None:
        """
        On away minutes updated, cancel away state listeners and set up new ones with new time.
        """

        self.cancel_listen_state(self.away_state_handler)
        away_duration_seconds = self.get_away_duration_seconds(new)
        self.away_state_handler = self.listen_state(self.on_person_state_updated, self.entities.owen, new="away",
                                                    duration=away_duration_seconds)
        self.log(f"away_minutes updated from {old} to {new}.")

    def on_schedule_time(self, args) -> None:
        """
        On climate day time or nighttime, update temperature.
        """

        state: ThermostatState = ThermostatState[self.get_state(self.entities.thermostat_state)]
        temperature: int = self.set_temperature(state)
        self.notify_time_based(f"Climate: Temperature set to {temperature}")

        if not self.is_day():
            self.turn_on_bedroom_fan()

    def on_person_state_updated(self, entity: str, attribute: str, old: str, new: str, args) -> None:
        """
        If someone is home or away, set state based on if anybody else is home or not.
        """

        existing_state = ThermostatState[self.get_state(self.entities.thermostat_state)]
        new_state = ThermostatState.Home
        anyone_home = self.anyone_home(person=True)

        if existing_state == ThermostatState.Gone and not anyone_home:
            new_state = ThermostatState.Gone
        elif not anyone_home:
            new_state = ThermostatState.Away

        self.set_state(self.entities.thermostat_state, state=new_state.name)

    def on_thermostat_state_updated(self, entity: str, attribute: str, old: str, new: str, args) -> None:
        """
        On state updated, set temperature based on state.
        """

        new_state = ThermostatState[new]
        temperature: int = self.set_temperature(new_state)
        self.notify_location_based(f"Climate: Temperature set to {temperature}")

        if new_state == ThermostatState.Home and not self.is_day():
            self.turn_on_bedroom_fan()

    def on_current_temperature_updated(self, entity: str, attribute: str, old: str, new: str, args) -> None:
        """
        On the current temperature of the thermostat changed, check if it's deviated too much
        from what's currently set at.
        """

        # If nobody is home, there's no need to notify anyone, because the
        # temperature is expected to be deviating.
        if not self.anyone_home(person=True):
            return

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
            self.notification_utils.notify_users(
                f"House is too hot! (Current: {current_temperature} Set: {set_temperature})", Person.Owen)
        elif not is_heat_mode and temperature_difference <= -2:
            self.notification_utils.notify_users(
                f"House is too cold! (Current: {current_temperature} Set: {set_temperature})", Person.Owen)

    def set_temperature(self, state: ThermostatState) -> int:
        """
        Sets the temperature of the thermostat based on the state.
        """

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

    def get_new_temperature(self, state: ThermostatState) -> int:
        """
        Updates the correct temperature to set based on the current state.
        """

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

    def is_day(self) -> bool:
        """
        Day is considered the time between the start time of the day temperature
        and the start time of the night temperature.
        """

        # Subtract 5 seconds from the user set day time to get rid of an edge case where
        # the automation running fast could result in `now_is_between` returning false.
        day_time = self.utils.add_seconds(self.day_time, -5)
        return self.now_is_between(str(day_time), str(self.night_time))

    def get_offset(self, offset: int) -> int:
        """
        Gets the correct offset, based on if the thermostat is in heat or cool mode.
        If mode is heat, we want to be cooler, so we multiply the offset by -1.
        If mode is cool, we want to be hotter, so the offset stays as is.
        Example: Offset = 5
        Heat: -5
        Cool: 5
        """
        
        return offset * -1 if self.is_heat_mode() else offset

    def is_heat_mode(self) -> bool:
        """
        Whether on not the thermostat is currently heating or cooling.
        """

        return bool(self.get_state(self.entities.thermostat) == "heat")

    def notify_time_based(self, message: str) -> None:
        """
        Notify user if notify user (time based) boolean is set.
        """

        if self.utils.is_entity_on(self.entities.notify_time):
            self.notification_utils.notify_users(message, Person.Owen, True)

    def notify_location_based(self, message: str) -> None:
        """
        Notify user if notify user (location based) boolean is set.
        """
        
        if self.utils.is_entity_on(self.entities.notify_location):
            self.notification_utils.notify_users(message, Person.Owen)

    def get_away_duration_seconds(self, state: str) -> int:
        """
        Converts state string to an integer (minutes) and multiplies to get seconds
        needed for AppDaemon durations.
        """
        
        return self.utils.get_input_number_integer(state) * 60

    def get_input_number_from_state(self, entity_id: str) -> int:
        """
        Gets the integer representation of the state of the input entity.
        """

        return self.utils.get_input_number_integer(self.get_state(entity_id))

    def get_set_temperature(self) -> int:
        """
        Gets the currently set temperature for the thermostat.
        """

        return int(self.get_state(self.entities.thermostat, attribute="temperature"))

    def turn_on_bedroom_fan(self) -> None:
        """
        Checks if the bedroom is currently warmer than the set temperature. If it's too
        hot, the bedroom fan is turned on.
        """

        if float(self.get_state(self.bedroom_temperature)) > float(self.get_set_temperature):
            self.turn_on(self.bedroom_fan)
