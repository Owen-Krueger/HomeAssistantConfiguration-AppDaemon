import appdaemon.plugins.hass.hassapi as hass


class OwenPhoneWifi(hass.Hass):
    """
    Automation to let Owen know when he's home, but not on Wi-Fi.
    """

    owen: str
    phone_network: str

    async def initialize(self):
        """
        Sets up the automation.
        """

        self.utils = self.get_app("utils")
        self.owen = self.args["owen"]
        self.phone_network = self.args["phone_network"]

        await self.listen_state(self.notify_owen, self.owen, new="home", duration=1800)  # When home for 30 minutes
        await self.listen_state(self.notify_owen, self.phone_network, new="cellular",
                                duration=1800)  # When on cellular data for 30 minutes

    """
    Notifies Owen if he's at home without Wifi on.
    """
    async def notify_owen(self, entity: str, attribute: str, old: str, new: str, kwargs):
        if await self.utils.is_entity_home(self.owen) and await self.get_state(self.phone_network) == "cellular":
            self.log("Notifying Owen that he's home with cellular on.")
            await self.notify("Your phone is currently connected to cellular data", name="owen")
