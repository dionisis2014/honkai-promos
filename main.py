"""
    Copyright (C) 2024  dionisis2014

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published
    by the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import json
import logging
import os
import pickle
import signal
import sys
from datetime import datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from typing import List, Tuple

import bs4
import colorlog
import pause
import requests
from colorlog.escape_codes import escape_codes as ec
from ha_mqtt_discoverable import Settings, DeviceInfo
from ha_mqtt_discoverable.sensors import DeviceTriggerInfo, DeviceTrigger

# STATIC AND ENVIRONMENT VARIABLES

URL_PAGE = "https://honkaiimpact3.fandom.com/wiki/Exchange_Rewards"

VERSION = "1.0.0"

HASS_HOST = os.environ['HASS_HOST']
HASS_USER = os.environ['HASS_USER']
HASS_PASS = os.environ['HASS_PASS']
RETRY_DELAY = 10
LOG_LEVEL = colorlog.INFO

PATH = "/mnt"
FILENAME = "last.pickle"

LOGO = """
     ██▄▄▄▄▄
      ██████████▄▄▄▄▄
       ▀██████████▄▀▀█████▄▄▄▄                    ▄▄▄▄▄
         ▀▀███████████▄▄██▀████████▄▄▄▄             ▀▀████▄▄    ▄▄▄▄▄▄▄▄▄
              ▀▀▀████████████▄▀█████▀█████▄▄           ▀▀▀█▄█████▀▀▀▀▀ ▄█████▄▄
                    ▀▀▀███████▄ ▀████████▄▄████▄       ▄█████████ ████▄▄▄▄█▀▀▀██▄
                         ▀▀▀▀▀▀  ▀███▄▄█████▀        ▄██████████████████▄██▄▄▄▀██
  ▄▄▄▄                              ▀▀██████▄    ▄██████████████████▄▀████████
  ▀█████████████████▄▄▄▄▄▄▄▄▄▄▄▄█████████▄▄▀▀██▀▀▀▀██████████  ▀▀ ▄▄▄▄▄███████
    ▀▀███████████████▀████████▀▀▀▀▀▀▀▀█▄████ ▄████████▀▀▀▀▀▀▀   ▀█████▀▀▀
              ▀▀▀▀▀▀▀██████▄▄          ▀▄▄▄▄▄██▀█████▀▄█▀▀▀▀ █████▄▄█
                                    ▄▄█▄███████▄▄███▀▄▄▄██████▀█▄ ▀▀▀██
                          ▀██████████▀▀▀▄▄▄ ▀  ▀███▄██▀████▄▄█ ██████████
                            ▄███▀▀█▄█████          ▀▀▀▀▀▀▀▀▀▀ ▄▀█████████▀██▄
              ▄▄▄▄▄▄███████▄▄▄▄██████████▄                ▄▄██ ███████████ ███
          ▀▀▀▀▀▀██████▀▀▀▀▀▀▀         ▀▀▀                ▀▀▀▀▀ ▀█████████▀▄██▀
                                                            ▄▄▄▄ ▄██▀   ▄▀▀
                                                            ▀████████▄▄▀
                                                               ▀▀████▀
                                                                   ▀
"""


# EARLY SETUP

def signal_handler(*_):
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

try:
    RETRY_DELAY = max(int(os.environ['RETRY_DELAY']), 1)
except (ValueError, TypeError):
    pass
if os.environ['LOG_LEVEL'] in logging.getLevelNamesMapping():
    LOG_LEVEL = os.environ['LOG_LEVEL']

colorlog.basicConfig(level=LOG_LEVEL)
logger = colorlog.getLogger(__name__)


# CLASS AND METHOD DEFINITIONS

class ParseException(RuntimeError):
    pass


def fetch(url: str) -> List[Tuple[str, bool]]:
    codes_: List[Tuple[str, bool]] = []

    try:
        logger.debug("Fetching promo code page ...")
        response: requests.Response = requests.get(url, allow_redirects=True)
        if response.ok:
            logger.debug("Parsing HTML document ...")
            soup: bs4.BeautifulSoup = bs4.BeautifulSoup(response.content, 'html.parser')
            main: bs4.Tag | None = soup.find('main')
            if main is None:
                raise ParseException("Failed to parse response (<main> not found)")
            table_bodies: bs4.ResultSet = main.find_all('tbody')
            for body in table_bodies:
                rows: bs4.ResultSet = body.find_all('tr')
                for row in rows:
                    code: bs4.ResultSet = row.find_all('td')
                    if len(code) != 5:
                        if len(row.find_all('th')) != 5:
                            raise ParseException("Failed to parse response (invalid <td> number in row)")
                        else:
                            continue
                    codes_.append((code[0].text, code[4].text.strip() != 'No'))
    except HTMLParser.HTMLParseError as ex:
        logger.error(ex)
    except requests.exceptions.RequestException as ex:
        logger.error(ex)
    finally:
        return codes_


def get_new(new_codes: List[Tuple[str, bool]]) -> List[Tuple[str, bool]] | None:
    try:
        with open(Path(PATH) / FILENAME, "rb") as file:
            last_num: int = pickle.load(file)
            logger.debug(f"Last check found {last_num} promo code{'' if last_num == 1 else 's'}")
            if last_num <= len(new_codes):
                logger.debug("New promo codes found")
                return new_codes[:len(new_codes) - last_num]
            logger.debug("No new promo codes found")
            return None
    except FileNotFoundError:
        logger.debug("Save file not found. Is this our first run?")
        logger.debug("All new promo codes will be treated as new ones")
        return new_codes
    except Exception as ex:
        logger.error(ex)
        return None
    finally:
        logger.debug("Saving new promo code count to save file ...")
        with open(Path(PATH) / FILENAME, "wb") as file:
            pickle.dump(len(new_codes), file)


# MAIN PROGRAM ENTRY

if __name__ == "__main__":
    if colorlog.root.level <= logging.INFO:
        print(f"{ec['cyan']}{LOGO}{ec['reset']}")
        print(f"{ec['bold']}{f'Honkai Impact 3rd promo code notifier v{VERSION}'.center(80).rstrip()}{ec['reset']}\n")

    logger.info(f"Home Assistant MQTT connection: {os.environ['HASS_USER']}@{os.environ['HASS_HOST']}")
    logger.debug("Setting up MQTT settings ...")
    mqtt_settings = Settings.MQTT(host=HASS_HOST, username=HASS_USER, password=HASS_PASS)

    logger.debug("Setting up device info ...")
    device_info = DeviceInfo(
        name="Honkai Impact 3rd Promos",
        sw_version=VERSION,
        identifiers="honkai_promos"
    )

    logger.debug("Setting up trigger info ...")
    trigger_info = DeviceTriggerInfo(
        name="New Codes Trigger",
        type="codes",
        subtype="found_new",
        unique_id="trigger",
        device=device_info
    )
    logger.debug("Setting up trigger settings ...")
    trigger_settings = Settings(mqtt=mqtt_settings, entity=trigger_info)
    logger.debug("Setting up trigger ...")
    trigger = DeviceTrigger(trigger_settings)
    logger.debug("Sending configuration to Home Assistant ...")
    trigger.write_config()

    logger.debug("Entering main loop ...")
    while True:
        wakeup: datetime = datetime.now()
        wakeup = wakeup.replace(
            hour=(wakeup.hour // 12) * 12,
            minute=0,
            second=0,
            microsecond=0
        )
        logger.debug(f"Current time slot: {wakeup}")

        try:
            logger.debug("Fetching available promo codes ...")
            codes = get_new(fetch(URL_PAGE))
            logger.debug(f"Found {len(codes)} promo code{'' if len(codes) == 1 else 's'}")

            if codes:
                logger.info(f"Found {len(codes)} new code{'' if len(codes) == 1 else 's'}: "
                            f"[ {' '.join(code[0] for code in codes)} ]")
                logger.debug("Sending trigger to Home Assistant ...")
                trigger.trigger(json.dumps(
                    {
                        "active": [code[0] for code in codes if not code[1]],
                        "expired": [code[0] for code in codes if code[1]]
                    }
                ))
        except Exception as ex:
            if isinstance(ex, ParseException):
                logger.error(f"Failed to check for promo codes: {ex}")
            else:
                logger.error(f"Unknown error while checking for promo codes: {ex}")
            logger.warning(f"Retying in {RETRY_DELAY} minute{'' if RETRY_DELAY == 1 else 's'} ...")
            wakeup += timedelta(minutes=RETRY_DELAY)
        else:
            wakeup += timedelta(hours=12)

        logger.debug(f"Next check @ {wakeup}")
        pause.until(wakeup)
