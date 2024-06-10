import appdaemon.plugins.hass.hassapi as hass
import importlib

try:
    Person = importlib.import_module("utils.person").Person
except ModuleNotFoundError:
    Person = importlib.import_module("person").Person


class Laundry(hass.Hass):
    """
    Laundry automations.
    """

    washer: str
    dryer: str

    def initialize(self):
        """
        Sets up the automation.
        """

        self.notification_utils = self.get_app("notification_utils")
        self.washer = self.args["washer"]
        self.dryer = self.args["dryer"]

        self.listen_state(self.notify_users, self.washer, old="run", new="stop")
        # Usually, state becomes "finished", but occasionally
        # goes from "cooling" to "none".
        self.listen_state(self.notify_users, self.dryer, old="run", new="stop")

    """
    Attempts to notify users about load being complete.
    If nobody is home, notifies both users.
    """
    def notify_users(self, entity: str, attribute: str, old: str, new: str, kwargs):
        device = "washer" if entity == self.washer else "dryer"
        message = "The {} has completed!".format(device)

        self.notification_utils.notify_users(message, Person.All)
