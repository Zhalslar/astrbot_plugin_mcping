import base64
import io
from io import BytesIO
from pathlib import Path

from mcstatus import BedrockServer, JavaServer
from mcstatus.status_response import BedrockStatusResponse
from PIL import Image, ImageDraw, ImageFont

from astrbot import logger

FONT_PATH: Path = Path(__file__).resolve().parent / "resource" / "simhei.ttf"
BACKGROUND_PATH: Path = Path(__file__).resolve().parent / "resource" / "background.png"


async def get_java_server_status(server_ip: str) -> bytes | None:
    if server_ip.find(":") != -1:
        server_ip += ":25565"
    try:
        server = await JavaServer.async_lookup(server_ip.strip())
        server_status = await server.async_status()
    except Exception as e:
        logger.warning(f"JAVA版服务器{server_ip}查询失败：{e}")
        return None
    return get_server_info_image(
        motd=server_status.description,
        icon_base64=server_status.favicon.removeprefix("data:image/png;base64,")
        if server_status.favicon
        else None,
        online=f"{server_status.players.online} / {server_status.players.max}",
        ping=int(server_status.latency),
        server_version=server_status.version.name,
    )


async def get_be_server_status(server_ip: str) -> bytes | None:
    server_port = 19132  # 默认端口号
    if ":" in server_ip:
        server_ip, server_port = server_ip.split(":")
        server_port = int(server_port)
    try:
        server = BedrockServer(host=server_ip.strip(), port=server_port)
        server_status: BedrockStatusResponse = await server.async_status()
    except Exception as e:
        logger.warning(f"基岩版服务器{server_ip}查询失败：{e}")
        return None

    return get_server_info_image(
        motd=str(server_status.motd),
        icon_base64=None,
        online=f"{server_status.players_online} / {server_status.players_max}\n",
        ping=int(server_status.latency),
        server_version=server_status.version.version,
    )


def base64_pil(base64_str: str) -> Image.Image:
    """将base64转为 PIL 图片"""
    image = base64.b64decode(base64_str)
    image = BytesIO(image)
    image = Image.open(image)
    return image


def image_to_bytes(image: Image.Image) -> bytes:
    imgByte = io.BytesIO()
    image.save(imgByte, format="PNG")
    return imgByte.getvalue()


color_dict = {
    "§0": (0, 0, 0),
    "§1": (0, 0, 170),
    "§2": (0, 170, 0),
    "§3": (0, 170, 170),
    "§4": (170, 0, 0),
    "§5": (170, 0, 170),
    "§6": (255, 170, 0),
    "§7": (170, 170, 170),
    "§8": (85, 85, 85),
    "§9": (85, 85, 255),
    "§a": (85, 255, 85),
    "§b": (85, 255, 255),
    "§c": (255, 85, 85),
    "§d": (255, 85, 255),
    "§e": (255, 255, 85),
    "§f": (255, 255, 255),
    "§g": (221, 214, 5),
}
"""颜色字典"""


def get_font(font_size: int):
    """根据参数返回不同号字体"""
    return ImageFont.truetype(font=FONT_PATH, size=font_size, encoding="utf-8")


def get_color(color_code: str) -> tuple:
    try:
        return color_dict[color_code]
    except KeyError:
        return 255, 255, 255


def get_server_info_image(
    motd: str,
    icon_base64: None | str,
    online: str,
    ping: int,
    server_version: str,
) -> bytes:
    # 通过颜色字符分割
    motd_list = motd.replace("§", ";;;§").splitlines(True)

    # 获取背景
    background_image = Image.open(BACKGROUND_PATH)

    image_long = int(background_image.size[0])
    image_short = int(background_image.size[1])
    image_side = int((image_short - 64) / 2)

    # 粘贴ICON
    if icon_base64:
        draw_icon(
            icon_base64=icon_base64,
            image_side=image_side,
            background_image=background_image,
        )

    # 获取图片 Draw
    draw = ImageDraw.Draw(background_image)

    word_start = image_side * 2 + 64
    """文字起始像素"""

    # 添加motd
    draw_motd(
        draw=draw,
        word_start=word_start,
        image_side=image_side,
        motd_list=motd_list,
        font_size=20,
    )

    # 添加人数
    draw_online(
        draw=draw,
        online=online,
        word_start=word_start,
        image_short=image_short,
        font_size=16,
    )

    # 添加服务端
    draw_server_version(
        draw=draw,
        image_long=image_long,
        image_short=image_short,
        server_version=server_version,
        font_size=16,
    )

    # 添加ping
    draw_ping(
        draw=draw, image_long=image_long, ping=ping, image_side=image_side, font_size=18
    )

    # 返回图片
    img_base64 = image_to_bytes(background_image)
    return img_base64


def draw_icon(icon_base64: str, image_side: int, background_image:Image.Image):
    """将服务器 Logo 粘贴至背景"""
    # 获取icon图片
    icon_image = base64_pil(icon_base64)
    # 将icon粘贴至背景
    box = (image_side, image_side, image_side + 64, image_side + 64)
    background_image.paste(icon_image, box)


def draw_motd(
    draw:ImageDraw.ImageDraw, word_start, image_side: int, motd_list: list[str], font_size: int
):
    """添加 MOTD"""
    for line in motd_list:
        line = line.split(";;;")
        for char in line:
            if char:
                char = char.strip()
                # 颜色代码
                color_code = char[:2] if "§" in char else "§f"
                # 文字字
                color_text = char[2:] if char[:1] == "§" else char

                # 颜色元组
                color = get_color(color_code)

                # 参数：位置、文本、填充、字体
                draw.text(
                    xy=(word_start, image_side),
                    text=color_text,
                    fill=color,
                    font=get_font(font_size),
                )
                word_start += image_side * len(color_text)
        image_side += font_size


def draw_online(
    draw:ImageDraw.ImageDraw, online: str, word_start: int, image_short: int, font_size: int
):
    """添加 在线人数"""
    online_text = f"在线人数：{online}"
    draw.text(
        xy=(word_start, image_short - 10 - font_size),
        text=online_text,
        fill=get_color("§7"),
        font=get_font(font_size),
    )


def draw_server_version(
    draw:ImageDraw.ImageDraw,
    image_long: int,
    image_short: int,
    server_version: str,
    font_size: int,
):
    """添加 服务端版本"""
    version_text = f"服务端：{server_version}"
    draw.text(
        xy=(image_long / 2, image_short - 10 - font_size),
        text=version_text,
        fill=get_color("§d"),
        font=get_font(font_size),
    )


def draw_ping(
    draw:ImageDraw.ImageDraw, image_long: int, ping: int, image_side: int, font_size: int
):
    """添加 Ping"""
    ping_text = f"Ping：{ping}"

    if ping <= 90:
        ping_color = get_color("§a")
    elif 90 < ping < 460:
        ping_color = get_color("§6")
    else:
        ping_color = get_color("§c")

    draw.text(
        xy=(image_long - len(ping_text) * 10 - 20, image_side),
        text=ping_text,
        fill=ping_color,
        font=get_font(font_size),
    )
