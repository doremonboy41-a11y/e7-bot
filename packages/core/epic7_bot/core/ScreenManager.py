
import base64
import logging
import time
import cv2
import random

from cv2 import Mat

import numpy as np
from epic7_bot.core.DeviceManager import DeviceManager
from epic7_bot.core.MathUtils import MathUtils
from epic7_bot.templates.Template import Template
from epic7_bot.utils.Singleton import Singleton


class ScreenManager(metaclass=Singleton):
    def __init__(self, fastMode=False, speed=1.0):
        self.MathUtils = MathUtils()
        self.DeviceManager = DeviceManager()
        self.fastMode = fastMode
        # Every wait is divided by this value (1 = original timing, 2 = twice as fast...)
        self.speed = speed if speed and speed > 0 else 1.0
        self._capture_methods = [self._screencap_native, self._screencap_busybox]
        self._size_checked = False

    def sleep(self, waitTime):
        if self.fastMode:
            time.sleep(random.uniform(0.5, 0.8))
            return
        time.sleep(random.uniform(waitTime, waitTime + 1) / self.speed)

    def get_position_of_template_match(self, matchTemplate):
        position_x = np.unravel_index(
            matchTemplate.argmax(), matchTemplate.shape)[1]
        position_y = np.unravel_index(
            matchTemplate.argmax(), matchTemplate.shape)[0]
        return position_x, position_y

    def _screencap_native(self):
        # Works on any emulator, no busybox needed (MuMu, BlueStacks, ...)
        data = self.DeviceManager.device.screencap()
        if not data:
            return None
        return cv2.imdecode(np.frombuffer(data, np.uint8), 0)

    def _screencap_busybox(self):
        # Legacy method, needs busybox on the device
        data = self.DeviceManager.device.shell("screencap -p | busybox base64")
        data = base64.b64decode(data)
        return cv2.imdecode(np.frombuffer(data, np.uint8), 0)

    def _check_screenshot_size(self, img):
        self._size_checked = True
        height, width = img.shape[:2]
        if (width, height) != (1600, 900):
            logging.warning(
                f"Screenshot size is {width}x{height}, the bot expects 1600x900. "
                f"Set your emulator resolution to 1600x900 (landscape).")

    def take_screenshot(self):
        # The method that worked last time is tried first.
        for method in list(self._capture_methods):
            try:
                img = method()
            except Exception as e:
                logging.debug(f"take_screenshot via {method.__name__} failed: {e}")
                continue
            if img is not None:
                if method is not self._capture_methods[0]:
                    self._capture_methods.remove(method)
                    self._capture_methods.insert(0, method)
                if not self._size_checked:
                    self._check_screenshot_size(img)
                return img
        logging.warning("take_screenshot: could not capture the screen")
        return None

    def take_screnshot_from_area(self, x1=None, x2=None, y1=None, y2=None):
        img = self.take_screenshot()
        if x1 != None and y1 != None and x2 != None and y2 != None:
            img = img[y1:y2, x1:x2]

        return img

    def match_template_on_screen(self, template: Template, percentage=0.6):
        image = self.take_screenshot()
        match = cv2.matchTemplate(
            image, template['image'], cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(match)

        logging.debug(
            f"match_template_on_screen {template['name']}, percentage: {max_val}, {max_val > percentage}")

        if max_val > percentage:
            return match
        else:
            return None

    def match_template_on_screen_area(self, x1, y1, x2, y2, template, percentage=0.55):
        image = self.take_screnshot_from_area(x1, x2, y1, y2)
        result = cv2.matchTemplate(
            image, template['image'], cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        logging.debug(
            f"match_template_on_screen_area {template['name']}, percentage: {max_val}, {max_val > percentage}")
        if max_val > percentage:
            return max_val
        else:
            return None

    def match_template_on_screen_and_click_it(self, template, waitTime=0):
        self.sleep(random.uniform(waitTime, waitTime + 0.5))
        match = self.match_template_on_screen(template)
        if match is not None:
            position_x, position_y = self.get_position_of_template_match(match)
            x, y = self.MathUtils.randomPoint(position_x, position_y)
            self.DeviceManager.device.shell("input tap " +
                                            str(x) + " " + str(y))

    def check_if_images_changed(self, img1, img2, percentage=70, action=None):
        if img1 is None or img2 is None:
            return False
        res = cv2.absdiff(img1, img2)
        res = res.astype(np.uint8)
        result = (np.count_nonzero(res) * 100) / res.size
        if action is not None:
            logging.debug(f"{action}, check_if_images_changed: {result}")
        return result >= percentage

    def click_position(self, position_x, position_y, waitTime, message=None):
        self.sleep(waitTime)
        x, y = self.MathUtils.randomPoint(position_x, position_y)
        self.DeviceManager.device.shell("input tap " + str(x) + " " + str(y))

    def random_click_on_area(self, x1, y1, x2, y2):
        position_x, position_y = self.MathUtils.random_point_in_area(
            x1, y1, x2, y2)
        self.click_position(position_x, position_y, waitTime=0)
        # position_x, position_y = self.MathUtils.midpoint(x1, y1, x2, y2)
        # self.click_position(position_x, position_y, waitTime=0)

    def random_click_on_area_get_before_and_after_images_from_screen(self, x1, y1, x2, y2):
        beforeImage = self.take_screenshot()
        self.random_click_on_area(x1, y1, x2, y2)
        self.sleep(3)
        afterImage = self.take_screenshot()
        return (beforeImage, afterImage)

    def random_click_on_area_and_check_change_on_screen_retry(self, x1, y1, x2, y2, action=None, percentage=70):
        self.sleep(1)
        if action is not None:
            logging.info(f"{action}")

        beforeImage, afterImage = None, None
        count = 0
        while self.check_if_images_changed(beforeImage, afterImage, percentage=percentage, action=action) is False and count < 2:
            beforeImage, afterImage = self.random_click_on_area_get_before_and_after_images_from_screen(
                x1, y1, x2, y2)
            count += 1
        if count < 2 == False:
            logging.error(f"{action}")

        return count < 2

    def random_click_on_area_get_before_and_after_images_from_area(self, x1, y1, x2, y2):
        beforeImage = self.take_screnshot_from_area(x1, x2, y1, y2)
        self.random_click_on_area(x1, y1, x2, y2)
        self.sleep(3)
        afterImage = self.take_screnshot_from_area(x1, x2, y1, y2)
        return (beforeImage, afterImage)

    # ---------- waits that do not depend on the speed setting ----------

    def wait_until_screen_stable(self, timeout=3.0, interval=0.1, stable_frames=2, tolerance=1.5):
        """Waits (real time, NOT divided by the speed) until the screen stops moving.

        Lists glide and bounce after a swipe and popups fade in. A fixed wait divided by
        the speed is too short at high speeds, so look at the screen instead: it is stable
        when `stable_frames` consecutive screenshots are (almost) identical.
        Returns True when it became stable, False when the timeout was reached (the caller
        carries on anyway).
        """
        start = time.time()
        previous = None
        calm = 0
        while time.time() - start < timeout:
            img = self.take_screenshot()
            if img is None:
                time.sleep(interval)
                continue
            small = cv2.resize(img, (160, 90), interpolation=cv2.INTER_AREA)
            if small.ndim == 3:
                small = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            if previous is not None:
                diff = float(np.mean(cv2.absdiff(previous, small)))
                if diff <= tolerance:
                    calm += 1
                    if calm >= stable_frames:
                        return True
                else:
                    calm = 0
            previous = small
            time.sleep(interval)
        logging.debug("wait_until_screen_stable: timeout, the screen is still moving")
        return False

    def click_area_and_confirm_change(self, x1, y1, x2, y2, action=None, percentage=70,
                                      attempts=2, timeout=2.5):
        """Clicks and waits until the screen really changed (polling, in real time).

        Unlike random_click_on_area_and_check_change_on_screen_retry the check is not
        done after one fixed wait that shrinks with the speed: it keeps looking for the
        change until `timeout`, and only clicks again when nothing happened.
        Returns True when the click had an effect, False otherwise.
        """
        if action is not None:
            logging.info(f"{action}")
        for attempt in range(1, attempts + 1):
            self.wait_until_screen_stable(timeout=1.5)
            before = self.take_screenshot()
            self.random_click_on_area(x1, y1, x2, y2)
            deadline = time.time() + max(timeout, 3.0 / self.speed)
            while time.time() < deadline:
                time.sleep(0.2)
                after = self.take_screenshot()
                if self.check_if_images_changed(before, after, percentage=percentage, action=action):
                    self.wait_until_screen_stable(timeout=1.5)
                    return True
            logging.warning(f"{action}: the screen did not change after the click "
                            f"(attempt {attempt}/{attempts})")
        logging.error(f"{action}: failed")
        return False

    def random_click_on_area_and_check_change_on_area_retry(self, x1, y1, x2, y2, action=None, percentage=70):
        self.sleep(1)
        if action is not None:
            logging.info(f"{action}")

        beforeImage, afterImage = None, None
        count = 0
        while self.check_if_images_changed(beforeImage, afterImage, percentage, action) is False and count < 2:
            beforeImage, afterImage = self.random_click_on_area_get_before_and_after_images_from_area(
                x1, y1, x2, y2)
            count += 1
        return count < 2

    def ensure_not_on_sleep_mode_on_lobby(self):
        logging.info(
            "Double Click on Screen to Ensure not on Sleep Mode on Lobby")
        self.random_click_on_area(
            x1=894, y1=848, x2=935, y2=879)
        self.sleep(1)
        self.random_click_on_area(
            x1=894, y1=848, x2=935, y2=879)
