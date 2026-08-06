#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
央视网 EPG 抓取工具

功能：
- 从央视网 API 获取指定频道在指定日期范围内的节目单
- 自动修正节目结束时间，并根据需要插入“收播”节目
- 生成符合 XMLTV 格式的 EPG 文件
- 支持异步并发请求，带重试和 Cookie 管理
"""

import asyncio
import random
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple

from curl_cffi.requests import AsyncSession

# ========================= 配置常量 =========================

# 获取天数与起始偏移
# 元组：(获取天数, 起始偏移)
# 偏移：-2=前天, -1=昨天, 0=今天, 1=明天, 2=后天...
# 例如 (3, -1) 表示从昨天开始获取 3 天（昨天、今天、明天）
FETCH_RANGE = (3, -1)

# 网络超时时间（秒），增大以容忍网络延迟
REQUEST_TIMEOUT = 60.0

# 请求失败时的最大重试次数
MAX_RETRIES = 2

# 重试间隔基数（秒），实际为 2~3 秒随机
RETRY_DELAY_MIN = 2.0
RETRY_DELAY_MAX = 3.0

# 判断是否插入“收播”节目的最大间隔小时数
# 当某天最后一个节目（E）与下一天第一个节目（F）之间的实际时间间隔（基于 API 返回的原始结束时间）大于或等于此阈值（小时）时，将在 E 和 F 之间插入一个标题为“收播”的节目，以填充空档；
# 若间隔小于此阈值，则直接将 E 的结束时间延长至 F 的开始时间，不再插入额外节目。
MAX_GAP_HOURS = 4

# 并发请求数量限制（同时最多进行的网络请求数）
CONCURRENT_LIMIT = 3

# XMLTV 文件名称
EPG_NAME = "cctv_epg.xml"

# 频道列表
CHANNELS = [
    {'channel_id': 'CCTV1', 'channel_name': 'CCTV-1 综合', 'api_id': 'cctv1', 'source': 'CCTV'},
    {'channel_id': 'CCTV2', 'channel_name': 'CCTV-2 财经', 'api_id': 'cctv2', 'source': 'CCTV'},
    {'channel_id': 'CCTV3', 'channel_name': 'CCTV-3 综艺', 'api_id': 'cctv3', 'source': 'CCTV'},
    {'channel_id': 'CCTV4', 'channel_name': 'CCTV-4 (亚洲)', 'api_id': 'cctv4', 'source': 'CCTV'},
    {'channel_id': 'CCTV4 欧洲', 'channel_name': 'CCTV-4 (欧洲)', 'api_id': 'cctveurope', 'source': 'CCTV'},
    {'channel_id': 'CCTV4 美洲', 'channel_name': 'CCTV-4 (美洲)', 'api_id': 'cctvamerica', 'source': 'CCTV'},
    {'channel_id': 'CCTV5', 'channel_name': 'CCTV-5 体育', 'api_id': 'cctv5', 'source': 'CCTV'},
    {'channel_id': 'CCTV5+', 'channel_name': 'CCTV-5+ 体育赛事', 'api_id': 'cctv5plus', 'source': 'CCTV'},
    {'channel_id': 'CCTV6', 'channel_name': 'CCTV-6 电影', 'api_id': 'cctv6', 'source': 'CCTV'},
    {'channel_id': 'CCTV7', 'channel_name': 'CCTV-7 国防军事', 'api_id': 'cctv7', 'source': 'CCTV'},
    {'channel_id': 'CCTV8', 'channel_name': 'CCTV-8 电视剧', 'api_id': 'cctv8', 'source': 'CCTV'},
    {'channel_id': 'CCTV9', 'channel_name': 'CCTV-9 纪录', 'api_id': 'cctvjilu', 'source': 'CCTV'},
    {'channel_id': 'CCTV10', 'channel_name': 'CCTV-10 科教', 'api_id': 'cctv10', 'source': 'CCTV'},
    {'channel_id': 'CCTV11', 'channel_name': 'CCTV-11 戏曲', 'api_id': 'cctv11', 'source': 'CCTV'},
    {'channel_id': 'CCTV12', 'channel_name': 'CCTV-12 社会与法', 'api_id': 'cctv12', 'source': 'CCTV'},
    {'channel_id': 'CCTV13', 'channel_name': 'CCTV-13 新闻', 'api_id': 'cctv13', 'source': 'CCTV'},
    {'channel_id': 'CCTV14', 'channel_name': 'CCTV-14 少儿', 'api_id': 'cctvchild', 'source': 'CCTV'},
    {'channel_id': 'CCTV15', 'channel_name': 'CCTV-15 音乐', 'api_id': 'cctv15', 'source': 'CCTV'},
    {'channel_id': 'CCTV16', 'channel_name': 'CCTV-16 奥林匹克', 'api_id': 'cctv16', 'source': 'CCTV'},
    {'channel_id': 'CCTV17', 'channel_name': 'CCTV-17 农业农村', 'api_id': 'cctv17', 'source': 'CCTV'},
    {'channel_id': 'CCTV4K', 'channel_name': 'CCTV-4K', 'api_id': 'cctv4k', 'source': 'CCTV'},
    {'channel_id': 'CCTV8K', 'channel_name': 'CCTV-8K', 'api_id': 'cctv8k', 'source': 'CCTV'},
    {'channel_id': '老故事', 'channel_name': 'CCTV老故事', 'api_id': 'cctvlaogushi', 'source': 'CCTV'},
    {'channel_id': '中学生', 'channel_name': 'CCTV中学生', 'api_id': 'zhongxuesheng', 'source': 'CCTV'},
    {'channel_id': '发现之旅', 'channel_name': 'CCTV发现之旅', 'api_id': 'cctvfxzl', 'source': 'CCTV'},
    {'channel_id': 'CCTV气象', 'channel_name': 'CCTV气象', 'api_id': 'cctvqixiang', 'source': 'CCTV'},
    {'channel_id': 'CCTV戏曲', 'channel_name': 'CCTV戏曲', 'api_id': 'cctvxiqu', 'source': 'CCTV'},
    {'channel_id': 'CCTV娱乐', 'channel_name': 'CCTV娱乐', 'api_id': 'cctvyule', 'source': 'CCTV'},
    {'channel_id': 'CCTV风云足球', 'channel_name': 'CCTV风云足球', 'api_id': 'cctvfyzq', 'source': 'CCTV'},
    {'channel_id': 'CCTV高尔夫网球', 'channel_name': 'CCTV高尔夫网球', 'api_id': 'cctvgaowang', 'source': 'CCTV'},
    {'channel_id': 'CCTV第一剧场', 'channel_name': 'CCTV第一剧场', 'api_id': 'diyijuchang', 'source': 'CCTV'},
    {'channel_id': 'CCTV中视购物', 'channel_name': 'CCTV中视购物', 'api_id': 'dianshigouwu', 'source': 'CCTV'},
    {'channel_id': 'CCTV风云剧场', 'channel_name': 'CCTV风云剧场', 'api_id': 'fyjc', 'source': 'CCTV'},
    {'channel_id': 'CCTV风云音乐', 'channel_name': 'CCTV风云音乐', 'api_id': 'fyyy', 'source': 'CCTV'},
    {'channel_id': 'CCTV国防军事', 'channel_name': 'CCTV国防军事', 'api_id': 'guofang', 'source': 'CCTV'},
    {'channel_id': 'CCTV怀旧剧场', 'channel_name': 'CCTV怀旧剧场', 'api_id': 'hjjc', 'source': 'CCTV'},
    {'channel_id': 'CCTV央视文化精品', 'channel_name': 'CCTV央视文化精品', 'api_id': 'jingpin', 'source': 'CCTV'},
    {'channel_id': 'CCTV世界地理', 'channel_name': 'CCTV世界地理', 'api_id': 'shijiedili', 'source': 'CCTV'},
    {'channel_id': 'CCTV女性时尚', 'channel_name': 'CCTV女性时尚', 'api_id': 'shishang', 'source': 'CCTV'},
    {'channel_id': 'CCTV央视台球', 'channel_name': 'CCTV央视台球', 'api_id': 'taiqiu', 'source': 'CCTV'},
    {'channel_id': 'CCTV卫生健康', 'channel_name': 'CCTV卫生健康', 'api_id': 'wsjk', 'source': 'CCTV'},
    {'channel_id': 'CCTV电视指南', 'channel_name': 'CCTV电视指南', 'api_id': 'zhinan', 'source': 'CCTV'},
    {'channel_id': 'CCTV早期教育', 'channel_name': 'CCTV早期教育', 'api_id': 'zaoqijiaoyu', 'source': 'CCTV'},
    {'channel_id': 'CETV1', 'channel_name': '中国教育电视1台', 'api_id': 'cetv1', 'source': 'CCTV'},
    {'channel_id': 'CETV2', 'channel_name': '中国教育电视2台', 'api_id': 'cetv2', 'source': 'CCTV'},
    {'channel_id': 'CETV3', 'channel_name': '中国教育电视3台', 'api_id': 'cetv3', 'source': 'CCTV'},
    {'channel_id': 'CETV4', 'channel_name': '中国教育电视4台', 'api_id': 'cetv4', 'source': 'CCTV'},
    {'channel_id': '汽摩', 'channel_name': '汽摩', 'api_id': 'cctvqimo', 'source': 'CCTV'},
    {'channel_id': '天元围棋', 'channel_name': '天元围棋', 'api_id': 'tianyuanweiqi', 'source': 'CCTV'},
    {'channel_id': '现代女性', 'channel_name': '现代女性', 'api_id': 'xiandainvxing', 'source': 'CCTV'},
    {'channel_id': '证券资讯', 'channel_name': '证券资讯', 'api_id': 'cctvzhengquanzixun', 'source': 'CCTV'},
    {'channel_id': '环球奇观', 'channel_name': '环球奇观', 'api_id': 'huanqiuqiguan', 'source': 'CCTV'},
    {'channel_id': '书画', 'channel_name': '书画', 'api_id': 'shuhua', 'source': 'CCTV'},
    {'channel_id': '说文解字', 'channel_name': '说文解字', 'api_id': 'shuowenjiezi', 'source': 'CCTV'},
    {'channel_id': 'CCTV新科动漫', 'channel_name': 'CCTV新科动漫', 'api_id': 'xinkedongman', 'source': 'CCTV'}
]

# 主页
HOME_URL = "https://tv.cctv.com/live/"

# 节目单接口模板
EPG_API_TEMPLATE = "http://api.cntv.cn/epg/getEpgInfoByChannelNew?c={api_id}&serviceId=tvcctv&d={date}"

# HTTP 基础请求头
BASE_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://tv.cctv.com/"
}

# 每个节目固定添加的分类标签
CATEGORIES = ["yufeilai666", "CCTV"]

# 全局并发信号量
semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)


# ========================= 辅助函数 =========================

def normalize_title(text: str) -> str:
    """
    规范化标题字符串，用于节目名称的比对和合成。

    处理规则（按顺序执行）：
    1. 去除首尾空白（包括全角空格）。
    2. 将所有全角空格（\u3000）替换为半角空格。
    3. 如果标题以 "-第...集" 或 "-第...季" 结尾（如 "-第1集" 或 "-第二季"），则保持该结尾不变；
       否则将末尾的 "第...集" 或 "第...季"（如 "第1集" 或 "第二季"）替换为 " 第...集" 或 " 第...季"
       （前面添加一个半角空格），以统一格式。
    4. 如果标题中不包含 "-第...集》" 或 "-第...季》" 形式的子串（如 "-第1集》" 或 "-第二季》"），
       则将标题中所有出现的 "第...集》" 或 "第...季》" 替换为 " 第...集》" 或 " 第...季》"
       （前面添加一个半角空格）。
    5. 将多个连续半角空格压缩为单个半角空格。
    6. 将 " : " 替换为 ": "（即冒号后跟一个空格，冒号前无空格）。

    示例：
        - "动画片第1集"         -> "动画片 第1集"
        - "动画片-第1集"        -> "动画片-第1集"（不变）
        - "纪录片第二季》"       -> "纪录片 第二季》"
        - "纪录片-第二季》"      -> "纪录片-第二季》"（不变）
        - "节目名： 第3集"       -> "节目名: 第3集"（压缩空格并格式化冒号）

    :param text: 原始标题字符串（可能包含多种空白字符）
    :return: 规范化后的字符串，若输入为空则返回空字符串
    """
    if not text:
        return ""
    text = text.strip()
    text = text.replace('\u3000', ' ')
    # 只有不以 "-第...集/季" 结尾时才进行替换
    if not re.search(r'-第[\d\u4e00-\u9fff\u3007]+[集季]$', text):
        text = re.sub(r"第([\d\u4e00-\u9fff\u3007]+)([集季])$", r" 第\1\2", text)
    # 只有不包含 "-第...集/季》" 时才进行替换
    if not re.search(r'-第[\d\u4e00-\u9fff\u3007]+[集季]》', text):
        text = re.sub(r"第([\d\u4e00-\u9fff\u3007]+[集季])》", r" 第\1》", text)
    text = re.sub(r' +', ' ', text)
    text = re.sub(r'\s*:\s*', ': ', text)
    # 将“ 【”、“ 《”和“】 ”、“》 ”格式化为“【”、“《”和“】”、“》”
    text = re.sub(r"\s*([《【])", r"\1", text)
    text = re.sub(r"([】》])\s*", r"\1", text)
    # 去除“•”两端空格
    text = re.sub(r"\s*•\s*", "•", text)
    # 将“．”替换为“·”
    text = re.sub(r"\s*．\s*", r"·", text)
    # 去除“（）”两端空格
    text = re.sub(r"\s*（(.+?)）\s*", r"（\1）", text)
    return text.strip()


def generate_dates() -> List[datetime.date]:
    """
    根据 FETCH_RANGE 配置生成需要获取的日期列表（北京时间日期）。

    规则：从当前北京时间的日期开始，按偏移量向前或向后移动，然后取连续的天数。

    :return: 日期列表，按从早到晚排序
    """
    now = datetime.now(timezone(timedelta(hours=8)))
    base_date = now.date()
    days = FETCH_RANGE[0]
    offset = FETCH_RANGE[1]
    return [base_date + timedelta(days=offset + i) for i in range(days)]


def datetime_to_xmltv(dt: datetime) -> str:
    """
    将带时区的 datetime 对象转换为 XMLTV 标准时间字符串。

    格式：YYYYMMDDHHMMSS +0800 （固定使用东八区偏移）

    :param dt: 带时区的 datetime 对象（通常为 UTC+8）
    :return: XMLTV 时间字符串
    """
    return dt.strftime("%Y%m%d%H%M%S") + " +0800"


# ========================= 网络请求 =========================

async def fetch_home_cookie(session: AsyncSession) -> None:
    """
    访问央视网首页，获取并保存 Cookie（由 Session 自动维护）。

    此步骤用于模拟浏览器访问，后续 API 请求需要使用这些 Cookie。

    :param session: AsyncSession 对象（来自 curl_cffi）
    :raises Exception: 当首页访问失败时抛出
    """
    resp = await session.get(HOME_URL, headers=BASE_HEADERS, timeout=REQUEST_TIMEOUT)
    if resp.status_code != 200:
        raise Exception(f"首页访问失败 HTTP {resp.status_code}")


async def fetch_epg(session: AsyncSession, api_id: str, date_str: str) -> List[Dict]:
    """
    获取单个频道单日 EPG 数据，含重试机制。

    请求 API 并解析返回的 JSON，提取节目列表。

    :param session: AsyncSession 对象
    :param api_id: 频道 API ID（例如 'cctv1'）
    :param date_str: 日期字符串，格式为 YYYYMMDD
    :return: 节目列表（原始 JSON 中的 list 字段），每个节目为字典
    :raises Exception: 当所有重试均失败时抛出异常
    """
    url = EPG_API_TEMPLATE.format(api_id=api_id, date=date_str)
    last_exception = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            if attempt > 0:
                delay = random.uniform(RETRY_DELAY_MIN, RETRY_DELAY_MAX)
                await asyncio.sleep(delay)

            async with semaphore:
                resp = await session.get(url, headers=BASE_HEADERS, timeout=REQUEST_TIMEOUT)

            if resp.status_code != 200:
                raise Exception(f"HTTP {resp.status_code}")

            data = resp.json()
            # 检查数据结构：data -> {api_id} -> list
            if 'data' in data and isinstance(data['data'], dict):
                channel_data = data['data'].get(api_id)
                if channel_data and isinstance(channel_data, dict):
                    prog_list = channel_data.get('list', [])
                    if isinstance(prog_list, list):
                        return prog_list
            return []  # 如果结构不对，返回空列表

        except Exception as e:
            last_exception = e
            if attempt == MAX_RETRIES:
                raise last_exception
            continue

    # 理论上不会到这里
    raise last_exception or Exception("未知错误")


# ========================= 频道处理 =========================

async def process_channel(session: AsyncSession, channel: Dict, date_list: List[datetime.date]) -> Tuple[Optional[List[Dict]], List[str], int, int]:
    """
    处理单个频道的所有日期数据。

    流程：
    1. 对每个日期调用 fetch_epg 获取原始节目。
    2. 过滤无效节目，转换时间戳为 datetime。
    3. 合并所有日期的节目，按开始时间排序。
    4. 按日期分组，检查相邻日期是否连续。
    5. 根据间隔修正结束时间或插入“收播”节目。
    6. 返回处理后的节目列表、日志记录、插入数量和总节目数。

    :param session: AsyncSession 对象
    :param channel: 频道信息字典，包含 channel_name, api_id 等
    :param date_list: 日期列表（datetime.date 对象）
    :return: 元组 (programmes, logs, insert_count, total_progs)
             - programmes: 处理后的节目列表，若无可返回 None
             - logs: 该频道处理过程中的日志消息列表
             - insert_count: 插入的“收播”节目数量
             - total_progs: 该频道最终节目总数
    """
    channel_name = channel['channel_name']
    api_id = channel['api_id']
    logs = []
    logs.append(f"📺 获取频道「{channel_name}」(api_id: {api_id}) 的EPG数据...")

    all_progs = []          # 所有节目（含原始和插入的收播）
    date_counts = {}        # 每个日期的原始节目数
    failed_dates = []

    for dt in date_list:
        date_str = dt.strftime("%Y%m%d")
        try:
            raw_list = await fetch_epg(session, api_id, date_str)
            if not raw_list:
                logs.append(f"⚠️ 频道「{channel_name}」日期 {dt.strftime('%Y-%m-%d')} 没有获取到符合条件的节目")
                date_counts[dt] = 0
                continue

            # 转换为内部格式
            progs = []
            for item in raw_list:
                title = normalize_title(item.get('title', ''))
                if not title:
                    continue
                try:
                    start_ts = int(item['startTime'])
                    end_ts = int(item['endTime'])
                except (ValueError, KeyError):
                    continue
                start_dt = datetime.fromtimestamp(start_ts, tz=timezone(timedelta(hours=8)))
                end_dt = datetime.fromtimestamp(end_ts, tz=timezone(timedelta(hours=8)))
                progs.append({
                    'title': title,
                    'start': start_dt,
                    'end': end_dt,
                    'original_end': end_dt,   # 保存原始结束时间
                })

            if progs:
                all_progs.extend(progs)
                logs.append(f"✅ 频道「{channel_name}」日期 {dt.strftime('%Y-%m-%d')} 获取到 {len(progs)} 个节目")
                date_counts[dt] = len(progs)
            else:
                logs.append(f"⚠️ 频道「{channel_name}」日期 {dt.strftime('%Y-%m-%d')} 没有获取到符合条件的节目（过滤后为空）")
                date_counts[dt] = 0

        except Exception as e:
            logs.append(f"❌ 频道「{channel_name}」日期 {dt.strftime('%Y-%m-%d')} 请求失败（已达最高重试次数）: {e}")
            failed_dates.append(dt)
            date_counts[dt] = 0

    # 如果没有任何节目，直接返回
    if not all_progs:
        logs.append(f"❌ 频道「{channel_name}」没有获取到任何节目")
        logs.append("*********************************")
        return None, logs, 0, 0

    # 按开始时间排序
    all_progs.sort(key=lambda x: x['start'])

    # 按日期分组
    groups = defaultdict(list)
    for p in all_progs:
        groups[p['start'].date()].append(p)

    sorted_dates = sorted(groups.keys())
    insert_count = 0

    # 遍历相邻日期，进行结束时间修正和收播插入
    for i in range(len(sorted_dates) - 1):
        d1 = sorted_dates[i]
        d2 = sorted_dates[i + 1]
        if (d2 - d1).days != 1:
            continue   # 不是连续日期，不处理

        group1 = groups[d1]
        group2 = groups[d2]
        E = group1[-1]          # d1 最后一个节目
        F = group2[0]           # d2 第一个节目

        gap_seconds = (F['start'] - E['original_end']).total_seconds()
        if gap_seconds < MAX_GAP_HOURS * 3600:
            # 间隔小于阈值：将 E 的结束时间延长至 F 的开始时间
            E['end'] = F['start']
        else:
            # 间隔过大：插入“收播”节目
            G = {
                'title': '收播',
                'start': E['original_end'],
                'end': F['start'],
                'original_end': F['start'],   # 不再使用，仅占位
            }
            group1.append(G)
            all_progs.append(G)
            insert_count += 1

    # 再次排序（插入的收播节目可能改变顺序）
    all_progs.sort(key=lambda x: x['start'])
    total_progs = len(all_progs)

    if insert_count > 0:
        logs.append(f"📌 频道「{channel_name}」插入了 {insert_count} 个'收播'节目")
    logs.append(f"✅ 频道「{channel_name}」总共添加了 {total_progs} 个节目")
    logs.append("*********************************")

    return all_progs, logs, insert_count, total_progs


# ========================= 主函数 =========================

async def main() -> None:
    """
    主入口函数，协调整个流程：

    1. 获取 Cookie。
    2. 生成日期列表。
    3. 并发处理所有频道。
    4. 收集日志并输出。
    5. 生成 XMLTV 文件。
    """
    # 全局日志收集（按顺序）
    global_log = []

    # 使用 impersonate="chrome" 模拟 Chrome 浏览器指纹
    async with AsyncSession(impersonate="chrome") as session:
        # 1. 获取 Cookie
        global_log.append("🍪 正在访问首页获取 Cookie...")
        try:
            await fetch_home_cookie(session)
            global_log.append("✅ 成功访问首页，获取到 Cookie")
            global_log.append("✅ Cookie 获取成功")
        except Exception as e:
            global_log.append(f"❌ 获取Cookie失败: {e}")
            print("\n".join(global_log))
            return
        global_log.append("=================================")

        # 2. 准备日期
        date_list = generate_dates()
        date_start = date_list[0].strftime("%Y%m%d")
        date_end = date_list[-1].strftime("%Y%m%d")
        global_log.append(f"📺 从「央视网」发现 {len(CHANNELS)} 个频道")
        global_log.append(f"📡 正在抓取 {len(CHANNELS)} 个频道的节目数据")
        global_log.append(f"ℹ️ 获取EPG数据日期范围: {date_start} 到 {date_end}")
        global_log.append("=================================")

        # 3. 并发处理所有频道
        tasks = [process_channel(session, ch, date_list) for ch in CHANNELS]
        results = await asyncio.gather(*tasks)

        # 4. 统计与生成 XML
        root = ET.Element("tv")
        root.set("generator-info-name", "yufeilai666")
        root.set("generator-info-url", "https://github.com/yufeilai666")

        # 收集有节目的频道信息（按顺序）
        active_channels = []
        for i, (progs, logs, ins, total) in enumerate(results):
            if progs is not None:
                channel = CHANNELS[i]
                active_channels.append(channel)

        # 如果没有节目，直接结束
        if not active_channels:
            global_log.append("❌ 没有生成任何节目，未生成XML文件")
            print("\n".join(global_log))
            return

        # ---- 第一阶段：写入所有频道定义 ----
        for channel in active_channels:
            channel_elem = ET.SubElement(root, "channel")
            channel_elem.set("id", channel['channel_id'])
            display_name = ET.SubElement(channel_elem, "display-name")
            display_name.text = channel['channel_name']

        # ---- 第二阶段：写入所有节目 ----
        total_channels = 0
        total_progs = 0
        for i, (progs, logs, ins, total) in enumerate(results):
            # 将当前频道的日志追加到全局日志
            global_log.extend(logs)

            if progs is not None:
                channel = CHANNELS[i]
                channel_id = channel['channel_id']
                total_channels += 1
                total_progs += len(progs)

                for p in progs:
                    prog_elem = ET.SubElement(root, "programme")
                    prog_elem.set("start", datetime_to_xmltv(p['start']))
                    prog_elem.set("stop", datetime_to_xmltv(p['end']))
                    prog_elem.set("channel", channel_id)
                    title_elem = ET.SubElement(prog_elem, "title")
                    title_elem.text = p['title']
                    for cat in CATEGORIES:
                        cat_elem = ET.SubElement(prog_elem, "category")
                        cat_elem.text = cat

        # 5. 写入文件
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        tree.write(EPG_NAME, encoding="utf-8", xml_declaration=True)
        global_log.append("=================================")
        global_log.append(f"✅ XMLTV文件已生成: {EPG_NAME}")
        global_log.append(f"📊 总共添加了 {total_channels} 个频道和 {total_progs} 个节目")
        global_log.append("=================================")

    # 一次性打印所有日志
    print("\n".join(global_log))


if __name__ == "__main__":
    asyncio.run(main())