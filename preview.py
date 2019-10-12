
import io
import picamera
import pygame
import queue
import threading
import time
from PIL import Image, ImageDraw, ImageFont

import activity

from consts import SHUTTER_BUTTON, QUAD_BUTTON, PLAY_BUTTON

def LoadImg(filename):
        png = Image.open(filename)
        padded_size = align_size(png.size)
        pimg = Image.new('RGBA', (padded_size[0], padded_size[1]), (0, 0, 0, 0))
        pimg.paste(png, (int((pimg.size[0] - png.size[0]) / 2), int((pimg.size[1] - png.size[1]) / 2)), png)
        return pimg

def align_size(size):
    return ((size[0] + 31) & ~0x1f, (size[1] + 15) & ~0xf)

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

    def from_file(self, filename, resize = False):
        png = Image.open(filename)
        if resize:
            png.thumbnail(self.pimg.size)
        if png.mode == 'RGBA':
            self.pimg.paste(png, (int((self.pimg.size[0] - png.size[0]) / 2), int((self.pimg.size[1] - png.size[1]) / 2)), png)
        else:
            self.pimg.paste(png, (int((self.pimg.size[0] - png.size[0]) / 2), int((self.pimg.size[1] - png.size[1]) / 2)))
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

class CaptureThread(threading.Thread):
    def __init__(self, camera):
        threading.Thread.__init__(self)
        self.camera = camera
        self.exit = threading.Event()
        self.shutter_sem = threading.Semaphore(value=0)
        self.frame_sem = threading.Semaphore(value=0)
        self.frame_queue = queue.Queue(maxsize=4)

    def takePhoto(self):
        self.shutter_sem.release()

    def getPhoto(self, blocking=True):
        try:
            return self.frame_queue.get(blocking)
        except queue.Empty:
            return None

    def stop(self):
        self.exit.set()

    def run(self):
        while not self.exit.is_set():
            if self.shutter_sem.acquire(timeout=0.5):
                stream = io.BytesIO()
                self.camera.capture(stream, 'rgba')
                im = Image.frombuffer('RGBA', align_size(self.camera.resolution),
                            stream.getbuffer(), 'raw', 'RGBA', 0, 1)
                im = im.crop((0, 0, self.camera.resolution[0], self.camera.resolution[1]))
                self.frame_queue.put(im)

class PreviewActivity(activity.Activity):
    NONE = 0
    COUNTDOWN = 1
    SHUTTER = 2
    REPEATSHUTTER = 3
    REVIEW = 4

    def __init__(self, cosmic, screen, screen_resolution, resolution, preview_resolution, album, flash):
        self.flash = flash
        self.album = album
        self.screen = screen
        self.cosmic = cosmic
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
        self.revovl = None
        self.quad = False

        self.shots = 0

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
        self.flash.on()
        self.screen.fill((0, 0, 0))
        pygame.display.flip()
        self.camera.start_preview(resolution=self.preview_resolution)
        self.setEffect(self.effect)

    def onPause(self):
        self.flash.off()
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

    def setEffect(self, effect):
        if effect < 0:
            effect += len(self.effects)
        elif effect >= len(self.effects):
            effect -= len(self.effects)
        self.effect = effect
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

    def onInputReceived(self, events):
        for event in events:
            if 'button' in event and event['button'] == SHUTTER_BUTTON:
                if self.state == PreviewActivity.COUNTDOWN:
                    self.stopCountdown()
                elif self.state == PreviewActivity.NONE:
                    self.startCountdown()
            elif 'button' in event and event['button'] == QUAD_BUTTON:
                if self.state == PreviewActivity.NONE:
                    self.quad = not(self.quad)
                    self.cosmic.led(QUAD_BUTTON).set(self.quad)
            elif 'button' in event and event['button'] == PLAY_BUTTON:
                if self.state == PreviewActivity.NONE:
                    return 'player'
                elif self.state == PreviewActivity.REVIEW:
                    self.stopReview()
                    return 'player'
            elif 'encoder' in event:
                if self.state == PreviewActivity.NONE:
                    effect = self.effect + event['encoder']
                    self.setEffect(effect)
            return None

    def onDraw(self):
        now = time.time()
        since = now - self.time
        if self.state == PreviewActivity.COUNTDOWN:
            if self.substate == 0 and since > 0.8:
                self.cosmic.led(SHUTTER_BUTTON).off()
                self.substate = 1
            elif self.substate == 1 and since > 1.0 :
                self.covl.set_content(self.images['2'].tobytes())
                self.cosmic.led(SHUTTER_BUTTON).on()
                self.substate = 2
            elif self.substate == 2 and since > 1.8:
                self.cosmic.led(SHUTTER_BUTTON).off()
                self.substate = 3
            elif self.substate == 3 and since > 2.0:
                self.covl.set_content(self.images['1'].tobytes())
                self.cosmic.led(SHUTTER_BUTTON).on()
                self.substate = 4
            elif self.substate == 4 and since > 2.8:
                self.cosmic.led(SHUTTER_BUTTON).off()
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
        elif self.state == PreviewActivity.REPEATSHUTTER:
            if since >= 0.8:
                self.startShutter()
        elif self.state == PreviewActivity.REVIEW:
            if since >= self.substate:
                self.stopReview()

    def startReview(self, filename, seconds):
            self.revovl = Overlay(self.camera, self.preview_resolution)
            self.revovl.from_file(filename, True)
            self.revovl.show()

            self.screen.fill((255, 255, 255))
            pygame.display.flip()
            self.state = PreviewActivity.REVIEW
            self.substate = seconds
            self.time = time.time()

    def stopReview(self):
        self.screen.fill((0, 0, 0))
        pygame.display.flip()
        self.revovl.close()
        self.revovl = None
        self.state = PreviewActivity.NONE

    def stopCountdown(self):
        self.state = PreviewActivity.NONE
        if self.covl is not None:
            self.covl.close()
            self.covl = None
        self.cosmic.led(SHUTTER_BUTTON).off()

    def startCountdown(self):
        self.state = PreviewActivity.COUNTDOWN
        self.substate = 0
        self.time = time.time()
        if self.quad:
            self.shots = 4
        else:
            self.shots = 1
        self.frames = []
        self.covl = AlphaOverlay(self.camera, self.images['3'].size)
        self.covl.window((
            int((self.screen_resolution[0] - self.covl.size()[0]) / 2),
            int((self.screen_resolution[1] - self.covl.size()[1]) / 2),
            int(self.covl.size()[0]),
            int(self.covl.size()[1]),
        ))
        self.covl.set_content(self.images['3'].tobytes())
        self.covl.show()
        self.cosmic.led(SHUTTER_BUTTON).on()

    def stopShutter(self):
        im = self.capture_thread.getPhoto(blocking=False)
        if im is None:
            return

        self.frames.append(im)

        self.state = PreviewActivity.NONE
        self.cosmic.led(SHUTTER_BUTTON).off()

        if self.shovl is not None:
            self.shovl.close()
            self.shovl = None

        self.shots = self.shots - 1
        if self.shots > 0:
            self.state = PreviewActivity.REPEATSHUTTER
        else:
            # Hack: Longer review for quads
            revtime = 2.0
            if len(self.frames) == 4:
                revtime = 4.0

            filename = self.album.writeOut(self.frames)
            self.frames = None
            self.startReview(filename, revtime)

    def startShutter(self):
        self.state = PreviewActivity.SHUTTER
        self.cosmic.led(SHUTTER_BUTTON).on()
        self.time = time.time()
        self.shovl = Overlay(self.camera, self.preview_resolution, color='white')
        self.shovl.show()
        self.takePhoto()

    def takePhoto(self):
        self.capture_thread.takePhoto()
