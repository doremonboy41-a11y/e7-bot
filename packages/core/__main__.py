import multiprocessing
import epic7_bot.cli as cli
import os

if __name__ == "__main__":
    multiprocessing.set_start_method("spawn", force=True)
    multiprocessing.freeze_support()
    cli.main()
