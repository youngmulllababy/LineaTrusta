import csv
import json
import random
import time
from tqdm import tqdm


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