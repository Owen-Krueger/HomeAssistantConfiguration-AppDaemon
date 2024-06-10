import appdaemon.plugins.hass.hassapi as hass


class UnavailableEntities(hass.Hass):
    """
    For notifying when entities have become unavailable.
    """

    async def initialize(self):
        """
        Sets up the automation.
        """

        for entity in self.args["list"]:
            await self.listen_state(self.notify_owen, entity, new="unavailable", duration=30)

    async def notify_owen(self, entity: str, attribute: str, old: str, new: str, kwargs):
        """
        Notify Owen that the entity has become unavailable.
        """

        message = "{} is unavailable.".format(entity)
        self.log("{} Notifying.".format(message))
        await self.notify(message, name="owen")
