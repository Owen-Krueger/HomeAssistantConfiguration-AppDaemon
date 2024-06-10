import appdaemon.plugins.hass.hassapi as hass


class OffLighting(hass.Hass):
    """
    Turning lights off automations.
    """

    all_off: str
    all_off_dynamic: str
    allison: str
    downstairs_active: str
    downstairs_lights: str
    mode_guest: str
    office_lights: str
    owen: str
    owen_computer_active: str
    owen_phone_charger_type: str
    night_lighting: str
    upstairs_active: str
    upstairs_living_area_off: str
    vacation_mode: str

    async def initialize(self):
        """
        Sets up the automation.
        """

        self.utils = self.get_app("utils")
        self.all_off = self.args["all_off"]
        self.all_off_dynamic = self.args["all_off_dynamic"]
        self.allison = self.args["allison"]
        self.downstairs_active = self.args["downstairs_active"]
        self.downstairs_lights = self.args["downstairs_lights"]
        self.mode_guest = self.args["mode_guest"]
        self.office_lights = self.args["office_lights"]
        self.owen = self.args["owen"]
        self.owen_computer_active = self.args["owen_computer_active"]
        self.owen_phone_charger_type = self.args["owen_phone_charger_type"]
        self.night_lighting = self.args["night_lighting"]
        self.upstairs_active = self.args["upstairs_active"]
        self.upstairs_living_area_off = self.args["upstairs_living_area_off"]
        self.vacation_mode = self.args["vacation_mode"]

        await self.listen_state(self.turn_off_lights, self.allison, new="not_home",
                                duration=300)  # When away for 5 minutes.
        await self.listen_state(self.turn_off_lights, self.owen, new="not_home",
                                duration=300)  # When away for 5 minutes.
        await self.listen_state(self.turn_off_lights_at_night, self.owen_phone_charger_type, new="wireless",
                                duration=10)  # When phone charging for 10 seconds.
        await self.listen_event(self.active_night_lighting,
                                "CUSTOM_EVENT_NIGHT_LIGHTING")  # When a night lighting event is triggered.

    """
    Checks who is home. If everyone is gone, all lights are turned off.
    If only Allison is gone and Owen is at work, turn on office lighting.
    """

    async def turn_off_lights(self, entity: str, attribute: str, old: str, new: str, kwargs):
        self.log("Executing automation.")
        if await self.utils.is_entity_on(self.mode_guest):
            return

        owen_home = await self.utils.is_entity_home(self.owen)
        allison_home = await self.utils.is_entity_home(self.allison)

        if not owen_home and not allison_home:
            self.log("Everyone away. Turning off all lights.")
            await self.turn_on(self.all_off)
        else:
            self.log("Turning off lights depending on state.")
            await self.turn_on(self.all_off_dynamic)
            await self.turn_off_lights_based_on_state()

    """
    Turns on night lighting scene.
    """

    async def active_night_lighting(self, event_name: str, data, kwargs):
        self.log("Turning on night lighting.")
        await self.turn_on(self.night_lighting)
        await self.turn_off_lights_based_on_state()

    """
    Turns off any lights that are on and don't have activity in that room.
    """

    async def turn_off_lights_based_on_state(self):
        await self.utils.set_state_conditionally(self.upstairs_active, "off",
                                                 self.upstairs_living_area_off, "on")
        await self.utils.set_state_conditionally(self.downstairs_active, "off",
                                                 self.downstairs_lights, "off")
        await self.utils.set_state_conditionally(self.owen_computer_active, "off",
                                                 self.office_lights, "off")

    """
    At night, turn off all lights in the house once people are sleeping.
    """

    async def turn_off_lights_at_night(self, entity: str, attribute: str, old: str, new: str, kwargs):
        if (not await self.utils.is_entity_on(self.vacation_mode) and
                await self.utils.is_entity_home(self.owen) and
                self.now_is_between("20:30:00", "03:00:00")):
            self.log("Turning off all lights due to phone charging at night.")
            await self.turn_on(self.all_off)
