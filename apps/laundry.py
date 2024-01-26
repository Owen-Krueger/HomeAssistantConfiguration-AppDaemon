import appdaemon.plugins.hass.hassapi as hass

"""
Laundry automations.
"""
class Laundry(hass.Hass):

    """
    Sets up the automation.
    """
    def initialize(self):
        self.washer = self.args["washer"]
        self.dryer = self.args["dryer"]

        self.listen_state(self.notify_users, self.washer, new = "finish")
        # Usually, state becomes "finished", but occasionally
        # goes from "cooling" to "none".
        self.listen_state(self.notify_users, self.dryer, old = "cooling")

    """
    Attempts to notify users about load being complete.
    If nobody is home, notifies both users.
    """
    def notify_users(self, entity: str, attribute: str, old: str, new: str, kwargs):
        device = "washer" if entity == self.washer else "dryer"
        message = "The {} has completed!".format(device)

        self.notify(message, name="owen")
        self.notify(message, name="allison")