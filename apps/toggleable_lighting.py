import appdaemon.plugins.hass.hassapi as hass


class ToggleableLighting(hass.Hass):
    """
    Automation to toggle lights on and off due to events received.
    """

    async def initialize(self):
        """
        Sets up the automations.
        """

        self.utils = self.get_app("utils")

        for event in self.args["dictionary"]:
            await self.listen_event(self.toggle_light, "zha_event", device_id=event["event_device_id"],
                                    command=event["command"], lights=event["lights"])

    """
    Turns light on if currently off and turns light off if currently on.
    """
    async def toggle_light(self, event_name: str, data, kwargs):
        lights = kwargs["lights"]

        first_light = lights[0]
        # Prevents duplicate events from toggling the light more than once.
        if await self.utils.recently_triggered(first_light):
            self.log("{} recently triggered. Not toggling.".format(lights))
            return

        # This is a work-around where sometimes lights get out of sync.
        current_state = await self.utils.is_entity_on(first_light)
        self.log("Toggle triggered for {}. Turning light {}.".format(lights, "off" if current_state else "on"))

        # Go through the lights and turn them all on/off.
        for light in lights:
            if current_state:
                await self.turn_off(light)
            else:
                await self.turn_on(light)
