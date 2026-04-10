import os
import time
import asyncio
import subprocess
import aiohttp
import aiofiles
from utils import progress_bar
from pyrogram.types import Message
from pyrogram import Client

def duration(filename):
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                             "format=duration", "-of",
                             "default=noprint_wrappers=1:nokey=1", filename],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return float(result.stdout)

async def download_video(url: str, name: str, resolution: str):
    res_map = {
        "144": "256x144", "240": "426x240", "360": "640x360",
        "480": "854x480", "720": "1280x720", "1080": "1920x1080"
    }
    height = res_map.get(resolution, "720")
    format_str = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]"
    output_template = f"{name}.%(ext)s"
    cmd = [
        "yt-dlp", "-f", format_str, "--merge-output-format", "mp4",
        "-o", output_template, "--no-playlist",
        "-R", "25", "--fragment-retries", "25",
        "--external-downloader", "aria2c",
        "--downloader-args", "aria2c:-x 16 -j 32",
        url
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        raise Exception(f"Download failed: {stderr.decode()}")
    for f in os.listdir():
        if f.startswith(name) and (f.endswith(".mp4") or f.endswith(".mkv") or f.endswith(".webm")):
            return f
    raise FileNotFoundError("No video file found after download")

async def send_vid(bot: Client, m: Message, caption: str, filename: str, thumb: str, prog_msg: Message):
    await prog_msg.delete()
    reply = await m.reply_text(f"**⥣ Uploading ...** » `{os.path.basename(filename)}`")
    if thumb == "no" or not thumb:
        thumb_path = None
    else:
        thumb_path = thumb
    if not thumb_path:
        thumb_path = filename + ".jpg"
        subprocess.run(f'ffmpeg -i "{filename}" -ss 00:01:00 -vframes 1 "{thumb_path}"', shell=True)
    dur = int(duration(filename))
    start_time = time.time()
    try:
        await m.reply_video(
            filename, caption=caption, supports_streaming=True,
            thumb=thumb_path, duration=dur,
            progress=progress_bar, progress_args=(reply, start_time)
        )
    except Exception:
        await m.reply_document(
            filename, caption=caption,
            progress=progress_bar, progress_args=(reply, start_time)
        )
    os.remove(filename)
    if thumb_path and thumb_path != thumb:
        os.remove(thumb_path)
    await reply.delete()

async def download(url: str, name: str):
    ext = ".mp4"
    if ".pdf" in url:
        ext = ".pdf"
    elif "drive" in url:
        ext = ".mp4"
    else:
        ext = ".bin"
    out_path = f"{name}{ext}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                f = await aiofiles.open(out_path, mode='wb')
                await f.write(await resp.read())
                await f.close()
    return out_path
