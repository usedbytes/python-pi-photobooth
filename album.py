import os
import shutil
import datetime

from PIL import Image

class Album:
    def __init__(self, directory, backup = None):
        self.directory = directory
        try:
            os.mkdir(self.directory)
        except FileExistsError:
            pass

        self.backup = backup
        if self.backup is not None:
            try:
                os.mkdir(self.backup)
            except FileExistsError:
                pass

    def writeOut(self, frames):
            filename = self.genFilename()
            if len(frames) == 1:
                frames[0].save(filename, 'jpeg')
            elif len(frames) == 4:
                size = frames[0].size
                points = [
                    (0, 0),
                    (size[0], 0),
                    (0, size[1]),
                    size,
                ]
                canvas = Image.new('RGBA', (size[0] * 2, size[1] * 2), (255, 255, 255, 255))
                for i in range(len(points)):
                    canvas.paste(frames[i], points[i])
                canvas.save(filename, 'jpeg')
                canvas.close()
            else:
                print("Unexpected number of frames {}".format(len(frames)))

            for f in frames:
                f.close()

            if self.backup is not None:
                shutil.copy2(filename, self.backup)

            return filename

    def genFilename(self):
        return "{}/IMG_{}.jpg".format(self.directory,
                datetime.datetime.utcnow().strftime("%Y-%m-%d_%H%M%SUTC"))
