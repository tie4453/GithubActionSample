import os
import requests
import json
from bs4 import BeautifulSoup
import logging
import datetime
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
import time
from urllib.parse import quote

# 配置日志 - 改进为更专业的配置
def setup_logging():
    """设置日志配置"""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    # 避免重复添加handler
    if not logger.handlers:
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 文件处理器（可选）
        file_handler = logging.FileHandler(
            filename=f'weather_report_{datetime.date.today().strftime("%Y%m%d")}.log',
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        
        # 格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    
    return logger

logger = setup_logging()

# 使用数据类存储配置
@dataclass
class Config:
    """配置信息类"""
    APP_ID: str = os.environ.get("APP_ID", "")
    APP_SECRET: str = os.environ.get("APP_SECRET", "")
    OPEN_ID: str = os.environ.get("OPEN_ID", "")
    TEMPLATE_ID: str = os.environ.get("TEMPLATE_ID", "")
    CITY: str = os.environ.get("CITY", "吉安")
    REQUEST_TIMEOUT: int = 10
    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 1.0
    
    def validate(self) -> bool:
        """验证配置是否完整"""
        required_fields = ["APP_ID", "APP_SECRET", "OPEN_ID", "TEMPLATE_ID"]
        missing_fields = []
        
        for field in required_fields:
            if not getattr(self, field):
                missing_fields.append(field)
        
        if missing_fields:
            logger.error(f"缺少必要的配置项: {', '.join(missing_fields)}")
            return False
        
        if not self.CITY:
            logger.error("未配置城市信息")
            return False
        
        return True

# 初始化配置
config = Config()

class WeatherFetcher:
    """天气信息获取器"""
    
    # 天气网站URL列表
    WEATHER_URLS = [
        "http://www.weather.com.cn/textFC/hb.shtml",  # 华北
        "http://www.weather.com.cn/textFC/db.shtml",  # 东北
        "http://www.weather.com.cn/textFC/hd.shtml",  # 华东
        "http://www.weather.com.cn/textFC/hz.shtml",  # 华中
        "http://www.weather.com.cn/textFC/hn.shtml",  # 华南
        "http://www.weather.com.cn/textFC/xb.shtml",  # 西北
        "http://www.weather.com.cn/textFC/xn.shtml",  # 西南
    ]
    
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    @staticmethod
    def _make_request(url: str, max_retries: int = 3) -> Optional[str]:
        """发送HTTP请求并返回响应内容"""
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    url, 
                    headers=WeatherFetcher.HEADERS, 
                    timeout=config.REQUEST_TIMEOUT
                )
                response.raise_for_status()
                response.encoding = 'utf-8'  # 确保编码正确
                return response.text
            except requests.exceptions.Timeout:
                logger.warning(f"请求超时 ({attempt + 1}/{max_retries}): {url}")
                if attempt < max_retries - 1:
                    time.sleep(config.RETRY_DELAY * (attempt + 1))
            except requests.exceptions.RequestException as e:
                logger.error(f"请求失败: {url}, 错误: {e}")
                if attempt < max_retries - 1:
                    time.sleep(config.RETRY_DELAY)
                else:
                    return None
        return None
    
    @classmethod
    def get_weather(cls, city: str) -> Optional[Tuple[str, str, str, str]]:
        """
        从中国天气网获取指定城市的天气信息
        
        Args:
            city (str): 要查询的城市名称
            
        Returns:
            Optional[Tuple]: (城市名, 温度, 天气类型, 风力) 或 None
        """
        logger.info(f"开始获取{city}的天气信息")
        
        for url in cls.WEATHER_URLS:
            try:
                logger.debug(f"尝试从 {url} 获取天气数据")
                html_content = cls._make_request(url)
                if not html_content:
                    continue
                    
                soup = BeautifulSoup(html_content, 'html.parser')
                div_conMidtab = soup.find("div", class_="conMidtab")
                
                if not div_conMidtab:
                    logger.debug(f"{url} 中未找到天气数据")
                    continue
                    
                tables = div_conMidtab.find_all("table")
                found_city = False
                
                for table in tables:
                    trs = table.find_all("tr")[2:]  # 跳过前两行标题行
                    for tr in trs:
                        try:
                            tds = tr.find_all("td")
                            if len(tds) < 8:  # 确保有足够的列
                                continue
                                
                            city_td = tds[-8]
                            this_city = next(city_td.stripped_strings, "")
                            
                            # 支持简写匹配（比如"北京"匹配"北京市"）
                            if city in this_city or this_city.startswith(city):
                                # 提取天气信息
                                high_temp = next(tds[-5].stripped_strings, "-")
                                low_temp = next(tds[-2].stripped_strings, "-")
                                weather_day = next(tds[-7].stripped_strings, "-")
                                weather_night = next(tds[-4].stripped_strings, "-")
                                
                                # 提取风向风速
                                wind_day_td = tds[-6]
                                wind_day_parts = list(wind_day_td.stripped_strings)
                                wind_day = "".join(wind_day_parts[:2]) if len(wind_day_parts) >= 2 else ""
                                
                                wind_night_td = tds[-3]
                                wind_night_parts = list(wind_night_td.stripped_strings)
                                wind_night = "".join(wind_night_parts[:2]) if len(wind_night_parts) >= 2 else ""
                                
                                # 格式化输出
                                if high_temp != "-" and low_temp != "-":
                                    temperature = f"{low_temp}~{high_temp}℃"
                                else:
                                    temperature = f"{low_temp if low_temp != '-' else '未知'}℃"
                                
                                weather_type = weather_day if weather_day != "-" else weather_night
                                wind = wind_day if wind_day else wind_night
                                
                                logger.info(f"成功获取{city}天气: {temperature}, {weather_type}, {wind}")
                                return (this_city, temperature, weather_type, wind)
                                
                        except (IndexError, StopIteration, AttributeError) as e:
                            logger.debug(f"解析表格行时出错: {e}")
                            continue
                
                if found_city:
                    break
                    
            except Exception as e:
                logger.error(f"处理 {url} 时出错: {e}", exc_info=True)
                continue
        
        logger.error(f"在所有天气页面中都未找到城市: {city}")
        return None

class WeChatAPI:
    """微信API接口类"""
    
    BASE_URL = "https://api.weixin.qq.com/cgi-bin"
    
    @staticmethod
    def get_access_token() -> Optional[str]:
        """
        获取微信公众号access_token
        
        Returns:
            str: access_token 或 None
        """
        try:
            if not config.APP_ID or not config.APP_SECRET:
                logger.error("APP_ID 或 APP_SECRET 未配置")
                return None
            
            url = f"{WeChatAPI.BASE_URL}/token"
            params = {
                'grant_type': 'client_credential',
                'appid': config.APP_ID,
                'secret': config.APP_SECRET
            }
            
            response = requests.get(url, params=params, timeout=config.REQUEST_TIMEOUT)
            response.raise_for_status()
            result = response.json()
            
            if 'access_token' in result:
                logger.info("成功获取access_token")
                return result['access_token']
            else:
                error_msg = result.get('errmsg', '未知错误')
                logger.error(f"获取access_token失败: {error_msg}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"请求access_token失败: {e}", exc_info=True)
            return None
        except json.JSONDecodeError as e:
            logger.error(f"解析access_token响应失败: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"获取access_token时发生未知错误: {e}", exc_info=True)
            return None
    
    @staticmethod
    def send_template_message(access_token: str, template_data: Dict[str, Any]) -> bool:
        """
        发送模板消息
        
        Args:
            access_token (str): 微信access_token
            template_data (Dict): 模板消息数据
            
        Returns:
            bool: 是否发送成功
        """
        try:
            url = f"{WeChatAPI.BASE_URL}/message/template/send"
            params = {'access_token': access_token}
            
            response = requests.post(
                url, 
                params=params, 
                json=template_data, 
                timeout=config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get('errcode') == 0:
                logger.info("模板消息发送成功")
                return True
            else:
                error_msg = result.get('errmsg', '未知错误')
                logger.error(f"发送模板消息失败: {error_msg}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"发送模板消息请求失败: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"发送模板消息时发生未知错误: {e}", exc_info=True)
            return False

class DailyInspiration:
    """每日激励语获取类"""
    
    APIS = [
        {
            'name': 'lovelive',
            'url': 'https://api.lovelive.tools/api/SweetNothings/Serialization/Json',
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json'
            },
            'parser': lambda data: data.get('returnObj', [])[0] if data.get('returnObj', []) else ""
        },
        {
            'name': 'fallback',
            'url': None,
            'parser': lambda data: get_fallback_inspiration()
        }
    ]
    
    @staticmethod
    def get_inspiration() -> str:
        """
        获取每日激励语
        
        Returns:
            str: 激励语内容
        """
        for api in DailyInspiration.APIS:
            try:
                if api['url'] is None:
                    return api['parser'](None)
                
                response = requests.get(
                    api['url'], 
                    headers=api['headers'], 
                    timeout=config.REQUEST_TIMEOUT
                )
                response.raise_for_status()
                data = response.json()
                
                sentence = api['parser'](data)
                if sentence and len(sentence) > 0:
                    logger.debug(f"从{api['name']}获取激励语成功")
                    return sentence.strip()
                    
            except Exception as e:
                logger.debug(f"从{api['name']}获取激励语失败: {e}")
                continue
        
        # 所有API都失败时使用备用
        return get_fallback_inspiration()

def get_fallback_inspiration() -> str:
    """获取备用激励语"""
    inspirations = [
        "每一天都是新的开始，加油！",
        "保持微笑，好运自然来！",
        "今天也要元气满满哦！",
        "愿你的一天充满阳光和欢笑！",
        "好事总会发生在下个转弯！",
        "保持热爱，奔赴山海！",
        "今天是你余生中最年轻的一天！",
        "坚持就是胜利！",
        "心若向阳，无畏悲伤！",
        "每天都要进步一点点！"
    ]
    
    # 使用日期作为种子，确保每天的消息相同（可选）
    today = datetime.date.today()
    seed = today.year * 10000 + today.month * 100 + today.day
    index = seed % len(inspirations)
    
    return inspirations[index]

def create_template_data(weather_info: Tuple[str, str, str, str]) -> Dict[str, Any]:
    """
    创建微信模板消息数据
    
    Args:
        weather_info (Tuple): 天气信息
        
    Returns:
        Dict: 模板消息数据
    """
    today = datetime.date.today()
    today_str = today.strftime("%Y年%m月%d日")
    weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][today.weekday()]
    
    city, temperature, weather_type, wind = weather_info
    
    return {
        "touser": config.OPEN_ID,
        "template_id": config.TEMPLATE_ID,
        "url": "https://mp.weixin.qq.com",
        "data": {
            "date": {
                "value": f"{today_str} {weekday}",
                "color": "#173177"
            },
            "region": {
                "value": city,
                "color": "#173177"
            },
            "weather": {
                "value": weather_type,
                "color": "#173177"
            },
            "temp": {
                "value": temperature,
                "color": "#FF0000"  # 温度用红色突出
            },
            "wind_dir": {
                "value": wind if wind else "微风",
                "color": "#173177"
            },
            "today_note": {
                "value": DailyInspiration.get_inspiration(),
                "color": "#FF69B4"  # 温馨的粉色
            },
            "update_time": {
                "value": datetime.datetime.now().strftime("%H:%M:%S"),
                "color": "#808080"
            }
        }
    }

def weather_report():
    """
    主函数，执行完整的天气报告流程
    """
    try:
        logger.info("=" * 50)
        logger.info("开始执行天气报告任务")
        
        # 1. 验证配置
        if not config.validate():
            logger.error("配置验证失败，任务终止")
            return False
        
        logger.info(f"配置验证通过，目标城市: {config.CITY}")
        
        # 2. 获取天气信息
        weather_info = WeatherFetcher.get_weather(config.CITY)
        if not weather_info:
            logger.error("无法获取天气信息，任务终止")
            return False
        
        logger.info(f"成功获取天气信息: {weather_info}")
        
        # 3. 获取access_token
        access_token = WeChatAPI.get_access_token()
        if not access_token:
            logger.error("无法获取access_token，任务终止")
            return False
        
        # 4. 准备并发送模板消息
        template_data = create_template_data(weather_info)
        success = WeChatAPI.send_template_message(access_token, template_data)
        
        if success:
            logger.info("天气报告任务执行成功！")
        else:
            logger.error("天气报告任务执行失败")
            
        return success
        
    except Exception as e:
        logger.error(f"天气报告任务执行过程中发生错误: {e}", exc_info=True)
        return False
    finally:
        logger.info("天气报告任务执行结束")
        logger.info("=" * 50)

if __name__ == '__main__':
    # 可以添加命令行参数支持
    import argparse
    
    parser = argparse.ArgumentParser(description='微信天气报告机器人')
    parser.add_argument('--city', type=str, help='指定城市名称', default=None)
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    
    args = parser.parse_args()
    
    # 如果命令行指定了城市，则覆盖配置
    if args.city:
        config.CITY = args.city
    
    # 设置调试模式
    if args.debug:
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)
    
    # 执行天气报告
    weather_report()
