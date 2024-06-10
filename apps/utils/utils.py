import appdaemon.plugins.hass.hassapi as hass
from datetime import datetime, timedelta, time


class Utils(hass.Hass):
    """
    Utility functions to be used by other scripts.
    """

    async def is_entity_on(self, entity: str) -> bool:
        """
        Returns if the entity state is currently "on".
        """

        return await self.get_state(entity) == "on"

    async def is_entity_home(self, entity: str) -> bool:
        """
        Returns if the entity state is currently "home".
        """

        return await self.get_state(entity) == "home"

    async def get_time(self, entity: str):
        """
        Gets the time from the entity's state.
        """

        return self.parse_time(await self.get_state(entity))

    async def close_to_home(self, entity: str) -> bool:
        """
        Gets direction and miles away to determine if entity is close to home.
        """

        state = await self.get_state(entity, attribute="all")
        miles_away = int(state["state"])
        direction = state["attributes"]["dir_of_travel"]

        return 0 < miles_away < 5 and direction == "towards"

    async def recently_triggered(self, entity: str, seconds: int = 2) -> bool:
        """
        Returns if the entity has been triggered recently (within the
        number of seconds inputted or two seconds if not specified).
        """

        last_changed = datetime.strptime(await self.get_state(entity, attribute="last_changed"),
                                         "%Y-%m-%dT%H:%M:%S.%f%z")

        return await self.datetime(True) <= last_changed + timedelta(seconds=seconds)

    async def sync_entities(self, correct_entity: str, entity_to_sync: str):
        """
        Syncs the states between two entities. `correct_entity` is the one to get state from.
        `entity_to_sync` is the entity to set to the state of the `correct_entity`.
        """

        correct_entity_state = self.is_entity_on(correct_entity)

        if correct_entity_state == self.is_entity_on(entity_to_sync):
            return

        if correct_entity_state:
            await self.turn_on(entity_to_sync)
        else:
            await self.turn_off(entity_to_sync)

    async def set_state_conditionally(self, entity_to_test: str, expected_state: str, entity_to_set: str, state_to_set: str):
        """
        If the state of `entity_to_test` matches `expected_state`, turn on or off
        `entity_to_set` based on `turn_on`.
        """

        current_state = await self.get_state(entity_to_test)
        self.log("Setting state conditionally for {}. Current state: {} Expected State: {} New State: {}",
                 entity_to_test, current_state, expected_state, state_to_set)

        if current_state == expected_state and current_state != state_to_set:
            await self.set_state(entity_to_set, state=state_to_set)

    def get_input_number_integer(self, state: str) -> int:
        """
        input_number is represented as a float string in HA. To convert these values
        to an integer, we must first cast the string to a float, and then cast it
        to an int.
        """

        return int(float(state))

    def notify_owen(self, message: str) -> None:
        """
        Notifies Owen with the provided message.
        """

        self.notify(message, name="owen")

    def notify_owen_if_people_home(self, message: str) -> None:
        """
        Notifies Owen with the provided message, if someone is home.
        """

        if self.anyone_home(person=True):
            self.notify(message, name="owen")

    def add_seconds(self, initial_time: time, seconds: int) -> time:
        """
        Adds input seconds to the input time by converting it to a datetime object,
        adding the seconds, and then converting back to a time object.
        """

        date = datetime.combine(datetime(2000, 1, 1), initial_time)
        date - timedelta(seconds=seconds)
        return date.time()
