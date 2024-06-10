import appdaemon.plugins.hass.hassapi as hass


class BedroomLighting(hass.Hass):
    """
    Bedroom lighting automations.
    """

    bedroom_button_device_id: str
    bedroom_lamps: str
    bedroom_lights: str

    def initialize(self):
        """
        Sets up the automation.
        """

        self.utils = self.get_app("utils")
        self.bedroom_button_device_id = self.args["bedroom_button_device_id"]
        self.bedroom_lamps = self.args["bedroom_lamps"]
        self.bedroom_lights = self.args["bedroom_lights"]

        self.listen_event(self.on_bedside_button_click, "zha_event", device_id=self.bedroom_button_device_id,
                          command="single")
        self.listen_state(self.activate_night_lighting, self.bedroom_lights, old="on", new="off")
        self.listen_state(self.activate_night_lighting, self.bedroom_lamps, old="off", new="on")

    def on_bedside_button_click(self, event_name: str, data, kwargs):
        """
        On bedroom bedside button clicked, toggle the bedroom lamps.
        If late and bedroom lights on, also turn them off.
        """

        self.toggle(self.bedroom_lamps)

        if self.is_late() and self.utils.is_entity_on(self.bedroom_lights):
            self.turn_off(self.bedroom_lights)

    def activate_night_lighting(self, entity: str, attribute: str, old: str, new: str, kwargs):
        """
        If late, turn on bedroom lamps and turn off bedroom lights.
        """

        if not self.is_late():
            return

        self.turn_on(self.bedroom_lamps)
        self.turn_off(self.bedroom_lights)

    def is_late(self) -> bool:
        """
        Returns if it's late at night.
        """

        return self.now_is_between("21:00:00", "23:59:59")
