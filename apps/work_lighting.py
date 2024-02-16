import hassapi as hass

"""
For automations based on the computer being active.
"""
class WorkLighting(hass.Hass):

    """
    Sets up the automation.
    """
    def initialize(self):
        self.utils = self.get_app("utils")
        self.dining_room_lights = self.args["dining_room_lights"]
        self.is_work_day = self.args["is_work_day"]
        self.mode_guest = self.args["mode_guest"]
        self.office_lights = self.args["office_lights"]
        self.owen = self.args["owen"]

        self.listen_state(self.on_office_light_off, self.office_lights, new = "off", duration = 30) # When office lights turned off for 30 seconds

    """
    Automations office lights turned off. Turns on dining room lights
    if lunchtime and they're currently off.
    """
    def on_office_light_off(self, entity: str, attribute: str, old: str, new: str, kwargs):
        self.log("Executing automations due to office lights being turned off.")

        # If Owen is home, it's a work day, and it's around lunch time.
        if (not self.utils.is_entity_on(self.mode_guest) and
            not self.utils.is_entity_on(self.dining_room_lights) and
            self.utils.is_entity_home(self.owen) and
            self.utils.is_entity_on(self.is_work_day) and
            self.now_is_between("11:00:00", "13:30:00")):
            self.turn_on(self.dining_room_lights)