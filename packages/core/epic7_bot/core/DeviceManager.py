import glob
import logging
import os
import shutil
import socket
import string
import struct
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

from ppadb.client import Client
from epic7_bot.utils.Singleton import Singleton

try:
    import psutil
except ImportError:  # the bot still works, it just cannot look at running emulators
    psutil = None

EPIC7_PACKAGE = "com.stove.epic7.google"
SCREEN_WIDTH = 1600
SCREEN_HEIGHT = 900

# Default ADB ports of the supported emulators. Several instances of the same
# emulator use the next ports of the list. Any other port can be given with the
# EPIC7_ADB_PORT environment variable (comma separated).
EMULATOR_PORTS = {
    "MuMu 12": [16384 + 32 * i for i in range(16)],
    "MuMu": [7555],
    "BlueStacks": [5555 + 10 * i for i in range(4)],
    "LDPlayer": [5555 + 2 * i for i in range(10)],
    "Nox": [62001] + list(range(62025, 62035)),
    "MEmu": [21503 + 10 * i for i in range(10)],
    "iTools": [54001],
    "TTPlayer": [6555],
    "Droid4X": [26744],
}

# Processes of the emulators, used to find the adb.exe that belongs to the one
# that is running (a different adb version would restart the ADB server).
EMULATOR_PROCESSES = {
    "mumuplayer.exe", "mumunxmain.exe", "mumunxdevice.exe", "mumuvmmheadless.exe",
    "mumuvmmsvc.exe", "nemuplayer.exe", "nemuheadless.exe",
    "hd-player.exe", "bluestacks.exe", "hd-agent.exe",
    "nox.exe", "noxvmhandle.exe", "noxvmsvc.exe",
    "memu.exe", "memuheadless.exe", "memuconsole.exe",
    "dnplayer.exe", "ld9boxheadless.exe", "ldvboxheadless.exe", "ldplayer.exe",
}
ADB_NAMES = ("adb.exe", "HD-Adb.exe", "nox_adb.exe")
ADB_SUBDIRS = ("", "shell", "nx_main", "bin")

# Last resort: usual install folders, relative to a drive or to "Program Files"
KNOWN_ADB_PATTERNS = (
    "Netease/MuMu*/shell/adb.exe",
    "Netease/MuMu*/nx_main/adb.exe",
    "MuMu*/shell/adb.exe",
    "MuMu*/nx_main/adb.exe",
    "BlueStacks*/HD-Adb.exe",
    "Nox/bin/nox_adb.exe",
    "Nox/bin/adb.exe",
    "Microvirt/MEmu/adb.exe",
    "LDPlayer*/adb.exe",
    "ChangZhi/ldplayer*/adb.exe",
)

BLUESTACKS_FOLDERS = ("BlueStacks_nxt", "BlueStacks_nxt_cn", "BlueStacks_msi5")


def existing_drives():
    return [f"{letter}:\\" for letter in string.ascii_uppercase
            if os.path.exists(f"{letter}:\\")]


def guess_emulator(serial):
    """Best guess of the emulator behind an ADB serial. Only used for the logs."""
    if serial.startswith("emulator-"):
        return "LDPlayer / Android emulator"
    try:
        port = int(serial.rsplit(":", 1)[1])
    except (IndexError, ValueError):
        return "unknown emulator"
    for name, ports in EMULATOR_PORTS.items():
        if port in ports:
            return name
    return "unknown emulator"


class DeviceManager(metaclass=Singleton):
    def __init__(self):
        self.adb_path = self.find_adb_executable()
        self.device = self.setup_device()

    def setup_device(self):
        self.ensure_adb_is_running()
        self.connect_devices_to_adb()

        client = Client(host="127.0.0.1", port=5037)
        devices = client.devices()
        if len(devices) == 0:
            logging.error(
                "No device found, are you sure your emulator (MuMu, BlueStacks, Nox, "
                "MEmu, LDPlayer...) is open and ADB is enabled in its settings?")
            sys.exit()
        logging.info(
            f"Found {len(devices)} devices: "
            + ", ".join(f"{d.serial} ({guess_emulator(d.serial)})" for d in devices))

        device = self.pick_epic7_device(devices)
        logging.info(f"Using device {device.serial} for Epic Seven")

        self.ensure_screen_size(device)
        return device

    def ensure_device_has_epic7_app(self, device):
        try:
            return device.is_installed(EPIC7_PACKAGE)
        except Exception as e:
            return None

    def is_epic7_running(self, device):
        """True / False if Epic Seven is running on the device, None if it cannot be told."""
        try:
            out = (device.shell(f"pidof {EPIC7_PACKAGE}") or "").strip()
            if out and "not found" not in out.lower():
                return out.split()[0].isdigit()
            if not out:
                return False
            # `pidof` does not exist on old Android versions: look at the process list
            for command in ("ps -A", "ps"):
                out = device.shell(command) or ""
                if "PID" in out:
                    return EPIC7_PACKAGE in out
        except Exception as e:
            logging.debug(f"is_epic7_running: {str(e)}")
        return None

    def pick_epic7_device(self, devices):
        """The device that has Epic Seven. Stops the bot when there is none, so it
        never clicks on another game or app that is open in the emulator."""
        installed = [self.ensure_device_has_epic7_app(d) for d in devices]
        candidates = [d for d, ok in zip(devices, installed) if ok]
        if not candidates:
            # None = could not be checked, so give it a try instead of giving up
            candidates = [d for d, ok in zip(devices, installed) if ok is None]
            if not candidates:
                logging.error(
                    "Epic Seven is not installed on any device found "
                    f"({EPIC7_PACKAGE}). Stopping the bot.")
                sys.exit()
            logging.warning("Could not check if Epic Seven is installed, trying anyway.")

        running = [self.is_epic7_running(d) for d in candidates]
        for d, is_running in zip(candidates, running):
            if is_running:
                return d
        if all(is_running is False for is_running in running):
            logging.error(
                "Epic Seven is installed but not running. Open the game on the "
                "lobby screen and start again. Stopping the bot.")
            sys.exit()
        return candidates[0]

    def get_screenshot_size(self, device):
        """(width, height) of what the bot will actually see, read from the PNG header.

        `wm size` is not reliable for this: emulators like MuMu report a portrait
        physical size (900x1600) and show it rotated to landscape.
        """
        try:
            data = device.screencap()
            if data and len(data) > 24 and data[:8] == b"\x89PNG\r\n\x1a\n":
                width, height = struct.unpack(">II", data[16:24])
                return width, height
        except Exception as e:
            logging.error(f"get_screenshot_size: {str(e)}")
        return None

    def ensure_screen_size(self, device):
        target = (SCREEN_WIDTH, SCREEN_HEIGHT)
        size = self.get_screenshot_size(device)
        if size == target:
            logging.info(
                f"Device {device.serial} screen is already {SCREEN_WIDTH}x{SCREEN_HEIGHT}, "
                f"leaving it untouched")
            return

        logging.info(f"Device {device.serial} screen is {size}, adjusting to "
                     f"{SCREEN_WIDTH}x{SCREEN_HEIGHT}")

        # A leftover `wm size` override can distort rotated emulators (MuMu),
        # so go back to the default size first and check again.
        device.shell("wm size reset")
        size = self.get_screenshot_size(device)
        if size == target:
            logging.info(f"Device {device.serial} size is {SCREEN_WIDTH}x{SCREEN_HEIGHT} "
                         f"after resetting the override")
            return

        device.shell(f"wm size {SCREEN_WIDTH}x{SCREEN_HEIGHT}")
        logging.info(
            f"Set device {device.serial} size to {SCREEN_WIDTH}x{SCREEN_HEIGHT}")
        size = self.get_screenshot_size(device)
        if size != target:
            logging.warning(
                f"Device {device.serial} screenshot size is {size}, but the bot needs "
                f"{SCREEN_WIDTH}x{SCREEN_HEIGHT}. Set the emulator to landscape "
                f"{SCREEN_WIDTH}x{SCREEN_HEIGHT} in its settings, otherwise clicks "
                f"and image matching will miss.")

    # ---------- adb executable ----------

    def find_adb_in_folder(self, folder):
        """Looks for an adb.exe in the folder of an emulator process and 2 levels above."""
        current = folder
        for _ in range(3):
            for sub in ADB_SUBDIRS:
                for name in ADB_NAMES:
                    candidate = os.path.join(current, sub, name)
                    if os.path.isfile(candidate):
                        return candidate
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent
        return None

    def find_adb_of_running_emulator(self):
        if psutil is None:
            return None
        try:
            for proc in psutil.process_iter(["name", "exe"]):
                name = (proc.info.get("name") or "").lower()
                exe = proc.info.get("exe")
                if name in EMULATOR_PROCESSES and exe:
                    adb = self.find_adb_in_folder(os.path.dirname(exe))
                    if adb:
                        logging.info(f"Using ADB of the running emulator {proc.info.get('name')}: {adb}")
                        return adb
        except Exception as e:
            logging.error(f"find_adb_of_running_emulator: {str(e)}")
        return None

    def find_adb_in_known_folders(self):
        for drive in existing_drives():
            for root in (drive, os.path.join(drive, "Program Files"),
                         os.path.join(drive, "Program Files (x86)")):
                for pattern in KNOWN_ADB_PATTERNS:
                    matches = sorted(glob.glob(os.path.join(root, pattern)))
                    if matches:
                        logging.info(f"Using ADB found in an emulator folder: {matches[-1]}")
                        return matches[-1]
        return None

    def find_adb_executable(self):
        custom = os.environ.get("EPIC7_ADB_PATH", "").strip().strip('"')
        if custom:
            if os.path.isfile(custom):
                logging.info(f"Using ADB from EPIC7_ADB_PATH: {custom}")
                return custom
            logging.warning(
                f"EPIC7_ADB_PATH is set but the file does not exist: {custom}")

        return (self.find_adb_of_running_emulator()
                or shutil.which("adb")
                or self.find_adb_in_known_folders()
                or "adb")

    def run_adb(self, *args, timeout=15):
        try:
            return subprocess.run(
                [self.adb_path, *args],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                timeout=timeout,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception as e:
            logging.error(f"adb {' '.join(args)} failed: {str(e)}")
            return None

    def ensure_adb_is_running(self):
        logging.info("Ensuring ADB is running")
        result = self.run_adb("start-server")
        if result is not None and result.returncode != 0:
            logging.error(
                f"ensure_adb_is_running - Something went wrong: "
                f"{result.stderr.decode(errors='replace')}")

    # ---------- finding the emulators ----------

    @staticmethod
    def is_port_open(port, host="127.0.0.1", timeout=0.3):
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            return False

    def read_bluestacks_ports(self):
        ports = set()
        for drive in existing_drives():
            for folder in BLUESTACKS_FOLDERS:
                path = os.path.join(drive, "ProgramData", folder, "bluestacks.conf")
                try:
                    if not os.path.isfile(path):
                        continue
                    logging.info(f"Checking Bluestacks Config on: {path}")
                    with open(path, "r") as f:
                        for line in f:
                            if "=" not in line:
                                continue
                            key, value = line.strip().split("=", 1)
                            if "adb_port" in key:
                                value = value.replace('"', "").strip()
                                if value.isdigit():
                                    ports.add(int(value))
                except Exception as e:
                    logging.error(f"read_bluestacks_ports: {str(e)}")
        return ports

    def find_emulator_ports(self):
        """Default ADB ports of every supported emulator that are listening right now."""
        candidates = sorted({p for ports in EMULATOR_PORTS.values() for p in ports})
        with ThreadPoolExecutor(max_workers=len(candidates)) as pool:
            opened = list(pool.map(self.is_port_open, candidates))
        ports = {p for p, is_open in zip(candidates, opened) if is_open}
        if ports:
            logging.info(f"Found emulator ADB ports listening: {sorted(ports)}")
        return ports

    def read_user_ports(self):
        ports = set()
        raw_ports = os.environ.get("EPIC7_ADB_PORT", "").replace(";", ",")
        for raw in raw_ports.split(","):
            raw = raw.strip()
            if raw.isdigit():
                ports.add(int(raw))
        return ports

    def connect_devices_to_adb(self):
        logging.info("Ensuring devices are connected")
        try:
            ports = set()
            ports |= self.read_bluestacks_ports()
            ports |= self.find_emulator_ports()
            ports |= self.read_user_ports()

            for port in sorted(ports):
                address = f"127.0.0.1:{port}"
                logging.info(f"Running \"adb connect {address}\"")
                self.run_adb("connect", address, timeout=10)
        except Exception as e:
            logging.error(
                f"connect_devices_to_adb - Something went wrong. {(str(e))}")
