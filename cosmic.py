#!/usr/bin/python

import time
import threading
import RPi.GPIO as GPIO

class Button:
    def __init__(self, channel, debounce = 30):
        self.channel = channel
        self._lock = threading.Lock()
        self._pressed = False
        self._time = time.time()
        self._debounce = debounce / 1000.0

        GPIO.setup(self.channel, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(self.channel, GPIO.BOTH, callback=self._callback, bouncetime=debounce)

    def _callback(self, channel):
        level = GPIO.input(self.channel)
        now = time.time()
        debounced = (now - self._time) > self._debounce
        if level == 0 and debounced:
            self._time = now
        elif level == 1 and debounced:
            self._lock.acquire()
            self._pressed = True
            self._lock.release()

    def pressed(self):
        self._lock.acquire()
        pressed = self._pressed
        self._pressed = False
        self._lock.release()
        return pressed

class Encoder(Button):
    def __init__(self, channel_a, channel_b, button):
        super(Encoder, self).__init__(button, 80)

        self.channel_a = channel_a
        self.channel_b = channel_b
        self._count = 0
        self._laststate = 0

        GPIO.setup(self.channel_a, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.channel_b, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(self.channel_a, GPIO.BOTH, callback=self._encoder_callback)
        GPIO.add_event_detect(self.channel_b, GPIO.BOTH, callback=self._encoder_callback)

    def _encoder_callback(self, channel):
        state = (self._laststate << 2) | ((GPIO.input(self.channel_a) & 1) << 1) | (GPIO.input(self.channel_b) & 1)
        state = state & 0xF

        self._lock.acquire()
        if (state == 0b0010):
            self._count = self._count + 1
        elif (state == 0b0111):
            self._count = self._count - 1
        else:
            pass
        self._lock.release()

        self._laststate = state

    def count(self):
        self._lock.acquire()
        count = self._count
        self._lock.release()
        return count

class LED():
    def __init__(self, pin, invert = False):
        self._pin = pin
        self.invert = invert
        self._state = invert
        GPIO.setup(self._pin, GPIO.OUT)
        GPIO.output(self._pin, 0)

    def on(self):
        self._state = not(self.invert)
        GPIO.output(self._pin, self._state)

    def off(self):
        self._state = self.invert
        GPIO.output(self._pin, self._state)

    def set(self, state):
        if state:
            self._state = not(self.invert)
        else:
            self._state = self.invert
        GPIO.output(self._pin, self._state)

    def toggle(self):
        self._state = not(self._state)
        GPIO.output(self._pin, self._state)

class Cosmic:
    def __init__(self, pin_enc_a, pin_enc_b, pin_enc_button,
                    pin_b1, pin_b2, pin_b3,
                    pin_led1, pin_led2, pin_led3):
        self.buttons = [
            Button(pin_b1),
            Button(pin_b2),
            Button(pin_b3),
        ]
        self.leds = [
            LED(pin_led1),
            LED(pin_led2),
            LED(pin_led3),
        ]
        self.enc = Encoder(pin_enc_a, pin_enc_b, pin_enc_button)

    def pressed(self, button):
        return self.buttons[button].pressed()

    def count(self):
        return self.enc.count()

    def led(self, led):
        return self.leds[led]
