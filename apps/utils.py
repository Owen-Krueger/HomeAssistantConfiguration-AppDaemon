import hassapi as hass
from datetime import datetime, timedelta

"""
Utility functions to be used by other scripts.
"""
class Utils(hass.Hass):
    
    """
    Returns if the entity state is currently "on".
    """
    def is_entity_on(self, entity: str) -> bool:
        return self.get_state(entity) == "on"

    """
    Returns if the entity state is currently "home".
    """
    def is_entity_home(self, entity: str) -> bool:
        return self.get_state(entity) == "home"

    """
    Gets the time from the entity's state.
    """
    def get_time(self, entity: str):
        return self.parse_time(self.get_state(entity))

    """
    Gets direction and miles away to determine if entity is close to home.
    """
    def close_to_home(self, entity: str) -> bool:
        state = self.get_state(entity, attribute="all")
        miles_away = int(state["state"])
        direction = state["attributes"]["dir_of_travel"]

        return miles_away > 0 and miles_away < 5 and direction == "towards"

    """
    Returns if the entity has been triggered recently (within the
    number of seconds inputted or two seconds if not specified).
    """
    def recently_triggered(self, entity: str, seconds: int = 2) -> bool:
        last_changed = datetime.strptime(self.get_state(entity, attribute="last_changed"), "%Y-%m-%dT%H:%M:%S.%f%z")

        return self.datetime(True) <= last_changed + timedelta(seconds=seconds)

    """
    Syncs the states between two entities. `correct_entity` is the one to get state from.
    `entity_to_sync` is the entity to set to the state of the `correct_entity`.
    """
    def sync_entities(self, correct_entity: str, entity_to_sync: str):
        correct_entity_state = self.is_entity_on(correct_entity)

        if correct_entity_state == self.is_entity_on(entity_to_sync):
            return

        if correct_entity_state:
            self.turn_on(entity_to_sync)
        else:
            self.turn_off(entity_to_sync)

    """
    If the state of `entity_to_test` matches `expected_state`, turn on or off
    `entity_to_set` based on `turn_on`.
    """
    def set_state_conditionally(self, entity_to_test: str, expected_state: str, entity_to_set: str, state_to_set: str):
        current_state = self.get_state(entity_to_test)
        self.log("Setting state conditionally. Current state: {} Expected State: {} New State: {}", current_state, expected_state, state_to_set)

        if current_state == expected_state and current_state != state_to_set:
            self.set_state(entity_to_set, state=state_to_set)