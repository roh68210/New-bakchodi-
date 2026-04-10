import os
import re
import time
import asyncio
import requests
import subprocess
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from pyromod import listen
from aiohttp import ClientSession
import helper
from utils import progress_bar
import sys
from config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID, SUDO_USERS

AUTH_USERS = [OWNER_ID] + SUDO_USERS
WEBHOOK = os.environ.get("WEBHOOK", "False").lower() == "true"
PORT = int(os.environ.get("PORT", 8080))

bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@bot.on_message(filters.command(["stop"]) & filters.user(AUTH_USERS))
async def stop_bot(bot: Client, m: Message):
    await m.reply_text("**STOPPED** 🛑", quote=True)
    os.execl(sys.executable, sys.executable, *sys.argv)

@bot.on_message(filters.command(["start"]))
async def start_bot(bot: Client, m: Message):
    user_id = m.from_user.id if m.from_user else None
    if user_id not in AUTH_USERS:
        await m.reply("🚫 **You are not authorized to use this bot.**", quote=True)
        return
    editable = await m.reply_text(f"**Hey {m.from_user.first_name}!**\nSend me a `.txt` file or paste links (one per line).")
    input_msg: Message = await bot.listen(editable.chat.id)
    if input_msg.document:
        x = await input_msg.download()
        await input_msg.delete(True)
        with open(x, "r") as f:
            content = f.read()
        os.remove(x)
        file_name, _ = os.path.splitext(os.path.basename(x))
    else:
        content = input_msg.text
        file_name = "links"
        await input_msg.delete(True)

    links = []
    for line in content.split("\n"):
        if line.strip():
            if "://" in line:
                proto, rest = line.split("://", 1)
                links.append((proto, rest))
            else:
                links.append(("http", line))

    await editable.edit(f"📊 Total links: **{len(links)}**\nSend starting index (default 1):")
    idx_msg = await bot.listen(editable.chat.id)
    start_idx = int(idx_msg.text) if idx_msg.text.isdigit() else 1
    await idx_msg.delete(True)

    await editable.edit("🏷️ Send batch name (or 'd' to use filename):")
    batch_msg = await bot.listen(editable.chat.id)
    batch_name = file_name if batch_msg.text.lower() == 'd' else batch_msg.text
    await batch_msg.delete(True)

    await editable.edit("🎬 Send resolution (144/240/360/480/720/1080):")
    res_msg = await bot.listen(editable.chat.id)
    resolution = res_msg.text
    await res_msg.delete(True)

    await editable.edit("✍️ Send credit name (or 'de' for default):")
    credit_msg = await bot.listen(editable.chat.id)
    credit = f"[{m.from_user.first_name}](tg://user?id={m.from_user.id})" if credit_msg.text.lower() == 'de' else credit_msg.text
    await credit_msg.delete(True)

    await editable.edit("🔑 Send PW/Classplus token (or 'No'):")
    token_msg = await bot.listen(editable.chat.id)
    working_token = token_msg.text
    await token_msg.delete(True)

    await editable.edit("🖼️ Send thumbnail URL (or 'No'):")
    thumb_msg = await bot.listen(editable.chat.id)
    thumb_url = thumb_msg.text
    await thumb_msg.delete(True)
    await editable.delete()

    thumb_file = None
    if thumb_url.startswith("http"):
        subprocess.run(f"wget '{thumb_url}' -O thumb.jpg", shell=True)
        thumb_file = "thumb.jpg"
    else:
        thumb_file = "no"

    count = start_idx
    for i in range(start_idx-1, len(links)):
        proto, url_part = links[i]
        url = proto + "://" + url_part

        if "visionias" in url:
            async with ClientSession() as session:
                async with session.get(url, headers={'User-Agent': 'Mozilla/5.0'}) as resp:
                    text = await resp.text()
                    match = re.search(r"(https://.*?playlist.m3u8.*?)\"", text)
                    if match:
                        url = match.group(1)
        elif "classplusapp" in url or "testbook.com" in url:
            if "&contentHashIdl=" in url:
                url, contentId = url.split('&contentHashIdl=')
            else:
                contentId = url.split('/')[-1]
            headers = {'x-access-token': working_token, 'api-version': '18'}
            params = {'contentId': contentId, 'offlineDownload': 'false'}
            res = requests.get("https://api.classplusapp.com/cams/uploader/video/jw-signed-url", params=params, headers=headers).json()
            url = res.get('url') or res.get('drmUrls', {}).get('manifestUrl', url)
        elif "d1d34p8vz63oiq" in url or "sec1.pw.live" in url:
            url = f"https://anonymouspwplayer-907e62cf4891.herokuapp.com/pw?url={url}?token={working_token}"

        name1 = proto.replace("\t", "").replace(":", "").replace("/", "").strip()
        name = f"{str(count).zfill(3)}) {name1[:60]}"
        caption = f"**{str(count).zfill(3)}.** {name1}\n**Batch:** {batch_name}\n**Downloaded by:** {credit}"
        prog = await m.reply_text(f"⏬ **Downloading:** `{name}`\n📺 Quality: {resolution}p")
        try:
            if "drive.google" in url or ".pdf" in url:
                file_path = await helper.download(url, name)
                await m.reply_document(file_path, caption=caption)
                os.remove(file_path)
            else:
                video_file = await helper.download_video(url, name, resolution)
                await helper.send_vid(bot, m, caption, video_file, thumb_file, prog)
            count += 1
        except Exception as e:
            await m.reply_text(f"❌ **Failed:** `{name}`\nReason: {e}")
            count += 1
        await asyncio.sleep(1)
    await m.reply_text("✅ **All downloads completed!**")

if WEBHOOK:
    from aiohttp import web
    import logging
    async def health_check(request):
        return web.Response(text="Bot is running")
    async def webhook(request):
        json_data = await request.json()
        update = pyrogram.types.Update(**json_data)
        await bot.process_update(update)
        return web.Response()
    async def main_webhook():
        await bot.start()
        app = web.Application()
        app.router.add_post(f"/{BOT_TOKEN}", webhook)
        app.router.add_get("/", health_check)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", PORT)
        await site.start()
        logging.info(f"Webhook running on port {PORT}")
        await asyncio.Event().wait()
    asyncio.run(main_webhook())
else:
    bot.run()
