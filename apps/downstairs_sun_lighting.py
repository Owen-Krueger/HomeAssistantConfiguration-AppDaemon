import appdaemon.plugins.hass.hassapi as hass


class DownstairsSunLighting(hass.Hass):
    """
    Sets downstairs light level depending on the elevation of the sun.
    """

    downstairs_lights: str
    sun: str

    async def initialize(self):
        """
        Sets up the automation.
        """

        self.downstairs_lights = self.args["downstairs_lights"]
        self.sun = self.args["sun"]

        # Wait 5 seconds to make sure brightness is available as an attribute.
        await self.listen_state(self.set_downstairs_light_level, self.downstairs_lights, new="on", duration=5)
        await self.listen_state(self.set_downstairs_light_level, self.sun, attribute="elevation",
                                old=lambda x: int(x) >= 10,
                                new=lambda x: int(x) < 10)  # Around sunset
        await self.listen_state(self.set_downstairs_light_level, self.sun, attribute="elevation",
                                old=lambda x: int(x) < 10,
                                new=lambda x: int(x) >= 10)  # Around sunrise

    """
    Sets downstairs light level depending on the elevation of the sun.
    If sun is at or above 10 degrees, set lights to 100% if not already.
    If sun is below 10 degrees, set lights to 50% if not already.
    """

    async def set_downstairs_light_level(self, entity: str, attribute: str, old: str, new: str, cb_args):
        brightness_str = await self.get_state(self.downstairs_lights, attribute="brightness")
        if brightness_str is None:  # Light is most likely off
            return

        elevation = int(await self.get_state(self.sun, attribute="elevation"))
        brightness = int(brightness_str)
        if elevation >= 10 and brightness != 255:  # 100% brightness
            self.log("Setting downstairs lights to 100% brightness")
            await self.set_state(self.downstairs_lights, state="on", attributes={"brightness": "255"})
        elif elevation < 10 and brightness != 128:  # 50% brightness
            self.log("Setting downstairs lights to 50% brightness")
            await self.set_state(self.downstairs_lights, state="on", attributes={"brightness": "128"})
