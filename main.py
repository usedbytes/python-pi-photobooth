#!/usr/bin/python3

import time
import RPi.GPIO as GPIO
from PIL import Image

import tkinter
import cosmic

import picamera

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

# Playback
button1 = cosmic.Button(pin_b1)
# 4up
button2 = cosmic.Button(pin_b2)
# Take photo
button3 = cosmic.Button(pin_b3)

enc = cosmic.Encoder(pin_enc_a, pin_enc_b, pin_enc_button)

led1 = cosmic.LED(pin_led1)
led2 = cosmic.LED(pin_led2)
led3 = cosmic.LED(pin_led3)

SHUTTER_BUTTON = 3
QUAD_BUTTON = 2
PLAY_BUTTON = 1

#root = tkinter.Tk()
#root.config(cursor='none')
#root.attributes("-fullscreen", True)
#root.update()
#root.configure(background='blue')
#window_size = (root.winfo_width(), root.winfo_height())
#root.geometry('%dx%d+0+0' % (window_size[0], window_size[1]))
window_size = (1024, 600)


#pimg.paste(png, (int((padded_size[0] - png.size[0]) / 2), int((padded_size[1] - png.size[1]) / 2)), png)

class Overlay():
    def __init__(self, size, filename = None, color = (0, 0, 0)):
        padded_size = ((size[0] + 31) & ~0x1f, (size[1] + 31) & ~0x1f)
        self.pimg = Image.new('RGB', (padded_size[0], padded_size[1]), color)
        self.ovl = camera.add_overlay(self.pimg.tobytes(), format='rgb', size=self.pimg.size)
        self.z = 3
        self.alpha = 255
        self.length = self.pimg.size[0] * self.pimg.size[1] * 3
        if filename is not None:
            self.from_file(filename)
        self.hide()

    def show(self):
        self.ovl.alpha = self.alpha
        self.ovl.layer = self.z

    def hide(self):
        self.ovl.alpha = 0
        self.ovl.layer = 0

    def close(self):
        self.ovl.close()

    def set_z(self, z):
        self.z = z
        self.ovl.layer = self.z

    def set_alpha(self, alpha):
        self.alpha = alpha
        self.ovl.alpha = self.alpha

    def set_content(self, content):
        if len(content) != self.length:
            print("Unexpected length %d vs %d" % (len(content), self.length))
            return
        self.ovl.update(content)

    def from_file(self, filename):
        png = Image.open(filename)
        self.pimg.paste(png, (int((self.pimg.size[0] - png.size[0]) / 2), int((self.pimg.size[1] - png.size[1]) / 2)), png)
        self.set_content(self.pimg.tobytes())

class AlphaOverlay(Overlay):
    def __init__(self, size, filename = None):
        padded_size = ((size[0] + 31) & ~0x1f, (size[1] + 31) & ~0x1f)
        self.pimg = Image.new('RGBA', (padded_size[0], padded_size[1]), (0, 0, 0, 0))
        self.ovl = camera.add_overlay(self.pimg.tobytes(), format='rgba', size=self.pimg.size)
        self.z = 3
        self.alpha = 255
        self.length = self.pimg.size[0] * self.pimg.size[1] * 4
        if filename is not None:
            self.from_file(filename)
        self.hide()

class Activity():
    def __init__(self):
        pass

    def onResume(self):
        pass

    def onPause(self):
        pass

    def onDraw(self):
        pass

    def onInputReceived(self, event):
        pass

def LoadImg(filename):
        png = Image.open(filename)
        padded_size = ((png.size[0] + 31) & ~0x1f, (png.size[1] + 31) & ~0x1f)
        pimg = Image.new('RGBA', (padded_size[0], padded_size[1]), (0, 0, 0, 0))
        pimg.paste(png, (int((pimg.size[0] - png.size[0]) / 2), int((pimg.size[1] - png.size[1]) / 2)), png)
        return pimg

class PreviewActivity(Activity):
    NONE = 0
    COUNTDOWN = 1
    SHUTTER = 2

    def __init__(self, resolution, preview_resolution):
        self.state = PreviewActivity.NONE
        self.time = time.time()
        self.camera = picamera.PiCamera()
        self.camera.framerate = 24
        self.camera.resolution = resolution
        self.preview_resolution = preview_resolution

        self.images = {
                '3': LoadImg('3.png'),
                '2': LoadImg('2.png'),
                '1': LoadImg('1.png'),
        }

    def onResume(self):
        self.camera.start_preview(resolution=self.preview_resolution)

    def onPause(self):
        self.stopCountdown()
        self.stopShutter()
        self.camera.stop_preview()

    def onInputReceived(self, event):
        print(event)
        if 'button' in event and event['button'] == SHUTTER_BUTTON:
            if self.state == COUNTDOWN:
                self.stopCountdown()
            else:
                self.startCountdown()

    def onDraw(self):
        now = time.time()
        if self.state == PreviewActivity.COUNTDOWN:
            if now - self.time > 0.8:
                led3.off()
            elif now - stamp >= 1.0:
                self.covl.set_content(self.images['2'].tobytes())
                led3.on()
            elif now - self.time > 1.8:
                led3.off()
            elif now - stamp >= 2.0:
                self.covl.set_content(self.images['1'].tobytes())
                led3.on()
            elif now - self.time > 2.8:
                led3.off()
            elif now - self.time >= 3.0:
                # Relies on us being single-threaded here to not
                # race with state changing somehow.
                self.stopCountdown()
                self.startShutter()
        elif self.state == PreviewActivity.SHUTTER:
            fadeTime = 0.8
            remaining = 1 - ((now - self.time) / fadeTime)
            if remaining <= 0:
                self.stopShutter()
            else:
                self.shovl.alpha = int(255 * remaining)

    def stopCountdown(self):
        self.state = PreviewActivity.NONE
        if self.covl is not None:
            self.covl.close()
            self.covl = None
        led3.off()

    def startCountdown(self):
        self.state = PreviewActivity.COUNTDOWN
        self.time = time.time()
        self.covl = AlphaOverlay(self.images['3'].size)
        self.covl.set_content(self.images['3'].tobytes()
        self.covl.show()
        led3.on()

    def stopShutter(self):
        self.state = PreviewActivity.NONE
        if self.shovl is not None:
            self.shovl.close()
            self.shovl = None
        led3.off()

    def startShutter(self):
        self.state = PreviewActivity.SHUTTER
        self.time = time.time()
        self.shovl = Overlay(self.preview_resolution, color='white'))
        self.shovl.show()
        led3.on()
        self.takePhoto()

    def takePhoto(self):
        self.camera.capture('out.jpg')

# (3280, 2464): v2 module max resolution
# (768, 576): 4:3, multiple of 32, and fits into 1024x600 screen
current = PreviewActivity(resolution=(3280, 2464), preview_resolution=(768, 576))

try:
    while True:
        time.sleep (1.0/24)

        if button1.pressed():
            print("Button 1 (Play)")
        if button2.pressed():
            print("Button 2 (Quad)")
            led2.toggle()
        if button3.pressed():
            current.onInputReceived({'button': SHUTTER_BUTTON})

        print("Encoder:" + str(enc.count()) + " " + str(enc.pressed()))

        current.onDraw()

except KeyboardInterrupt:
    pass

GPIO.cleanup()
