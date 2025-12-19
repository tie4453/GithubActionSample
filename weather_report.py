import os
import requests
import json
from bs4 import BeautifulSoup
import logging
import datetime
import time
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 配置信息类
@dataclass
class Config:
    """配置信息类，用于类型提示和验证"""
    APP_ID: str
    APP_SECRET: str
    OPEN_ID: str
    TEMPLATE_ID: str
    CITY: str = "吉安"
    
    @classmethod
    def from_env(cls) -> Optional['Config']:
        """从环境变量加载配置"""
        try:
            app_id = os.environ.get("APP_ID")
            app_secret = os.environ.get("APP_SECRET")
            open_id = os.environ.get("OPEN_ID")
            template_id = os.environ.get("TEMPLATE_ID")
            city = os.environ.get("CITY", "吉安")
            
            # 验证必要配置
            missing = []
            if not app_id:
                missing.append("APP_ID")
            if not app_secret:
                missing.append("APP_SECRET")
            if not open_id:
                missing.append("OPEN_ID")
            if not template_id:
                missing.append("TEMPLATE_ID")
                
            if missing:
                logger.error(f"缺少必要的环境变量: {', '.join(missing)}")
                return None
                
            return cls(
                APP_ID=app_id,
                APP_SECRET=app_secret,
                OPEN_ID=open_id,
                TEMPLATE_ID=template_id,
                CITY=city
            )
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            return None

# 天气信息类
@dataclass
class WeatherInfo:
    """天气信息数据类"""
    city: str
    temperature: str
    weather_type: str
    wind: str
    date: str = None
    
    def __post_init__(self):
        if not self.date:
            self.date = datetime.date.today().strftime("%Y年%m月%d日")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "city": self.city,
            "temperature": self.temperature,
            "weather_type": self.weather_type,
            "wind": self.wind,
            "date": self.date
        }

class WeatherFetcher:
    """天气获取器，封装天气数据获取逻辑"""
    
    # 中国天气网各区域URL
    WEATHER_URLS = [
        "http://www.weather.com.cn/textFC/hb.shtml",   # 华北
        "http://www.weather.com.cn/textFC/db.shtml",   # 东北
        "http://www.weather.com.cn/textFC/hd.shtml",   # 华东
        "http://www.weather.com.cn/textFC/hz.shtml",   # 华中
        "http://www.weather.com.cn/textFC/hn.shtml",   # 华南
        "http://www.weather.com.cn/textFC/xb.shtml",   # 西北
        "http://www.weather.com.cn/textFC/xn.shtml",   # 西南
        "http://www.weather.com.cn/textFC/gat.shtml",  # 港澳台
    ]
    
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'http://www.weather.com.cn/',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }
    
    @staticmethod
    def retry_request(url: str, max_retries: int = 3, timeout: int = 10) -> Optional[requests.Response]:
        """带重试的请求函数"""
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=WeatherFetcher.HEADERS, timeout=timeout)
                response.raise_for_status()
                # 检查编码
                if response.encoding.lower() in ('utf-8', 'gbk', 'gb2312'):
                    return response
                else:
                    response.encoding = 'utf-8'
                return response
            except requests.exceptions.Timeout:
                logger.warning(f"请求超时 ({attempt+1}/{max_retries}): {url}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # 指数退避
            except requests.exceptions.RequestException as e:
                logger.warning(f"请求失败 ({attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
        return None
    
    @classmethod
    def get_weather(cls, city_name: str) -> Optional[WeatherInfo]:
        """
        从中国天气网获取指定城市的天气信息
        
        Args:
            city_name (str): 要查询的城市名称
            
        Returns:
            WeatherInfo or None: 天气信息对象
        """
        logger.info(f"开始获取{city_name}的天气信息")
        
        for url in cls.WEATHER_URLS:
            try:
                logger.debug(f"尝试从 {url} 获取数据")
                response = cls.retry_request(url)
                if not response:
                    continue
                    
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # 尝试不同的选择器定位天气表格
                weather_tables = soup.find_all("div", class_="conMidtab")
                if not weather_tables:
                    # 备用选择器
                    weather_tables = soup.find_all("div", class_="conMidtab2")
                
                for table_div in weather_tables:
                    tables = table_div.find_all("table")
                    
                    for table in tables:
                        # 跳过表头行
                        rows = table.find_all("tr")[2:] if len(table.find_all("tr")) > 2 else table.find_all("tr")
                        
                        for row in rows:
                            cells = row.find_all("td")
                            if len(cells) < 8:  # 确保有足够的单元格
                                continue
                            
                            # 城市单元格通常是倒数第8个
                            city_cell = cells[-8] if len(cells) >= 8 else cells[0]
                            current_city = ''.join(city_cell.stripped_strings)
                            
                            # 模糊匹配城市名（支持简写）
                            if city_name in current_city or current_city in city_name:
                                try:
                                    # 提取天气数据
                                    high_temp = cls._extract_text(cells[-5]) if len(cells) >= 5 else '-'
                                    low_temp = cls._extract_text(cells[-2]) if len(cells) >= 2 else '-'
                                    weather_day = cls._extract_text(cells[-7]) if len(cells) >= 7 else '-'
                                    weather_night = cls._extract_text(cells[-4]) if len(cells) >= 4 else '-'
                                    
                                    # 处理风力信息
                                    wind_day_cell = cells[-6] if len(cells) >= 6 else None
                                    wind_night_cell = cells[-3] if len(cells) >= 3 else None
                                    
                                    wind_day = cls._extract_wind(wind_day_cell)
                                    wind_night = cls._extract_wind(wind_night_cell)
                                    
                                    # 构建返回结果
                                    if high_temp != '-' and low_temp != '-':
                                        temperature = f"{low_temp}~{high_temp}℃"
                                    elif low_temp != '-':
                                        temperature = f"{low_temp}℃"
                                    elif high_temp != '-':
                                        temperature = f"{high_temp}℃"
                                    else:
                                        temperature = "暂无数据"
                                    
                                    # 选择白天天气或夜间天气
                                    weather_type = weather_day if weather_day != '-' else weather_night
                                    if weather_type == '-':
                                        weather_type = "暂无数据"
                                    
                                    # 选择风力信息
                                    wind = wind_day if wind_day and wind_day != '--' else wind_night
                                    if not wind or wind == '--':
                                        wind = "暂无数据"
                                    
                                    logger.info(f"成功获取{city_name}天气: {weather_type}, {temperature}")
                                    return WeatherInfo(
                                        city=current_city,
                                        temperature=temperature,
                                        weather_type=weather_type,
                                        wind=wind
                                    )
                                    
                                except (IndexError, AttributeError, ValueError) as e:
                                    logger.warning(f"解析{city_name}天气数据时出错: {e}")
                                    continue
                
            except Exception as e:
                logger.error(f"处理URL {url} 时出错: {e}")
                continue
        
        logger.error(f"在所有天气页面中未找到城市: {city_name}")
        return None
    
    @staticmethod
    def _extract_text(element) -> str:
        """从BeautifulSoup元素中提取文本"""
        if not element:
            return '-'
        text = ''.join(element.stripped_strings)
        return text if text else '-'
    
    @staticmethod
    def _extract_wind(element) -> str:
        """提取风力信息"""
        if not element:
            return '--'
        wind_parts = list(element.stripped_strings)
        if len(wind_parts) >= 2:
            return f"{wind_parts[0]}{wind_parts[1]}"
        elif len(wind_parts) == 1:
            return wind_parts[0]
        else:
            return '--'


class WeChatAPI:
    """微信API封装类"""
    
    BASE_URL = "https://api.weixin.qq.com/cgi-bin"
    
    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self._access_token = None
        self._token_expire_time = 0
        
    def get_access_token(self, force_refresh: bool = False) -> Optional[str]:
        """
        获取微信公众号access_token（带缓存）
        
        Args:
            force_refresh (bool): 是否强制刷新token
            
        Returns:
            str or None: access_token
        """
        # 检查缓存，token有效期通常为7200秒，这里设置为7000秒
        if not force_refresh and self._access_token and time.time() < self._token_expire_time:
            logger.debug("使用缓存的access_token")
            return self._access_token
        
        try:
            url = f"{self.BASE_URL}/token"
            params = {
                "grant_type": "client_credential",
                "appid": self.app_id,
                "secret": self.app_secret
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if 'access_token' in result:
                self._access_token = result['access_token']
                # 设置过期时间（提前5分钟过期）
                self._token_expire_time = time.time() + result.get('expires_in', 7200) - 300
                logger.info("获取access_token成功")
                return self._access_token
            else:
                error_msg = result.get('errmsg', '未知错误')
                logger.error(f"获取access_token失败: {error_msg} (错误码: {result.get('errcode')})")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"请求access_token失败: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"解析access_token响应失败: {e}")
            return None
        except Exception as e:
            logger.error(f"获取access_token时发生未知错误: {e}")
            return None
    
    def send_template_message(self, open_id: str, template_id: str, 
                            weather_info: WeatherInfo, daily_note: str) -> bool:
        """
        发送模板消息
        
        Args:
            open_id (str): 用户OpenID
            template_id (str): 模板ID
            weather_info (WeatherInfo): 天气信息
            daily_note (str): 每日情话
            
        Returns:
            bool: 是否发送成功
        """
        try:
            access_token = self.get_access_token()
            if not access_token:
                logger.error("无法获取有效的access_token")
                return False
            
            # 构建消息数据
            message_data = {
                "touser": open_id,
                "template_id": template_id,
                "url": "https://mp.weixin.qq.com",
                "data": {
                    "date": {
                        "value": weather_info.date,
                        "color": "#173177"
                    },
                    "region": {
                        "value": weather_info.city,
                        "color": "#173177"
                    },
                    "weather": {
                        "value": weather_info.weather_type,
                        "color": "#173177"
                    },
                    "temp": {
                        "value": weather_info.temperature,
                        "color": "#FF0000"  # 温度用红色突出
                    },
                    "wind_dir": {
                        "value": weather_info.wind,
                        "color": "#173177"
                    },
                    "today_note": {
                        "value": daily_note,
                        "color": "#FF69B4"  # 情话用粉色
                    }
                }
            }
            
            url = f"{self.BASE_URL}/message/template/send"
            params = {"access_token": access_token}
            
            response = requests.post(url, params=params, json=message_data, timeout=15)
            response.raise_for_status()
            result = response.json()
            
            if result.get('errcode') == 0:
                logger.info(f"模板消息发送成功 (消息ID: {result.get('msgid')})")
                return True
            else:
                error_msg = result.get('errmsg', '未知错误')
                error_code = result.get('errcode')
                logger.error(f"发送模板消息失败: {error_msg} (错误码: {error_code})")
                
                # 如果token过期，强制刷新后重试一次
                if error_code in [40001, 40014, 42001]:
                    logger.warning("access_token可能已过期，尝试刷新后重试")
                    access_token = self.get_access_token(force_refresh=True)
                    if access_token:
                        return self.send_template_message(open_id, template_id, weather_info, daily_note)
                
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"发送模板消息请求失败: {e}")
            return False
        except Exception as e:
            logger.error(f"发送模板消息时发生未知错误: {e}")
            return False


class DailyService:
    """每日服务类，整合各种服务"""
    
    @staticmethod
    def get_daily_love(backup_message: str = "每天都要开心哦！") -> str:
        """
        获取每日情话，支持多个备用源
        
        Args:
            backup_message (str): 备用情话
            
        Returns:
            str: 情话内容
        """
        # 多个情话API源
        love_apis = [
            {
                'url': "https://api.lovelive.tools/api/SweetNothings/Serialization/Json",
                'parser': lambda data: data.get('returnObj', [])[0] if data.get('returnObj', []) else None
            },
            {
                'url': "https://v1.hitokoto.cn/",
                'parser': lambda data: data.get('hitokoto', '') + f" ——{data.get('from', '')}"
            },
            {
                'url': "https://api.shadiao.pro/chp",
                'parser': lambda data: data.get('data', {}).get('text', '') if data.get('data') else None
            }
        ]
        
        for api in love_apis:
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'application/json'
                }
                
                response = requests.get(api['url'], headers=headers, timeout=5)
                response.raise_for_status()
                data = response.json()
                
                sentence = api['parser'](data)
                if sentence and len(sentence.strip()) > 0:
                    # 清理和截断过长的句子
                    sentence = sentence.strip()
                    if len(sentence) > 50:
                        sentence = sentence[:47] + "..."
                    logger.info(f"成功获取情话: {sentence}")
                    return sentence
                    
            except Exception as e:
                logger.debug(f"情话API {api['url']} 失败: {e}")
                continue
        
        logger.warning("所有情话API都失败，使用备用情话")
        return backup_message
    
    @staticmethod
    def get_random_tip() -> str:
        """获取随机小贴士"""
        tips = [
            "记得多喝水，保持身体水分~",
            "出门记得带伞，有备无患哦！",
            "天气变化大，注意增减衣物~",
            "今天也要保持好心情呀！",
            "记得按时吃饭，身体最重要~",
            "工作学习之余，记得休息眼睛~"
        ]
        import random
        return random.choice(tips)


def main():
    """主函数"""
    try:
        logger.info("=" * 50)
        logger.info("开始执行天气预报推送任务")
        logger.info(f"执行时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 50)
        
        # 1. 加载配置
        config = Config.from_env()
        if not config:
            logger.error("配置加载失败，程序退出")
            return False
        
        logger.info(f"配置加载成功，城市: {config.CITY}")
        
        # 2. 获取天气信息
        weather_info = WeatherFetcher.get_weather(config.CITY)
        if not weather_info:
            logger.error("获取天气信息失败，程序退出")
            return False
        
        logger.info(f"天气信息获取成功: {weather_info}")
        
        # 3. 获取每日情话
        daily_love = DailyService.get_daily_love()
        logger.info(f"每日情话: {daily_love}")
        
        # 4. 初始化微信API并发送消息
        wechat = WeChatAPI(config.APP_ID, config.APP_SECRET)
        
        success = wechat.send_template_message(
            open_id=config.OPEN_ID,
            template_id=config.TEMPLATE_ID,
            weather_info=weather_info,
            daily_note=daily_love
        )
        
        if success:
            logger.info("天气预报推送任务执行成功！")
        else:
            logger.error("天气预报推送任务执行失败！")
        
        return success
        
    except KeyboardInterrupt:
        logger.info("用户中断执行")
        return False
    except Exception as e:
        logger.error(f"主程序发生未预期的错误: {e}", exc_info=True)
        return False
    finally:
        logger.info("=" * 50)
        logger.info("天气预报推送任务执行结束")
        logger.info("=" * 50)


if __name__ == '__main__':
    # 设置详细日志级别（生产环境可以调整为INFO）
    if os.environ.get('DEBUG', '').lower() in ('true', '1', 'yes'):
        logger.setLevel(logging.DEBUG)
    
    success = main()
    exit_code = 0 if success else 1
    exit(exit_code)
