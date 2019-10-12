
class Activity():
    def __init__(self):
        pass

    def onResume(self):
        pass

    def onPause(self):
        pass

    def onDraw(self):
        pass

    def onInputReceived(self, events):
        pass

class ActivityManager():
    def __init__(self):
        self.activities = { }
        self.current = None

    def register(self, name, activity):
        self.activities[name] = activity

    def start(self, name):
        if self.current is not None:
            self.current.onPause()
        self.current = self.activities[name]
        self.current.onResume()

    def stop(self):
        self.current.onPause()

    def tick(self, events):
        self.current.onInputReceived(events)
        self.current.onDraw()
