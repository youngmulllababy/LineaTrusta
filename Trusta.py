from time import sleep
from eth_account.messages import encode_defunct
from loguru import logger
from requests import Session
from fake_useragent import UserAgent
from better_automation.twitter import TwitterAccount, TwitterClient
from urllib.parse import urlparse, parse_qs
from web3 import Web3
import config
import settings
from utils import Utils


class Trusta:
    def __init__(self, proxy, private_key, auth_token):
        self.max_retries = 5
        ua = UserAgent()
        self.session = Session()
        self.session.headers = {
            'user-agent': ua.random,
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-US,en;q=0.5",
            "content-type": "application/json",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "Referer": "https://trustgo.trustalabs.ai/",
            "Origin": "https://trustgo.trustalabs.ai/",
        }
        self.auth_token = auth_token
        self.private_key = private_key
        self.w3 = Web3(Web3.HTTPProvider(config.RPC_DATA['linea']))
        self.account = self.w3.eth.account.from_key(private_key)
        self.address = self.account.address
        if proxy:
            Utils.change_ip(self.session)
            self.proxy = {'http': f'http://{proxy}', 'https': f'http://{proxy}'}
            self.session.proxies.update(self.proxy)
        else:
            logger.warning('You are not using proxy')

    def wait_for_linea_gwei(self):
        first_check = True
        while True:
            try:
                new_gwei = round(self.w3.eth.gas_price / 10 ** 9, 2)
                if new_gwei < settings.MAX_LINEA_GWEI:
                    if not first_check: logger.debug(f'New GWEI is {new_gwei}')
                    break
                sleep(5)
                if first_check:
                    first_check = False
                    logger.debug(f'Waiting for GWEI in Linea at least {settings.MAX_LINEA_GWEI}. Now it is {new_gwei}')
            except Exception as err:
                logger.warning(f'Gwei waiting error: {err}')
                Utils.sleeping(5, 15)
                
    async def attest(self, attest_type):
        logger.info(f'[{attest_type}][{self.address}][{self.auth_token}] starting work ')
        if not 'Authorization' in self.session.headers:
            logger.info(f'[{self.address}][{self.auth_token}] starting trusta auth')
            self.trusta_auth()
            Utils.sleeping(*settings.SLEEP_BETWEEN_REQUESTS)

        twitter_verified = self.trasta_check_twitter_status()
        Utils.sleeping(*settings.SLEEP_BETWEEN_REQUESTS)
        if not twitter_verified:
            logger.info(f'[{self.address}][{self.auth_token}] starting to verify twitter')
            await self.trusta_twitter_bind()
            Utils.sleeping(*settings.SLEEP_BETWEEN_REQUESTS)

            self.trusta_twitter_follow()
            logger.success(f'[{self.address}][{self.auth_token}] completed follow task')
            Utils.sleeping(*settings.SLEEP_BETWEEN_REQUESTS)
        else:
            logger.info(f'[{self.address}][{self.auth_token}] twitter already verified!')

        minted = self.is_attestation_minted(attest_type)
        Utils.sleeping(*settings.SLEEP_BETWEEN_REQUESTS)
        if minted:
            logger.warning(f'[{self.address}][{self.auth_token}] address already minted attestation type {attest_type}!')
            return
        self.mint_attestation(attest_type)


    def get_attestation_calldata(self, attest_type):
        response = self.session.get('https://mp.trustalabs.ai/accounts/attest_calldata', params={'attest_type': attest_type})
        json_response = response.json()
        return json_response['data']

    def is_attestation_minted(self, attest_type):
        response = self.session.get('https://mp.trustalabs.ai/accounts/attestation', params={'attest_type': attest_type})
        total_minted = response.json()['data']['total']
        return total_minted != 0

    def is_allowed_to_mint(self, attest_type, data):
        user_score = data['message']['score']
        min_score = config.ATTESTATION_SCORE[attest_type][0]
        max_score = config.ATTESTATION_SCORE[attest_type][1]
        allowed_to_mint = min_score <= user_score <= max_score
        return user_score, min_score, allowed_to_mint

    def mint_attestation(self, attest_type):
        humanity_data = self.get_attestation_calldata(attest_type='humanity')
        if not self.is_allowed_to_mint('humanity', humanity_data):
            raise Exception('cant mint humanity due to low score, skip to next account')
        data = self.get_attestation_calldata(attest_type=attest_type)
        user_score, min_score, allowed_to_mint = self.is_allowed_to_mint(attest_type, data)
        if not allowed_to_mint:
            raise Exception(f'wallet does not meet minimum criteria for mint - \nuser_score: {user_score}\n min_score: {config.ATTESTATION_SCORE[attest_type][0]}\n max_score: {config.ATTESTATION_SCORE[attest_type][1]}')
        self.wait_for_linea_gwei()

        calldata = data['calldata']['data']
        value = data['calldata']['value']
        abi = Utils.load_abi()

        logger.info(f'[{self.address}][{self.auth_token}] starting to mint attestation {attest_type}')

        contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(config.TRUSTA_ATTESTATION_CONTRACT),
            abi=abi,
        )
        function, arguments = contract.decode_function_input(calldata)
        attestation_payload = arguments['attestationPayload']
        validation_payloads = arguments['validationPayloads']

        tx = contract.functions.attest(attestation_payload, validation_payloads).build_transaction({
            'from': self.address,
            'value': value,
            'nonce': self.w3.eth.get_transaction_count(self.address),
            'gasPrice': self.w3.eth.gas_price
        })
        signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
        raw_tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        tx_hash = self.w3.to_hex(raw_tx_hash)
        tx_link = f'{config.CHAINS_DATA["linea"]["explorer"]}{tx_hash}'
        logger.debug(f'[Attestation type: {attest_type}][{self.address}] |tx sent: {tx_link}')

        status = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=int(settings.TO_WAIT_TX * 60)).status

        if status == 1:
            logger.success(f'[Attestation type: {attest_type}][{self.address}] | tx confirmed')
            return tx_hash
        else:
            logger.error(f'❌{tx_link}')
            raise Exception(f'transaction failed - {tx_link}')


    def trasta_check_twitter_status(self):
        r = self.session.get('https://mp.trustalabs.ai/twitter/twitter_task_info')
        res = r.json()
        if res['data'] == None:
            return False
        is_verified = res['data']['has_auth']
        return is_verified


    def trusta_twitter_follow(self):
        params = {
            'event': 'FOLLOW',
            'target': 'LINEA'
        }
        self.session.get('https://mp.trustalabs.ai/twitter/twitter_event', params=params)

        params = {
            'event': 'FOLLOW',
            'target': 'TRUSTALABS'
        }
        self.session.get('https://mp.trustalabs.ai/twitter/twitter_event', params=params)


    async def trusta_twitter_bind(self):
        params = {
            'landing_page': 'https://trustgo.trustalabs.ai/etrusta/0xf9726ec833b7a4faf0965824bfe38f986005c3c0/lineaverax/m?f=linea&chainId=59144'
        }

        r = self.session.get('https://mp.trustalabs.ai/twitter/twitter_auth_url', params=params)
        res = r.json()
        auth_data = res['data']
        data = urlparse(auth_data)
        parsed_data = parse_qs(data.query)

        state = parsed_data['state'][0]
        code_challenge = parsed_data['code_challenge'][0]

        account = TwitterAccount(self.auth_token)
        try:
            async with TwitterClient(account, proxy=self.proxy['http'], verify=False) as twitter:
                bind_data = {
                    'response_type': 'code',
                    'client_id': 'REdOWXBKeUh3aThXV2RTNnlBMm46MTpjaQ',
                    'redirect_uri': 'https://mp.trustalabs.ai/twitter/callback',
                    'scope': 'tweet.read users.read follows.read offline.access',
                    'state': state,
                    'code_challenge': code_challenge,
                    'code_challenge_method': 'plain'
                }

                bind_code = await twitter.bind_app(**bind_data)

            url = 'https://mp.trustalabs.ai/twitter/twitter_auth_callback'
            params = {
                'state': state,
                'code': bind_code
            }
            r = self.session.get(url, params=params)
            if r.status_code == 200:
                logger.success(f'[{self.address}][{self.auth_token}] twitter bind success')
            else:
                raise Exception('error while binding twitter')
        except Exception as e:
            reason = str(e)
            raise Exception(f'[twitter_bind] - {reason}')

    def trusta_auth(self):
        message = 'Please sign this message to confirm you are the owner of this address and Sign in to TrustGo App'
        message_object = encode_defunct(text=message)
        sign = self.w3.eth.account.sign_message(message_object, private_key=self.private_key)
        signature = self.w3.to_hex(sign.signature)
        payload = {
            'mode': 'evm',
            'address': self.address,
            'signature': signature,
            'message': message,
        }
        url = 'https://mp.trustalabs.ai/accounts/check_signed_message'

        r = self.session.post(url, json=payload)
        response = r.json()

        if response['success']:
            token = response['data']['token']
            self.session.headers.update({'Authorization': f'TOKEN {token}', 'Cookies': r.headers["Set-Cookie"].split(';')[0]})
            logger.success(f'[{self.address}][{self.auth_token}] auth success')
        else:
            raise Exception(f'error while sign in to trusta {r.status_code} | {response}')