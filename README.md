<div align="center">

<h1 align="center">
Epic7 Bot
</h1>

Version 1.0.0 · by Kazari
</div>

## Disclaimer

This software is an external tool designed to automate playing Epic Seven. It is designed to interact with the game only through existing user interfaces and comply with relevant laws and regulations. The package aims to provide simplified and user-friendly interaction with the game, and it is not intended to disrupt game balance in any way or provide any unfair advantages. The package will not modify any game files or game code in any way.

This software is open source, free of charge, and for learning and exchange purposes only. The developer team has the final right to interpret this project. All problems arising from the use of this software are not related to this project and the developer team. If you encounter a merchant using this software to practice on your behalf and charging for it, it may be the cost of equipment and time, etc. The problems and consequences arising from this software have nothing to do with it.

## Requirements
- [Android Debug Bridge](https://community.chocolatey.org/packages/adb)

### Supported emulators

MuMu, BlueStacks, LDPlayer, Nox and MEmu (also iTools, TTPlayer and Droid4X). The bot looks for them by itself:

- It checks the default ADB ports of each emulator and runs `adb connect` on the ones that are open: MuMu 12 `16384 + 32 * n`, MuMu `7555`, BlueStacks the ports of `bluestacks.conf` (usually `5555`, `5565`...), LDPlayer `5555 + 2 * n` (or `emulator-5554`), Nox `62001`, `62025`..., MEmu `21503 + 10 * n`.
- It uses the `adb.exe` of the emulator that is running (`adb.exe`, `HD-Adb.exe` or `nox_adb.exe`), so the ADB server is not restarted by a different version. If the emulator is not running yet it falls back to the `adb` of your PATH, then to the usual install folders.
- The Logs show every device found with its emulator, e.g. `127.0.0.1:16416 (MuMu 12)`.
- If your emulator uses another port, set the `EPIC7_ADB_PORT` environment variable (comma separated for several ports), e.g. `setx EPIC7_ADB_PORT 5555`, then restart the bot. To force an `adb.exe`, set `EPIC7_ADB_PATH`.
- The emulator must run in landscape. The bot sets 1600x900 by itself when needed, but 1600x900 in the emulator settings is the safest.

### Secret Shop options

On the Shop page:

- **Speed**: from 1x (the original timing) to 10x. It divides every wait of the bot. Higher speeds are less stable, lower it if clicks start missing.
- **Refresh limit**: tick **Skystone** or **Gold** (only one at a time, the other one is dimmed) and type the amount. Leave both unticked to refresh until you press Stop.
    - Skystone: stops after spending that many skystones (3 skystones = 1 refresh). The last refresh is always scanned before stopping.
    - Gold: only buys while the total stays inside the amount (Covenant 184,000, Mystic 280,000) and stops when not even a Covenant fits.
- **Confirm & Start / Confirm & Restart**: starts the bot (or stops it and starts it again when it is already running) with the Speed and limit that are on screen.
- **Stop**: stops the bot. It is below Confirm and is only enabled while the bot is running.
- The bot only runs when an emulator with Epic Seven installed **and open** is found. Otherwise it stops by itself, the Logs say why and the status changes to **Stopped**.
- The Summary and the Logs show the total skystones and gold used. These totals are counted by the bot (each refresh/buy it clicked), they are not read from the game, so keep the limits below your real balance.

## Getting Started

1. Install Chocolatey https://chocolatey.org/install#individual.
    - Chocolatey is a package manager for Windows. It is easier to install Android Debug Bridge with it.
2. Install Android Debug Bridge by running  `choco install adb` on your terminal as admin.
    - Android Debug Bridge is command-line tool that enable communication with a device. It enables to send inputs directly to the emulator.
3. Enable Android Debug Bridge on your emulator of choice. **(MuMu, BlueStacks, LDPlayer, Nox and MEmu are supported.)**
    - Bluestacks: Settings > Advanced > Enable Android Debug Bridge.
    - LDPlayer: Settings > Other settings > ADB debugging > Enable local connection, save and restart the emulator.
    - MuMu Player: enable ADB debugging in the emulator settings (see the "ADB Manual" link in MuMu's About window).
    - Nox / MEmu: enable ADB / USB debugging in the emulator settings.
4. Open `Epic7 Bot.exe`.


