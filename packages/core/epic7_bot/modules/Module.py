from epic7_bot.core.ScreenManager import ScreenManager


class Module:
    def __init__(self, fastMode=False, speed=1.0):
        self.ScreenManager = ScreenManager(fastMode, speed)
