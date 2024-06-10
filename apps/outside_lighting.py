import appdaemon.plugins.hass.hassapi as hass
import datetime


class OutsideLighting(hass.Hass):
    """
    Outside lighting automations.
    """

    default_time: datetime.time
    allison: str
    owen: str
    porch_off_time: str
    should_override_time: str
    front_porch_switch: str
    proximity_allison: str
    proximity_owen: str
    holiday_lights: str
    holiday_mode: str
    handle: str

    async def initialize(self):
        """
        Sets up the automation.
        """

        self.utils = self.get_app("utils")
        self.default_time = datetime.time(22, 0, 0)
        self.allison = self.args["allison"]
        self.owen = self.args["owen"]
        self.porch_off_time = self.args["porch_off_time"]
        self.should_override_time = self.args["should_override_time"]
        self.front_porch_switch = self.args["front_porch_switch"]
        self.proximity_allison = self.args["proximity_allison"]
        self.proximity_owen = self.args["proximity_owen"]
        self.holiday_lights = self.args["holiday_lights"]
        self.holiday_mode = self.args["holiday_mode"]

        # Turn lights on 15 minutes before sunset.
        await self.run_at_sunset(self.turn_on_front_porch, offset=datetime.timedelta(minutes=-15).total_seconds())
        self.handle = await self.run_daily(self.turn_off_front_porch_time_based,
                                           await self.utils.get_time(self.porch_off_time))
        # Only update the next execution time when time has been set for 30 seconds.
        await self.listen_state(self.on_porch_off_time_change, self.porch_off_time, duration=30)
        # Only check if execution time needs defaulting when boolean has been off for 30 seconds.
        await self.listen_state(self.on_override_boolean_turned_off, self.should_override_time, new="off", duration=30)
        await self.listen_state(self.turn_on_front_porch_location_based, self.proximity_owen,
                                old=lambda x: int(x) > 5,
                                new=lambda x: int(x) <= 5)  # When getting close to home.
        await self.listen_state(self.turn_on_front_porch_location_based, self.proximity_allison,
                                old=lambda x: int(x) > 5,
                                new=lambda x: int(x) <= 5)  # When getting close to home.
        await self.listen_state(self.turn_off_front_porch_location_based, self.allison, new="home",
                                duration=300)  # When home for 5 minutes.
        await self.listen_state(self.turn_off_front_porch_location_based, self.owen, new="home",
                                duration=300)  # When home for 5 minutes.

    """
    On time change, cancel the timer and re-set it up so it executes
    at the new time. Sets override boolean if necessary.
    """

    async def on_porch_off_time_change(self, entity: str, attribute: str, old: str, new: str, kwargs):
        self.log("Setting new execution time: {}".format(new))
        await self.cancel_timer(self.handle)
        self.handle = await self.run_daily(self.turn_off_front_porch_time_based, new)

        # If the override time, but the boolean wasn't turned on, turn on the boolean. Only set if time wasn't set to
        # default.
        if not await self.utils.is_entity_on(self.should_override_time) and await self.utils.get_time(
                self.porch_off_time) != self.default_time:
            self.log("Override boolean off but should be on. Turning on.")
            await self.set_state(self.should_override_time, state="on")

    """
    On override boolean changed, check if turned off. If turned off, reset
    the execution time to the default time of 10:00 PM.
    """

    async def on_override_boolean_turned_off(self, entity: str, attribute: str, old: str, new: str, kwargs):
        self.log("Override turned off. Resetting time to 10:00 PM")
        await self.set_state(self.porch_off_time, state=self.default_time)

    """
    Turns on the front porch lights if they are off.
    """

    async def turn_on_front_porch(self, kwargs):
        if not await self.utils.is_entity_on(self.front_porch_switch):
            self.log("Turning porch lights on.")
            await self.turn_on(self.front_porch_switch)

        if await self.utils.is_entity_on(self.holiday_mode) and not await self.utils.is_entity_on(self.holiday_lights):
            await self.turn_on(self.holiday_lights)

    """
    Turns on porch if someone is close to home, lights are off, and it's late at
    night.
    """

    async def turn_on_front_porch_location_based(self, entity: str, attribute: str, old: str, new: str, kwargs):
        if await self.is_late() and not await self.utils.is_entity_on(self.front_porch_switch):
            self.log("Turning on front porch lights due to someone getting close to home at night.")
            await self.turn_on_front_porch({})

    """
    Turns off the front porch lights if they are on and nobody is close to
    getting home.
    """

    async def turn_off_front_porch_time_based(self, kwargs):
        if await self.someone_close_to_home():
            self.log("Someone getting close to home. Not turning off front porch lights.")
            return

        if await self.utils.is_entity_on(self.front_porch_switch):
            self.log("Turning off front porch lights.")
            await self.turn_off_front_porch()

    """
    Turns off front porch lights if they're on, someone just got home, and it's
    late at night.
    """

    async def turn_off_front_porch_location_based(self, entity: str, attribute: str, old: str, new: str, kwargs):
        if await self.is_late() and await self.utils.is_entity_on(self.front_porch_switch):
            self.log("Turning off front porch lights, due to lights being on and someone getting home late at night.")
            await self.turn_off_front_porch()

    """
    Turns off the front porch lights if they are on.
    Will also reset the execution time for future runs if time was
    overridden for this run.
    """

    async def turn_off_front_porch(self):
        await self.turn_off(self.front_porch_switch)

        if await self.utils.is_entity_on(self.should_override_time):
            self.log("Time overriden. Resetting execution time to default.")
            await self.set_state(self.should_override_time, state="off")
            await self.set_state(self.porch_off_time, state=self.default_time)
        pass

        if await self.utils.is_entity_on(self.holiday_mode) and await self.utils.is_entity_on(self.holiday_lights):
            await self.turn_off(self.holiday_lights)

    """
    Returns if someone is close to home.
    """

    async def someone_close_to_home(self):
        allison_close = await self.utils.close_to_home(self.proximity_allison)
        owen_close = await self.utils.close_to_home(self.proximity_owen)

        return allison_close or owen_close

    """
    Returns if it's late (but not too late...)
    """

    async def is_late(self) -> bool:
        return await self.now_is_between("22:00:00", "01:00:00")
