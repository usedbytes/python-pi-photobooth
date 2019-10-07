#!/usr/bin/python3

import pygame
import threading
import time
import RPi.GPIO as GPIO
from PIL import Image, ImageDraw, ImageFont

#import tkinter
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

#window_size = (root.winfo_width(), root.winfo_height())
#root.geometry('%dx%d+0+0' % (window_size[0], window_size[1]))

#pimg.paste(png, (int((padded_size[0] - png.size[0]) / 2), int((padded_size[1] - png.size[1]) / 2)), png)

def sign(val):
    if val > 0:
        return 1
    elif val < 0:
        return -1
    else:
        return 0

def align_size(size):
    return ((size[0] + 31) & ~0x1f, (size[1] + 31) & ~0x1f)

class Overlay():
    def __init__(self, camera, size, filename = None, color = (0, 0, 0)):
        padded_size = align_size(size)
        self.pimg = Image.new('RGB', (padded_size[0], padded_size[1]), color)
        self.ovl = camera.add_overlay(self.pimg.tobytes(), format='rgb', size=self.pimg.size)
        self.z = 3
        self.alpha = 255
        self.length = self.pimg.size[0] * self.pimg.size[1] * 3
        if filename is not None:
            self.from_file(filename)
        self.hide()

    def size(self):
        return self.pimg.size

    def window(self, window):
        if window != None:
            self.ovl.window = window
            self.ovl.fullscreen = False
        else:
            self.ovl.fullscreen = True

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
    def __init__(self, camera, size, filename = None):
        padded_size = align_size(size)
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

class CaptureThread(threading.Thread):
    def __init__(self, camera):
        threading.Thread.__init__(self)
        self.camera = camera
        self.exit = threading.Event()
        self.shutter_sem = threading.Semaphore(value=0)
        self.frame_sem = threading.Semaphore(value=0)

    def takePhoto(self):
        self.shutter_sem.release()

    def getPhoto(self, blocking=True):
        return self.frame_sem.acquire(blocking=blocking)

    def stop(self):
        self.exit.set()

    def run(self):
        while not self.exit.is_set():
            if self.shutter_sem.acquire(timeout=0.5):
                self.camera.capture('out.jpg')
                self.frame_sem.release()

class PreviewActivity(Activity):
    NONE = 0
    COUNTDOWN = 1
    SHUTTER = 2

    def __init__(self, screen_resolution, resolution, preview_resolution):
        self.state = PreviewActivity.NONE
        self.substate = 0
        self.time = time.time()
        self.camera = picamera.PiCamera()
        self.camera.framerate = 24
        self.camera.hflip = True
        self.screen_resolution = screen_resolution
        self.camera.resolution = resolution
        self.preview_resolution = preview_resolution
        self.capture_thread = CaptureThread(self.camera)
        self.capture_thread.start()
        self.covl = None
        self.shovl = None
        self.efovl = None

        self.images = {
                '3': LoadImg('3.png'),
                '2': LoadImg('2.png'),
                '1': LoadImg('1.png'),
        }

        self.effect = 0
        self.effects = [
            # name,        image_effect,  image_effect_params, color_effects
            ['',           'none',        None,                None],
            ['Invert',     'negative',    None,                None],
            ['Solarize',   'solarize',    [128, 128, 128, 0],  None],
            ['Sketch',     'sketch',      None,                None],
            ['Emboss',     'emboss',      None,                None],
            ['Cartoon',    'cartoon',     None,                None],
            ['Pop Green',  'colorpoint',  0,                   None],
            ['Pop Red',    'colorpoint',  1,                   None],
            ['Pop Blue',   'colorpoint',  2,                   None],
            ['Pop Purple', 'colorpoint',  3,                   None],
            ['Film',       'film',        [50, 130, 120],      None],
            ['Sepia',      'none',        None,                [100, 150]],
        ]
        font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeSansBold.ttf", 28)
        for e in self.effects:
            if len(e[0]) == 0:
                e.append(None)
                continue
            string = "Effect: " + e[0]
            fontsize = font.getsize(string)
            size = align_size(fontsize)
            txt = Image.new('RGBA', size, (0, 0, 0, 0))
            d = ImageDraw.Draw(txt)
            x = (size[0] - fontsize[0]) / 2
            y = (size[1] - fontsize[1]) / 2
            d.text((x-1, y-1), string, font=font, fill=(0, 0, 0, 200))
            d.text((x+1, y-1), string, font=font, fill=(0, 0, 0, 200))
            d.text((x-1, y+1), string, font=font, fill=(0, 0, 0, 200))
            d.text((x+1, y+1), string, font=font, fill=(0, 0, 0, 200))
            d.text((x, y), string, font=font, fill=(255, 255, 255, 200))
            e.append(txt)


    def onResume(self):
        self.camera.start_preview(resolution=self.preview_resolution)

    def onPause(self):
        self.stopCountdown()
        self.stopShutter()
        if self.efovl is not None:
            self.efovl.close()
            self.efovl = None
        self.camera.stop_preview()

    def onExit(self):
        self.capture_thread.stop()
        self.capture_thread.join()
        self.onPause()

    def onInputReceived(self, event):
        if 'button' in event and event['button'] == SHUTTER_BUTTON:
            if self.state == PreviewActivity.COUNTDOWN:
                self.stopCountdown()
            else:
                self.startCountdown()
        elif 'encoder' in event:
            if self.state == PreviewActivity.NONE:
                self.effect = self.effect + event['encoder']
                if self.effect < 0:
                    self.effect += len(self.effects)
                elif self.effect >= len(self.effects):
                    self.effect -= len(self.effects)
                effect = self.effects[self.effect]
                self.camera.image_effect = effect[1]
                self.camera.color_effects = effect[3]
                if effect[2] is not None:
                    self.camera.image_effect_params = effect[2]

                if self.efovl is not None:
                    self.efovl.close()
                    self.efovl = None

                if effect[-1] is not None:
                    img = effect[-1]
                    self.efovl = AlphaOverlay(self.camera, img.size)
                    self.efovl.hide()
                    self.efovl.window((
                        int((self.screen_resolution[0] - img.size[0]) / 2),
                        int(self.screen_resolution[1] / 20),
                        int(img.size[0]),
                        int(img.size[1]),
                    ))
                    self.efovl.set_content(img.tobytes())
                    self.efovl.show()


    def onDraw(self):
        now = time.time()
        since = now - self.time
        if self.state == PreviewActivity.COUNTDOWN:
            if self.substate == 0 and since > 0.8:
                led3.off()
                self.substate = 1
            elif self.substate == 1 and since > 1.0 :
                self.covl.set_content(self.images['2'].tobytes())
                led3.on()
                self.substate = 2
            elif self.substate == 2 and since > 1.8:
                led3.off()
                self.substate = 3
            elif self.substate == 3 and since > 2.0:
                self.covl.set_content(self.images['1'].tobytes())
                led3.on()
                self.substate = 4
            elif self.substate == 4 and since > 2.8:
                led3.off()
                self.substate = 5
            elif self.substate == 5 and since > 3.0:
                # Relies on us being single-threaded here to not
                # race with state changing somehow.
                self.stopCountdown()
                self.startShutter()
                self.substate = 6
        elif self.state == PreviewActivity.SHUTTER:
            fadeTime = 1.0
            remaining = 1.0 - (since / fadeTime)
            if remaining <= 0:
                self.stopShutter()
            else:
                self.shovl.set_alpha(int(255 * remaining))

    def stopCountdown(self):
        self.state = PreviewActivity.NONE
        if self.covl is not None:
            self.covl.close()
            self.covl = None
        led3.off()

    def startCountdown(self):
        self.state = PreviewActivity.COUNTDOWN
        self.substate = 0
        self.time = time.time()
        self.covl = AlphaOverlay(self.camera, self.images['3'].size)
        self.covl.window((
            int((self.screen_resolution[0] - self.covl.size()[0]) / 2),
            int((self.screen_resolution[1] - self.covl.size()[1]) / 2),
            int(self.covl.size()[0]),
            int(self.covl.size()[1]),
        ))
        self.covl.set_content(self.images['3'].tobytes())
        self.covl.show()
        led3.on()

    def stopShutter(self):
        if not self.capture_thread.getPhoto(blocking=False):
            return
        self.state = PreviewActivity.NONE
        led3.off()
        if self.shovl is not None:
            self.shovl.close()
            self.shovl = None

    def startShutter(self):
        self.state = PreviewActivity.SHUTTER
        led3.on()
        self.time = time.time()
        self.shovl = Overlay(self.camera, self.preview_resolution, color='white')
        self.shovl.show()
        self.takePhoto()

    def takePhoto(self):
        self.capture_thread.takePhoto()

# (3280, 2464): v2 module max resolution
#capture_resolution = (3280, 2464)
# 1640x1232 is smallest full frame mode
capture_resolution = (1640, 1232)

# (768, 576): 4:3, multiple of 32, and fits into 1024x600 screen
preview_resolution = (768, 576)

window_size = (1024, 600)

#root = tkinter.Tk()
#root.config(cursor='none')
#root.attributes("-fullscreen", True)
#root.configure(background='blue')
#root.update()
#app = tkinter.Frame(root)

pygame.init()
pygame.mouse.set_visible(False)
screen = pygame.display.set_mode((1024, 600))
screen.fill((255, 0, 0))
pygame.display.flip()


current = PreviewActivity(screen_resolution=window_size, resolution=capture_resolution, preview_resolution=preview_resolution)

current.onResume()

try:
    encoder_pos = enc.count()
    while True:
        time.sleep (1.0/24)

        if button1.pressed():
            print("Button 1 (Play)")
        if button2.pressed():
            print("Button 2 (Quad)")
            led2.toggle()
        if button3.pressed():
            current.onInputReceived({'button': SHUTTER_BUTTON})
        if enc.count() != encoder_pos:
            val = sign(enc.count() - encoder_pos)
            encoder_pos += val
            current.onInputReceived({'encoder': val})

        current.onDraw()
except KeyboardInterrupt:
    pass

current.onExit()
GPIO.cleanup()
