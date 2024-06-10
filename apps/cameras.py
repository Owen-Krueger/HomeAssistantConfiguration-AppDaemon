import appdaemon.plugins.hass.hassapi as hass


class Cameras(hass.Hass):
    """
    Camera automation depending on people being home or not.
    """

    allison: str
    cameras: str
    cameras_on: str
    owen: str

    def initialize(self):
        """
        Sets up the automation.
        """

        self.utils = self.get_app("utils")
        self.allison = self.args["allison"]
        self.cameras = self.args["cameras"]
        self.cameras_on = self.args["cameras_on"]
        self.owen = self.args["owen"]

        self.listen_state(self.turn_off_cameras, self.allison, new="home")
        self.listen_state(self.turn_off_cameras, self.owen, new="home")
        self.listen_state(self.turn_on_cameras, self.cameras_on, new="on")

    def turn_on_cameras(self, entity: str, attribute: str, old: str, new: str, kwargs):
        """
        Turns on the cameras if nobody is home and the triggered is moving away.
        """

        if self.anyone_home(person=True):
            return
        
        self.turn_off_on_cameras(True)

    def turn_off_cameras(self, entity: str, attribute: str, old: str, new: str, kwargs):
        """
        Turns off the cameras if someone is home.
        """

        if not self.anyone_home(person=True):
            return

        self.turn_off_on_cameras(False)

        if self.utils.is_entity_on(self.cameras_on):
            self.turn_off(self.cameras_on)

    def turn_off_on_cameras(self, turn_on: bool):
        """
        Turns off cameras if anyone home and cameras are on.
        Turns on cameras if everyone away from home and cameras are off.
        """

        camera_state_log_message = "on" if turn_on else "off"

        cameras_updated = False
        for camera in self.cameras:
            cameras_updated = self.turn_off_on_camera(camera, turn_on) or cameras_updated

        if cameras_updated:
            message = "Cameras turned {}.".format(camera_state_log_message)
            self.log(message)
            self.notify(message, name="owen")

    def turn_off_on_camera(self, entity: str, turn_on: bool) -> bool:
        """
        Turns off or on the camera, depending on input and current state.
        """

        if turn_on and not self.utils.is_entity_on(entity):
            self.turn_on(entity)
            return True
        elif not turn_on and self.utils.is_entity_on(entity):
            self.turn_off(entity)
            return True
        
        return False
