import asyncio
import random
import ssl
import json
import time
import uuid
import requests
from loguru import logger
from websockets_proxy import Proxy, proxy_connect
from fake_useragent import UserAgent

# Fungsi untuk menghubungkan ke WSS
async def connect_to_wss(socks5_proxy, user_id, max_retries=5):
    retry_count = 0  # Track retries
    while retry_count < max_retries:
        try:
            user_agent = UserAgent(os=['windows', 'macos', 'linux'], browsers='chrome')
            random_user_agent = user_agent.random
            device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, socks5_proxy))
            logger.info(f"Connecting with device_id: {device_id}, retry_count: {retry_count}")

            await asyncio.sleep(random.randint(1, 10) / 10)
            custom_headers = {
                "User-Agent": random_user_agent,
                "Origin": "chrome-extension://lkbnfiajjmbhnfledhphioinpickokdi"
            }
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            urilist = ["wss://proxy2.wynd.network:4444/", "wss://proxy2.wynd.network:4650/"]
            uri = random.choice(urilist)
            server_hostname = "proxy2.wynd.network"
            proxy = Proxy.from_url(socks5_proxy)

            async with proxy_connect(uri, proxy=proxy, ssl=ssl_context, server_hostname=server_hostname,
                                     extra_headers=custom_headers) as websocket:
                async def send_ping():
                    while True:
                        send_message = json.dumps(
                            {"id": str(uuid.uuid4()), "version": "1.0.0", "action": "PING", "data": {}})
                        logger.debug(send_message)
                        await websocket.send(send_message)
                        await asyncio.sleep(5)

                await asyncio.sleep(1)
                asyncio.create_task(send_ping())

                while True:
                    response = await websocket.recv()
                    message = json.loads(response)
                    logger.info(message)
                    if message.get("action") == "AUTH":
                        auth_response = {
                            "id": message["id"],
                            "origin_action": "AUTH",
                            "result": {
                                "browser_id": device_id,
                                "user_id": user_id,
                                "user_agent": custom_headers['User-Agent'],
                                "timestamp": int(time.time()),
                                "device_type": "extension",
                                "version": "4.26.2",
                                "extension_id": "lkbnfiajjmbhnfledhphioinpickokdi"
                            }
                        }
                        logger.debug(auth_response)
                        await websocket.send(json.dumps(auth_response))

                    elif message.get("action") == "PONG":
                        pong_response = {"id": message["id"], "origin_action": "PONG"}
                        logger.debug(pong_response)
                        await websocket.send(json.dumps(pong_response))

        except Exception as e:
            logger.error(f"Error occurred: {e}")
            retry_count += 1  # Increment retry count
            logger.error(f"Retrying... ({retry_count}/{max_retries})")

            if retry_count >= max_retries:
                logger.error(f"Max retries reached for proxy {socks5_proxy}. Moving to the next proxy.")
                break  # Break out of the loop when max retries are reached

            await asyncio.sleep(2)  # Optional: Wait for a few seconds before retrying

    logger.info(f"Switching to a new proxy after {retry_count} retries")

# Fungsi utama yang menginisiasi program
async def main():
    while True:
        try:
            #find user_id on the site in console localStorage.getItem('userId') (if you can't get it, write allow pasting)
            _user_id = input('Please Enter your user ID: ')
            #put the proxy in a file in the format socks5://username:password@ip:port or socks5://ip:port
            r = requests.get("https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&proxy_format=protocolipport&format=text", stream=True)
            if r.status_code == 200:
                with open('auto_proxies.txt', 'wb') as f:
                    for chunk in r:
                        f.write(chunk)
                with open('auto_proxies.txt', 'r') as file:
                    auto_proxy_list = file.read().splitlines()

            # Membuat task untuk setiap proxy
            tasks = [asyncio.ensure_future(connect_to_wss(i, _user_id)) for i in auto_proxy_list]
            await asyncio.gather(*tasks)

        except Exception as e:
            logger.error(f"An error occurred in main(): {e}")
            logger.info("Restarting program from the beginning in 5 seconds...")
            await asyncio.sleep(5)  # Tunggu beberapa detik sebelum restart
            continue  # Memulai ulang dari awal

if __name__ == '__main__':
    # Jalankan program dengan loop otomatis jika terjadi error
    asyncio.run(main())
