import hassapi as hass

"""
For notifying when entities have become unavailable.
"""
class UnavailableEntities(hass.Hass):
    
    """
    Sets up the automation.
    """
    def initialize(self):
        for entity in self.args["list"]:
            self.listen_state(self.notify_owen, entity, new = "unavailable", duration = 30) # When unavailable for 30 seconds.

    """
    Notify Owen that the entity has become unavailable.
    """
    def notify_owen(self, entity: str, attribute: str, old: str, new: str, kwargs):
        message = "{} is unavailable.".format(entity)
        self.log("{} Notifying.".format(message))
        self.notify(message, name="owen")