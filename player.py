import pygame

import activity
import threading

from consts import SHUTTER_BUTTON, QUAD_BUTTON, PLAY_BUTTON

def add_wrap(val, add, n):
    return (val + add) % n

class ImageCache(dict):
    def __init__(self, nslots, files, large_res, small_res, start_idx = 0):
        self.sem = threading.Semaphore()
        self.items = {}
        self.files = files
        self.nslots = nslots
        self.large_res = large_res
        self.small_res = small_res

        self.trigger_refill(start_idx)

    def get(self, idx):
        if idx not in self.items:
            self.load(idx)
            self.trigger_refill(idx)
        imgs = self.items[idx]
        return imgs

    def trigger_refill(self, idx):
        if self.sem.acquire(blocking=False):
            self.thread = threading.Thread(target=self.__refill, args=[idx]).start()
        return

    def load(self, idx):
        if idx in self.items:
            return

        img = pygame.image.load(self.files[idx])
        imgs = (
                pygame.transform.scale(img, self.large_res),
                pygame.transform.scale(img, self.small_res)
        )
        self.items[idx] = imgs

    def evict(self, idx):
        del self.items[idx]

    def __refill(self, idx):
        new_range = set([add_wrap(idx, i - ((self.nslots) // 2), len(self.files)) for i in range(self.nslots)])
        old_range = self.items.keys()
        to_load = new_range - old_range
        to_evict = old_range - new_range

        for k in to_evict:
            self.evict(k)

        for k in to_load:
            self.load(k)

        self.sem.release()


class PlayerActivity(activity.Activity):
    def __init__(self, cosmic, screen, screen_resolution, album):
        self.cosmic = cosmic
        self.screen = screen
        self.album = album
        self.screen_resolution = screen_resolution
        self.main_resolution = (768, 576)
        self.small_resolution = (252, 63 * 3)
        self.colors = [
            [255, 100, 0],
            [100, 250, 0],
            [255, 0, 128],
            [0, 100, 128],
            [255, 100, 128],
            [255, 0, 0],
            [0, 0, 255],
            [0, 255, 255],
        ]
        self.files = self.album.list()
        self.cache = ImageCache(12, self.files, self.main_resolution, self.small_resolution)
        self.idx = 0
        self.dirty = True

        top_border = (self.screen_resolution[1] - self.main_resolution[1]) / 2
        self.rects = [
            pygame.Rect((0, top_border), self.main_resolution),
            pygame.Rect((self.screen_resolution[0] - self.small_resolution[0], top_border),
                self.small_resolution),
            pygame.Rect((self.screen_resolution[0] - self.small_resolution[0],
                (self.screen_resolution[1] - self.small_resolution[1]) / 2),
                self.small_resolution),
            pygame.Rect((self.screen_resolution[0] - self.small_resolution[0],
                self.screen_resolution[1] - self.small_resolution[1] - top_border),
                self.small_resolution),
        ]



    def onResume(self):
        self.cosmic.led(PLAY_BUTTON).on()
        self.screen.fill((255, 255, 255))
        self.screen.fill((255, 255, 0), self.rects[2].inflate(8, 8))
        pygame.display.update()
        self.files = self.album.list()
        self.cache = ImageCache(12, self.files, self.main_resolution, self.small_resolution)
        self.idx = 0
        self.cache.get(self.idx)
        self.dirty = True

    def onPause(self):
        self.cosmic.led(PLAY_BUTTON).off()

    def onDraw(self):
        if not self.dirty:
            return

        # Main picture in main and middle slot
        idx = self.idx
        imgs = self.cache.get(idx)
        self.screen.blit(imgs[0], self.rects[0])
        self.screen.blit(imgs[1], self.rects[2])

        idx = add_wrap(self.idx, -1, len(self.files))
        imgs = self.cache.get(idx)
        self.screen.blit(imgs[1], self.rects[1])

        idx = add_wrap(self.idx, 1, len(self.files))
        imgs = self.cache.get(idx)
        self.screen.blit(imgs[1], self.rects[3])

        pygame.display.flip()
        self.dirty = False

    def onInputReceived(self, events):
        for event in events:
            if 'button' in event and event['button'] == PLAY_BUTTON:
                return 'preview'
            elif 'encoder' in event:
                self.idx = add_wrap(self.idx, event['encoder'], len(self.files))
                self.dirty = True
