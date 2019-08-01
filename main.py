#!/usr/bin/python3

import time
import RPi.GPIO as GPIO

import cosmic

pin_enc_a = 23
pin_enc_b = 24
pin_enc_button = 27

pin_b1 = 4
pin_b2 = 5
pin_b3 = 6

pin_led1 = 14
pin_led2 = 15
pin_led3 = 16

GPIO.setmode(GPIO.BCM)

button1 = cosmic.Button(pin_b1)
button2 = cosmic.Button(pin_b2)
button3 = cosmic.Button(pin_b3)

enc = cosmic.Encoder(pin_enc_a, pin_enc_b, pin_enc_button)

led1 = cosmic.LED(pin_led1)
led2 = cosmic.LED(pin_led2)
led3 = cosmic.LED(pin_led3)

try:
    while True:
        time.sleep (1.0/10)
        if button1.pressed():
            print("Button 1")
            led1.toggle()
        if button2.pressed():
            print("Button 2")
            led2.toggle()
        if button3.pressed():
            print("Button 3")
            led3.toggle()
        print("Encoder:" + str(enc.count()) + " " + str(enc.pressed()))

except KeyboardInterrupt:
    pass

GPIO.cleanup()
