import logging
import math
import os
import time

import cv2

from tinydb import TinyDB, table
from epic7_bot.utils.runInParallel import runInParallel
from epic7_bot.core.DeviceManager import DeviceManager
from epic7_bot.core.MathUtils import MathUtils
from epic7_bot.modules.Module import Module
from epic7_bot.templates.SecretShopTemplates import SecretShopTemplates

# Costs used to count what the bot spends (change here if the game changes them)
SKYSTONES_PER_REFRESH = 3
COVENANT_PRICE = 184000  # gold
MYSTIC_PRICE = 280000  # gold
FRIENDSHIP_PRICE = 18000  # gold (50 friendship points)
# The heart is a smooth shape that is easy to confuse with other things, so it needs a stricter match
FRIENDSHIP_MATCH = 0.85
BUY_BUTTON_MATCH = 0.7

MIN_SPEED = 0.5
MAX_SPEED = 10.0


class SecretShop(Module):
    def __init__(self, fastMode, options=None):
        options = options or {}
        self.speed = self.parse_speed(options.get("--speed"))
        # None = unlimited
        self.max_skystones = self.parse_limit(options.get("--max-skystones"))
        self.max_gold = self.parse_limit(options.get("--max-gold"))
        # Also buy the friendship points when they show up in the shop
        self.buy_friendship = bool(options.get("--buy-friendship"))

        super(self.__class__, self).__init__(fastMode, self.speed)
        self.DeviceManager = DeviceManager()
        self.SecretShopTemplates = SecretShopTemplates()
        self.MathUtils = MathUtils()

        self.mystic_count = 0
        self.refreshes_count = 0
        self.covenant_count = 0
        self.friendship_count = 0
        self.skystones_used = 0
        self.gold_used = 0
        self.mystic_bought = False
        self.covenant_bought = False
        self.friendship_bought = False
        self.mystic_skipped = False
        self.covenant_skipped = False
        self.friendship_skipped = False

        # Init table and contents
        ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
        db = TinyDB(ROOT_DIR + "\\..\\..\\db.json")
        self.table = db.table("secret_shop")
        if len(self.table.all()) != 1:
            self.table.insert(table.Document(self.stats(), doc_id=1))
        else:
            self.table.update(self.stats(), doc_ids=[1])

    @staticmethod
    def parse_speed(value):
        try:
            speed = float(value)
        except (TypeError, ValueError):
            return 1.0
        return min(max(speed, MIN_SPEED), MAX_SPEED)

    @staticmethod
    def parse_limit(value):
        if value is None or value == "":
            return None
        try:
            limit = int(float(value))
        except (TypeError, ValueError):
            return None
        return limit if limit >= 0 else None

    # ---------- budget ----------

    def can_afford(self, price):
        return self.max_gold is None or self.gold_used + price <= self.max_gold

    def gold_exhausted(self):
        """True when not even the cheapest bookmark fits in the gold budget anymore."""
        return not self.can_afford(min(COVENANT_PRICE, MYSTIC_PRICE))

    def skystones_exhausted(self):
        """True when the skystone budget cannot pay for one more refresh."""
        return (self.max_skystones is not None
                and self.skystones_used + SKYSTONES_PER_REFRESH > self.max_skystones)

    def stop_reason(self):
        if self.gold_exhausted():
            return "Gold limit reached"
        if self.skystones_exhausted():
            return "Skystone limit reached"
        return None

    def usage_summary(self):
        skystones = f"{self.skystones_used}"
        if self.max_skystones is not None:
            skystones += f"/{self.max_skystones}"
        gold = f"{self.gold_used:,}"
        if self.max_gold is not None:
            gold += f"/{self.max_gold:,}"
        return f"Total skystones used: {skystones} | Total gold used: {gold}"

    def log_usage(self, message):
        logging.info(f"{message} | {self.usage_summary()}")
        self.show_stats()

    def log_limits(self):
        skystone_limit = "unlimited"
        if self.max_skystones is not None:
            refreshes = self.max_skystones // SKYSTONES_PER_REFRESH
            skystone_limit = f"{self.max_skystones} ({refreshes} refreshes)"
        gold_limit = "unlimited" if self.max_gold is None else f"{self.max_gold:,}"
        speed = f"{self.speed:g}x"
        logging.info(
            f"Secret Shop started | Speed: {speed} | Friendship points: {'on' if self.buy_friendship else 'off'} | Skystone limit: {skystone_limit} | Gold limit: {gold_limit}")

    # ---------- shop ----------

    def locate_again(self, template, threshold=0.6):
        """The screen may still have been moving when the item was first found (scroll
        bounce, animations), so find it again on a calm screen right before clicking."""
        self.ScreenManager.wait_until_screen_stable(timeout=1.5)
        return self.ScreenManager.match_template_on_screen(template, threshold)

    def buy_bookmark(self, match, template, name, label=None):
        """Returns True only when the purchase was really done."""
        label = label or f"{name} Bookmark"
        logging.info(f"Found {label}")
        match = self.locate_again(template)
        if match is None:
            logging.warning(f"{label} moved or disappeared before buying, skipped")
            return False
        x, y = self.ScreenManager.get_position_of_template_match(match)

        width, height = template["image"].shape[::-1]

        x1 = x + math.floor(width / 2) + 580
        y1 = y + math.floor(height / 2) + 10
        x2 = x + math.floor(width / 2) + 800
        y2 = y + math.floor(height / 2) + 55

        if not self.ScreenManager.click_area_and_confirm_change(
                x1=x1, y1=y1, x2=x2, y2=y2, action="Click on Buy"):
            logging.warning(f"Could not click Buy for {label}")
            return False

        if not self.ScreenManager.click_area_and_confirm_change(
                x1=761, y1=605, x2=1059, y2=660, action="Click on Confirm Buy"):
            logging.warning(f"Could not confirm the purchase of {label}")
            return False
        return True

    def find_buy_button(self, item_cx, item_cy):
        """Locate the Buy button of the row of an item by matching the button itself, so the
        click does not depend on where the center of the item template happens to be."""
        template = self.SecretShopTemplates.buy_button_covenant["image"]
        screen = self.ScreenManager.take_screenshot()
        if screen is None or template is None:
            return None
        h, w = template.shape[:2]
        result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        best = None
        while True:
            _, max_val, _, (bx, by) = cv2.minMaxLoc(result)
            if max_val < BUY_BUTTON_MATCH:
                break
            # remove this peak so the next buttons (other rows) can be found
            result[max(0, by - h):by + h, max(0, bx - w):bx + w] = -1
            btn_cy = by + h / 2
            on_the_right = bx > item_cx + 200
            # the button of the covenant row is ~32px below the center of the icon
            distance = abs(btn_cy - (item_cy + 32))
            if on_the_right and distance < 70 and (best is None or distance < best[0]):
                best = (distance, bx, by, w, h)
        return best

    def buy_friendship_points(self, match):
        match = self.locate_again(self.SecretShopTemplates.friendship, FRIENDSHIP_MATCH)
        if match is None:
            logging.warning("Friendship Points moved or disappeared before buying, skipped")
            return False
        x, y = self.ScreenManager.get_position_of_template_match(match)
        height, width = self.SecretShopTemplates.friendship["image"].shape[:2]
        item_cx, item_cy = x + width // 2, y + height // 2
        logging.info(f"Found Friendship Points at ({item_cx}, {item_cy})")

        found = self.find_buy_button(item_cx, item_cy)
        if found is None:
            # Not safe to click blindly: a wrong click here is worse than missing the item
            logging.warning("Friendship Points found but its Buy button was not found, skipped")
            return False
        _, bx, by, w, h = found
        if not self.ScreenManager.click_area_and_confirm_change(
                x1=bx + 15, y1=by + 8, x2=bx + w - 15, y2=by + h - 8, action="Click on Buy"):
            logging.warning("Could not click Buy for Friendship Points")
            return False
        if not self.ScreenManager.click_area_and_confirm_change(
                x1=761, y1=605, x2=1059, y2=660, action="Click on Confirm Buy"):
            logging.warning("Could not confirm the purchase of Friendship Points")
            return False
        return True

    def check_bookmarks(self):
        if self.buy_friendship:
            logging.info("Check Mystic, Covenant Bookmarks and Friendship Points")
        else:
            logging.info("Check Mystic and Covenant Bookmarks")

        [mystic_pos, coven_pos, friend_pos] = runInParallel(
            lambda: self.ScreenManager.match_template_on_screen(
                self.SecretShopTemplates.mystic),
            lambda: self.ScreenManager.match_template_on_screen(
                self.SecretShopTemplates.covenant),
            lambda: self.ScreenManager.match_template_on_screen(
                self.SecretShopTemplates.friendship, FRIENDSHIP_MATCH) if self.buy_friendship else None)

        if mystic_pos is not None and self.mystic_bought is not True:
            if self.can_afford(MYSTIC_PRICE):
                # not marked as bought when the purchase failed, so the next check tries again
                if self.buy_bookmark(
                        mystic_pos, self.SecretShopTemplates.mystic, "Mystic"):
                    self.mystic_count += 1
                    self.mystic_bought = True
                    self.gold_used += MYSTIC_PRICE
                    self.log_usage(f"Bought Mystic Bookmark (-{MYSTIC_PRICE:,} gold)")
            elif not self.mystic_skipped:
                self.mystic_skipped = True
                logging.info("Skipped Mystic Bookmark: not enough gold left in the budget")

        if coven_pos is not None and self.covenant_bought is not True:
            if self.can_afford(COVENANT_PRICE):
                if self.buy_bookmark(
                        coven_pos, self.SecretShopTemplates.covenant, "Covenant"):
                    self.covenant_count += 1
                    self.covenant_bought = True
                    self.gold_used += COVENANT_PRICE
                    self.log_usage(f"Bought Covenant Bookmark (-{COVENANT_PRICE:,} gold)")
            elif not self.covenant_skipped:
                self.covenant_skipped = True
                logging.info("Skipped Covenant Bookmark: not enough gold left in the budget")

        if friend_pos is not None and self.friendship_bought is not True:
            if self.can_afford(FRIENDSHIP_PRICE):
                if self.buy_friendship_points(friend_pos):
                    self.friendship_bought = True
                    self.friendship_count += 1
                    self.gold_used += FRIENDSHIP_PRICE
                    self.log_usage(f"Bought Friendship Points (-{FRIENDSHIP_PRICE:,} gold)")
            elif not self.friendship_skipped:
                self.friendship_skipped = True
                logging.info("Skipped Friendship Points: not enough gold left in the budget")

    def scroll(self):
        x1, y1 = self.MathUtils.random_point_in_area(
            x1=750, y1=781, x2=1282, y2=845)
        x2, y2 = self.MathUtils.random_point_in_area(
            x1=701, y1=98, x2=1288, y2=174)

        self.DeviceManager.device.shell(
            f"input touchscreen swipe {x1} {y1} {x2} {y2} 400")
        # The list keeps gliding (and bounces at the end) after the finger is lifted.
        # Wait until it really stopped instead of a fixed time shortened by the speed.
        time.sleep(0.15)
        self.ScreenManager.wait_until_screen_stable(timeout=2.5)

    def check_store(self):
        # the shop may still be loading / animating right after a refresh
        self.ScreenManager.wait_until_screen_stable(timeout=2.0)
        self.check_bookmarks()
        self.scroll()
        self.check_bookmarks()

    def refresh(self):
        self.ScreenManager.random_click_on_area_and_check_change_on_screen_retry(
            x1=287, y1=808, x2=387, y2=838, action="Click on Refresh Button")
        self.ScreenManager.random_click_on_area_and_check_change_on_screen_retry(
            x1=878, y1=537, x2=986, y2=568, action="Click on Confirm Button")

        self.refreshes_count += 1
        self.skystones_used += SKYSTONES_PER_REFRESH
        self.mystic_bought = False
        self.covenant_bought = False
        self.friendship_bought = False
        self.mystic_skipped = False
        self.covenant_skipped = False
        self.friendship_skipped = False
        self.log_usage(
            f"Refresh #{self.refreshes_count} (-{SKYSTONES_PER_REFRESH} skystones)")

    def stats(self):
        return {
            'covenant_count': self.covenant_count,
            'mystic_count': self.mystic_count,
            'friendship_count': self.friendship_count,
            'buy_friendship': self.buy_friendship,
            'refreshes_count': self.refreshes_count,
            'skystones_used': self.skystones_used,
            'gold_used': self.gold_used,
            'max_skystones': self.max_skystones,
            'max_gold': self.max_gold,
        }

    def show_stats(self):
        self.table.update(self.stats(), doc_ids=[1])

    def finish(self, reason):
        self.show_stats()
        logging.info(f"Secret Shop finished: {reason} | {self.usage_summary()}")

    def start_auto_buy_secret_shop(self):
        self.log_limits()
        if self.gold_exhausted():
            self.finish("Gold limit is lower than the cheapest bookmark, nothing to buy")
            return

        while True:
            self.check_store()
            # Checked after buying and before refreshing, so no skystones are
            # wasted on a refresh that could not be used.
            reason = self.stop_reason()
            if reason is not None:
                self.finish(reason)
                return
            self.refresh()

    def start_auto_buy_secret_shop_from_lobby(self):
        self.ScreenManager.ensure_not_on_sleep_mode_on_lobby()

        self.ScreenManager.random_click_on_area_and_check_change_on_screen_retry(
            x1=683, y1=204, x2=728, y2=246, action="Click on Bartender")
        self.start_auto_buy_secret_shop()
