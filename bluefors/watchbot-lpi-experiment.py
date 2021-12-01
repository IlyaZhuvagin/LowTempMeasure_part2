# encoding: utf-8

import threading
import psutil
import time
import logging
import xmlrpc.client
import datetime
import socket
import os
import sys

import telegram
from telegram.ext import Updater
from telegram.ext import CommandHandler

socket.setdefaulttimeout(1)

os.makedirs("log/", exist_ok=True)
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s",
                    level=logging.DEBUG,
                    handlers=[logging.FileHandler(os.path.join("log", "watchbot-lpi-experiment-{:%Y-%m-%d---%H-%M}.txt".format(datetime.datetime.today()))),
                              logging.StreamHandler(sys.stdout)])

UPDATER = None
CHAT_IDS = []
STATUS_THREAD = None


def start(bot, update):
    CHAT_IDS.append(update.message.chat_id)
    bot.sendMessage(chat_id=update.message.chat_id, text="Your are the listener now!")


def stop(bot, update):
    try:
        CHAT_IDS.remove(update.message.chat_id)
        bot.sendMessage(chat_id=update.message.chat_id, text="Removed from the listeners list!")
    except ValueError:
        bot.sendMessage(chat_id=update.message.chat_id, text="Your were not the listener!")


def status(bot, update):
    msg = ""

    msg += "Listener: *" + str(update.message.chat_id in CHAT_IDS).upper() + "*\n"
    msg += "Thread running: *" + str(not STATUS_THREAD.is_alive()).upper() + "*\n"
    msg += "Experiment2 running: *" + str(STATUS_THREAD.experiment2_found).upper() + "*\n"

    if STATUS_THREAD.status_time is not None:
        delta = int((datetime.datetime.now() - STATUS_THREAD.status_time).total_seconds())
        msg += f"Status timestamp: *{delta//60:02d}:{delta%60:02d}* ago\n\n"

        for key, value in STATUS_THREAD.status.items():
            msg += str(key) + ": *" + str(value) + "*\n"

    bot.sendMessage(chat_id=update.message.chat_id,
                    parse_mode=telegram.ParseMode.MARKDOWN,
                    text=msg)


class StatusThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

        self.stopped = False
        self.experiment2_found = False
        self.status = {}
        self.status_time = None

    def run(self):
        global UPDATER, CHAT_IDS

        while not self.stopped:

            try:
                self.experiment2_found = False

                for process in psutil.process_iter():
                    try:
                        if "python" not in process.name().lower():
                            continue

                        if "experiment2" in process.cmdline()[1]:
                            self.experiment2_found = True
                            break

                    except psutil.NoSuchProcess:
                        pass

                if not self.experiment2_found:
                    logging.warning("Experiment2 process not found!")
                    for chat_id in CHAT_IDS:
                        UPDATER.bot.sendMessage(chat_id, text="Experiment2 process not found!")

                try:
                    logging.debug("Sending request...")
                    with xmlrpc.client.ServerProxy("http://127.0.0.1:13000", allow_none=True) as proxy:
                        self.status = proxy.status()
                        self.status_time = datetime.datetime.now()
                except Exception as exc:
                    logging.exception(exc)

                    for chat_id in CHAT_IDS:
                        UPDATER.bot.sendMessage(chat_id,
                                                text="Experiment2 xml rpc client error!")

            except Exception as exc:
                logging.error("Exception is StatusThread!")
                logging.exception(exc)

                try:
                    for chat_id in CHAT_IDS:
                        UPDATER.bot.sendMessage(chat_id,
                                                text="Experiment2 monitoring thread error!")
                except Exception as exc:
                    logging.error("Exception in sendMessage!")
                    logging.exception(exc)


            time.sleep(1)


if __name__ == "__main__":
    UPDATER = Updater(token="597022404:AAE14MzErf1OMwZ-xIU4AKAMuHcdhv9pLWU",
                      request_kwargs={
                          "proxy_url": "socks5://127.0.0.1:9150"
                      })

    UPDATER.dispatcher.add_handler(CommandHandler("start", start))
    UPDATER.dispatcher.add_handler(CommandHandler("stop", stop))
    UPDATER.dispatcher.add_handler(CommandHandler("status", status))

    STATUS_THREAD = StatusThread()
    STATUS_THREAD.start()

    UPDATER.start_polling(timeout=30)
