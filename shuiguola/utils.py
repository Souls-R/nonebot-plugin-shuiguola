try:
    import ujson as json
except ModuleNotFoundError:
    import json
from nonebot import logger
from nonebot.typing import Union, Optional
import aiohttp
import numpy as np
import cv2
from PIL import Image
import io
import re


def get_message_images(data: str):
    """
    获取消息中所有的 图片 的链接
    :param data:
    :return:
    """
    try:
        img_list = []
        subTypelist = []
        filelist = []
        data = json.loads(data)
        for msg in data["message"]:
            if msg["type"] == "image":
                img_list.append(msg["data"]["url"])
                subTypelist.append(msg["data"]["subType"])
                filelist.append(msg["data"]["file"])
        return (img_list, filelist, subTypelist)
    except KeyError:
        return []


async def get_pic_from_url(url: str) -> bytes:
    async with aiohttp.ClientSession() as session:
        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36 Edg/95.0.1020.53",
        }
        try:
            async with session.get(url, headers=headers) as resp:
                #logger.info(f"图片下载状态码：{resp.status}")
                #logger.info(f"图片下载地址：{url}")
                return await resp.read()
        except TimeoutError:
            raise Exception("获取错误")


def calculate_hamming_distance(fingerprint1: int, fingerprint2: int) -> int:
    """
    计算hash的汉明距离
    :param fingerprint1:
    :param fingerprint2:
    :return:
    """
    # assert len(fingerprint1) == len(fingerprint2), 'Hash length err!'
    mix = fingerprint1 ^ fingerprint2
    ans = 0
    while mix != 0:
        mix &= (mix - 1)
        ans += 1
    return ans


def PILImageToCV(img: Image.Image) -> np.ndarray:
    """
    PIL Image转换成OpenCV格式
    :param img:
    :return:
    """
    img = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
    return img


def bytes2cv(img_bytes: bytes) -> np.ndarray:
    # bytes 转 numpy
    # 将 图片字节码bytes  转换成一维的numpy数组 到缓存中
    # 从指定的内存缓存中读取一维numpy数据，并把数据转换(解码)成图像矩阵格式
    img_buffer_numpy = np.frombuffer(img_bytes, dtype=np.uint8)
    img_numpy = cv2.imdecode(img_buffer_numpy, cv2.IMREAD_COLOR)
    return img_numpy


def pre_hash(img: Union[Image.Image, np.ndarray, bytes], to_size: tuple = (8, 8)):
    """
    hash前的预处理
    :param to_size: 转换的大小
    :param img:
    :return:
    """
    if isinstance(img, bytes):
        img_reformat = bytes2cv(img)
    elif isinstance(img, Image.Image):
        img_reformat = PILImageToCV(img)
    else:
        img_reformat = img
    try:
        img_reformat = cv2.resize(img_reformat, to_size)
    except cv2.error:  # 对gif的特殊处理
        frame = Image.open(io.BytesIO(img))
        img_reformat = PILImageToCV(frame)
        img_reformat = cv2.resize(img_reformat, to_size)
    # 转换灰度图
    gray = cv2.cvtColor(img_reformat, cv2.COLOR_BGR2GRAY)
    return gray


def dhash(img: Union[Image.Image, np.ndarray, bytes]) -> int:
    """
    # 图片差值哈希算法
    :param img:
    :return:64位dhash值
    """
    gray = pre_hash(img, (9, 8))
    hash_str = ''
    # 每行前一个像素大于后一个像素为1，相反为0，生成哈希
    for i in range(8):
        for j in range(8):
            if gray[i, j] > gray[i, j + 1]:
                hash_str = hash_str + '1'
            else:
                hash_str = hash_str + '0'
    return int(hash_str, 2)


