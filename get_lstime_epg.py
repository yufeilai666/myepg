import re
import os
import time
import random
from datetime import datetime, timedelta
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
import requests
from bs4 import BeautifulSoup

# TMDB配置
TMDB_API_KEY = os.environ.get('TMDB_API_KEY')

def clean_movie_title(title):
    """
    清理电影标题，移除括号及其内容
    """
    # 移除中文括号及其内容
    cleaned_title = re.sub(r'（[^）]*）', '', title)
    # 移除英文括号及其内容
    cleaned_title = re.sub(r'\([^)]*\)', '', cleaned_title)
    # 移除方括号及其内容
    cleaned_title = re.sub(r'\[[^\]]*\]', '', cleaned_title)
    # 移除多余空格
    cleaned_title = cleaned_title.strip()
    
    print(f"ℹ️ 清理标题: '{title}' -> '{cleaned_title}'")
    return cleaned_title

def format_description(description):
    """
    格式化描述文本：处理各种换行符，按段落处理，去除空白行，每个段首添加两个全角空格
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

def get_movie_description_from_url(url, original_title, max_retries=3):
    """
    从电影详情页面获取描述信息，按段落处理并添加全角空格
    添加重试机制和随机延迟
    """
    # 清理标题
    clean_title = clean_movie_title(original_title)
    
    # 如果清理后标题为空，使用原始标题
    if not clean_title:
        clean_title = original_title
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    for attempt in range(max_retries):
        try:
            # 随机延迟 0.5 到 1.1 秒
            delay = random.uniform(0.5, 1.1)
            print(f"⏳️ 等待 {delay:.2f} 秒后获取电影《{clean_title}》的详情...")
            time.sleep(delay)
            
            print(f"ℹ️ 正在获取电影《{clean_title}》的详情 (尝试 {attempt+1}/{max_retries}): {url}")
            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = 'utf-8'
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 查找电影介绍部分
                movie_info_article = soup.find('article', class_='movie-info')
                if movie_info_article:
                    # 查找介绍标题后面的p标签
                    intro_header = movie_info_article.find('h4', string=re.compile('介紹'))
                    if intro_header:
                        # 获取h4后面的p标签内容
                        p_tag = intro_header.find_next_sibling('p')
                        if p_tag:
                            # 获取p标签内的HTML内容，保留<br>标签
                            p_html = str(p_tag)
                            
                            # 将<br>标签转换为换行符
                            description = re.sub(r'<br\s*/?\s*>', '\n', p_html, flags=re.IGNORECASE)
                            
                            # 移除其他HTML标签，只保留文本和换行符
                            description = re.sub(r'<[^>]+>', '', description)
                            
                            # 使用改进的格式化函数处理描述文本
                            description = format_description(description)
                            
                            print(f"✅ 从原始网页成功获取电影《{clean_title}》的描述信息，长度: {len(description)}")
                            return description
                
                print(f"⚠️ 未在节目单网页找到电影《{clean_title}》的描述信息")
                return None
            else:
                print(f"❌ HTTP请求失败，状态码: {response.status_code}")
                # 如果不是最后一次尝试，则等待后重试
                if attempt < max_retries - 1:
                    retry_delay = random.uniform(0.5, 1.1)
                    print(f"⏳️ 等待 {retry_delay:.2f} 秒后重试...")
                    time.sleep(retry_delay)
                    
        except requests.exceptions.RequestException as e:
            print(f"❌ 获取电影《{clean_title}》的详情错误 (尝试 {attempt+1}/{max_retries}): {e}")
            
            # 如果是HTTP/2协议错误，尝试使用HTTP/1.1
            if "HTTP2" in str(e).upper() or "PROTOCOL" in str(e).upper():
                print("⚠️ 检测到HTTP/2协议错误，尝试使用HTTP/1.1...")
                try:
                    # 使用HTTP/1.1重试
                    session = requests.Session()
                    session.mount('https://', requests.adapters.HTTPAdapter(max_retries=1))
                    
                    response = session.get(url, headers=headers, timeout=10)
                    response.encoding = 'utf-8'
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # 查找电影介绍部分
                        movie_info_article = soup.find('article', class_='movie-info')
                        if movie_info_article:
                            # 查找介绍标题后面的p标签
                            intro_header = movie_info_article.find('h4', string=re.compile('介紹'))
                            if intro_header:
                                # 获取h4后面的p标签内容
                                p_tag = intro_header.find_next_sibling('p')
                                if p_tag:
                                    # 获取p标签内的HTML内容，保留<br>标签
                                    p_html = str(p_tag)
                                    
                                    # 将<br>标签转换为换行符
                                    description = re.sub(r'<br\s*/?\s*>', '\n', p_html, flags=re.IGNORECASE)
                                    description = re.sub(r'<[^>]+>', '', description)
                                    
                                    # 使用改进的格式化函数处理描述文本
                                    description = format_description(description)
                                    
                                    print(f"✅ 从原始网页成功获取电影《{clean_title}》的描述信息，长度: {len(description)}")
                                    return description
                except Exception as retry_e:
                    print(f"❌ HTTP/1.1重试也失败: {retry_e}")
            
            # 如果不是最后一次尝试，则等待后重试
            if attempt < max_retries - 1:
                retry_delay = random.uniform(0.5, 1.1)
                print(f"⏳️ 等待 {retry_delay:.2f} 秒后重试...")
                time.sleep(retry_delay)
                
        except Exception as e:
            print(f"❌ 获取电影《{clean_title}》的详情未知错误 (尝试 {attempt+1}/{max_retries}): {e}")
            
            # 如果不是最后一次尝试，则等待后重试
            if attempt < max_retries - 1:
                retry_delay = random.uniform(0.5, 1.1)
                print(f"⏳️ 等待 {retry_delay:.2f} 秒后重试...")
                time.sleep(retry_delay)
    
    print(f"⚠️ 经过 {max_retries} 次尝试后仍未能获取电影《{clean_title}》的描述信息")
    return None

def search_tmdb_movie_direct(original_title):
    """
    直接使用TMDB API搜索电影信息，避免第三方库的问题
    """
    if not TMDB_API_KEY:
        return None
    
    # 清理标题
    clean_title = clean_movie_title(original_title)
    
    # 如果清理后标题为空，使用原始标题
    if not clean_title:
        clean_title = original_title
    
    # 地区搜索顺序
    regions = ['zh-TW', 'zh-HK', 'zh-CN']
    
    for region in regions:
        try:
            # 构建搜索URL
            search_url = "https://api.themoviedb.org/3/search/movie"
            params = {
                'api_key': TMDB_API_KEY,
                'language': region,
                'query': clean_title,
                'page': 1
            }
            
            print(f"🔎 在 {region} 地区搜索电影: '{clean_title}' (原始标题: '{original_title}')")
            
            # 发送搜索请求
            response = requests.get(search_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                if results:
                    # 取第一个结果
                    movie_id = results[0]['id']
                    
                    # 获取电影详情
                    details_url = f"https://api.themoviedb.org/3/movie/{movie_id}"
                    details_params = {
                        'api_key': TMDB_API_KEY,
                        'language': region
                    }
                    
                    details_response = requests.get(details_url, params=details_params, timeout=10)
                    
                    if details_response.status_code == 200:
                        movie_details = details_response.json()
                        
                        # 检查是否有描述信息
                        overview = movie_details.get('overview', '')
                        if overview:
                            print(f"✅ 在 {region} 找到电影信息: {movie_details.get('title', '未知标题')}")
                            
                            # 使用改进的格式化函数处理TMDB的描述信息
                            formatted_overview = format_description(overview)
                            
                            return {
                                'title': original_title,  # 使用原始标题显示
                                'overview': formatted_overview,
                                'release_date': movie_details.get('release_date', ''),
                                'vote_average': movie_details.get('vote_average', 0),
                                'id': movie_id
                            }
                        else:
                            print(f"⚠️ 在 {region} 找到电影但无描述信息，继续搜索其他地区")
                    else:
                        print(f"❌ 获取电影详情失败: {details_response.status_code}")
                else:
                    print(f"⚠️ 在 {region} 未找到电影: {clean_title}")
            else:
                print(f"❌ TMDB搜索请求失败: {response.status_code}")
            
            # 避免请求过快
            time.sleep(random.uniform(0.5, 1.1))
            
        except Exception as e:
            print(f"❌ TMDB搜索错误 ({region}): {e}")
            continue
    
    print(f"⚠️ 在所有地区均未找到电影描述信息: {clean_title}")
    return None

def parse_schedule_html(html_content):
    """
    从HTML内容中解析节目信息
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    schedule_data = []
    
    # 查找所有包含节目列表的div
    time_lists = soup.find_all('div', class_='time-list')
    
    for time_list in time_lists:
        # 提取日期信息
        date_span = time_list.find('span', class_='viewDate')
        if not date_span:
            continue
            
        date_val = date_span.get('data-val', '')  # 格式: MM/DD
        
        day_info = {
            'date': date_val,
            'programs': []
        }
        
        # 提取节目信息
        program_items = time_list.find_all('li')
        for item in program_items:
            link_tag = item.find('a')
            if not link_tag:
                continue
                
            time_tag = link_tag.find('time')
            title_tag = link_tag.find('h2')
            rating_tag = link_tag.find('span', class_=re.compile('rating'))
            href = link_tag.get('href', '')
            
            # 补全链接
            if href and not href.startswith('http'):
                href = 'https://www.lstime.com.tw' + href
            
            if time_tag and title_tag:
                original_title = title_tag.text.strip()
                
                program_info = {
                    'time': time_tag.text.strip(),
                    'title': original_title,  # 直接使用原始标题
                    'rating': rating_tag.text.strip() if rating_tag else '',
                    'link': href
                }
                day_info['programs'].append(program_info)
        
        schedule_data.append(day_info)
    
    return schedule_data

def generate_xmltv_epg(schedule_data):
    """
    生成XMLTV格式的EPG节目单
    """
    # 创建根元素
    root = Element('tv')
    root.set('generator-info-name', 'yufeilai666')
    root.set('generator-info-url', 'https://github.com/yufeilai666/tvepg')
    root.set('source-info-name', 'lstime.com.tw')
    root.set('source-info-url', 'https://www.lstime.com.tw')
    
    # 添加频道信息
    channel_elem = SubElement(root, 'channel', id='LS TIME 龙祥时代')
    display_name = SubElement(channel_elem, 'display-name')
    display_name.text = '龙祥时代'
    display_name.set('lang', 'zh')
    
    # 获取当前年份
    current_year = datetime.now().year
    
    # 缓存电影信息，避免重复查询
    movie_cache = {}
    
    # 处理7天的数据
    days_to_process = min(7, len(schedule_data))
    
    print(f"📅 处理 {days_to_process} 天的节目数据")
    
    # 处理7天的节目
    for day_idx in range(days_to_process):
        day_info = schedule_data[day_idx]
        date_parts = day_info['date'].split('/')
        if len(date_parts) != 2:
            continue
            
        month, day = date_parts
        programs = day_info['programs']
        
        print(f"📺 处理 {month}/{day} 的节目，共 {len(programs)} 个")
        
        # 为每个节目计算结束时间
        for i in range(len(programs)):
            program = programs[i]
            
            # 解析开始时间
            start_time_parts = program['time'].split(':')
            if len(start_time_parts) != 2:
                continue
                
            start_hour, start_minute = start_time_parts
            
            # 创建开始时间
            start_dt = datetime(current_year, int(month), int(day), int(start_hour), int(start_minute))
            start_time = start_dt.strftime("%Y%m%d%H%M00")
            
            # 计算结束时间
            if i < len(programs) - 1:
                # 下一个节目的开始时间作为当前节目的结束时间
                next_program = programs[i + 1]
                next_time_parts = next_program['time'].split(':')
                if len(next_time_parts) == 2:
                    end_hour, end_minute = next_time_parts
                    end_dt = datetime(current_year, int(month), int(day), int(end_hour), int(end_minute))
                else:
                    # 如果无法解析下一个节目时间，使用默认2小时
                    end_dt = start_dt + timedelta(hours=2)
            else:
                # 当天最后一个节目
                if day_idx < len(schedule_data) - 1 and day_idx < days_to_process - 1:
                    # 使用下一天的第一个节目的开始时间（确保有下一天且在第7天内）
                    next_day_info = schedule_data[day_idx + 1]
                    if next_day_info['programs']:
                        next_day_program = next_day_info['programs'][0]
                        next_time_parts = next_day_program['time'].split(':')
                        if len(next_time_parts) == 2:
                            next_day_date_parts = next_day_info['date'].split('/')
                            if len(next_day_date_parts) == 2:
                                next_month, next_day = next_day_date_parts
                                end_hour, end_minute = next_time_parts
                                end_dt = datetime(current_year, int(next_month), int(next_day), int(end_hour), int(end_minute))
                                print(f"✅ 使用下一天第一个节目作为结束时间: {end_dt}")
                            else:
                                # 使用第八天的0点
                                end_dt = start_dt.replace(hour=0, minute=0) + timedelta(days=1)
                                print(f"⚠️ 无法解析下一天日期，使用第八天0点: {end_dt}")
                        else:
                            # 使用第八天的0点
                            end_dt = start_dt.replace(hour=0, minute=0) + timedelta(days=1)
                            print(f"⚠️ 无法解析下一天时间，使用第八天0点: {end_dt}")
                    else:
                        # 使用第八天的0点
                        end_dt = start_dt.replace(hour=0, minute=0) + timedelta(days=1)
                        print(f"⚠️ 下一天无节目，使用第八天0点: {end_dt}")
                else:
                    # 第七天或最后一天，使用第八天的0点
                    end_dt = start_dt.replace(hour=0, minute=0) + timedelta(days=1)
                    print(f"ℹ️ 第七天最后一个节目，使用第八天0点: {end_dt}")
            
            end_time = end_dt.strftime("%Y%m%d%H%M00")
            
            # 创建programme元素
            programme_elem = SubElement(root, 'programme')
            programme_elem.set('start', start_time + ' +0800')  # 台北时区
            programme_elem.set('stop', end_time + ' +0800')
            programme_elem.set('channel', 'LS TIME 龙祥时代')
            
            # 添加标题 - 使用原始标题
            title_elem = SubElement(programme_elem, 'title')
            title_elem.text = program['title']
            title_elem.set('lang', 'zh')
            
            # 添加描述 - 优先从原始网页获取，失败则使用TMDB API
            desc_text = ""
            
            # 检查缓存中是否有电影信息
            cache_key = program['title']
            if cache_key in movie_cache:
                movie_info = movie_cache[cache_key]
                desc_text = movie_info.get('description', '')
                print(f"☑️ 使用缓存中的描述信息: {program['title']}")
            else:
                # 优先尝试从原始网页获取描述
                if program.get('link'):
                    description = get_movie_description_from_url(url=program['link'], original_title=program['title'])
                    if description:
                        desc_text = description
                        # 缓存结果
                        movie_cache[cache_key] = {'description': description, 'source': 'website'}
                    else:
                        # 如果原始网页没有描述，再尝试TMDB
                        if TMDB_API_KEY:
                            movie_info = search_tmdb_movie_direct(program['title'])
                            if movie_info and movie_info.get('overview'):
                                desc_text = movie_info['overview']
                                # 缓存结果
                                movie_cache[cache_key] = {'description': desc_text, 'source': 'tmdb'}
                        else:
                            print("⚠️ 未设置TMDB_API_KEY，跳过TMDB搜索")
                else:
                    print(f"⚠️ 电影 '{program['title']}' 没有详情链接，跳过获取描述")
            
            desc_elem = SubElement(programme_elem, 'desc')
            desc_elem.text = desc_text
            desc_elem.set('lang', 'zh')
            
            # 添加分类
            category_elem = SubElement(programme_elem, 'category')
            category_elem.text = '电影'
            category_elem.set('lang', 'zh')
            
            # 添加分级信息
            if program['rating']:
                rating_elem = SubElement(programme_elem, 'rating')
                rating_system = SubElement(rating_elem, 'system')
                rating_system.text = 'TW'
                rating_value = SubElement(rating_elem, 'value')
                rating_value.text = program['rating']
    
    return root

def prettify_xml(elem):
    """
    美化XML输出
    """
    rough_string = tostring(elem, encoding='utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ", encoding='utf-8')

def main():
    """
    主函数 - 从网站获取数据并生成XMLTV EPG
    """
    try:
        # 获取TMDB API Key
        if not TMDB_API_KEY:
            print("⚠️ 警告: 未找到TMDB_API_KEY环境变量，将只使用原始网页描述")
        
        # 获取网页内容
        url = "https://www.lstime.com.tw/schedule"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        print("ℹ️ 正在获取节目表数据...")
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        if response.status_code == 200:
            # 解析HTML
            schedule_data = parse_schedule_html(response.text)
            print(f"✅ 成功解析 {len(schedule_data)} 天的节目数据")
            
            # 生成XMLTV EPG
            xml_root = generate_xmltv_epg(schedule_data)
            
            # 美化XML并保存
            pretty_xml = prettify_xml(xml_root)
            
            # 保存到文件
            with open('lstime_epg.xml', 'wb') as f:
                f.write(pretty_xml)
            
            print("🎉 EPG文件已生成: lstime_epg.xml")
            
        else:
            print(f"❌ 获取网页失败，状态码: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 发生错误: {e}")

if __name__ == "__main__":
    main()