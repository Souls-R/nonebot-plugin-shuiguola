from datetime import datetime
import os
import sqlite3
import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, DateTime
from .utils import calculate_hamming_distance, dhash
from nonebot import logger

countLimit = 100000
like_limit = 5  # 相似阈值
hash_method = dhash  # 设置hash方法


Base = declarative_base()


class MemePic(Base):
    __tablename__ = 'pics'
    id = Column(Integer, primary_key=True, autoincrement=True)
    pic_hash = Column(String(64))
    pic_file = Column(String(64))
    subType = Column(String(4))
    count = Column(Integer)
    url = Column(String(256), nullable=False)
    date = Column(DateTime)
    group_id = Column(String(64))


dbpath = os.path.join(os.path.dirname(__file__), 'memepic.db')
engine = sqlalchemy.create_engine('sqlite:///'+dbpath)
Session = sessionmaker(bind=engine)
session = Session()
# create table
MemePic.metadata.create_all(engine)


AllPics = session.query(MemePic).all()


def addPic(url: str, pic_file: str, subType: str, group_id: str):
    """
    向数据库添加图片并查询，返回是否为新图片
    :param url:
    :param pic_file:
    :param subType:
    :param group_id:
    :return:
    """
    # file id exists
    pics = session.query(MemePic).filter(
        MemePic.pic_file == pic_file, MemePic.group_id == group_id)
    if pics.count() > 0:
        pic = pics.first()
        pic.count += 1
        pic.date = datetime.now()
        pic.url = url
        session.commit()
        return ("old", pic.count, pic.date,pic.subType)

    pic = MemePic(pic_file=pic_file, count=1, url=url,
                  subType=subType, date=datetime.now(), group_id=group_id)
    # countlimit
    if session.query(MemePic).count() > countLimit:
        session.query(MemePic).order_by(MemePic.count).limit(1).delete()
    AllPics.append(pic)
    session.add(pic)
    session.commit()
    return ("new", 0, 0,"0")


def addPic_hashlike(image_bytes: bytes, url: str, group_id: str = '0'):
    """
    向数据库添加图片, 使用hash方法判断是否为新图片
    :param image_bytes:
    :param url:
    :param group_id:
    :return:
    """
    hash = hash_method(image_bytes)
    #logger.info("hash: %s" % hash)
    #logger.info("url: %s" % url)
    for pic in AllPics:
        if calculate_hamming_distance(hash, int(pic.hash)) <= like_limit:
            pic.count += 1
            pic.date = datetime.now()
            pic.url = url
            session.commit()
            return ("old",pic.count, pic.date)


    pic = MemePic(hash=str(hash), count=1, url=url)
    #countlimit
    if session.query(MemePic).count() > countLimit:
        session.query(MemePic).order_by(MemePic.count).limit(1).delete()
    AllPics.append(pic)
    session.add(pic)
    session.commit()
    return ("new",0, 0)


def getTop(subType: str = "0", group_id: str = "0", limit=5):
    TopK = session.query(MemePic).filter(MemePic.count > 1,
                                         MemePic.subType == subType,
                                         MemePic.group_id == group_id).order_by(MemePic.count.desc()).limit(limit).all()
    info = []
    for i in TopK:
        info.append({"url": i.url, "count": i.count})
    return info
