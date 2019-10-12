#!/usr/bin/python3

import pygame
import RPi.GPIO as GPIO
import time

import album
import cosmic
import preview

from consts import SHUTTER_BUTTON, QUAD_BUTTON, PLAY_BUTTON

pin_enc_a = 23
pin_enc_b = 24
pin_enc_button = 27

pin_b1 = 4
pin_b2 = 5
pin_b3 = 6

pin_led1 = 14
pin_led2 = 15
pin_led3 = 16

def sign(val):
    if val > 0:
        return 1
    elif val < 0:
        return -1
    else:
        return 0

# (3280, 2464): v2 module max resolution
#capture_resolution = (3280, 2464)
# 1640x1232 is smallest full frame mode
capture_resolution = (1640, 1232)

# (768, 576): 4:3, multiple of 32, and fits into 1024x600 screen
preview_resolution = (768, 576)

window_size = (1024, 600)

GPIO.setmode(GPIO.BCM)

panel = cosmic.Cosmic(pin_enc_a, pin_enc_b, pin_enc_button,
            pin_b1, pin_b2, pin_b3,
            pin_led1, pin_led2, pin_led3)

pygame.init()
screen = pygame.display.set_mode((1024, 600))
pygame.mouse.set_visible(False)
screen.fill((0, 0, 0))
pygame.display.flip()

album = album.Album('out')

current = preview.PreviewActivity(cosmic=panel, screen=screen, screen_resolution=window_size, resolution=capture_resolution, preview_resolution=preview_resolution, album=album)

current.onResume()

try:
    encoder_pos = panel.count()
    while True:
        time.sleep (1.0/24)

        if panel.pressed(PLAY_BUTTON):
            print("Button 1 (Play)")
        if panel.pressed(QUAD_BUTTON):
            current.onInputReceived({'button': QUAD_BUTTON})
        if panel.pressed(SHUTTER_BUTTON):
            current.onInputReceived({'button': SHUTTER_BUTTON})
        if panel.count() != encoder_pos:
            val = sign(panel.count() - encoder_pos)
            encoder_pos += val
            current.onInputReceived({'encoder': val})

        current.onDraw()
except KeyboardInterrupt:
    pass

current.onExit()
GPIO.cleanup()
