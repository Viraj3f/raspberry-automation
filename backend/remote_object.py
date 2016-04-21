# These are the remotes themselves. They are hardware devices that are
# controlled by the pi. They use wtforms to create attributes about them,
# such as which pin they are connected to the pi from


import wtforms
from wtforms import TextField, IntegerField, BooleanField
from wtforms import validators

if __debug__:  # if not editing from the raspberry pi
    from gpiozero import OutputDevice
    from gpiozero import GPIODevice
    from gpiozero import MotionSensor as Motion
    from gpiozero import Button
    from gpiozero import GPIOPinInUse
else:
    print("DEBUG MODE IS ON, HARDWARE WILL NOT WORK")

MIN_GPIO = 4
MAX_GPIO = 26


# Has min max attributes so javascript can check if a pin is
# valid or not


class MinMaxIntegerField(IntegerField):
    def __init__(self, min=None, max=None, **kwargs):
        super().__init__(**kwargs)
        self.min = min
        self.max = max


# Abstract remote class. All Remotes should have a primary pin
# number and a name


class RemoteAbstract():
    def __init__(self, dic, Type=None):
        self.pin = dic["pin"]
        if __debug__:
            if Type is None:
                Type = GPIODevice
            try:
                self.Type = Type
                self.device = self.Type(self.pin)
            except GPIOPinInUse as e:
                raise ValueError(str(e))
            except Exception as e:
                raise e

    def close(self):
        if __debug__:
            self.device.close()

    def change_pin(self, new_pin):
        self.close()
        if __debug__:
            try:
                self.device = self.Type(self.pin)
            except GPIOPinInUse as e:
                raise ValueError(str(e))
            except Exception as e:
                raise e

    # Gets information from database
    def input(self, data):
        if self.pin != data["pin"]:
            self.pin = data["pin"]
            self.change_pin(self.pin)

    # Modifies database
    def output(self, database, query):
        pass

    class Form(wtforms.Form):
        name = TextField("Name", [validators.Required(message="Name must not" +
                         " be left blank")])

        blank_gpio_message = "GPIO pin must not be left blank"
        wrong_pin_message = "GPIO pin must be between " +\
                            str(MIN_GPIO) + " - " + str(MAX_GPIO)

        blank_validator = validators.Required(message=blank_gpio_message)
        num_validator = validators.NumberRange(min=MIN_GPIO,
                                               max=MAX_GPIO,
                                               message=wrong_pin_message)

        pin = MinMaxIntegerField(label="GPIO pin", min=MIN_GPIO, max=MAX_GPIO,
                                 validators=[blank_validator, num_validator])

    @classmethod
    def to_dic(cls, form):
        return {
                "pin": form.pin.data,
                "name": form.name.data,
                "type": cls.__name__
                }


# For devices that only have an on/off state


class SimpleOutput(RemoteAbstract):
    def __init__(self, dic):
        if __debug__:
            super().__init__(dic, OutputDevice)
        else:
            super().__init__(dic)

    def input(self, data):
        super().input(data)
        if __debug__:
            if data["keep_on"]:
                self.device.on()
            else:
                self.device.off()

    class Form(RemoteAbstract.Form):
        keep_on = BooleanField("Initial State")

    @classmethod
    def to_dic(self, form):
        dic = super().to_dic(form)
        dic["keep_on"] = form.keep_on.data
        return dic


# Simple Input Device, this class should be subclassed


class SimpleInput(RemoteAbstract):
    def __init__(self, dic, Type=None):
        if __debug__:
            super().__init__(dic, Type)
        else:
            super().__init__(dic)

        self.data = None

    def is_active(self):
        if __debug__:
            return self.device.is_active
        else:
            return True

    def output(self, database, query, data=None):
        if data is None:
            data = {"data": self.data}

        database.update({"data": self.data}, query["pin"] == self.pin)

    @classmethod
    def to_dic(cls, form):
        dic = super().to_dic(form)
        dic["data"] = None
        return dic

# A motion sensor


class MotionSensor(SimpleInput):
    def __init__(self, dic):
        if __debug__:
            super().__init__(dic, Motion)
        else:
            super().__init__(dic)

    def output(self, database, query):
        import time
        if self.is_active():
            self.data = int(time.time())

        super().output(database, query)


class Switch(SimpleInput):
    def __init__(self, dic):
        if __debug__:
            super().__init__(dic, Button)
        else:
            super().__init(dic)

    def output(self, database, query):
        if self.is_active():
            self.data = "ON"
        else:
            self.data = "OFF"
        super().output(database, query)


# The "pin" is for the switch. There's also a pin required for:
# The buzzer, and motion sensor. Also, there's a camera
class AlarmSystem(RemoteAbstract):
    def __init__(self, dic):
        if __debug__:
            super().__init__(dic, Button)
        else:
            super().__init__(dic)

        self.keep_on = dic["keep_on"]

    def input(self, data):
        super().input(data)

        self.keep_on = data["keep_on"]
        if self.keep_on:
            pass
        else:
            pass

    def change_pin(self, pin):
        self.change_pin(pin)

    def close(self, remote=None):
        if __debug__:
            self.device.close()

    class Form(RemoteAbstract.Form):
        v_b = RemoteAbstract.Form.blank_validator
        v_n = RemoteAbstract.Form.num_validator

        pin_buzzer = MinMaxIntegerField(label="GPIO pin for Buzzer",
                                        min=MIN_GPIO, max=MAX_GPIO,
                                        validators=[v_b, v_n])

        pin_motion = MinMaxIntegerField(label="GPIO pin for Motion Sensor",
                                        min=MIN_GPIO, max=MAX_GPIO,
                                        validators=[v_b, v_n])

        keep_on = BooleanField("Enable Away From Home?")
        emails = TextField(label="Enter Email Adresses Separated by Commas",
                           validators=[])

        def validate_emails(form, field):
            import re
            regex = "[^@]+@[^@]+\.[^@]+"
            for email in field.data.split(","):
                if re.search(regex, email.replace(" ", "")) is None:
                    raise validators.ValidationError("Unable to validate" +
                                                     " email")

    @classmethod
    def to_dic(cls, form):
        dic = super().to_dic(form)
        dic["pin_buzzer"] = form.pin_buzzer.data
        dic["pin_motion"] = form.pin_motion.data

        dic["keep_on"] = form.keep_on.data
        dic["motion"] = None
        dic["photo_toggle"] = False

        dic["emails"] = form.emails.data

        return dic
