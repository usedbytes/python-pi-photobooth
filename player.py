import pygame

import activity

from consts import SHUTTER_BUTTON, QUAD_BUTTON, PLAY_BUTTON

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

        pass

    def onResume(self):
        self.cosmic.led(PLAY_BUTTON).on()
        self.screen.fill((0, 0, 0))
        pygame.display.update()
        pass

    def onPause(self):
        self.cosmic.led(PLAY_BUTTON).off()
        pass

    def onDraw(self):
        pygame.draw.rect(self.screen, self.colors[0], self.rects[0])

        pygame.draw.rect(self.screen, self.colors[1], self.rects[1])

        pygame.draw.rect(self.screen, self.colors[2], self.rects[2])

        pygame.draw.rect(self.screen, self.colors[3], self.rects[3])

        pygame.display.flip()
        pass

    def onInputReceived(self, events):
        for event in events:
            if 'button' in event and event['button'] == PLAY_BUTTON:
                return 'preview'
        pass
