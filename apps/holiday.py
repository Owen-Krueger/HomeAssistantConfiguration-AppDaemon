import appdaemon.plugins.hass.hassapi as hass
from datetime import datetime, time

"""
Automations for managing holiday lights.
"""
class Holiday(hass.Hass):

    on_holiday_time_handler: str = None
    off_holiday_time_handler: str = None
    allison_home_handler: str = None
    allison_away_handler: str = None
    christmas_tree_smart_plug_id: str
    allison_id: str

    """
    Sets up automations.
    """
    def initialize(self) -> None:
        self.utils = self.get_app("utils")
        holiday_mode_id = self.args["holiday_mode"]
        self.christmas_tree_smart_plug_id = self.args["christmas_tree_smart_plug"]
        self.allison_id = self.args["allison"]

        self.listen_state(self.on_holiday_mode_updated, holiday_mode_id, duration = 15)

        if self.utils.is_entity_on(holiday_mode_id):
            self.set_up_handlers()

    """
    Sets up automation handlers.
    """
    def set_up_handlers(self) -> None:
        self.log("Setting up handlers.")
        self.on_holiday_time_handler = self.run_daily(self.on_holiday_lights_on, datetime.time(7, 0, 0))
        self.off_holiday_time_handler = self.run_daily(self.on_holiday_lights_off, datetime.time(22, 0, 0))
        self.allison_home_handler = self.listen_state(self.on_person_state_changed, self.allison_id, new = "home")
        self.allison_away_handler = self.listen_state(self.on_person_state_changed, self.allison_id, old = "home", duration = 300) # 5 minutes

    """
    Cancels any active handlers.
    """
    def cancel_handlers(self) -> None:
        self.log("Cancelling existing handlers.")
        if self.on_holiday_time_handler != None:
            self.cancel_timer(self.on_holiday_time_handler)
        if self.off_holiday_time_handler != None:
            self.cancel_timer(self.off_holiday_time_handler)
        if self.allison_home_handler != None:
            self.cancel_listen_state(self.allison_home_handler)
        if self.allison_away_handler != None:
            self.cancel_listen_state(self.allison_away_handler)

    """
    When holiday mode input boolean is updated, cancel any existing handlers. Set up handlers
    if boolean was turned on. If boolean was turned off and the lights are actively on, turn
    them off.
    """
    def on_holiday_mode_updated(self, entity: str, attribute: str, old: str, new: str, args) -> None:
        self.cancel_handlers() # Cancel any existing handlers.

        if new == "on":
            self.set_up_handlers()

        # Turn off lights if we are no longer in holiday mode but lights are still on.
        if new == "off" and not self.utils.is_entity_on(self.christmas_tree_smart_plug_id):
            self.log("Holiday mode turned off, but lights are actively on. Turning off.")
            self.turn_off(self.christmas_tree_smart_plug_id)

    """
    On Allison state updated, check if she's home or away. If away, turn lights off. If home,
    turn lights on.
    """
    def on_person_state_changed(self, entity: str, attribute: str, old: str, new: str, args) -> None:
        if new == "home":
            self.set_lights_state(True)
        elif old == "home":
            self.set_lights_state(False)

    """
    On holiday lights on time, turn on lights if Allison is home.
    """
    def on_holiday_lights_on(self, args) -> None:
        if self.utils.is_entity_home(self.allison_id):
            self.set_lights_state(True)

    """
    On holiday lights off time, turn off lights, no matter what.
    """
    def on_holiday_lights_off(self, args) -> None:
        self.set_lights_state(False)

    """
    Updates the holiday lights depending on the input state.
    """
    def set_lights_state(self, state: bool) -> None:
        current_state = self.utils.is_entity_on(self.christmas_tree_smart_plug_id)

        if state == True and not current_state:
            self.log("Turning on holiday lights.")
            self.turn_on(self.christmas_tree_smart_plug_id)
        elif state == False and current_state:
            self.log("Turning off holiday lights.")
            self.turn_off(self.christmas_tree_smart_plug_id)