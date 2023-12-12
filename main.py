import asyncio
import random
import sys
from loguru import logger
from Trusta import Trusta
from settings import SLEEP_BETWEEN_ATTESTATIONS, ATTESTATION_TYPES
from utils import Utils

with open('data/tokens.txt', 'r') as file:
    tokens = [i.strip() for i in file]

with open('data/private_keys.txt', 'r') as file:
    private_keys = [i.strip() for i in file]

with open('data/proxies.txt', 'r') as file:
    proxies = [i.strip() for i in file]


def set_windows_event_loop_policy():
    if sys.version_info >= (3, 8) and sys.platform.lower().startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


set_windows_event_loop_policy()


async def main():
    for i, (token, key) in enumerate(zip(tokens, private_keys)):
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
                res['status'] = "SUCCESS"
                Utils.write_to_csv(res)
                Utils.sleeping(*SLEEP_BETWEEN_ATTESTATIONS)
        except Exception as e:
            res['status'] = 'FAILURE'
            Utils.write_to_csv(res)
            logger.error(f'failed white trying to complete {attest_type} attestation - {e}')
            Utils.sleeping(1, 10)


if __name__ == '__main__':
    asyncio.run(main())
