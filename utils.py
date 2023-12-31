import csv
import json
import random
import time
from requests import post
from loguru import logger
from tqdm import tqdm
import telebot
import settings


class Utils:

    @staticmethod
    def sleeping(from_sleep, to_sleep):
        x = random.randint(from_sleep, to_sleep)
        for i in tqdm(range(x), desc='sleep ', bar_format='{desc}: {n_fmt}/{total_fmt}'):
            time.sleep(1)

    @staticmethod
    def load_abi() -> str:
        with open(f'data/abi.json') as f:
            abi: str = json.load(f)
        return abi

    @staticmethod
    def write_to_csv(res):
        with open(f'results.csv', 'a', newline='', encoding='utf-8-sig') as file:
            writer = csv.DictWriter(file, res.keys())
            if file.tell() == 0:
                writer.writeheader()
            writer.writerow(res)

    @staticmethod
    def change_ip(session):
        if settings.CHANGE_IP_LINK not in ['https://changeip.mobileproxy.space/?proxy_key=...&format=json', '']:
            while True:
                r = session.get(settings.CHANGE_IP_LINK)
                if r.status_code == 200:
                    logger.info(f'[+] Proxy | Changed ip: {r.text}')
                    return True
                logger.warning(f'[•] Proxy | Change IP error: {r.text} | {r.status_code} {r.reason}')
                Utils.sleeping(10,10)

    @staticmethod
    def send_msg(messages):
        try:
            if messages and settings.TG_BOT_TOKEN \
                    and settings.TG_USER_ID:
                messages.insert(0, 'Linea - Week 6 (Trusta)')
                str_send = '\n'.join(messages)
                bot = telebot.TeleBot(settings.TG_BOT_TOKEN)
                bot.send_message(settings.TG_USER_ID, str_send, parse_mode='html')
        except Exception as error:
            logger.error(error)

