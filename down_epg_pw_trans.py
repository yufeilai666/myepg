#!/usr/bin/env python3
"""
EPG 处理脚本 - 增强版

功能概述:
==========
本脚本从多个 XMLTV 源获取电子节目指南(EPG)数据，并通过以下方式增强节目信息:
1. 使用 TMDB API 补充中文标题和描述
2. 支持时区转换、时间偏移和直接时区替换
3. 支持本地 JSON 缓存以减少重复的 TMDB 查询
4. 支持频道级别的独立配置
5. 支持电影和电视剧的不同处理逻辑
6. 强大的JSON文件容错处理，支持多种JSON修复方法
7. 支持only_desc_from_tmdb模式，仅从TMDB获取描述信息并更新节目desc，不查询和缓存JSON，不拼接标题

主要功能:
==========
1. 多源EPG数据下载与合并
   - 支持普通XML和GZ压缩格式
   - 自动合并多个源的节目信息

2. TMDB信息查询与补充
   - 自动查询电影和电视剧的中文信息
   - 支持多个地区(zh-CN, zh-HK, zh-TW)的查询
   - 智能拼接原标题和新标题(格式: "新标题 / 原始标题")
   - 电视剧查询失败时可回退到电影查询(fallback_to_movie)，查询顺序：本地tv -> 本地movie -> TMDB tv -> TMDB movie；支持布尔值 True/False 和字符串 "true"/"false"
   - 电影查询失败时可回退到电视剧查询(fallback_to_tv)，查询顺序：本地movie -> 本地tv -> TMDB movie -> TMDB tv；支持布尔值 True/False 和字符串 "true"/"false"
   - only_desc_from_tmdb模式：仅TMDB获取描述信息并更新频道desc，不修改标题，不查询和缓存JSON

3. 时间处理功能
   - 时区转换: 将节目时间从源时区转换为目标时区
   - 时间偏移: 按分钟级别调整节目时间，同时直接替换时区
   - 直接时区替换: 只更改时区信息而不改变实际时间
   - 频道级别目标时区: 支持频道级别的独立目标时区设置(channel_timezone)，优先级高于源级别目标时区

4. 本地缓存系统
   - 使用epg_title_info.json缓存已查询的节目信息
   - 使用local_json_file，支持频道级别指定本地缓存文件，如有设置，优先使用
   - 减少对TMDB API的重复调用
   - 支持离线模式下使用缓存数据
   - 强大的JSON文件容错处理，支持多种JSON修复方法

5. 频道级别配置
   - 每个频道可独立配置处理方式
   - 支持跳过TMDB查询和缓存(skip_tmdb_and_json)
   - 支持only_desc_from_tmdb模式，仅从TMDB获取描述信息并更新频道desc，不拼接标题，不查询和缓存JSON
   - 支持不同类型的节目(电影/电视剧)处理
   - 支持电视剧查询失败时回退到电影查询(fallback_to_movie)，查询顺序：本地tv -> 本地movie -> TMDB tv -> TMDB movie；支持布尔值 True/False 和字符串 "true"/"false"
   - 支持电影查询失败时回退到电视剧查询(fallback_to_tv)，查询顺序：本地movie -> 本地tv -> TMDB movie -> TMDB tv；支持布尔值 True/False 和字符串 "true"/"false"
   - 支持指定频道本地缓存文件(local_json_file)
   - 支持频道级别目标时区设置(channel_timezone)，优先级高于源级别目标时区

6. JSON文件容错处理
   - 支持标准JSON库解析
   - 支持json5库解析（更宽松的JSON格式）
   - 支持demjson3库解析（强大的JSON解析器）
   - 自动修复常见JSON格式错误
   - 损坏文件自动备份功能

7. 描述文本格式化
   - 统一换行符为单个\n
   - 去除段落两端空格
   - 去除所有空白行
   - 每个段首添加两个全角空格

使用方法:
==========
1. 环境设置:
   - 必须设置TMDB_API_KEY环境变量: export TMDB_API_KEY='your_api_key'
   - 安装基础依赖: pip install requests pytz tmdbv3api
   - 安装JSON增强依赖（可选但推荐）: pip install json5 demjson3

2. 配置说明:
   在脚本底部main函数中的sources列表中配置EPG源和频道信息:
   - epg_name: 源名称(仅用于显示)
   - epg_url: EPG数据源的URL(支持.xml和.xml.gz)
   - timezone: 源级别目标时区(如"UTC+8"或"+08:15")
   - channel_info: 频道配置列表
     * channel_timezone: 频道级别目标时区设置，优先级高于源级别时区(如"UTC+8"或"+08:15")，为空或不存在时，使用源级别目标时区
     * channel_id: 源中的原始频道ID
     * channel_name: 源中的原始频道名称
     * new_channel_id: 输出中的新频道ID
     * new_channel_name: 输出中的新频道名称
     * type: 节目类型("movie"或"tv")
     * fallback_to_movie: 电视剧查询失败时是否回退到TMDB电影查询(True/False)
     * fallback_to_tv: 电影查询失败时是否回退到TMDB电视剧查询(True/False)
     * skip_tmdb_and_json: 是否跳过TMDB、epg_title_info.json、频道指定JSON的查询和缓存(True/False)
     * only_desc_from_tmdb: 是否仅从TMDB获取描述信息并更新频道desc，不修改标题，不进行JSON查询和缓存(True/False)
     * direct_set_timezone: 是否直接替换时区而不转换时间(True/False)
     * time_offset_minutes: 时间偏移分钟数，支持超过60分钟的偏移，正数表示往未来偏移，原时间加上分钟偏移量；负数表示往过去偏移，原时间减去分钟偏移量
     * 只设置 time_offset_minutes，不设置 direct_set_timezone 时（两个参数互斥），偏移分钟数后，直接替换时区
     * local_json_file: 指定本地缓存JSON文件(如"epgTW_title_info.json")，如有设置，优先使用

3. 运行脚本:
   python down_epg_pw_trans.py

4. 输出文件:
   - epgpw.xml: 处理后的EPG数据
   - epg_title_info.json: 缓存的中文节目信息
   - local_json_file设置的其他指定的本地缓存文件

配置示例:
==========
sources = [
    {
        "epg_name": "epg_MY.xml",
        "epg_url": "https://epg.pw/xmltv/epg_MY.xml",
        "timezone": "UTC+8",
        "channel_info": [
            {
                "channel_id": "1298",
                "channel_name": "Celestial Movies HD (马来astro)",
                "new_channel_id": "天映频道 (astro)",
                "new_channel_name": "天映频道 (astro)",
                "type": "movie",
                "skip_tmdb_and_json": False,
                "direct_set_timezone": True
            },
            {
                "channel_timezone": "UTC+7",  # 频道级别目标时区，优先级高于源级别目标时区
                "channel_id": "369718",
                "channel_name": "TVBS Asia (新加坡)",
                "new_channel_id": "TVBS Asia (astro)",
                "new_channel_name": "TVBS Asia (astro)",
                "type": "tv",
                "only_desc_from_tmdb": True,
                "local_json_file": "epgTW_title_info.json"  # 会自动放到epg_title_info目录下
            }
        ]
    }
]

注意事项:
==========
1. TMDB API有请求频率限制，请合理使用
2. 首次运行会创建缓存文件，后续运行会使用缓存数据
3. 时区转换依赖于pytz库支持的时区格式
4. 电视剧标题解析支持常见格式(S1 Ep5, Ep7, S2等)
5. 布尔值配置项支持True/False或"True"/"False"字符串格式
6. 推荐安装json5和demjson3库以获得更好的JSON文件容错能力
7. only_desc_from_tmdb 模式会清理标题后缀，按照HK、TW顺序查询TMDB（根据channel_type决定查询顺序）并更新频道desc，不拼接标题，不查询和缓存JSON

作者: yufeilai666
项目地址: https://github.com/yufeilai666/tvepg
"""

import xml.etree.ElementTree as ET
import requests
import gzip
import json
import os
import sys
import pytz
import re
from datetime import datetime, timedelta
from tmdbv3api import TMDb, Movie, TV
from urllib.parse import urlparse
from typing import Dict, List, Any, Optional, Tuple

# ==================== 路径配置 ====================
# 可以在这里修改缓存文件的存储路径和名称
EPG_TITLE_INFO_DIR = './epg_title_info'           # 缓存文件目录
EPG_TITLE_INFO_FILE = 'epg_title_info.json'       # 主缓存文件名
EPG_OUTPUT_FILE = 'epgpw.xml'                     # 输出XML文件名
# =================================================

# 尝试导入额外的JSON处理库
try:
    import json5
    JSON5_AVAILABLE = True
except ImportError:
    JSON5_AVAILABLE = False
    print("⚠️ 注意: json5 库未安装，将使用有限的JSON修复功能")

try:
    import demjson3
    DEMJSON3_AVAILABLE = True
except ImportError:
    DEMJSON3_AVAILABLE = False
    print("⚠️ 注意: demjson3 库未安装，将使用有限的JSON修复功能")

# 初始化TMDB配置
tmdb = TMDb()
tmdb.api_key = os.environ.get('TMDB_API_KEY')
if not tmdb.api_key:
    print("❌ 错误: 未设置 TMDB_API_KEY 环境变量")
    sys.exit(1)

movie_api = Movie()
tv_api = TV()


def ensure_directory(directory: str) -> None:
    """
    确保目录存在，如果不存在则创建
    
    参数:
        directory (str): 目录路径
    """
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
        print(f"✅ 已创建目录: {directory}")


def get_json_path(filename: str) -> str:
    """
    获取JSON文件的完整路径
    
    参数:
        filename (str): JSON文件名（可以带相对路径）
        
    返回:
        str: 完整的文件路径
    """
    # 如果已经是绝对路径或包含目录，直接返回
    if os.path.isabs(filename) or '/' in filename or '\\' in filename:
        return filename
    
    # 否则，放到缓存目录下
    return os.path.join(EPG_TITLE_INFO_DIR, filename)


def get_main_json_path() -> str:
    """
    获取主缓存文件的完整路径
    
    返回:
        str: 主缓存文件的完整路径
    """
    return get_json_path(EPG_TITLE_INFO_FILE)


def get_output_xml_path() -> str:
    """
    获取输出XML文件的完整路径
    
    返回:
        str: 输出XML文件的完整路径
    """
    return EPG_OUTPUT_FILE


def format_description(description: str) -> str:
    """
    格式化描述文本：处理各种换行符，按段落处理，去除空白行，每个段首添加两个全角空格
    
    参数:
        description (str): 原始描述文本
        
    返回:
        str: 格式化后的描述文本
    """
    if not description:
        return ""
    
    # 1. 统一换行符：将 \r\n、\r 和多个连续换行符统一为单个 \n
    description = re.sub(r'\r\n|\r|\n+', '\n', description)
    
    # 2. 按换行符分割成段落
    paragraphs = description.split('\n')
    
    # 3. 清理每个段落：移除首尾空白，过滤空段落
    cleaned_paragraphs = []
    for para in paragraphs:
        para = para.strip()
        if para:  # 只保留非空段落
            # 4. 在每个段落开始添加两个全角空格
            para = '　　' + para
            cleaned_paragraphs.append(para)
    
    # 5. 用换行符连接所有段落
    formatted_description = '\n'.join(cleaned_paragraphs)
    
    return formatted_description


def remove_control_characters(s: str) -> str:
    """
    移除字符串中的控制字符
    
    参数:
        s (str): 原始字符串
        
    返回:
        str: 清理后的字符串
    """
    if not s:
        return s
    # 移除非打印字符（除了制表符、换行符和回车符）
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', s)


def clean_json_data(data: Any) -> Any:
    """
    递归清理JSON数据中的控制字符
    
    参数:
        data (Any): 原始JSON数据
        
    返回:
        Any: 清理后的JSON数据
    """
    if isinstance(data, dict):
        return {k: clean_json_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_json_data(item) for item in data]
    elif isinstance(data, str):
        return remove_control_characters(data)
    else:
        return data


def advanced_json_repair(json_str: str) -> str:
    """
    高级JSON修复函数，处理多种常见错误
    
    修复功能包括:
    - 修复未闭合的字符串
    - 修复尾随逗号
    - 修复缺失的逗号
    - 修复单引号字符串为双引号
    - 移除注释（单行和多行）
    
    参数:
        json_str (str): 原始的JSON字符串
        
    返回:
        str: 修复后的JSON字符串
    """
    # 1. 修复未闭合的字符串
    lines = json_str.split('\n')
    in_string = False
    escape_next = False
    
    for i, line in enumerate(lines):
        new_line = ""
        for char in line:
            if char == '\\' and not escape_next:
                escape_next = True
                new_line += char
            elif char == '"' and not escape_next:
                in_string = not in_string
                new_line += char
            else:
                escape_next = False
                new_line += char
        
        # 如果行结束时仍在字符串中，添加闭合引号
        if in_string:
            new_line += '"'
            in_string = False
        
        lines[i] = new_line
    
    repaired = '\n'.join(lines)
    
    # 2. 修复尾随逗号
    repaired = re.sub(r',(\s*[}\]])', r'\1', repaired)
    
    # 3. 修复缺失的逗号 between 对象/数组元素
    repaired = re.sub(r'("[^"]*")\s*([}\]])', r'\1,\2', repaired)
    repaired = re.sub(r'([}\]"])\s*("[^"]*")', r'\1,\2', repaired)
    
    # 4. 修复单引号字符串为双引号
    repaired = re.sub(r"'([^']*)'", r'"\1"', repaired)
    
    # 5. 修复注释（移除单行和多行注释）
    repaired = re.sub(r'//.*', '', repaired)  # 单行注释
    repaired = re.sub(r'/\*.*?\*/', '', repaired, flags=re.DOTALL)  # 多行注释
    
    return repaired


def robust_json_loader(filename: str) -> Dict[str, Any]:
    """
    强大的JSON加载器，尝试多种方法解析JSON
    
    使用多层解析策略:
    1. 标准JSON库
    2. json5库（如果可用）
    3. demjson3库（如果可用）
    4. 高级修复+标准库
    5. 高级修复+demjson3（如果可用）
    6. 激进修复（提取和合并JSON对象）
    
    参数:
        filename (str): JSON文件名
        
    返回:
        Dict[str, Any]: 解析后的JSON数据，如果所有方法都失败则返回空字典
    """
    # 获取完整路径
    full_path = get_json_path(filename)
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"❌ 读取JSON文件 {full_path} 失败: {e}")
        return {}
    
    methods = [("标准JSON库", lambda: json.loads(content))]
    
    if JSON5_AVAILABLE:
        methods.append(("json5库", lambda: json5.loads(content)))
    
    if DEMJSON3_AVAILABLE:
        methods.append(("demjson3库", lambda: demjson3.decode(content)))
    
    # 添加修复方法
    methods.append(("高级修复+标准库", lambda: json.loads(advanced_json_repair(content))))
    
    if DEMJSON3_AVAILABLE:
        methods.append(("高级修复+demjson3", lambda: demjson3.decode(advanced_json_repair(content))))
    
    for method_name, method_func in methods:
        try:
            result = method_func()
            print(f"✅ 使用 {method_name} 解析 {full_path} 成功")
            return result
        except Exception as e:
            print(f"❌ 使用 {method_name} 解析 {full_path} 失败: {e}")
    
    # 如果所有方法都失败，尝试更激进的修复
    print(f"⚠️ 所有标准方法失败，尝试激进修复 {full_path}...")
    try:
        # 尝试提取看起来像JSON对象的部分
        json_objects = re.findall(r'\{.*?\}', content, re.DOTALL)
        if json_objects:
            # 合并所有对象
            combined = '{' + ', '.join([obj[1:-1] for obj in json_objects]) + '}'
            return json.loads(combined)
    except Exception as e:
        print(f"❌ 激进修复 {full_path} 也失败: {e}")
    
    print(f"⚠️ 无法修复JSON文件 {full_path}，返回空字典")
    # 备份损坏的文件
    backup_filename = f"{full_path}_bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        with open(backup_filename, 'w', encoding='utf-8') as bak:
            bak.write(content)
        print(f"✅ 已备份损坏的文件为: {backup_filename}")
    except Exception as e:
        print(f"❌ 备份文件 {full_path} 失败: {e}")
    
    return {}


def load_epg_title_json() -> Dict[str, List[Dict[str, Any]]]:
    """
    从本地文件加载 epg_title_info.json，使用强大的修复功能
    
    返回:
        Dict[str, List[Dict[str, Any]]]: 解析后的JSON缓存数据，结构为{标题: [{类型信息}]}
    """
    # 确保目录存在
    ensure_directory(EPG_TITLE_INFO_DIR)
    
    data = robust_json_loader(EPG_TITLE_INFO_FILE)
    
    # 兼容旧格式：如果是字典但值不是列表，转换为新格式
    if isinstance(data, dict):
        new_data = {}
        for key, value in data.items():
            if isinstance(value, list):
                new_data[key] = value
            else:
                # 旧格式：单个对象 -> 转换为列表
                new_data[key] = [value]
        return new_data
    
    return data


def save_epg_title_json(data: Dict[str, List[Dict[str, Any]]]) -> None:
    """
    保存 epg_title_info.json 到本地文件，确保数据清洁
    
    参数:
        data (Dict[str, List[Dict[str, Any]]]): 要保存的JSON缓存数据
    """
    # 确保目录存在
    ensure_directory(EPG_TITLE_INFO_DIR)
    
    save_json_to_file(EPG_TITLE_INFO_FILE, data)


def save_json_to_file(filename: str, data: Dict[str, Any]) -> None:
    """
    保存 JSON 数据到指定文件，确保数据清洁
    
    参数:
        filename (str): 要保存的文件名
        data (Dict[str, Any]): 要保存的JSON数据
    """
    # 获取完整路径
    full_path = get_json_path(filename)
    
    try:
        # 确保目录存在
        ensure_directory(os.path.dirname(full_path) or EPG_TITLE_INFO_DIR)
        
        # 清理数据中的控制字符
        cleaned_data = clean_json_data(data)
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(cleaned_data, f, ensure_ascii=False, indent=2)
        print(f"✅ 已保存 {full_path}")
    except Exception as e:
        print(f"❌ 保存 {full_path} 失败: {e}")
        # 尝试使用更简单的保存方式
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
            print(f"✅ 简化保存 {full_path} 成功")
        except Exception as e2:
            print(f"❌ 简化保存 {full_path} 也失败: {e2}")


def download_and_parse_xml(epg_url: str) -> Optional[ET.Element]:
    """
    下载并解析 XML 文件，支持普通和 gzip 压缩格式
    
    参数:
        epg_url (str): EPG数据源的URL
        
    返回:
        Optional[ET.Element]: 解析后的XML根元素，如果失败则返回None
    """
    parsed_url = urlparse(epg_url)
    file_ext = os.path.splitext(parsed_url.path)[1]
    
    try:
        if file_ext == '.gz':
            # 处理 gzip 压缩的 XML
            response = requests.get(epg_url, stream=True, timeout=30)
            if response.status_code == 200:
                # 保存临时文件
                temp_gz = "temp.xml.gz"
                with open(temp_gz, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                # 解压并解析
                with gzip.open(temp_gz, 'rb') as f:
                    xml_content = f.read()
                    os.remove(temp_gz)
                    return ET.fromstring(xml_content)
        else:
            # 处理普通 XML
            response = requests.get(epg_url, timeout=30)
            if response.status_code == 200:
                return ET.fromstring(response.content)
    except Exception as e:
        print(f"❌ 下载或解析 XML 失败 ({epg_url}): {e}")
    
    return None


def get_movie_info_from_tmdb(title: str, regions: List[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    从 TMDB 获取电影信息
    
    按顺序从指定地区查找，如果前一个地区只找到标题，则继续在下一个地区查找描述
    
    参数:
        title (str): 电影标题
        regions (List[str]): 查询地区列表，如 ['zh-CN', 'zh-HK', 'zh-TW']
        
    返回:
        Tuple[Optional[str], Optional[str]]: (标题, 描述) 元组，如果某部分没找到则为 None
    """
    original_language = tmdb.language
    found_title = None
    found_desc = None
    
    for region in regions:
        try:
            tmdb.language = region
            print(f"🎬🔎 在 {region} 地区搜索电影: {title}")
            
            search_results = movie_api.search(title)
            
            # 修复：检查 search_results 是否有效且不为空
            if not search_results or not hasattr(search_results, '__iter__'):
                print(f"⚠️ 在 {region} 没有找到有效结果")
                continue
                
            # 将结果转换为列表
            results_list = list(search_results)
            if not results_list:
                print(f"⚠️ 在 {region} 没有找到结果")
                continue
                
            # 获取第一个结果
            movie = results_list[0]
            
            # 确保 movie 对象有 id 属性
            if hasattr(movie, 'id'):
                details = movie_api.details(movie.id)
                
                # 确保 details 对象有 title 和 overview 属性
                if hasattr(details, 'title') and details.title:
                    found_title = details.title
                    print(f"✅ 在 {region} 找到电影标题: {found_title}")
                
                if hasattr(details, 'overview') and details.overview:
                    # 格式化描述文本
                    found_desc = format_description(details.overview)
                    print(f"✅ 在 {region} 找到电影描述")
                
                # 如果两者都找到了，就停止搜索
                if found_title and found_desc:
                    print(f"✅ 在 {region} 找到完整电影信息")
                    break
            else:
                print(f"⚠️ 在 {region} 找到结果，但结果缺少 id 属性")
                    
        except Exception as e:
            print(f"❌ TMDB 电影查询失败 ({region}): {e}")
            # 打印更详细的错误信息
            import traceback
            traceback.print_exc()
            continue
    
    # 恢复原始语言设置
    tmdb.language = original_language
    return found_title, found_desc


def get_tv_info_from_tmdb(title: str, regions: List[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    从 TMDB 获取电视剧信息
    
    按顺序从指定地区查找，如果前一个地区只找到标题，则继续在下一个地区查找描述
    
    参数:
        title (str): 电视剧标题
        regions (List[str]): 查询地区列表，如 ['zh-CN', 'zh-HK', 'zh-TW']
        
    返回:
        Tuple[Optional[str], Optional[str]]: (标题, 描述) 元组，如果某部分没找到则为 None
    """
    original_language = tmdb.language
    found_title = None
    found_desc = None
    
    for region in regions:
        try:
            tmdb.language = region
            print(f"📺🔎 在 {region} 地区搜索电视剧: {title}")
            
            search_results = tv_api.search(title)
            
            # 修复：检查 search_results 是否有效且不为空
            if not search_results or not hasattr(search_results, '__iter__'):
                print(f"⚠️ 在 {region} 没有找到有效结果")
                continue
                
            # 将结果转换为列表
            results_list = list(search_results)
            if not results_list:
                print(f"⚠️ 在 {region} 没有找到结果")
                continue
                
            # 获取第一个结果
            tv_show = results_list[0]
            
            # 确保 tv_show 对象有 id 属性
            if hasattr(tv_show, 'id'):
                details = tv_api.details(tv_show.id)
                
                # 确保 details 对象有 name 和 overview 属性
                if hasattr(details, 'name') and details.name:
                    found_title = details.name
                    print(f"✅ 在 {region} 找到电视剧标题: {found_title}")
                
                if hasattr(details, 'overview') and details.overview:
                    # 格式化描述文本
                    found_desc = format_description(details.overview)
                    print(f"✅ 在 {region} 找到电视剧描述")
                
                # 如果两者都找到了，就停止搜索
                if found_title and found_desc:
                    print(f"✅ 在 {region} 找到完整电视剧信息")
                    break
            else:
                print(f"⚠️ 在 {region} 找到结果，但结果缺少 id 属性")
                    
        except Exception as e:
            print(f"❌ TMDB 电视剧查询失败 ({region}): {e}")
            # 打印更详细的错误信息
            import traceback
            traceback.print_exc()
            continue
    
    # 恢复原始语言设置
    tmdb.language = original_language
    return found_title, found_desc


def clean_title_suffix(original_title: str) -> str:
    """
    清理标题后缀，只保留电影/电视剧名称部分
    
    处理示例:
    - "愛回家之開心速遞 #2504 - #2507(2504 - 2507)(普)" → "愛回家之開心速遞"
    - "虎膽女兒紅(輔15)" → "虎膽女兒紅"
    - "危險的十七歲(護)" → "危險的十七歲"
    - "拆彈專家2（輔12）" → "拆彈專家2"
    - "鐵三角(郭南宏導演)(護)" → "鐵三角"
    - "還珠格格 # 1(1)(護)" → "還珠格格"
    
    参数:
        original_title (str): 原始标题
        
    返回:
        str: 清理后的标题
    """
    # 定义常见后缀模式
    patterns = [
        r'\s*#\s*\d+.*$',  # # 1, #2504 - #2507 等剧集编号
        r'\s*\(\d+.*\)$',  # (1), (2504 - 2507) 等括号内容
        r'\s*（\d+.*）$',  # 全角括号
        r'\s*[\(（](輔\d+)[\)）]$',  # 輔15 等评级
        r'\s*[\(（](护|護|普|普遍級|保護級|輔導級|限制級)[\)）]$',  # 简单评级
        r'\s*[\(（](輔\d+).*[\)）]$',  # 輔15) 可能还有其他内容
        # r'\s*[\(（].*導演.*[\)）]$',  # 导演信息，如(郭南宏導演)
        # r'\s*[\(（].*导演.*[\)）]$',  # 导演信息，简体中文
    ]
    
    clean_title = original_title
    for pattern in patterns:
        clean_title = re.sub(pattern, '', clean_title)
    
    # 去除两端空格
    return clean_title.strip()


def get_desc_from_tmdb_only(title: str, channel_type: str) -> Optional[str]:
    """
    只从TMDB获取描述信息，不修改标题，不进行缓存
    
    查询顺序: 
    - 当channel_type为"movie"时：先查询movie类型，找不到再查询tv类型
    - 当channel_type为"tv"时：先查询tv类型，找不到再查询movie类型
    按照HK、TW顺序查询
    
    参数:
        title (str): 节目标题
        channel_type (str): 频道类型，"movie"或"tv"
        
    返回:
        Optional[str]: 找到的描述信息，如果没有找到则返回None
    """
    original_language = tmdb.language
    found_desc = None
    found_title = None
    
    # 定义查询地区顺序：HK、TW
    regions = ['zh-HK', 'zh-TW']
    
    # 根据频道类型决定查询顺序
    if channel_type == "movie":
        # 先尝试电影查询
        movie_found = False
        for region in regions:
            try:
                tmdb.language = region
                print(f"🎬🔎 在 {region} 地区搜索电影描述信息: {title}")
                
                search_results = movie_api.search(title)
                
                if not search_results or not hasattr(search_results, '__iter__'):
                    continue
                    
                results_list = list(search_results)
                if not results_list:
                    continue
                    
                movie = results_list[0]
                
                if hasattr(movie, 'id'):
                    details = movie_api.details(movie.id)
                    
                    if hasattr(details, 'overview') and details.overview:
                        found_desc = format_description(details.overview)
                        found_title = details.title if hasattr(details, 'title') else "未知标题"
                        print(f"✅ 在 {region} 找到电影描述信息：{found_title}")
                        movie_found = True
                        break
                        
            except Exception as e:
                print(f"❌ TMDB 电影描述查询失败 ({region}): {e}")
                continue
        
        if not movie_found:
            print(f"⚠️ 在电影类型中未找到描述信息: {title}")
        
        # 如果电影没找到描述，尝试电视剧查询
        if not found_desc:
            tv_found = False
            for region in regions:
                try:
                    tmdb.language = region
                    print(f"📺🔎 在 {region} 地区搜索电视剧描述信息: {title}")
                    
                    search_results = tv_api.search(title)
                    
                    if not search_results or not hasattr(search_results, '__iter__'):
                        continue
                        
                    results_list = list(search_results)
                    if not results_list:
                        continue
                        
                    tv_show = results_list[0]
                    
                    if hasattr(tv_show, 'id'):
                        details = tv_api.details(tv_show.id)
                        
                        if hasattr(details, 'overview') and details.overview:
                            found_desc = format_description(details.overview)
                            found_title = details.name if hasattr(details, 'name') else "未知标题"
                            print(f"✅ 在 {region} 找到电视剧描述信息：{found_title}")
                            tv_found = True
                            break
                            
                except Exception as e:
                    print(f"❌ TMDB 电视剧描述查询失败 ({region}): {e}")
                    continue
            
            if not tv_found and not found_desc:
                print(f"⚠️ 在电视剧类型中未找到描述信息: {title}")
    
    elif channel_type == "tv":
        # 先尝试电视剧查询
        tv_found = False
        for region in regions:
            try:
                tmdb.language = region
                print(f"📺🔎 在 {region} 地区搜索电视剧描述信息: {title}")
                
                search_results = tv_api.search(title)
                
                if not search_results or not hasattr(search_results, '__iter__'):
                    continue
                    
                results_list = list(search_results)
                if not results_list:
                    continue
                    
                tv_show = results_list[0]
                
                if hasattr(tv_show, 'id'):
                    details = tv_api.details(tv_show.id)
                    
                    if hasattr(details, 'overview') and details.overview:
                        found_desc = format_description(details.overview)
                        found_title = details.name if hasattr(details, 'name') else "未知标题"
                        print(f"✅ 在 {region} 找到电视剧描述信息：{found_title}")
                        tv_found = True
                        break
                        
            except Exception as e:
                print(f"❌ TMDB 电视剧描述查询失败 ({region}): {e}")
                continue
        
        if not tv_found:
            print(f"⚠️ 在电视剧类型中未找到描述信息: {title}")
        
        # 如果电视剧没找到描述，尝试电影查询
        if not found_desc:
            movie_found = False
            for region in regions:
                try:
                    tmdb.language = region
                    print(f"🎬🔎 在 {region} 地区搜索电影描述信息: {title}")
                    
                    search_results = movie_api.search(title)
                    
                    if not search_results or not hasattr(search_results, '__iter__'):
                        continue
                        
                    results_list = list(search_results)
                    if not results_list:
                        continue
                        
                    movie = results_list[0]
                    
                    if hasattr(movie, 'id'):
                        details = movie_api.details(movie.id)
                        
                        if hasattr(details, 'overview') and details.overview:
                            found_desc = format_description(details.overview)
                            found_title = details.title if hasattr(details, 'title') else "未知标题"
                            print(f"✅ 在 {region} 找到电影描述信息：{found_title}")
                            movie_found = True
                            break
                            
                except Exception as e:
                    print(f"❌ TMDB 电影描述查询失败 ({region}): {e}")
                    continue
            
            if not movie_found and not found_desc:
                print(f"⚠️ 在电影类型中未找到描述信息: {title}")
    
    # 如果最终没有找到描述
    if not found_desc:
        print(f"⚠️ TMDB 查询不到描述信息，使用原始描述: {title}")
    
    # 恢复原始语言设置
    tmdb.language = original_language
    return found_desc


def parse_timezone_offset(timezone_str: str) -> timedelta:
    """
    解析时区字符串，返回 timedelta 对象
    
    参数:
        timezone_str (str): 时区字符串，如 "UTC+8" 或 "+08:00"
        
    返回:
        timedelta: 时区偏移量
    """
    try:
        # 处理 UTC+8 格式
        if timezone_str.upper().startswith('UTC'):
            offset_str = timezone_str[3:]
            if offset_str.startswith('+'):
                hours = int(offset_str[1:])
                return timedelta(hours=hours)
            elif offset_str.startswith('-'):
                hours = int(offset_str[1:])
                return timedelta(hours=-hours)
            else:
                # 如果没有符号，默认为正
                hours = int(offset_str)
                return timedelta(hours=hours)
        # 处理 +08:00 格式
        elif timezone_str.startswith(('+', '-')):
            sign = 1 if timezone_str[0] == '+' else -1
            parts = timezone_str[1:].split(':')
            hours = int(parts[0])
            minutes = int(parts[1]) if len(parts) > 1 else 0
            return timedelta(hours=sign * hours, minutes=sign * minutes)
        else:
            # 默认使用 UTC
            return timedelta(0)
    except (ValueError, IndexError):
        print(f"⚠️ 无法解析时区: {timezone_str}, 使用 UTC")
        return timedelta(0)


def format_timezone_offset(timezone_offset: timedelta) -> str:
    """
    将 timedelta 对象格式化为时区字符串（如 +0800）
    
    参数:
        timezone_offset (timedelta): 时区偏移量
        
    返回:
        str: 格式化的时区字符串
    """
    total_seconds = int(timezone_offset.total_seconds())
    hours = abs(total_seconds) // 3600
    minutes = (abs(total_seconds) % 3600) // 60
    sign = '+' if total_seconds >= 0 else '-'
    return f"{sign}{hours:02d}{minutes:02d}"


def convert_time_to_timezone(time_str: str, timezone_offset: timedelta) -> str:
    """
    将时间字符串转换为目标时区
    
    参数:
        time_str (str): 原始时间字符串，格式: YYYYMMDDHHMMSS +0000
        timezone_offset (timedelta): 目标时区偏移量
        
    返回:
        str: 转换后的时间字符串
    """
    try:
        # 解析时间字符串 (格式: YYYYMMDDHHMMSS +0000)
        if ' ' in time_str:
            dt_str, tz_str = time_str.split(' ')
            dt = datetime.strptime(dt_str, '%Y%m%d%H%M%S')
            
            # 解析原始时区偏移
            if tz_str.startswith(('+', '-')):
                sign = 1 if tz_str[0] == '+' else -1
                tz_hours = int(tz_str[1:3])
                tz_minutes = int(tz_str[3:5]) if len(tz_str) > 4 else 0
                original_offset = timedelta(hours=sign * tz_hours, minutes=sign * tz_minutes)
            else:
                original_offset = timedelta(0)
        else:
            # 如果没有时区信息，假设为 UTC
            dt = datetime.strptime(time_str, '%Y%m%d%H%M%S')
            original_offset = timedelta(0)
        
        # 计算总偏移量
        total_offset = timezone_offset - original_offset
        
        # 应用偏移量
        adjusted_dt = dt + total_offset
        
        # 格式化为字符串
        adjusted_dt_str = adjusted_dt.strftime('%Y%m%d%H%M%S')
        
        # 格式化时区偏移
        tz_str = format_timezone_offset(timezone_offset)
        
        return f"{adjusted_dt_str} {tz_str}"
    except Exception as e:
        print(f"❌ 时间转换失败: {time_str}, 错误: {e}")
        return time_str  # 如果转换失败，返回原始时间


def replace_timezone_directly(time_str: str, target_timezone: str) -> str:
    """
    直接替换时区信息而不转换时间
    
    参数:
        time_str (str): 原始时间字符串，格式: YYYYMMDDHHMMSS +0000
        target_timezone (str): 目标时区字符串，如 "UTC+8"
        
    返回:
        str: 替换时区后的时间字符串
    """
    try:
        # 解析目标时区
        timezone_offset = parse_timezone_offset(target_timezone)
        tz_str = format_timezone_offset(timezone_offset)
        
        # 提取时间部分（去掉原来的时区）
        if ' ' in time_str:
            dt_str, _ = time_str.split(' ')
            return f"{dt_str} {tz_str}"
        else:
            # 如果没有时区信息，添加时区
            return f"{time_str} {tz_str}"
    except Exception as e:
        print(f"❌ 直接替换时区失败: {time_str}, 错误: {e}")
        return time_str  # 如果替换失败，返回原始时间


def adjust_time_with_offset(time_str: str, offset_minutes: int, target_timezone: str) -> str:
    """
    调整时间偏移并直接替换时区
    
    参数:
        time_str (str): 原始时间字符串，格式: YYYYMMDDHHMMSS +0000
        offset_minutes (int): 分钟偏移量（正数表示向未来，原时间加上分钟偏移量；负数表示向过去，原时间减去分钟偏移量）
        target_timezone (str): 目标时区字符串，如 "UTC+8"
        
    返回:
        str: 调整后的时间字符串
    """
    try:
        # 解析目标时区
        timezone_offset = parse_timezone_offset(target_timezone)
        tz_str = format_timezone_offset(timezone_offset)
        
        # 提取时间部分
        if ' ' in time_str:
            dt_str, _ = time_str.split(' ')
        else:
            dt_str = time_str
        
        # 解析时间
        dt = datetime.strptime(dt_str, '%Y%m%d%H%M%S')
        
        # 应用分钟偏移
        adjusted_dt = dt + timedelta(minutes=offset_minutes)
        
        # 格式化为字符串
        adjusted_dt_str = adjusted_dt.strftime('%Y%m%d%H%M%S')
        
        return f"{adjusted_dt_str} {tz_str}"
    except Exception as e:
        print(f"❌ 时间偏移调整失败: {time_str}, 错误: {e}")
        return time_str  # 如果调整失败，返回原始时间


def parse_tv_title(original_title: str) -> Tuple[str, str, Optional[int]]:
    """
    解析电视剧标题，提取主标题和剧集信息
    
    支持格式（不区分大小写）:
    - S1 Ep5:              "剧名 S1 Ep5"     → ("剧名", "第1季第5集", 1)
    - Season 2 Ep1:        "剧名 Season 2 Ep1" → ("剧名", "第2季第1集", 2)
    - Season 2 Episode 1:  "剧名 Season 2 Episode 1" → ("剧名", "第2季第1集", 2)
    - S2 Episode 1:        "剧名 S2 Episode 1" → ("剧名", "第2季第1集", 2)
    - Ep7:                 "剧名 Ep7"        → ("剧名", "第7集", None)
    - Episode 1:           "剧名 Episode 1"  → ("剧名", "第1集", None)
    - S2:                  "剧名 S2"         → ("剧名", "第2季", 2)
    
    参数:
        original_title (str): 原始电视剧标题
        
    返回:
        Tuple[str, str, Optional[int]]: (主标题, 剧集信息, 季号) 元组
    """
    # 去除两端空格
    original_title = original_title.strip()
    
    # 定义匹配模式，顺序：更具体的先匹配
    # 1. Season X Episode Y
    match = re.match(r'^(.*?)\s+Season\s+(\d+)\s+Episode\s+(\d+)$', original_title, re.IGNORECASE)
    if match:
        main_title = match.group(1).strip()
        season_num = int(match.group(2))
        episode_num = int(match.group(3))
        return main_title, f"第{season_num}季第{episode_num}集", season_num
    
    # 2. Season X EpY
    match = re.match(r'^(.*?)\s+Season\s+(\d+)\s+Ep\s*(\d+)$', original_title, re.IGNORECASE)
    if match:
        main_title = match.group(1).strip()
        season_num = int(match.group(2))
        episode_num = int(match.group(3))
        return main_title, f"第{season_num}季第{episode_num}集", season_num
    
    # 3. SX Episode Y
    match = re.match(r'^(.*?)\s+S(\d+)\s+Episode\s+(\d+)$', original_title, re.IGNORECASE)
    if match:
        main_title = match.group(1).strip()
        season_num = int(match.group(2))
        episode_num = int(match.group(3))
        return main_title, f"第{season_num}季第{episode_num}集", season_num
    
    # 4. SX EpY
    match = re.match(r'^(.*?)\s+S(\d+)\s+Ep\s*(\d+)$', original_title, re.IGNORECASE)
    if match:
        main_title = match.group(1).strip()
        season_num = int(match.group(2))
        episode_num = int(match.group(3))
        return main_title, f"第{season_num}季第{episode_num}集", season_num
    
    # 5. Episode Y（仅剧集，无季号）
    match = re.match(r'^(.*?)\s+Episode\s+(\d+)$', original_title, re.IGNORECASE)
    if match:
        main_title = match.group(1).strip()
        episode_num = int(match.group(2))
        return main_title, f"第{episode_num}集", None
    
    # 6. EpY
    match = re.match(r'^(.*?)\s+Ep\s*(\d+)$', original_title, re.IGNORECASE)
    if match:
        main_title = match.group(1).strip()
        episode_num = int(match.group(2))
        return main_title, f"第{episode_num}集", None
    
    # 7. SX（仅季号）
    match = re.match(r'^(.*?)\s+S(\d+)$', original_title, re.IGNORECASE)
    if match:
        main_title = match.group(1).strip()
        season_num = int(match.group(2))
        return main_title, f"第{season_num}季", season_num
    
    # 没有匹配到任何模式，直接返回原标题
    return original_title, "", None


def find_in_json_cache(json_cache_data: Dict[str, List[Dict[str, Any]]], lookup_key: str, target_type: str, season_number: Optional[int] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    在JSON缓存数据中查找匹配的标题和描述
    
    只在查找时忽略大小写，但返回查到的原始信息
    
    对于电视剧类型:
    - 如果有季信息（season_number不为None），优先使用 S{season_number}_name 作为标题（若存在），
      否则回退到通用 name 字段；描述仅使用 S{season_number}_desc，不进行回退。
    - 如果没有季信息，可以匹配 desc 或第一季的描述键，标题使用 name。
    
    对于电影类型:
    - 使用 name 和 desc 字段。
    
    参数:
        json_cache_data (Dict[str, List[Dict[str, Any]]]): JSON缓存数据
        lookup_key (str): 要查找的标题键
        target_type (str): 目标类型，"movie" 或 "tv"
        season_number (Optional[int]): 季号，仅对电视剧类型有效
        
    返回:
        Tuple[Optional[str], Optional[str]]: (找到的标题, 找到的描述) 元组，如果没有找到则为(None, None)
    """
    # 先尝试精确匹配（大小写敏感）
    if lookup_key in json_cache_data:
        info_list = json_cache_data[lookup_key]
        for info in info_list:
            if info.get('type') == target_type:
                # 对于电视剧且有季信息的情况
                if target_type == 'tv' and season_number is not None:
                    # 【新增】优先使用季特定标题，若不存在则回退到通用名称
                    season_name_key = f'S{season_number}_name'
                    found_title = info.get(season_name_key)
                    if found_title is None:
                        found_title = info.get('name')
                    # 只查找对应季的描述，不进行回退（原有逻辑）
                    season_desc_key = f'S{season_number}_desc'
                    found_desc = info.get(season_desc_key)
                    return found_title, found_desc
                else:
                    # 对于电影或没有季信息的电视剧，使用通用描述
                    if 'desc' in info:
                        return info.get('name'), info.get('desc')
                    # 标题存在但描述不存在
                    if info.get('name'):
                        return info.get('name'), None
    
    # 尝试忽略大小写匹配
    for title_key, info_list in json_cache_data.items():
        if title_key.lower() == lookup_key.lower():
            for info in info_list:
                if info.get('type') == target_type:
                    # 对于电视剧且有季信息的情况
                    if target_type == 'tv' and season_number is not None:
                        # 【新增】优先使用季特定标题，若不存在则回退到通用名称
                        season_name_key = f'S{season_number}_name'
                        found_title = info.get(season_name_key)
                        if found_title is None:
                            found_title = info.get('name')
                        # 只查找对应季的描述，不进行回退（原有逻辑）
                        season_desc_key = f'S{season_number}_desc'
                        found_desc = info.get(season_desc_key)
                        return found_title, found_desc
                    elif target_type == 'tv' and season_number is None:
                        # 对于没有季信息的电视剧，可以匹配通用描述键和第一季的描述键
                        # 优先使用通用描述
                        if 'desc' in info:
                            return info.get('name'), info.get('desc')
                        # 如果没有通用描述，查找第一季的描述
                        for key in info.keys():
                            if key.endswith('S1_desc'):
                                return info.get('name'), info.get(key)
                            if key.endswith('s1_desc'):
                                return info.get('name'), info.get(key)
                        # 标题存在但描述不存在
                        if info.get('name'):
                            return info.get('name'), None
                    else:
                        # 对于电影，使用通用描述
                        if 'desc' in info:
                            return info.get('name'), info.get('desc')
                        # 标题存在但描述不存在
                        if info.get('name'):
                            return info.get('name'), None
    
    return None, None


def update_json_cache(json_cache_data: Dict[str, List[Dict[str, Any]]], title_key: str, new_info: Dict[str, Any]) -> None:
    """
    更新JSON缓存数据，将新信息添加到对应的标题键下
    
    如果标题键不存在，创建新条目
    如果标题键存在但相同类型的信息不存在，添加到列表
    如果标题键存在且相同类型的信息已存在，更新该信息
    
    参数:
        json_cache_data (Dict[str, List[Dict[str, Any]]]): JSON缓存数据
        title_key (str): 标题键
        new_info (Dict[str, Any]): 要添加或更新的信息
    """
    if title_key not in json_cache_data:
        json_cache_data[title_key] = [new_info]
        return
    
    # 查找是否已存在相同类型的信息
    target_type = new_info.get('type')
    for i, info in enumerate(json_cache_data[title_key]):
        if info.get('type') == target_type:
            # 更新现有信息
            json_cache_data[title_key][i].update(new_info)
            return
    
    # 如果不存在相同类型的信息，添加到列表
    json_cache_data[title_key].append(new_info)


def process_programme(programme_elem: ET.Element, epg_title_data: Dict[str, List[Dict[str, Any]]], channel_id: str, channel_name: str, channel_info: Dict[str, Any], source_config: Dict[str, Any]) -> None:
    """
    处理单个节目元素的完整流程
    
    处理顺序:
    ==========
    1. 基础信息提取阶段
       - 提取节目标题元素和原始标题
       - 提取节目描述元素和原始描述
       - 获取节目的开始和结束时间
    
    2. 时间处理阶段
       - 确定时区：优先使用频道级别目标时区(channel_timezone)，不存在时使用源级别目标时区(timezone)
       - 根据配置选择时间处理方式：
         * 时间偏移模式 (time_offset_minutes)：时间偏移分钟数，支持超过60分钟的偏移，正数表示往未来偏移，原时间加上分钟偏移量；负数表示往过去偏移，原时间减去分钟偏移量
         * 只设置 time_offset_minutes，不设置 direct_set_timezone 时（两个参数互斥），偏移分钟数后，直接替换时区
         * 直接时区替换模式 (direct_set_timezone) 
         * 标准时区转换模式
       - 分别处理开始时间和结束时间
    
    3. only_desc_from_tmdb 模式检查
       - 如果启用此模式：
         * 清理标题后缀
         * 根据频道类型查询TMDB获取描述信息
         * 更新描述但不修改标题
         * 不进行JSON缓存
         * 直接返回
    
    4. skip_tmdb_and_json 模式检查  
       - 如果启用此模式：
         * 使用原始标题和描述
         * 跳过TMDB查询和JSON缓存
         * 直接返回
    
    5. 电影类型节目处理
       - 本地缓存查询：
         * 首先在 type=movie 的缓存中查找
         * 如果没找到且启用 fallback_to_tv，在 type=tv 的缓存中查找
       - TMDB查询：
         * 本地缓存没找到时查询TMDB电影
         * 如果TMDB电影没找到且启用 fallback_to_tv，查询TMDB电视剧
       - 结果处理：
         * 拼接标题格式：新标题 / 原始标题
         * 优先使用找到的描述，否则使用原始描述
         * 将查询结果保存到缓存
    
    6. 电视剧类型节目处理
       - 标题解析：提取主标题和剧集信息
       - 本地缓存查询：
         * 首先在 type=tv 的缓存中查找
         * 如果没找到且启用 fallback_to_movie，在 type=movie 的缓存中查找
       - TMDB查询：
         * 本地缓存没找到时查询TMDB电视剧
         * 如果TMDB电视剧没找到且启用 fallback_to_movie，查询TMDB电影
       - 结果处理：
         * 拼接标题格式：新标题 剧集信息 / 原始标题
         * 优先使用找到的描述，否则使用原始描述
         * 将查询结果保存到缓存（根据是否有季信息使用不同的描述键）
    
    7. 最终更新
       - 更新节目标题
       - 更新或创建描述元素
       - 更新节目的频道属性
    
    关键逻辑特点:
    ============
    - 优先级处理：本地缓存 > TMDB查询
    - 回退机制：支持电影<->电视剧类型间的相互回退查询
    - 标题拼接：保持原始标题信息，采用 / 分隔符
    - 缓存策略：所有成功查询的结果都会保存到相应缓存文件
    - 模式互斥：only_desc_from_tmdb 和 skip_tmdb_and_json 模式优先于常规处理
    - 时区优先级：频道级别目标时区 > 源级别目标时区
    - 容错处理：各阶段都有异常捕获和回退机制
    
    参数:
        programme_elem (ET.Element): 节目XML元素
        epg_title_data (Dict[str, List[Dict[str, Any]]]): JSON缓存数据
        channel_id (str): 频道ID
        channel_name (str): 频道名称  
        channel_info (Dict[str, Any]): 频道配置信息
        source_config (Dict[str, Any]): 源配置信息
    """
    title_elem = programme_elem.find('title')
    if title_elem is None or not title_elem.text:
        return
    
    original_title = title_elem.text.strip()
    if not original_title:
        return
    
    # 获取原始描述
    original_desc_elem = programme_elem.find('desc')
    original_desc = original_desc_elem.text if original_desc_elem is not None and original_desc_elem.text else "暂无简介"
    
    # 处理时间
    start_time = programme_elem.get('start')
    stop_time = programme_elem.get('stop')
    
    # 确定目标时区：优先使用频道级别目标时区，不存在时使用源级别目标时区
    timezone = channel_info.get('channel_timezone') or source_config.get('timezone')
    
    if start_time and timezone:
        # 检查频道级别的时间处理配置
        time_offset_minutes = channel_info.get('time_offset_minutes')
        direct_set_timezone = channel_info.get('direct_set_timezone', False)
        
        # 处理 direct_set_timezone 可能为字符串的情况
        if isinstance(direct_set_timezone, str):
            direct_set_timezone = direct_set_timezone.lower() == 'true'
        
        if time_offset_minutes is not None:
            # 使用时间偏移模式
            programme_elem.set('start', adjust_time_with_offset(start_time, time_offset_minutes, timezone))
        elif direct_set_timezone:
            # 使用直接替换时区模式
            programme_elem.set('start', replace_timezone_directly(start_time, timezone))
        else:
            # 使用时区转换模式
            timezone_offset = parse_timezone_offset(timezone)
            programme_elem.set('start', convert_time_to_timezone(start_time, timezone_offset))
    
    if stop_time and timezone:
        # 检查频道级别的时间处理配置
        time_offset_minutes = channel_info.get('time_offset_minutes')
        direct_set_timezone = channel_info.get('direct_set_timezone', False)
        
        # 处理 direct_set_timezone 可能为字符串的情况
        if isinstance(direct_set_timezone, str):
            direct_set_timezone = direct_set_timezone.lower() == 'true'
        
        if time_offset_minutes is not None:
            # 使用时间偏移模式
            programme_elem.set('stop', adjust_time_with_offset(stop_time, time_offset_minutes, timezone))
        elif direct_set_timezone:
            # 使用直接替换时区模式
            programme_elem.set('stop', replace_timezone_directly(stop_time, timezone))
        else:
            # 使用时区转换模式
            timezone_offset = parse_timezone_offset(timezone)
            programme_elem.set('stop', convert_time_to_timezone(stop_time, timezone_offset))
    
    # 检查是否启用 only_desc_from_tmdb 模式
    only_desc_from_tmdb = channel_info.get('only_desc_from_tmdb', False)
    
    # 处理 only_desc_from_tmdb 可能为字符串的情况
    if isinstance(only_desc_from_tmdb, str):
        only_desc_from_tmdb = only_desc_from_tmdb.lower() == 'true'
    
    if only_desc_from_tmdb:
        print("*"*36)
        print(f"🆗 启用 only_desc_from_tmdb 模式: {original_title}")
        
        # 清理标题，移除后缀
        clean_title = clean_title_suffix(original_title)
        print(f"ℹ️ 清理后标题: {clean_title}")
        
        # 获取频道类型
        channel_type = channel_info.get('type', 'movie')
        
        # 按照HK、TW顺序查询TMDB，根据频道类型决定查询顺序
        found_desc = get_desc_from_tmdb_only(clean_title, channel_type)
        
        # 更新描述
        new_desc = found_desc if found_desc else original_desc
        
        # 更新或创建描述元素
        desc_elem = programme_elem.find('desc')
        if desc_elem is None:
            desc_elem = ET.SubElement(programme_elem, 'desc')
        desc_elem.text = new_desc
        
        # 标题保持不变
        title_elem.text = original_title
        
        # 更新 channel 属性
        programme_elem.set('channel', channel_id)
        return
    
    # 检查是否跳过TMDB查询和JSON缓存
    skip_tmdb_and_json = channel_info.get('skip_tmdb_and_json', False)
    
    # 处理 skip_tmdb_and_json 可能为字符串的情况
    if isinstance(skip_tmdb_and_json, str):
        skip_tmdb_and_json = skip_tmdb_and_json.lower() == 'true'
    
    if skip_tmdb_and_json:
        # 跳过 TMDB 查询和缓存，直接使用原始标题和描述
        print(f"📌 跳过 TMDB 查询和缓存，使用原始标题: {original_title}")
        # 截取字符串前20个字符（如果长度不足则保持原样）
        truncated_desc = original_desc[:20] + ('...' if len(original_desc) > 20 else '')
        print(f"  ┖ 使用原始描述: {truncated_desc}")
        title_elem.text = original_title
        
        # 更新或创建描述元素
        desc_elem = programme_elem.find('desc')
        if desc_elem is None:
            desc_elem = ET.SubElement(programme_elem, 'desc')
        desc_elem.text = original_desc
        
        # 更新 channel 属性
        programme_elem.set('channel', channel_id)
        return
    
    channel_type = channel_info.get('type', 'movie')
    
    if channel_type == "movie":
        # 电影类型处理
        # 第一步：先从 type=movie 的本地缓存获取
        found_title, found_desc = find_in_json_cache(epg_title_data, original_title, 'movie')
        
        # 第二步：如果没找到，并且设置了fallback_to_tv，则从 type=tv 的本地缓存获取
        if found_title is None and found_desc is None:
            fallback_to_tv = channel_info.get('fallback_to_tv', False)
            if isinstance(fallback_to_tv, str):
                fallback_to_tv = fallback_to_tv.lower() == 'true'
            if fallback_to_tv:
                found_title, found_desc = find_in_json_cache(epg_title_data, original_title, 'tv')
                if found_title is not None or found_desc is not None:
                    print(f"☑️ 从本地缓存获取到电影 (tv类型): {original_title}")
                    # 添加警告检查
                    if found_title is not None and found_desc is None:
                        print(f"⚠️ 在缓存中找到tv类型标题但未找到描述: {original_title}")
        
        if found_title is not None or found_desc is not None:
            print(f"☑️ 从本地缓存获取到电影: {original_title}")
            
            # 添加警告检查
            if found_title is not None and found_desc is None:
                print(f"⚠️ 在缓存中找到movie类型标题但未找到描述: {original_title}")
            
            # 确定最终标题和描述
            if found_title:
                # 拼接新标题（从缓存获取的）和原始标题：新标题 / 原始标题
                new_title = f"{found_title} / {original_title}"
            else:
                new_title = original_title
                
            new_desc = found_desc if found_desc is not None else original_desc
        else:
            print("*"*36)
            print(f"🌏 在 TMDB 中查询电影: {original_title}")
            # 第二步：如果本地缓存没找到，从 TMDB 查找
            found_title, found_desc = get_movie_info_from_tmdb(original_title, ['zh-CN', 'zh-HK', 'zh-TW'])
            
            # 第三步：如果TMDB电影没找到，并且设置了fallback_to_tv，则查询TMDB电视剧
            if found_title is None and found_desc is None:
                fallback_to_tv = channel_info.get('fallback_to_tv', False)
                if isinstance(fallback_to_tv, str):
                    fallback_to_tv = fallback_to_tv.lower() == 'true'
                if fallback_to_tv:
                    print(f"⚠️ TMDB 电影查询失败且配置了fallback_to_tv，尝试 TMDB 电视剧查询: {original_title}")
                    found_title, found_desc = get_tv_info_from_tmdb(original_title, ['zh-CN', 'zh-HK', 'zh-TW'])
                    # 如果从TMDB电视剧查询到信息，则将其保存为电视剧类型
                    if found_title is not None or found_desc is not None:
                        tv_info = {'type': 'tv'}
                        if found_title is not None:
                            tv_info['name'] = found_title
                        if found_desc is not None:
                            tv_info['desc'] = found_desc
                        update_json_cache(epg_title_data, original_title, tv_info)
                        print(f"✅ 找到电视剧信息并缓存: {original_title}")
                        print("*"*36)
                    else:
                        print(f"⚠️ 未在 TMDB 中找到任何该电视剧信息: {original_title}")
                        print("*"*36)
                else:
                    print(f"⚠️ 未在 TMDB 中找到任何该电影信息: {original_title}")
                    print("*"*36)
            
            # 如果是从TMDB电影查询到的，则保存为电影类型
            elif found_title is not None or found_desc is not None:
                movie_info = {'type': 'movie'}
                if found_title is not None:
                    movie_info['name'] = found_title
                if found_desc is not None:
                    movie_info['desc'] = found_desc
                update_json_cache(epg_title_data, original_title, movie_info)
                print(f"✅ 找到电影信息并缓存: {original_title}")
                print("*"*36)
            
            # 确定最终标题和描述
            if found_title:
                # 拼接新标题（从TMDB获取的）和原始标题：新标题 / 原始标题
                new_title = f"{found_title} / {original_title}"
            else:
                new_title = original_title
                
            new_desc = found_desc if found_desc is not None else original_desc
    
    elif channel_type == "tv":
        # 电视剧类型处理
        main_title, episode_info, season_number = parse_tv_title(original_title)
        
        # 第一步：在type=tv的本地缓存数据中查找
        found_title, found_desc = find_in_json_cache(epg_title_data, main_title, 'tv', season_number)
        if found_title is not None or found_desc is not None:
            print(f"☑️ 从本地缓存获取到电视剧 (tv类型): {main_title}")
            # 添加警告检查
            if found_title is not None and found_desc is None:
                print(f"⚠️ 在缓存中找到tv类型标题但未找到描述: {main_title}")
        
        # 第二步：如果设置了fallback_to_movie并且在type=tv的本地缓存没找到，在type=movie的本地缓存数据中查找
        if found_title is None and found_desc is None:
            fallback_to_movie = channel_info.get('fallback_to_movie', False)
            
            # 处理 fallback_to_movie 可能为字符串的情况
            if isinstance(fallback_to_movie, str):
                fallback_to_movie = fallback_to_movie.lower() == 'true'
                
            if fallback_to_movie:
                found_title, found_desc = find_in_json_cache(epg_title_data, main_title, 'movie')
                if found_title is not None or found_desc is not None:
                    print(f"☑️ 从本地缓存获取到电视剧 (movie类型): {main_title}")
                    # 添加警告检查
                    if found_title is not None and found_desc is None:
                        print(f"⚠️ 在缓存中找到movie类型标题但未找到描述: {main_title}")
        
        # 第三步：如果还没找到，从TMDB查找电视剧
        if found_title is None and found_desc is None:
            print("*"*36)
            print(f"🌏 在 TMDB 中查询电视剧: {main_title}")
            found_title, found_desc = get_tv_info_from_tmdb(main_title, ['zh-CN', 'zh-HK', 'zh-TW'])
            
            # 保存到缓存
            if found_title is not None or found_desc is not None:
                tv_info = {'type': 'tv'}
                if found_title is not None:
                    tv_info['name'] = found_title
                if found_desc is not None:
                    # 根据是否有季信息使用不同的描述键
                    if season_number is not None:
                        season_key = f'S{season_number}_desc'
                        tv_info[season_key] = found_desc
                    else:
                        tv_info['desc'] = found_desc
                
                # 使用原始主标题作为键（不转换为小写）
                update_json_cache(epg_title_data, main_title, tv_info)
                print(f"✅ 找到电视剧信息并缓存: {main_title}")
                print("*"*36)
            else:
                print(f"⚠️ 未在 TMDB 中找到任何该电视剧信息: {main_title}")
                print("*"*36)
        
        # 第四步：如果 TMDB 电视剧查询失败且配置了fallback_to_movie，尝试 TMDB 电影查询
        if found_title is None and found_desc is None:
            fallback_to_movie = channel_info.get('fallback_to_movie', False)
            
            # 处理 fallback_to_movie 可能为字符串的情况
            if isinstance(fallback_to_movie, str):
                fallback_to_movie = fallback_to_movie.lower() == 'true'
            
            if fallback_to_movie:
                print(f"⚠️ TMDB 电视剧查询失败且配置了fallback_to_movie，尝试 TMDB 电影查询: {main_title}")
                found_title, found_desc = get_movie_info_from_tmdb(main_title, ['zh-CN', 'zh-HK', 'zh-TW'])
                
                # 保存到缓存（作为电影类型）
                if found_title is not None or found_desc is not None:
                    movie_info = {'type': 'movie'}
                    if found_title is not None:
                        movie_info['name'] = found_title
                    if found_desc is not None:
                        movie_info['desc'] = found_desc
                    
                    # 使用原始主标题作为键（不转换为小写）
                    update_json_cache(epg_title_data, main_title, movie_info)
                    print(f"✅ 找到电影信息并缓存: {main_title}")
                    print("*"*36)
                else:
                    print(f"⚠️ 未在 TMDB 中找到任何该电影信息: {main_title}")
                    print("*"*36)
        
        # 确定最终标题和描述
        if found_title:
            # 如果有剧集信息，拼接
            if episode_info:
                new_main_title = f"{found_title} {episode_info}"
            else:
                new_main_title = found_title
            # 拼接新标题和原始标题：新标题 / 原始标题
            new_title = f"{new_main_title} / {original_title}"
        else:
            new_title = original_title
            
        new_desc = found_desc if found_desc is not None else original_desc
    
    else:
        # 未知类型，保持原样
        new_title = original_title
        new_desc = original_desc
    
    # 更新标题
    title_elem.text = new_title
    
    # 更新或创建描述元素
    desc_elem = programme_elem.find('desc')
    if desc_elem is None:
        desc_elem = ET.SubElement(programme_elem, 'desc')
    desc_elem.text = new_desc
    
    # 更新 channel 属性
    programme_elem.set('channel', channel_id)


def process_epg_sources(sources: List[Dict[str, Any]], epg_title_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    处理所有 EPG 源，返回更新后的节目数据
    
    参数:
        sources (List[Dict[str, Any]]): EPG源配置列表
        epg_title_data (Dict[str, List[Dict[str, Any]]]): JSON缓存数据
        
    返回:
        Dict[str, List[Dict[str, Any]]]: 更新后的JSON缓存数据
    """
    # 创建新的 XML 根元素
    new_root = ET.Element('tv')
    new_root.set('generator-info-name', 'yufeilai666')
    new_root.set('generator-info-url', 'https://github.com/yufeilai666/tvepg')
    new_root.set('source-info-name', 'epgpw')
    new_root.set('source-info-url', 'https://epg.pw')
    
    # 用于跟踪已添加的频道，避免重复
    added_channels = set()
    
    # 用于存储各个本地缓存文件的更新
    local_json_updates = {}
    
    for source in sources:
        print(f"\n\n💖💖💖 处理源: {source['epg_name']} 💖💖💖")
        
        # 下载并解析 XML
        root = download_and_parse_xml(source['epg_url'])
        if root is None:
            print(f"❌❌❌ 无法处理 {source['epg_name']} ❌❌❌")
            continue
        
        # 为每个频道处理
        for channel_info in source['channel_info']:
            original_channel_id = str(channel_info['channel_id'])
            original_channel_name = channel_info['channel_name']
            new_channel_id = channel_info['new_channel_id']
            new_channel_name = channel_info['new_channel_name']
            
            print("\n" + "="*36)
            print(f"☀☀☀ 开始处理频道: {original_channel_name} -> {new_channel_id} ☀☀☀")
            
            # 如果新频道已添加，跳过
            if new_channel_id in added_channels:
                print(f"🌺🌺🌺 新频道已添加: {new_channel_id} 🌺🌺🌺")
                continue
            
            # 检查是否指定了本地缓存文件
            local_json_file = channel_info.get('local_json_file')
            if local_json_file:
                # 获取完整路径
                full_json_path = get_json_path(local_json_file)
                
                # 加载指定的本地缓存文件
                if full_json_path not in local_json_updates:
                    local_json_updates[full_json_path] = robust_json_loader(local_json_file)
                    # 兼容旧格式：如果是字典但值不是列表，转换为新格式
                    if isinstance(local_json_updates[full_json_path], dict):
                        data = local_json_updates[full_json_path]
                        new_data = {}
                        for key, value in data.items():
                            if isinstance(value, list):
                                new_data[key] = value
                            else:
                                # 旧格式：单个对象 -> 转换为列表
                                new_data[key] = [value]
                        local_json_updates[full_json_path] = new_data
                channel_epg_data = local_json_updates[full_json_path]
                print(f"💫💫💫 使用本地缓存文件: {full_json_path} 💫💫💫")
            else:
                # 使用全局缓存
                channel_epg_data = epg_title_data
            
            # 查找原始频道节点
            original_channel = root.find(f"./channel[@id='{original_channel_id}']")
            if original_channel is None:
                print(f"❄❄❄ 未找到频道 ID: {original_channel_id} ❄❄❄")
                continue
            
            # 创建新频道节点
            new_channel = ET.SubElement(new_root, 'channel', {'id': new_channel_id})
            display_name = ET.SubElement(new_channel, 'display-name')
            display_name.text = new_channel_name
            
            # 复制其他属性
            for elem in original_channel:
                if elem.tag != 'display-name':
                    new_elem = ET.SubElement(new_channel, elem.tag)
                    new_elem.text = elem.text
                    if elem.attrib:
                        new_elem.attrib = elem.attrib
            
            # 处理节目信息
            programmes = root.findall(f"./programme[@channel='{original_channel_id}']")
            print(f"🎯 找到 {len(programmes)} 个节目")
            print("="*36)
            
            # 创建节目的深拷贝，确保每个频道有独立的节目数据
            for programme in programmes:
                # 创建节目的深拷贝
                programme_copy = ET.fromstring(ET.tostring(programme, encoding='unicode'))
                
                # 处理节目信息（包括时区处理）
                process_programme(programme_copy, channel_epg_data, new_channel_id, new_channel_name, channel_info, source)
                
                # 添加到新XML树
                new_root.append(programme_copy)
            
            # 标记频道已添加
            added_channels.add(new_channel_id)
            print("="*36)
            print(f"🌹🌹🌹 已处理频道: {original_channel_name} -> {new_channel_id} 🌹🌹🌹")
            print("="*36 + "\n")
    
    # 保存所有更新的本地缓存文件
    for local_json_file, data in local_json_updates.items():
        # 确保目录存在
        ensure_directory(os.path.dirname(local_json_file) or EPG_TITLE_INFO_DIR)
        save_json_to_file(local_json_file, data)
        print(f"🎉🎉🎉 已保存本地缓存文件: {local_json_file} 🎉🎉🎉")
    
    # 保存合并的 XML 文件
    output_path = get_output_xml_path()
    tree = ET.ElementTree(new_root)
    # 美化 XML 输出
    ET.indent(tree, space="  ", level=0)
    tree.write(output_path, encoding='utf-8', xml_declaration=True)
    print(f"\n🎉🎉🎉 已保存合并的 EPG 文件: {output_path} 🎉🎉🎉")
    
    return epg_title_data


def main():
    """主函数"""
    # 确保缓存目录存在
    ensure_directory(EPG_TITLE_INFO_DIR)
    
    # 加载 epg_title_info.json
    epg_title_data = load_epg_title_json()
    print(f"💞💞💞 已从 {get_main_json_path()} 加载 {len(epg_title_data)} 条节目记录 💞💞💞")
    
    # 定义源数据
    # timezone  源级别目标时区，支持 "UTC+8" 形式；支持 "+08:30"形式，冒号后面的30表示偏移量
    # channel_timezone  频道级别目标时区设置，优先级高于源级别目标时区，支持 "UTC+8" 形式；支持 "+08:30"形式
    #   1、channel_timezone不为空时，优先使用它进行时区转换，timezone无效
    #   2、channel_timezone不存在或为空时，使用timezone进行时区转换
    # direct_set_timezone  是否直接替换时区，支持布尔值 True/False 和 字符串 "true"/"false"
    # time_offset_minutes  时间偏移分钟数，支持超过60分钟的偏移，偏移分钟数后，直接替换时区。正数表示往未来偏移，原时间加上分钟偏移量；负数表示往过去偏移，原时间减去分钟偏移量。
    # 时区时间处理逻辑：
    #   1、time_offset_minutes不为空时，使用时间偏移模式，direct_set_timezone和时区转换模式无效
    #   2、time_offset_minutes不存在或为空，direct_set_timezone为True时，使用时区直接替换模式，时区转换模式无效
    #   3、time_offset_minutes和direct_set_timezone都不存在或为空时，使用时区转换模式（channel_timezone优先）
    # skip_tmdb_and_json  是否跳过查询 TMDB、epg_title_info.json 和跳过缓存到 epg_title_info.json，支持布尔值 True/False 和字符串 "true"/"false"
    # only_desc_from_tmdb  是否仅从TMDB获取描述信息并更新频道desc，不修改标题，不进行查询和缓存JSON，支持布尔值 True/False 和字符串 "true"/"false"
    # fallback_to_movie  type为tv时使用，电视剧查询失败时回退到电影查询，查询顺序：本地tv -> 本地movie -> TMDB tv -> TMDB movie；支持布尔值 True/False 和字符串 "true"/"false"
    # fallback_to_tv  type为movie时使用，电影查询失败时回退到电视剧查询，查询顺序：本地movie -> 本地tv -> TMDB movie -> TMDB tv；支持布尔值 True/False 和字符串 "true"/"false"
    # local_json_file  指定本地缓存JSON文件，如"epgTW_title_info.json"，如有设置优先使用
    sources = [
        {
            "epg_name": "epg_MY.xml",
            "epg_url": "https://epg.pw/xmltv/epg_MY.xml",
            "timezone": "UTC+8",
            "channel_info": [
                # {
                    # "channel_id": "1298",
                    # "channel_name": "Celestial Movies HD (马来astro)",
                    # "new_channel_id": "天映频道 (astro)",
                    # "new_channel_name": "天映频道 (astro)",
                    # "type": "movie",
                    # "skip_tmdb_and_json": False,
                    # "direct_set_timezone": True
                # },
                {
                    "channel_id": "3493",
                    "channel_name": "TVB Xing He HD (马来astro)",
                    "new_channel_id": "TVB星河 (astro)",
                    "new_channel_name": "TVB星河 (astro)",
                    "type": "tv",
                    "skip_tmdb_and_json": False,
                    "direct_set_timezone": True
                },
                {
                    "channel_id": "3493",
                    "channel_name": "TVB Xing He HD (马来astro)",
                    "new_channel_id": "TVB星河 (starhub)",
                    "new_channel_name": "TVB星河 (starhub)",
                    "type": "tv",
                    "skip_tmdb_and_json": False,
                    "time_offset_minutes": -10
                },
                {
                    "channel_id": "3493",
                    "channel_name": "TVB Xing He HD (马来astro)",
                    "new_channel_id": "TVB星河 (singtel)",
                    "new_channel_name": "TVB星河 (singtel)",
                    "type": "tv",
                    "skip_tmdb_and_json": False,
                    "time_offset_minutes": 50
                },
                {
                    "channel_id": "3493",
                    "channel_name": "TVB Xing He HD (马来astro)",
                    "new_channel_id": "TVB星河 (HK)",
                    "new_channel_name": "TVB星河 (HK)",
                    "type": "tv",
                    "skip_tmdb_and_json": False,
                    "time_offset_minutes": -10
                },
                {
                    "channel_id": "2524",
                    "channel_name": "TVB Jade (马来astro)",
                    "new_channel_id": "翡翠台 (astro)",
                    "new_channel_name": "翡翠台 (astro)",
                    "type": "tv",
                    "fallback_to_movie": True,
                    "skip_tmdb_and_json": False,
                    "direct_set_timezone": True
                },
                {
                    "channel_id": "3290",
                    "channel_name": "iQIYI HD (马来astro)",
                    "new_channel_id": "iQIYI (astro)",
                    "new_channel_name": "iQIYI (astro)",
                    "type": "tv",
                    "fallback_to_movie": True,  # 电视剧查询失败时回退到电影查询，查询顺序：本地tv -> 本地movie -> TMDB tv -> TMDB movie
                    "skip_tmdb_and_json": False,
                    "local_json_file": "epgIQIYI_title_info.json",
                    "direct_set_timezone": True
                },
                {
                    "channel_id": "3509",
                    "channel_name": "TVBS Asia HD (马来astro)",
                    "new_channel_id": "TVBS Asia (astro)",
                    "new_channel_name": "TVBS Asia (astro)",
                    "type": "tv",
                    "skip_tmdb_and_json": False,
                    "local_json_file": "epgTW_title_info.json",  # 指定本地缓存文件
                    "direct_set_timezone": True
                },
                {
                    "channel_id": "2124",
                    "channel_name": "Astro AOD 311 (马来astro)",
                    "new_channel_id": "astro AOD (astro)",
                    "new_channel_name": "astro AOD (astro)",
                    "type": "tv",
                    "skip_tmdb_and_json": False,
                    "local_json_file": "epgASTRO_title_info.json",
                    "direct_set_timezone": True
                },
                {
                    "channel_id": "2226",
                    "channel_name": "Astro AEC HD (马来astro)",
                    "new_channel_id": "astro AEC (astro)",
                    "new_channel_name": "astro AEC (astro)",
                    "type": "tv",
                    "fallback_to_movie": True,  # 电视剧查询失败时回退到电影查询，查询顺序：本地tv -> 本地movie -> TMDB tv -> TMDB movie
                    "skip_tmdb_and_json": False,
                    "local_json_file": "epgASTRO_title_info.json",
                    "direct_set_timezone": True
                },
                {
                    "channel_id": "1781",
                    "channel_name": "Astro Quan Jia HD (马来astro)",
                    "new_channel_id": "astro QJ (astro)",
                    "new_channel_name": "astro QJ (astro)",
                    "type": "tv",
                    "fallback_to_movie": True,  # 电视剧查询失败时回退到电影查询，查询顺序：本地tv -> 本地movie -> TMDB tv -> TMDB movie
                    "skip_tmdb_and_json": False,
                    "local_json_file": "epgASTRO_title_info.json",
                    "direct_set_timezone": True
                }
            ]
        },
        # {
            # "epg_name": "epg_ID.xml",
            # "epg_url": "https://epg.pw/xmltv/epg_ID.xml",
            # "timezone": "UTC+8",
            # "channel_info": [
                # {
                    # "channel_id": "171999",
                    # "channel_name": "Celestial Movies (印尼)",
                    # "new_channel_id": "天映频道 (印尼)",
                    # "new_channel_name": "天映频道 (印尼)",
                    # "type": "movie",
                    # "skip_tmdb_and_json": False,
                    # "direct_set_timezone": True
                # }
            # ]
        # },
        # {
            # "epg_name": "epg_SG.xml",
            # "epg_url": "https://epg.pw/xmltv/epg_SG.xml",
            # "timezone": "UTC+8",
            # "channel_info": [
                # {
                    # "channel_id": "369819",
                    # "channel_name": "CCM (新加坡)",
                    # "new_channel_id": "天映经典 (astro)",
                    # "new_channel_name": "天映经典 (astro)",
                    # "type": "movie",
                    # "skip_tmdb_and_json": True,
                    # "time_offset_minutes": 60
                # }
            # ]
        # },
        {
            "epg_name": "epg_TW.xml",
            "epg_url": "https://epg.pw/xmltv/epg_TW.xml",
            "timezone": "UTC+8",
            "channel_info": [
                {
                    "channel_id": "456637",
                    "channel_name": "Global Trekker 探索世界 (台湾TBC)",
                    "new_channel_id": "Global Trekker (astro)",
                    "new_channel_name": "Global Trekker (astro)",
                    "type": "tv",
                    "skip_tmdb_and_json": True,
                    "time_offset_minutes": 10
                },
                {
                    "channel_id": "457360",
                    "channel_name": "美亞電影HD (台湾Mod)",
                    "new_channel_id": "美亚电影台 (Mod)",
                    "new_channel_name": "美亚电影台 (Mod)",
                    "type": "movie",
                    "only_desc_from_tmdb": True,
                    "direct_set_timezone": True
                }
            ]
        },
        {
            "epg_name": "epg_HK.xml",
            "epg_url": "https://epg.pw/xmltv/epg_HK.xml",
            "timezone": "UTC+8",
            "channel_info": [
                {
                    "channel_id": "410304",
                    "channel_name": "HISTORY (香港)",
                    "new_channel_id": "History (astro)",
                    "new_channel_name": "History (astro)",
                    "type": "tv",
                    "skip_tmdb_and_json": True,
                    "time_offset_minutes": 5
                },
                {
                    "channel_id": "410370",
                    "channel_name": "亞洲美食台 (香港)",
                    "new_channel_id": "亚洲美食台 (astro)",
                    "new_channel_name": "亚洲美食台 (astro)",
                    "type": "tv",
                    "skip_tmdb_and_json": True,
                    "time_offset_minutes": 10
                },
                {
                    "channel_id": "410293",
                    "channel_name": "Discovery Asia (香港)",
                    "new_channel_id": "Discovery Asia (astro)",
                    "new_channel_name": "Discovery Asia (astro)",
                    "type": "tv",
                    "skip_tmdb_and_json": True,
                    "time_offset_minutes": 5
                }# ,
                # {
                    # "channel_id": "368325",
                    # "channel_name": "千禧經典台 (香港TVB)",
                    # "new_channel_id": "千禧经典台 (astro)",
                    # "new_channel_name": "千禧经典台 (astro)",
                    # "type": "tv",
                    # "skip_tmdb_and_json": True,
                    # "time_offset_minutes": 10
                # }
            ]
        },
        {
            "epg_name": "mytvsuper.xml",
            "epg_url": "https://raw.githubusercontent.com/yufeilai666/test/main/epg/mytvsuper.xml",
            "timezone": "UTC+8",
            "channel_info": [
                {
                    "channel_id": "86.myTV",
                    "channel_name": "千禧經典台 (myTV Super)",
                    "new_channel_id": "千禧经典台 (astro)",
                    "new_channel_name": "千禧经典台 (astro)",
                    "type": "tv",
                    "skip_tmdb_and_json": True,
                    "time_offset_minutes": 10
                }
            ]
        },
        {
            "epg_name": "LiuYi0526_EPG.xml",
            "epg_url": "https://raw.githubusercontent.com/LiuYi0526/IPTVnew/EPG/EPG.xml.gz",
            "timezone": "UTC+8",
            "channel_info": [
                {
                    "channel_id": "bfgd_4200000636",
                    "channel_name": "重温经典",
                    "new_channel_id": "重温经典",
                    "new_channel_name": "重温经典",
                    "type": "tv",
                    "skip_tmdb_and_json": True,
                    "direct_set_timezone": True
                }
            ]
        }# ,
        # {
            # "epg_name": "epg_CA.xml",
            # "epg_url": "https://epg.pw/xmltv/epg_CA.xml",
            # "timezone": "UTC+8",
            # "channel_info": [
                # {
                    # "channel_id": "470891",
                    # "channel_name": "LS Times TV (加拿大)",
                    # "new_channel_id": "LS TIME 龙祥频道 (CA)",
                    # "new_channel_name": "LS TIME 龙祥频道 (CA)",
                    # "type": "tv",
                    # "fallback_to_movie": True,  # 电视剧查询失败时回退到电影查询，查询顺序：本地tv -> 本地movie -> TMDB tv -> TMDB movie
                    # "skip_tmdb_and_json": False,
                    # "direct_set_timezone": True
                # }
            # ]
        # }
    ]
    
    # 处理 EPG 源
    updated_epg_data = process_epg_sources(sources, epg_title_data)
    
    # 保存更新后的 epg_title_info.json
    save_epg_title_json(updated_epg_data)
    print(f"🎉🎉🎉 已更新 {get_main_json_path()}，现有 {len(updated_epg_data)} 条记录 🎉🎉🎉")


if __name__ == "__main__":
    main()