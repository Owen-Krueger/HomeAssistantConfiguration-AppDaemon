import appdaemon.plugins.hass.hassapi as hass
from person import Person


class NotificationUtils(hass.Hass):
    """
    Utilities used to notify users.
    """

    def notify_users(self, message: str, person: Person, if_people_home: bool = False):
        """
        Notifies the provided user or users with the provided message.
        @param message: The message to send.
        @param person: The person to notify. 'All' notifies everyone.
        @param if_people_home: If True, the message will be sent if anyone is at home.
        """

        send_notification = not if_people_home or self.anyone_home(person=True)

        if send_notification and person == Person.All:
            self.notify(message, name=Person.Owen.value)
            self.notify(message, name=Person.Allison.value)
        elif send_notification:
            self.notify(message, name=person.value)
