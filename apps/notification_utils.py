from enum import Enum

import appdaemon.plugins.hass.hassapi as hass


class Person(Enum):
    """
    People that can be notified.
    """

    All = 'all',
    Owen = 'owen',
    Allison = 'allison',


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
            self.notify(message, Person.Owen.value)
            self.notify(message, Person.Allison.value)
        elif send_notification:
            self.notify(message, person.value)
