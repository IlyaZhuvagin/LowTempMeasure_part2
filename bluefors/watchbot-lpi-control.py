# encoding: utf-8

import threading
import time
import logging
import datetime
import serial
import os
import sys

import telegram
from telegram.ext import Updater
from telegram.ext import CommandHandler

os.makedirs("log/", exist_ok=True)
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s",
                    level=logging.DEBUG,
                    handlers=[logging.FileHandler(os.path.join("log", "watchbot-lpi-control-{:%Y-%m-%d---%H-%M}.txt".format(datetime.datetime.today()))),
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
    msg += "Thread running: *" + str(STATUS_THREAD.is_alive()).upper() + "*\n"

    if STATUS_THREAD.status_time is not None:
        delta = int((datetime.datetime.now() - STATUS_THREAD.status_time).total_seconds())
        msg += f"Status timestamp: *{delta//60:02d}:{delta%60:02d}* ago\n\n"

        msg += f"Compressor state: *{'ON' if STATUS_THREAD.compressor_on else 'OFF'}*\n"
        if STATUS_THREAD.error_code != 0:
            msg += f"ERROR: *{STATUS_THREAD.error_code}*\n"
        msg += f"All thermometers ok: *{str(not STATUS_THREAD.temp_err_any).upper()}*\n"
        msg += f"Input water temperature = *{STATUS_THREAD.input_water_temp:.1f}*\n"
        msg += f"Output water temperature = *{STATUS_THREAD.output_water_temp:.1f}*\n"
        msg += f"Helium temperature = *{STATUS_THREAD.helium_temp:.1f}*\n"
        msg += f"Oil temperature = *{STATUS_THREAD.oil_temp:.1f}*\n"

    bot.sendMessage(chat_id=update.message.chat_id,
                    parse_mode=telegram.ParseMode.MARKDOWN,
                    text=msg)


class StatusThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

        self.stopped = False
        self.status_time = None
        self.input_water_temp = None
        self.output_water_temp = None
        self.helium_temp = None
        self.oil_temp = None
        self.temp_err_any = None
        self.compressor_on = None
        self.error_code = None

    def query(self, port, data):
        stx = b"\x02"
        addr = b"\x10"
        cmd_rsp = b"\x80"
        data = data
        cr = b"\x0d"

        chksum = (addr[0] + cmd_rsp[0] + data[0] + data[1] + data[2] + data[3]) % 256
        cksum1 = ((chksum & 0b11110000) >> 4) + 0x30
        cksum2 = (chksum & 0b00001111) + 0x30

        # BYTE STUFFING
        data = data.replace(b"\x07", b"\x07\x32").replace(b"\x02", b"\x07\x30").replace(b"\x0d", b"\x07\x31")

        msg = stx + addr + cmd_rsp + data + bytes([cksum1]) + bytes([cksum2]) + cr
        
        logging.debug(">---> " + repr(msg))

        port.write(msg)
        recv = port.read()
        while recv[-1] != 0x0d:
            recv += port.read()

        logging.debug("<---< " + repr(recv))

        recv = recv.replace(b"\x07\x32", b"\x07").replace(b"\x07\x30", b"\x02").replace(b"\x07\x31", b"\x0d")                     
        
        return int.from_bytes(recv[7:11], byteorder="big")


    def run(self):
        global UPDATER, CHAT_IDS

        while not self.stopped:

            try:
                with serial.Serial("COM11", 115200, timeout=1) as port:
                    # Celsium degrees
                    self.input_water_temp = self.query(port, b"\x63\x0d\x8f\x00") * 0.1
                    self.output_water_temp = self.query(port, b"\x63\x0d\x8f\x01") * 0.1
                    self.helium_temp = self.query(port, b"\x63\x0d\x8f\x02") * 0.1
                    self.oil_temp = self.query(port, b"\x63\x0d\x8f\x03") * 0.1
                    # If true, one of thermometers failed
                    self.temp_err_any = bool(self.query(port, b"\x63\x6e\x2d\x00"))

                    self.compressor_on = bool(self.query(port, b"\x63\x5f\x95\x00"))
                    self.error_code = self.query(port, b"\x63\x65\xa4\x00")

                    self.status_time = datetime.datetime.now()

                    logging.info(f"All thermometers ok: {str(not self.temp_err_any).upper()}")
                    logging.info(f"Input water temperature = {self.input_water_temp:.1f}")
                    logging.info(f"Output water temperature = {self.output_water_temp:.1f}")
                    logging.info(f"Helium temperature = {self.helium_temp:.1f}")
                    logging.info(f"Oil temperature = {self.oil_temp:.1f}")
                    logging.info(f"Compressor state = {'ON' if self.compressor_on else 'OFF'}")
                    logging.info(f"Error code = {self.error_code}")

                    if self.error_code != 0:
                        for chat_id in CHAT_IDS:
                            UPDATER.bot.sendMessage(chat_id=chat_id,
                                                    parse_mode=telegram.ParseMode.MARKDOWN,
                                                    text=f"ERROR! ERROR CODE = {self.error_code}")

            except Exception as exc:
                logging.error("Exception in StatusThread!")
                logging.exception(exc)

                try:
                    for chat_id in CHAT_IDS:
                        UPDATER.bot.sendMessage(chat_id=chat_id,
                                                parse_mode=telegram.ParseMode.MARKDOWN,
                                                text=f"ERROR! Exception {exc}")
                except Exception as exc:
                    logging.error("Exception in sendMessage!")
                    logging.exception(exc)

            time.sleep(1)


if __name__ == "__main__":
    # WatchLPIControlBot
    UPDATER = Updater(token="572747699:AAFDT7h8dWLNBiY8LJvxDmFWAyZdLa-mL1Y",
                      request_kwargs={
                          "proxy_url": "socks5://127.0.0.1:9150"
                      })

    UPDATER.dispatcher.add_handler(CommandHandler("start", start))
    UPDATER.dispatcher.add_handler(CommandHandler("stop", stop))
    UPDATER.dispatcher.add_handler(CommandHandler("status", status))

    STATUS_THREAD = StatusThread()
    STATUS_THREAD.start()

    UPDATER.start_polling(timeout=30)
