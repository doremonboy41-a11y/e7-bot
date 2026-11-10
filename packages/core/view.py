from tinydb import TinyDB
import webview
import os
import mimetypes
import multiprocessing
import json
import base64
import cv2
import numpy as np
from epic7_bot.processes.CommandRunner import CommandRunner

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CURRENT_APP_VERSION = "v1.0.0"
AUTHOR = "Kazari"

# Settings of the user (background...) live outside the app folder, which is temporary in the .exe
SETTINGS_DIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "Epic7Bot")
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "settings.json")

# Background pictures that come with the app (packed inside the .exe, see config/windows.spec)
BACKGROUNDS_DIR = os.path.join(ROOT_DIR, "backgrounds")
BACKGROUND_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".bmp")
BACKGROUND_MAX_WIDTH = 1920

# Table of db.json that holds the summary of each command
COMMAND_TABLES = {"shop": "secret_shop", "hunt": "hunt",
                  "arena": "arena", "daily": "daily"}


class Api:
    def __init__(self) -> None:
        self.runningCommand = None
        multiprocessing.set_start_method("spawn", force=True)
        multiprocessing.freeze_support()

    def get_version(self):
        return {'current_app_version': CURRENT_APP_VERSION, 'author': AUTHOR}

    def reset_run_files(self, command):
        # Without this the previous run (old logs and numbers) would still be
        # shown for a few seconds while the new process boots.
        try:
            open(ROOT_DIR + "\\logs", "w").close()
            table = COMMAND_TABLES.get(command)
            if table is not None:
                TinyDB(ROOT_DIR + "\\db.json").table(table).truncate()
        except BaseException:
            pass

    def start_command(self, args):
        if self.runningCommand is not None:
            self.stop_running_command()
        self.reset_run_files(args["<command>"])
        self.runningCommand = CommandRunner(args)
        self.runningCommand.start()

    def start_shop(self, args={}):
        self.start_command({
            "<command>": "shop", "--current": False, "--fast": False, **args})

    def start_hunt(self, args={}):
        self.start_command(
            {"<command>": "hunt", "--current": False, "--fast": False, **args})

    def start_arena(self, args={}):
        self.start_command(
            {"<command>": "arena", "--current": False, "--fast": False, **args})

    def start_daily(self, args={}):
        self.start_command(
            {"<command>": "daily", "--current": False, "--fast": False, **args})

    def stop_running_command(self):
        if self.runningCommand is not None:
            self.runningCommand.terminate()

    def get_settings(self):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except BaseException:
            return {}

    def save_settings(self, settings):
        # Only the keys that are sent are changed
        try:
            current = self.get_settings()
            current.update(settings)
            os.makedirs(SETTINGS_DIR, exist_ok=True)
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(current, f)
        except BaseException:
            pass

    # ---------- background pictures ----------

    @staticmethod
    def _read_picture(path):
        # np.fromfile instead of cv2.imread, so names with accents / non-latin letters work on Windows
        data = np.fromfile(path, dtype=np.uint8)
        return cv2.imdecode(data, cv2.IMREAD_COLOR)

    @staticmethod
    def _to_data_url(image, max_width, quality):
        height, width = image.shape[:2]
        if width > max_width:
            image = cv2.resize(image, (max_width, int(height * max_width / width)), interpolation=cv2.INTER_AREA)
        ok, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality])
        if not ok:
            return None
        return "data:image/jpeg;base64," + base64.b64encode(buffer.tobytes()).decode("ascii")

    def _background_files(self):
        try:
            return sorted(f for f in os.listdir(BACKGROUNDS_DIR)
                          if f.lower().endswith(BACKGROUND_EXTENSIONS))
        except BaseException:
            return []

    def list_backgrounds(self):
        # Small thumbnails only, the full picture is loaded when it is chosen
        result = []
        for name in self._background_files():
            try:
                image = self._read_picture(os.path.join(BACKGROUNDS_DIR, name))
                thumb = self._to_data_url(image, 160, 70) if image is not None else None
            except BaseException:
                thumb = None
            if thumb is not None:
                result.append({"id": name, "name": os.path.splitext(name)[0], "thumb": thumb})
        return result

    def get_background(self, name):
        # Only files that are in the backgrounds folder can be read
        if name not in self._background_files():
            return None
        try:
            image = self._read_picture(os.path.join(BACKGROUNDS_DIR, name))
            return self._to_data_url(image, BACKGROUND_MAX_WIDTH, 85) if image is not None else None
        except BaseException:
            return None

    def is_running(self):
        # False once the bot has exited by itself (finished, or stopped on an error)
        return self.runningCommand is not None and self.runningCommand.is_alive()

    def get_logs(self):
        try:
            f = open(ROOT_DIR + "\logs", "r")
            return f.read()
        except BaseException as e:
            raise e

    def get_summary(self, table):
        db = TinyDB(ROOT_DIR + "\\db.json")
        table = db.table(table)
        contents = table.all()
        if len(contents) > 0:
            return contents[0]


def setup_tray(window, api):
    """Minimizing hides the window in the system tray. Click the tray icon to bring it back,
    right click for Open / Quit. Without pystray / Pillow installed the app works as before."""
    try:
        import pystray
        from PIL import Image
        image = Image.open(os.path.join(ROOT_DIR, "dist-app", "icon.ico"))
    except BaseException:
        return

    def show(icon=None, item=None):
        window.show()
        window.restore()

    def quit_app(icon, item):
        icon.stop()
        try:
            api.stop_running_command()
        except BaseException:
            pass
        window.destroy()

    menu = pystray.Menu(
        pystray.MenuItem("Open", show, default=True),
        pystray.MenuItem("Quit", quit_app))
    tray = pystray.Icon("Epic7 Bot", image, "Epic7 Bot", menu)

    window.events.minimized += lambda: window.hide()
    window.events.closed += lambda: tray.stop()
    tray.run_detached()


if __name__ == "__main__":
    # Create logs file
    if os.path.exists(ROOT_DIR + "\\logs") is not True:
        with open(ROOT_DIR + "\\logs", "w") as log:
            pass
    # Create db file
    if os.path.exists(ROOT_DIR + "\\db.json") is not True:
        with open(ROOT_DIR + "\\db.json", "w") as db:
            pass
    mimetypes.add_type("application/javascript", ".js")
    api = Api()
    window = webview.create_window(
        "Epic7 Bot",
        "dist-app/index.html",
        js_api=api,
        width=1000,
        height=720,
        min_size=(900, 540),
    )
    setup_tray(window, api)
    webview.start(debug=False)
