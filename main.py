import asyncio
import random
import sys
from loguru import logger

import settings
from Trusta import Trusta
from config import SUCCESS_ICON, FAIL_ICON
from settings import SLEEP_BETWEEN_ATTESTATIONS, ATTESTATION_TYPES
from utils import Utils

with open('data/tokens.txt', 'r') as file:
    tokens = [row.strip() for row in file if not row.isspace()]

with open('data/private_keys.txt', 'r') as file:
    private_keys = [row.strip() for row in file if not row.isspace()]

with open('data/proxies.txt', 'r') as file:
    proxies = [row.strip() for row in file if not row.isspace()]


def set_windows_event_loop_policy():
    if sys.version_info >= (3, 8) and sys.platform.lower().startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


set_windows_event_loop_policy()


async def main():
    indexes = list(range(len(tokens)))
    if settings.SHUFFLE_WALLETS:
        random.shuffle(indexes)

    for i, index in enumerate(indexes):
        tg_messages = []
        logger.info(f'account {i+1}/{len(tokens)}')
        token = tokens[index]
        key = private_keys[index]
        proxy = None
        if proxies:
            proxy = proxies[i % len(proxies)]
        trusta = Trusta(proxy, key, token)
        res = {
            'address': trusta.address,
            'key': key,
            'auth_token': token,
        }

        random.shuffle(ATTESTATION_TYPES)

        try:
            for attest_type in ATTESTATION_TYPES:
                res['attest_type'] = attest_type
                await trusta.attest(attest_type)
                tg_messages.append(
                    f"[{SUCCESS_ICON}][{i+1}/{len(tokens)}][{trusta.address}]\nCompleted {attest_type} attestation")
                res['status'] = "SUCCESS"
                Utils.write_to_csv(res)
                Utils.sleeping(*SLEEP_BETWEEN_ATTESTATIONS)
        except Exception as e:
            tg_messages.append(
                f"[{FAIL_ICON}][{i + 1}/{len(tokens)}][{trusta.address}]\nfailed {attest_type} attestation")
            res['status'] = 'FAILURE'
            Utils.write_to_csv(res)
            logger.error(f'failed white trying to complete {attest_type} attestation - {e}')
            Utils.sleeping(1, 10)
        finally:
            Utils.send_msg(tg_messages)


if __name__ == '__main__':
    asyncio.run(main())
