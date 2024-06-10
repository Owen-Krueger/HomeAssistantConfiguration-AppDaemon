import appdaemon.plugins.hass.hassapi as hass


class TelevisionLighting(hass.Hass):
    """
    Turns lights on and off due to state of televisions.
    """

    downstairs_lights: str
    downstairs_tv_on: str
    living_room_automations_on: str
    living_room_lamps: str
    is_work_day: str
    mode_guest: str
    owen: str
    upstairs_tv_on: str
    vacation_mode: str
    downstairs_tv_on_handler: str
    upstairs_tv_on_lamp_handler: str
    upstairs_tv_off_lamp_handler: str
    upstairs_tv_off_handler: str

    async def initialize(self):
        """
        Sets up the automation.
        """

        self.utils = self.get_app("utils")
        self.downstairs_lights = self.args["downstairs_lights"]
        self.downstairs_tv_on = self.args["downstairs_tv_on"]
        self.living_room_automations_on = self.args["living_room_automations_on"]
        self.living_room_lamps = self.args["living_room_lamps"]
        self.is_work_day = self.args["is_work_day"]
        self.mode_guest = self.args["mode_guest"]
        self.owen = self.args["owen"]
        self.upstairs_tv_on = self.args["upstairs_tv_on"]
        self.vacation_mode = self.args["vacation_mode"]

        if await self.utils.is_entity_on(self.living_room_automations_on):
            await self.set_up_triggers()  # Sets up listeners for TV statuses

        await self.listen_state(self.on_boolean_change, self.living_room_automations_on,
                          duration=30)  # Only update the automation triggers when boolean is set for 30 seconds.

    """
    Sets up triggers for downstairs and upstairs TVs.
    """

    async def set_up_triggers(self):
        self.downstairs_tv_on_handler = await self.listen_state(self.turn_on_lights, self.downstairs_tv_on, new="on",
                                                                duration=15)
        self.upstairs_tv_on_lamp_handler = await self.listen_state(self.turn_on_lights, self.upstairs_tv_on, new="on",
                                                                   duration=15)
        self.upstairs_tv_off_lamp_handler = await self.listen_state(self.turn_off_living_room_lamps,
                                                                    self.upstairs_tv_on,
                                                                    new="off",
                                                                    duration=120)
        self.upstairs_tv_off_handler = await self.listen_state(self.turn_on_downstairs_lights_during_work,
                                                               self.upstairs_tv_on,
                                                               new="off")  # Any time the upstairs TV is turned off.

    """
    On living room automations boolean change, cancel listeners if they're active and
    re-set them up if living room light should be automated
    """

    async def on_boolean_change(self, entity: str, attribute: str, old: str, new: str, kwargs):
        self.log("Living room automations boolean changed: {}".format(new))

        if old == "on":  # Cancel old listeners if they were active.
            await self.cancel_listen_state(self.downstairs_tv_on_handler)
            await self.cancel_listen_state(self.upstairs_tv_on_lamp_handler)
            await self.cancel_listen_state(self.upstairs_tv_off_lamp_handler)
            await self.cancel_listen_state(self.upstairs_tv_off_handler)

        if new == "on":
            self.set_up_triggers()

    """
    Turn on lights depending on which TV is on.
    """

    async def turn_on_lights(self, entity: str, attribute: str, old: str, new: str, kwargs):
        if not await self.now_is_between("05:30:00", "21:00:00"):  # So lights don't turn on while we're sleeping.
            self.log("{} on but it's late. Not turning lights on.".format(entity))
            return

        if await self.utils.is_entity_on(self.vacation_mode):  # So lights don't turn on in vacation mode.
            self.log("{} on, but in vacation mode. Not turning lights on.".format(entity))
            return

        entity_to_turn_on = self.downstairs_lights if entity == self.downstairs_tv_on else self.living_room_lamps
        self.log("{} turned on. Turning on {}.".format(entity, entity_to_turn_on))

        if not await self.utils.is_entity_on(entity_to_turn_on):
            await self.turn_on(entity_to_turn_on)
        else:
            self.log("{} already on.".format(entity_to_turn_on))

    """
    Turn off living room lamps if they're currently on.
    """

    async def turn_off_living_room_lamps(self, entity: str, attribute: str, old: str, new: str, kwargs):
        if await self.utils.is_entity_on(self.living_room_lamps):
            self.log("Turning off living room lamps due to Upstairs TV being off.")
            await self.turn_off(self.living_room_lamps)

    """
    Turns on the downstairs lights if it's a workday and a period where Owen
    typically walks from upstairs to downstairs.
    """

    async def turn_on_downstairs_lights_during_work(self, entity: str, attribute: str, old: str, new: str, kwargs):
        # If Owen is home, it's a work day, and it's around a time that Owen may be in the basement.
        if (not await self.utils.is_entity_on(self.upstairs_tv_on) and
                not await self.utils.is_entity_on(self.mode_guest) and
                not await self.utils.is_entity_on(self.downstairs_lights) and
                await self.utils.is_entity_home(self.owen) and
                await self.utils.is_entity_on(self.is_work_day) and
                (self.now_is_between("11:00:00", "13:30:00") or
                 self.now_is_between("06:00:00", "09:00:00"))):
            self.log("Turning on downstairs lights.")
            await self.turn_on(self.downstairs_lights)
