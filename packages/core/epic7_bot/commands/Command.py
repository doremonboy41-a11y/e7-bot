class Command:
    def __init__(self, currentScreen, fastMode, options=None):
        self.currentScreen = currentScreen
        self.fastMode = fastMode
        # Extra options sent by the GUI, e.g. {"--speed": 2, "--max-gold": 1000000}
        self.options = options or {}

    def start(self):
        pass
