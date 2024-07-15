import asyncio
from urllib.parse import unquote

import aiohttp
from aiocfscrape import CloudflareScraper
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
from pyrogram import Client
from pyrogram.errors import Unauthorized, UserDeactivated, AuthKeyUnregistered, FloodWait
from pyrogram.raw.functions.messages import RequestWebView

from bot.config import settings
from bot.utils import logger
from bot.exceptions import InvalidSession
from .headers import headers
from .agents import generate_random_user_agent
from datetime import datetime, timedelta, timezone
from random import shuffle, randint
import json


class Tapper:
    def __init__(self, tg_client: Client):
        self.session_name = tg_client.name
        self.tg_client = tg_client
        self.user_id = 0

    async def get_tg_web_data(self, proxy: str | None) -> str:
        if proxy:
            proxy = Proxy.from_str(proxy)
            proxy_dict = dict(
                scheme=proxy.protocol,
                hostname=proxy.host,
                port=proxy.port,
                username=proxy.login,
                password=proxy.password
            )
        else:
            proxy_dict = None

        self.tg_client.proxy = proxy_dict

        try:
            with_tg = True

            if not self.tg_client.is_connected:
                with_tg = False
                try:
                    await self.tg_client.connect()
                except (Unauthorized, UserDeactivated, AuthKeyUnregistered):
                    raise InvalidSession(self.session_name)

            while True:
                try:
                    peer = await self.tg_client.resolve_peer('cedex_tap_bot')
                    break
                except FloodWait as fl:
                    fls = fl.value

                    logger.warning(f"{self.session_name} | FloodWait {fl}")
                    logger.info(f"{self.session_name} | Sleep {fls}s")

                    await asyncio.sleep(fls + 3)

            web_view = await self.tg_client.invoke(RequestWebView(
                peer=peer,
                bot=peer,
                platform='android',
                from_bot_menu=False,
                url='https://cdxp.cedex.io/'
            ))
            auth_url = web_view.url
            tg_web_data = unquote(
                string=unquote(
                    string=auth_url.split('tgWebAppData=', maxsplit=1)[1].split('&tgWebAppVersion', maxsplit=1)[0]))

            self.user_id = (await self.tg_client.get_me()).id

            if with_tg is False:
                await self.tg_client.disconnect()

            return tg_web_data

        except InvalidSession as error:
            raise error

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error during Authorization: {error}")
            await asyncio.sleep(delay=3)

    async def startTasks(self, http_client: aiohttp.ClientSession, task_list, tg_web_data: str):
        try:
            shuffle(task_list)
            results = []
            for task_id in task_list:
                response = await http_client.post(url='https://cdxp.cedex.io/api/startTask',
                                                  json={'authData': tg_web_data, 'devAuthData': self.user_id,
                                                        'data': {'taskId': task_id}})
                response_text = await response.text()
                response.raise_for_status()
                data = json.loads(response_text)
                if data["status"] == "ok":
                    results.append(True)
                else:
                    logger.info(f'{self.session_name} | Непредвиденная ошибка')
                    results.append(False)
            return results
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when starting tasks, {error}")
            await asyncio.sleep(delay=3)
            return [error] * len(task_list)

    async def checkTasks(self, http_client: aiohttp.ClientSession, task_list, tg_web_data: str):
        try:
            shuffle(task_list)
            results = []
            for task_id in task_list:
                response = await http_client.post(url='https://cdxp.cedex.io/api/startTask/api/checkTask',
                                                  json={'authData': tg_web_data, 'devAuthData': self.user_id,
                                                        'data': {'taskId': task_id}})
                response_text = await response.text()
                response.raise_for_status()
                data = json.loads(response_text)
                if data["status"] == "ok":
                    results.append(True)
                else:
                    logger.info(f'{self.session_name} | Непредвиденная ошибка')
                    results.append(False)
            return results
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when claiming tasks, {error}")
            await asyncio.sleep(delay=3)
            return [error] * len(task_list)

    async def claimTasks(self, http_client: aiohttp.ClientSession, task_list, tg_web_data: str):
        try:
            shuffle(task_list)
            results = []
            for task_id in task_list:
                response = await http_client.post(url='https://cdxp.cedex.io/api/claimTask',
                                                  json={'authData': tg_web_data, 'devAuthData': self.user_id,
                                                        'data': {'taskId': task_id}})
                response_text = await response.text()
                response.raise_for_status()
                data = json.loads(response_text)
                if data["status"] == "ok":
                    results.append(True)
                else:
                    logger.info(f'{self.session_name} | Непредвиденная ошибка')
                    results.append(False)
            return results
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when claiming tasks, {error}")
            await asyncio.sleep(delay=3)
            return [error] * len(task_list)

    async def start_farm(self, http_client: aiohttp.ClientSession, tg_web_data: str) -> bool:
        try:
            response = await http_client.post(url='https://cdxp.cedex.io/api/startFarm',
                                              json={'authData': tg_web_data, 'devAuthData': self.user_id,
                                                    'data': {}})
            response_text = await response.text()
            response.raise_for_status()
            data = json.loads(response_text)
            if data["status"] == "ok":
                return True
            else:
                logger.info(f'{self.session_name} | Непредвиденная ошибка')
                return False
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when starting farm, {error}")
            await asyncio.sleep(delay=3)

            return False

    async def claim_farm(self, http_client: aiohttp.ClientSession, tg_web_data: str):
        try:
            response = await http_client.post(url='https://cdxp.cedex.io/api/claimFarm',
                                              json={'authData': tg_web_data, 'devAuthData': self.user_id,
                                                    'data': {}})
            response_text = await response.text()
            response.raise_for_status()
            data = json.loads(response_text)
            if data["status"] == "ok":
                return "ok"
            elif data["status"] == "error":
                return data["data"]["reason"]
            else:
                logger.info(f'{self.session_name} | Непредвиденная ошибка')
                return False
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when claiming farm, {error}")
            await asyncio.sleep(delay=3)

            return error

    async def profile_data(self, http_client: aiohttp.ClientSession, tg_web_data: str):
        try:
            response = await http_client.post(url='https://cdxp.cedex.io/api/getUserInfo',
                                              json={'authData': tg_web_data, 'devAuthData': int(self.user_id),
                                                    'data': {}, 'platform': 'ios'})

            response_text = await response.text()
            response.raise_for_status()      
            data = json.loads(response_text)
            if data:
                return data
            else:
                logger.error('Data error get')
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when getting data, {error}")
            await asyncio.sleep(delay=3)

            return error

    async def check_proxy(self, http_client: aiohttp.ClientSession, proxy: Proxy) -> None:
        try:
            response = await http_client.get(url='https://httpbin.org/ip', timeout=aiohttp.ClientTimeout(5))
            ip = (await response.json()).get('origin')
            logger.info(f"{self.session_name} | Proxy IP: {ip}")
        except Exception as error:
            logger.error(f"{self.session_name} | Proxy: {proxy} | Error: {error}")

    async def run(self, proxy: str | None) -> None:
        proxy_conn = ProxyConnector().from_url(proxy) if proxy else None

        headers['User-Agent'] = generate_random_user_agent(device_type='android', browser_type='chrome')
        async with CloudflareScraper(headers=headers, connector=proxy_conn) as http_client:
            if proxy:
                await self.check_proxy(http_client=http_client, proxy=proxy)

            tg_web_data = await self.get_tg_web_data(proxy=proxy)

            while True:
                try:
                    prof_data = await self.profile_data(http_client=http_client, tg_web_data=tg_web_data)
                    if prof_data:
                        pass
                    available_taps = int(prof_data['data']['availableTaps'])
                    farm_reward = int(float(prof_data['data']['farmReward']))
                    if farm_reward == 0 and settings.FARM_MINING_ERA:
                        status = await self.start_farm(http_client=http_client, tg_web_data=tg_web_data)
                        if status is True:
                            prof_data = await self.profile_data(http_client=http_client, tg_web_data=tg_web_data)
                            farm_reward = int(float(prof_data['data']['farmReward']))
                            logger.success(f'{self.session_name} | Start mining era, early reward: {farm_reward}')

                    if farm_reward != 0 and settings.FARM_MINING_ERA:
                        try:
                            farm_reward = int(float(prof_data['data']['farmReward']))
                            current_time = datetime.now()
                            time_conv_rn = current_time.astimezone(timezone.utc)
                            time_conv_rn = time_conv_rn.strftime("%Y-%m-%d %H:%M:%S")
                            time_conv_test = datetime.strptime(time_conv_rn, "%Y-%m-%d %H:%M:%S")

                            farm_start = prof_data['data']['farmStartedAt']
                            convert = datetime.strptime(farm_start, "%Y-%m-%dT%H:%M:%S.%fZ")
                            convert += timedelta(hours=4)
                            balance = int(float(prof_data['data']['balance']))

                            time_diff = convert - time_conv_test
                            hours_diff = round(time_diff.total_seconds() / 3600, 1)
                            if time_conv_rn > str(convert):
                                status = await self.claim_farm(http_client=http_client, tg_web_data=tg_web_data)
                                if status == "ok":
                                    logger.success(f'{self.session_name} | Claimed mining era, got amount: '
                                                   f'{farm_reward} | Balance: {balance}')
                                    status = await self.start_farm(http_client=http_client, tg_web_data=tg_web_data)
                                    if status is True:
                                        prof_data = await self.profile_data(http_client=http_client,
                                                                            tg_web_data=tg_web_data)
                                        farm_reward = int(float(prof_data['data']['farmReward']))
                                        logger.success(
                                            f'{self.session_name} | Start mining era, early reward: {farm_reward}')
                                else:
                                    logger.info(f'{self.session_name} | {status}')
                            else:                                       
                                logger.info(f'{self.session_name} | Balance: {balance} | Time until next claim: {hours_diff} hours | Waiting 10 minutes')
                                await asyncio.sleep(600)  
                        except Exception as e:
                            logger.error(e)
                except InvalidSession as error:
                    raise error

                except Exception as error:
                    logger.error(f"{self.session_name} | Unknown error: {error}")
                    await asyncio.sleep(delay=3)

async def run_tapper(tg_client: Client, proxy: str | None):
    try:
        await Tapper(tg_client=tg_client).run(proxy=proxy)
    except InvalidSession:
        logger.error(f"{tg_client.name} | Invalid Session")
