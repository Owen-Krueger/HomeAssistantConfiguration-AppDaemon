import appdaemon.plugins.hass.hassapi as hass
from appdaemon.appdaemon import AppDaemon

from person import Person

class Security(hass.Hass):
    """
    Automations for security.
    """

    allison: str
    front_door_lock: str
    owen: str

    def initialize(self) -> None:
        """
        Sets up the security automations.
        """

        self.notification_utils = self.get_app("notification_utils")
        self.allison = self.args["allison"]
        self.front_door_lock = self.args["front_door_lock"]
        self.owen = self.args["owen"]

        self.listen_state(self.on_people_away, self.allison, old="not_home", duration=60)
        self.listen_state(self.on_people_away, self.owen, old="not_home", duration=60)
        self.run_daily(self.on_night_time, "21:30:00")

    def on_people_away(self, entity: str, attribute: str, old: str, new: str, args) -> None:
        """
        When everyone is away from home, checks if the front door is locked and lock it if it is not.
        """
        if self.anyone_home(person=True):
            return

        if not self.is_front_door_locked():
            self.lock_front_door()

    def on_night_time(self, args) -> None:
        """
        At night, checks if the front door is locked and lock it if it is not.
        """
        if not self.is_front_door_locked():
            self.lock_front_door()

    def lock_front_door(self) -> None:
        """
        Locks the front door and registers a callback to verify door is locked after 10 seconds.
        """
        self.lock(self.front_door_lock)
        self.run_in(self.verify_front_door_locked, 10)

    def verify_front_door_locked(self, args) -> None:
        """
        After requesting the door has been locked, verifies that the door is locked. Notifies everyone regardless.
        """
        message = "Locked the front door." \
            if self.is_front_door_locked() else "Attempted to lock the front door but failed."
        self.notification_utils.notify_users(message, person=Person.All)

    def is_front_door_locked(self) -> bool:
        """
        Returns if the front door is locked.
        """
        return self.get_state(self.front_door_lock) == "locked"
