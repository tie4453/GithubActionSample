import os
import requests
import json
from bs4 import BeautifulSoup
import logging
import datetime
from typing import Optional, Tuple, Dict, Any, List
from dataclasses import dataclass
import time
import re
from enum import Enum

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 配置信息
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
        missing_fields = [field for field in required_fields if not getattr(self, field)]
        
        if missing_fields:
            logger.error(f"缺少必要的配置项: {', '.join(missing_fields)}")
            return False
        
        if not self.CITY:
            logger.error("未配置城市信息")
            return False
        
        return True

config = Config()

# 天气信息数据类
@dataclass
class WeatherInfo:
    """天气信息数据类"""
    city: str
    date: str
    week: str
    temperature: str  # 温度范围
    current_temp: str  # 当前温度
    weather: str  # 天气状况
    weather_desc: str  # 天气描述
    wind_direction: str  # 风向
    wind_force: str  # 风力等级
    wind_speed: str  # 风速
    humidity: str  # 湿度
    pressure: str  # 气压
    visibility: str  # 能见度
    uv_index: str  # 紫外线指数
    uv_desc: str  # 紫外线描述
    aqi: str  # 空气质量指数
    aqi_desc: str  # 空气质量描述
    comfort: str  # 舒适度指数
    dressing: str  # 穿衣指数
    car_washing: str  # 洗车指数
    cold_risk: str  # 感冒风险
    sunrise: str  # 日出时间
    sunset: str  # 日落时间
    update_time: str  # 更新时间
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "city": self.city,
            "date": self.date,
            "week": self.week,
            "temperature": self.temperature,
            "current_temp": self.current_temp,
            "weather": self.weather,
            "weather_desc": self.weather_desc,
            "wind_direction": self.wind_direction,
            "wind_force": self.wind_force,
            "wind_speed": self.wind_speed,
            "humidity": self.humidity,
            "pressure": self.pressure,
            "visibility": self.visibility,
            "uv_index": self.uv_index,
            "uv_desc": self.uv_desc,
            "aqi": self.aqi,
            "aqi_desc": self.aqi_desc,
            "comfort": self.comfort,
            "dressing": self.dressing,
            "car_washing": self.car_washing,
            "cold_risk": self.cold_risk,
            "sunrise": self.sunrise,
            "sunset": self.sunset,
            "update_time": self.update_time
        }

class WeatherService:
    """天气服务类"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
        }
        
        # 省份简称映射（用于搜索）
        self.province_short = {
            '北京': 'bj', '上海': 'sh', '天津': 'tj', '重庆': 'cq',
            '河北': 'hb', '山西': 'sx', '辽宁': 'ln', '吉林': 'jl',
            '黑龙江': 'hlj', '江苏': 'js', '浙江': 'zj', '安徽': 'ah',
            '福建': 'fj', '江西': 'jx', '山东': 'sd', '河南': 'ha',
            '湖北': 'hb', '湖南': 'hn', '广东': 'gd', '海南': 'hn',
            '四川': 'sc', '贵州': 'gz', '云南': 'yn', '陕西': 'sn',
            '甘肃': 'gs', '青海': 'qh', '台湾': 'tw', '内蒙古': 'nm',
            '广西': 'gx', '西藏': 'xz', '宁夏': 'nx', '新疆': 'xj',
            '香港': 'hk', '澳门': 'mo'
        }
    
    def get_weather_by_api(self, city: str) -> Optional[WeatherInfo]:
        """
        通过天气API获取详细天气信息（使用心知天气API示例，需要自行申请key）
        注意：这里使用免费API，实际使用时需要注册获取API_KEY
        """
        try:
            # 这里使用公开的API，实际使用时建议使用正规天气API服务
            # 示例：心知天气API
            api_key = os.environ.get("WEATHER_API_KEY", "your_api_key_here")
            
            # 获取城市ID（需要先调用城市搜索API）
            city_search_url = f"https://api.seniverse.com/v3/location/search.json?key={api_key}&q={city}"
            city_response = requests.get(city_search_url, timeout=config.REQUEST_TIMEOUT)
            
            if city_response.status_code == 200:
                city_data = city_response.json()
                if city_data and len(city_data) > 0:
                    city_id = city_data[0]['id']
                    
                    # 获取实时天气
                    weather_url = f"https://api.seniverse.com/v3/weather/now.json?key={api_key}&location={city_id}&language=zh-Hans&unit=c"
                    weather_response = requests.get(weather_url, timeout=config.REQUEST_TIMEOUT)
                    
                    if weather_response.status_code == 200:
                        weather_data = weather_response.json()
                        # 处理天气数据...
                        pass
            
            return None
            
        except Exception as e:
            logger.error(f"API获取天气失败: {e}")
            return None
    
    def get_weather_by_web(self, city: str) -> Optional[WeatherInfo]:
        """
        从中国天气网获取详细天气信息
        """
        try:
            # 构建城市页面URL（需要先找到城市代码）
            city_code = self._get_city_code(city)
            if not city_code:
                logger.error(f"未找到城市代码: {city}")
                return None
            
            # 获取城市详细天气页面
            url = f"http://www.weather.com.cn/weather/{city_code}.shtml"
            logger.info(f"正在获取天气数据: {url}")
            
            response = requests.get(url, headers=self.headers, timeout=config.REQUEST_TIMEOUT)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                logger.error(f"请求失败: {response.status_code}")
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 获取今天日期和星期
            today = datetime.date.today()
            today_str = today.strftime("%Y年%m月%d日")
            weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
            week = weekdays[today.weekday()]
            
            # 解析天气信息
            weather_info = self._parse_weather_page(soup, city, today_str, week)
            
            # 获取生活指数
            life_index = self._get_life_index(city_code)
            if life_index:
                weather_info.comfort = life_index.get('comfort', '舒适')
                weather_info.dressing = life_index.get('dressing', '舒适')
                weather_info.car_washing = life_index.get('car_washing', '适宜')
                weather_info.cold_risk = life_index.get('cold_risk', '少发')
            
            # 获取空气质量
            aqi_info = self._get_aqi_info(city)
            if aqi_info:
                weather_info.aqi = aqi_info.get('aqi', '--')
                weather_info.aqi_desc = aqi_info.get('level', '未知')
            
            weather_info.update_time = datetime.datetime.now().strftime("%H:%M:%S")
            
            return weather_info
            
        except Exception as e:
            logger.error(f"网页获取天气失败: {e}", exc_info=True)
            return None
    
    def _get_city_code(self, city: str) -> Optional[str]:
        """获取城市代码"""
        # 简化的城市代码映射表（实际应该从数据库或文件加载）
        city_codes = {
            "北京": "101010100", "上海": "101020100", "广州": "101280101",
            "深圳": "101280601", "杭州": "101210101", "南京": "101190101",
            "苏州": "101190401", "武汉": "101200101", "成都": "101270101",
            "重庆": "101040100", "天津": "101030100", "西安": "101110101",
            "郑州": "101180101", "长沙": "101250101", "沈阳": "101070101",
            "青岛": "101120201", "大连": "101070201", "济南": "101120101",
            "厦门": "101230201", "福州": "101230101", "合肥": "101220101",
            "石家庄": "101090101", "太原": "101100101", "长春": "101060101",
            "哈尔滨": "101050101", "南昌": "101240101", "南宁": "101300101",
            "海口": "101310101", "贵阳": "101260101", "昆明": "101290101",
            "兰州": "101160101", "西宁": "101150101", "银川": "101170101",
            "乌鲁木齐": "101130101", "拉萨": "101140101", "呼和浩特": "101080101",
            "香港": "101320101", "澳门": "101330101", "台北": "101340101",
            "吉安": "101240601",  # 吉安的代码
        }
        
        # 精确匹配
        if city in city_codes:
            return city_codes[city]
        
        # 尝试模糊匹配
        for city_name, code in city_codes.items():
            if city in city_name or city_name in city:
                return code
        
        # 如果找不到，尝试搜索
        logger.warning(f"未在映射表中找到城市代码: {city}, 尝试搜索...")
        return self._search_city_code(city)
    
    def _search_city_code(self, city: str) -> Optional[str]:
        """搜索城市代码"""
        try:
            search_url = f"http://toy1.weather.com.cn/search?cityname={city}"
            response = requests.get(search_url, headers=self.headers, timeout=5)
            response.encoding = 'utf-8'
            
            if response.status_code == 200:
                # 返回格式通常是：~101240601~，需要解析
                content = response.text
                pattern = r'~(\d+)~'
                matches = re.findall(pattern, content)
                if matches:
                    return matches[0]
        except Exception as e:
            logger.error(f"搜索城市代码失败: {e}")
        
        return None
    
    def _parse_weather_page(self, soup: BeautifulSoup, city: str, date: str, week: str) -> WeatherInfo:
        """解析天气页面"""
        try:
            # 获取今天天气信息
            today_div = soup.find('div', id='today')
            
            # 温度信息
            temp_div = today_div.find('div', class_='tem') if today_div else None
            temperature = "未知"
            current_temp = "未知"
            
            if temp_div:
                temp_span = temp_div.find('span')
                temp_i = temp_div.find('i')
                if temp_span and temp_i:
                    high_temp = temp_span.get_text(strip=True)  # 最高温
                    low_temp = temp_i.get_text(strip=True)  # 最低温
                    temperature = f"{low_temp}~{high_temp}℃"
                    
                    # 尝试获取当前温度（可能在em标签中）
                    temp_em = temp_div.find('em')
                    if temp_em:
                        current_temp = temp_em.get_text(strip=True) + "℃"
            
            # 天气状况
            weather_div = today_div.find('div', class_='wea') if today_div else None
            weather = "未知"
            weather_desc = "未知"
            
            if weather_div:
                weather = weather_div.get_text(strip=True)
                # 获取更详细的天气描述（可能在父元素中）
                parent_div = weather_div.parent
                if parent_div:
                    wea_text = parent_div.get_text(" ", strip=True)
                    parts = wea_text.split()
                    if len(parts) > 1:
                        weather_desc = parts[1] if len(parts) > 1 else weather
            
            # 风力风向
            win_div = today_div.find('div', class_='win') if today_div else None
            wind_direction = "未知"
            wind_force = "未知"
            wind_speed = "未知"
            
            if win_div:
                # 风向
                wind_direction_span = win_div.find('span')
                if wind_direction_span:
                    wind_direction = wind_direction_span.get('title', '未知')
                
                # 风力和风速
                win_text = win_div.get_text(" ", strip=True)
                # 尝试提取风力等级（如：<3级）
                force_match = re.search(r'[<≤]?(\d+)[\-~]?(\d+)?级', win_text)
                if force_match:
                    if force_match.group(2):
                        wind_force = f"{force_match.group(1)}-{force_match.group(2)}级"
                    else:
                        wind_force = f"{force_match.group(1)}级"
                
                # 尝试提取风速
                speed_match = re.search(r'(\d+)(\.\d+)?米/秒', win_text)
                if speed_match:
                    wind_speed = f"{speed_match.group()}"
            
            # 湿度、气压、能见度（可能在详细信息的div中）
            details_div = soup.find('div', class_='livezs')
            humidity = "未知"
            pressure = "未知"
            visibility = "未知"
            sunrise = "未知"
            sunset = "未知"
            
            if details_div:
                # 查找湿度
                humidity_li = details_div.find('li', text=re.compile(r'湿度'))
                if humidity_li:
                    humidity_text = humidity_li.get_text(strip=True)
                    humidity_match = re.search(r'(\d+)%', humidity_text)
                    if humidity_match:
                        humidity = f"{humidity_match.group(1)}%"
                
                # 查找气压
                pressure_li = details_div.find('li', text=re.compile(r'气压'))
                if pressure_li:
                    pressure_text = pressure_li.get_text(strip=True)
                    pressure_match = re.search(r'(\d+)\s*hPa', pressure_text)
                    if pressure_match:
                        pressure = f"{pressure_match.group(1)}hPa"
                
                # 查找能见度
                visibility_li = details_div.find('li', text=re.compile(r'能见度'))
                if visibility_li:
                    visibility_text = visibility_li.get_text(strip=True)
                    visibility_match = re.search(r'(\d+)\s*公里', visibility_text)
                    if visibility_match:
                        visibility = f"{visibility_match.group(1)}公里"
                
                # 查找日出日落
                sun_li = details_div.find('li', text=re.compile(r'日出'))
                if sun_li:
                    sun_text = sun_li.get_text(strip=True)
                    sun_match = re.search(r'日出\s*(\d+:\d+).*日落\s*(\d+:\d+)', sun_text)
                    if sun_match:
                        sunrise = sun_match.group(1)
                        sunset = sun_match.group(2)
            
            # 紫外线指数
            uv_index = "未知"
            uv_desc = "未知"
            uv_div = details_div.find('li', text=re.compile(r'紫外线')) if details_div else None
            if uv_div:
                uv_text = uv_div.get_text(strip=True)
                uv_match = re.search(r'紫外线\s*(\d+)\s*([弱低中高强]+)', uv_text)
                if uv_match:
                    uv_index = uv_match.group(1)
                    uv_desc = uv_match.group(2)
            
            return WeatherInfo(
                city=city,
                date=date,
                week=week,
                temperature=temperature,
                current_temp=current_temp,
                weather=weather,
                weather_desc=weather_desc,
                wind_direction=wind_direction,
                wind_force=wind_force,
                wind_speed=wind_speed,
                humidity=humidity,
                pressure=pressure,
                visibility=visibility,
                uv_index=uv_index,
                uv_desc=uv_desc,
                aqi="--",
                aqi_desc="未知",
                comfort="舒适",
                dressing="舒适",
                car_washing="适宜",
                cold_risk="少发",
                sunrise=sunrise,
                sunset=sunset,
                update_time=""
            )
            
        except Exception as e:
            logger.error(f"解析天气页面失败: {e}")
            # 返回基础信息
            return WeatherInfo(
                city=city,
                date=date,
                week=week,
                temperature="未知",
                current_temp="未知",
                weather="未知",
                weather_desc="未知",
                wind_direction="未知",
                wind_force="未知",
                wind_speed="未知",
                humidity="未知",
                pressure="未知",
                visibility="未知",
                uv_index="未知",
                uv_desc="未知",
                aqi="--",
                aqi_desc="未知",
                comfort="舒适",
                dressing="舒适",
                car_washing="适宜",
                cold_risk="少发",
                sunrise="未知",
                sunset="未知",
                update_time=""
            )
    
    def _get_life_index(self, city_code: str) -> Dict[str, str]:
        """获取生活指数"""
        try:
            url = f"http://www.weather.com.cn/weather1d/{city_code}.shtml"
            response = requests.get(url, headers=self.headers, timeout=5)
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            life_index_div = soup.find('div', class_='live_index')
            if not life_index_div:
                return {}
            
            indices = {}
            index_items = life_index_div.find_all('li')
            
            for item in index_items:
                text = item.get_text(strip=True)
                if '舒适度' in text:
                    indices['comfort'] = self._extract_index_level(text)
                elif '穿衣' in text:
                    indices['dressing'] = self._extract_index_level(text)
                elif '洗车' in text:
                    indices['car_washing'] = self._extract_index_level(text)
                elif '感冒' in text:
                    indices['cold_risk'] = self._extract_index_level(text)
            
            return indices
            
        except Exception as e:
            logger.error(f"获取生活指数失败: {e}")
            return {}
    
    def _extract_index_level(self, text: str) -> str:
        """提取指数等级"""
        levels = ["适宜", "较适宜", "适宜", "不太适宜", "不适宜", 
                  "舒适", "较舒适", "不舒适", "极易发", "易发", "较易发", "少发"]
        
        for level in levels:
            if level in text:
                return level
        
        # 提取括号中的内容
        match = re.search(r'[（(]([^）)]+)[）)]', text)
        if match:
            return match.group(1)
        
        return "未知"
    
    def _get_aqi_info(self, city: str) -> Dict[str, str]:
        """获取空气质量信息"""
        try:
            # 尝试从中国天气网获取AQI
            url = f"http://www.weather.com.cn/air/?city={city}"
            response = requests.get(url, headers=self.headers, timeout=5)
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            aqi_div = soup.find('div', class_='level')
            if not aqi_div:
                return {}
            
            aqi_text = aqi_div.get_text(strip=True)
            aqi_match = re.search(r'(\d+)', aqi_text)
            
            if aqi_match:
                aqi_value = int(aqi_match.group(1))
                aqi_level = self._get_aqi_level(aqi_value)
                
                return {
                    'aqi': str(aqi_value),
                    'level': aqi_level
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"获取空气质量信息失败: {e}")
            return {}
    
    def _get_aqi_level(self, aqi: int) -> str:
        """根据AQI值获取空气质量等级"""
        if aqi <= 50:
            return "优"
        elif aqi <= 100:
            return "良"
        elif aqi <= 150:
            return "轻度污染"
        elif aqi <= 200:
            return "中度污染"
        elif aqi <= 300:
            return "重度污染"
        else:
            return "严重污染"
    
    def get_weather(self, city: str) -> Optional[WeatherInfo]:
        """获取天气信息（主入口）"""
        logger.info(f"开始获取{city}的详细天气信息")
        
        # 优先使用网页方式获取
        weather_info = self.get_weather_by_web(city)
        
        if not weather_info:
            logger.warning("网页获取失败，尝试API方式")
            weather_info = self.get_weather_by_api(city)
        
        if weather_info:
            logger.info(f"成功获取{city}天气信息")
            logger.info(f"温度: {weather_info.temperature}, 天气: {weather_info.weather}")
            logger.info(f"风力: {weather_info.wind_force} {weather_info.wind_direction}")
            logger.info(f"湿度: {weather_info.humidity}, 气压: {weather_info.pressure}")
            
        return weather_info

class MessageBuilder:
    """消息构建器"""
    
    @staticmethod
    def build_wechat_message(weather_info: WeatherInfo, inspiration: str) -> Dict[str, Any]:
        """构建微信消息"""
        # 准备详细天气描述
        weather_details = f"""
{weather_info.weather_desc}
温度：{weather_info.current_temp}（{weather_info.temperature}）
湿度：{weather_info.humidity}
气压：{weather_info.pressure}
风向：{weather_info.wind_direction}
风力：{weather_info.wind_force}
风速：{weather_info.wind_speed}
能见度：{weather_info.visibility}
紫外线：{weather_info.uv_index}（{weather_info.uv_desc}）
空气质量：{weather_info.aqi}（{weather_info.aqi_desc}）
日出/日落：{weather_info.sunrise}/{weather_info.sunset}
        """.strip()
        
        # 生活指数提示
        life_tips = f"""
👕 穿衣指数：{weather_info.dressing}
🚗 洗车指数：{weather_info.car_washing}
😷 感冒风险：{weather_info.cold_risk}
😊 舒适度：{weather_info.comfort}
        """.strip()
        
        # 今日寄语
        today_note = f"{inspiration}\n\n{life_tips}"
        
        return {
            "touser": config.OPEN_ID,
            "template_id": config.TEMPLATE_ID,
            "url": "https://mp.weixin.qq.com",
            "data": {
                "date": {
                    "value": f"{weather_info.date} {weather_info.week}",
                    "color": "#173177"
                },
                "region": {
                    "value": weather_info.city,
                    "color": "#173177"
                },
                "weather": {
                    "value": weather_info.weather,
                    "color": "#173177"
                },
                "temp": {
                    "value": weather_info.temperature,
                    "color": "#FF0000"
                },
                "current_temp": {
                    "value": weather_info.current_temp,
                    "color": "#FF4500"
                },
                "wind_info": {
                    "value": f"{weather_info.wind_direction} {weather_info.wind_force}",
                    "color": "#4169E1"
                },
                "humidity": {
                    "value": weather_info.humidity,
                    "color": "#1E90FF"
                },
                "pressure": {
                    "value": weather_info.pressure,
                    "color": "#4682B4"
                },
                "uv_index": {
                    "value": f"{weather_info.uv_index} ({weather_info.uv_desc})",
                    "color": "#FF8C00"
                },
                "aqi": {
                    "value": f"{weather_info.aqi} ({weather_info.aqi_desc})",
                    "color": self._get_aqi_color(weather_info.aqi_desc)
                },
                "weather_details": {
                    "value": weather_details,
                    "color": "#2E8B57"
                },
                "life_index": {
                    "value": life_tips,
                    "color": "#8B4513"
                },
                "today_note": {
                    "value": today_note,
                    "color": "#FF69B4"
                },
                "sun_info": {
                    "value": f"日出: {weather_info.sunrise} 日落: {weather_info.sunset}",
                    "color": "#FFD700"
                },
                "update_time": {
                    "value": weather_info.update_time,
                    "color": "#808080"
                }
            }
        }
    
    @staticmethod
    def _get_aqi_color(aqi_desc: str) -> str:
        """根据空气质量获取颜色"""
        color_map = {
            "优": "#00FF00",
            "良": "#90EE90",
            "轻度污染": "#FFFF00",
            "中度污染": "#FFA500",
            "重度污染": "#FF4500",
            "严重污染": "#FF0000"
        }
        return color_map.get(aqi_desc, "#000000")

class InspirationService:
    """激励语服务"""
    
    @staticmethod
    def get_inspiration() -> str:
        """获取每日激励语"""
        try:
            # 多个API源
            apis = [
                {
                    'url': 'https://api.lovelive.tools/api/SweetNothings/Serialization/Json',
                    'parser': lambda data: data.get('returnObj', [])[0] if data.get('returnObj', []) else ""
                },
                {
                    'url': 'https://v1.hitokoto.cn/?c=a&c=b&c=c&c=d&c=e&c=f&c=g&c=h&c=i&c=j&c=k&c=l',
                    'parser': lambda data: f"{data.get('hitokoto', '')} ——{data.get('from', '')}"
                }
            ]
            
            for api in apis:
                try:
                    response = requests.get(api['url'], timeout=5)
                    response.raise_for_status()
                    data = response.json()
                    inspiration = api['parser'](data)
                    
                    if inspiration and len(inspiration.strip()) > 5:
                        return inspiration.strip()
                        
                except Exception:
                    continue
            
            # 如果API都失败，使用本地库
            return InspirationService.get_local_inspiration()
            
        except Exception as e:
            logger.error(f"获取激励语失败: {e}")
            return InspirationService.get_local_inspiration()
    
    @staticmethod
    def get_local_inspiration() -> str:
        """获取本地激励语"""
        inspirations = [
            "生活不是等待风暴过去，而是学会在雨中跳舞。",
            "每一天都是新的开始，微笑面对，好运自然来。",
            "保持热爱，奔赴山海，忠于自己，热爱生活。",
            "心若向阳，无畏悲伤，眼中有光，心中有爱。",
            "努力成为更好的自己，比仰望别人更有意义。",
            "生活总会给你答案，但不会马上告诉你一切。",
            "把平凡的日子过成诗，简单的生活过成画。",
            "愿你眼中总有光芒，活成自己想要的模样。",
            "不为模糊的未来担忧，只为清楚的现在努力。",
            "生活就是一边失去，一边拥有，一边选择，一边放弃。"
        ]
        
        # 使用日期作为索引，确保每天相同
        day_of_year = datetime.date.today().timetuple().tm_yday
        return inspirations[day_of_year % len(inspirations)]

def get_access_token():
    """获取微信access_token"""
    try:
        url = f'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={config.APP_ID}&secret={config.APP_SECRET}'
        response = requests.get(url, timeout=config.REQUEST_TIMEOUT)
        response.raise_for_status()
        result = response.json()
        
        if 'access_token' in result:
            logger.info("成功获取access_token")
            return result['access_token']
        else:
            logger.error(f"获取access_token失败: {result.get('errmsg', '未知错误')}")
            return None
            
    except Exception as e:
        logger.error(f"获取access_token失败: {e}")
        return None

def send_wechat_message(access_token: str, message_data: Dict[str, Any]) -> bool:
    """发送微信消息"""
    try:
        url = f'https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}'
        response = requests.post(url, json=message_data, timeout=config.REQUEST_TIMEOUT)
        response.raise_for_status()
        result = response.json()
        
        if result.get('errcode') == 0:
            logger.info("微信消息发送成功")
            return True
        else:
            logger.error(f"微信消息发送失败: {result.get('errmsg', '未知错误')}")
            return False
            
    except Exception as e:
        logger.error(f"发送微信消息失败: {e}")
        return False

def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("开始执行详细天气报告任务")
    
    try:
        # 1. 验证配置
        if not config.validate():
            logger.error("配置验证失败")
            return False
        
        logger.info(f"目标城市: {config.CITY}")
        
        # 2. 获取详细天气信息
        weather_service = WeatherService()
        weather_info = weather_service.get_weather(config.CITY)
        
        if not weather_info:
            logger.error("获取天气信息失败")
            return False
        
        logger.info(f"获取到详细天气信息:")
        logger.info(f"城市: {weather_info.city}")
        logger.info(f"温度: {weather_info.current_temp} ({weather_info.temperature})")
        logger.info(f"天气: {weather_info.weather}")
        logger.info(f"风向风力: {weather_info.wind_direction} {weather_info.wind_force}")
        logger.info(f"风速: {weather_info.wind_speed}")
        logger.info(f"湿度: {weather_info.humidity}")
        logger.info(f"气压: {weather_info.pressure}")
        logger.info(f"紫外线: {weather_info.uv_index} ({weather_info.uv_desc})")
        logger.info(f"空气质量: {weather_info.aqi} ({weather_info.aqi_desc})")
        
        # 3. 获取激励语
        inspiration = InspirationService.get_inspiration()
        logger.info(f"今日寄语: {inspiration[:30]}...")
        
        # 4. 构建微信消息
        message_builder = MessageBuilder()
        message_data = message_builder.build_wechat_message(weather_info, inspiration)
        
        # 5. 获取access_token
        access_token = get_access_token()
        if not access_token:
            logger.error("获取access_token失败")
            return False
        
        # 6. 发送消息
        success = send_wechat_message(access_token, message_data)
        
        if success:
            logger.info("天气报告任务执行成功！")
        else:
            logger.error("天气报告任务执行失败")
        
        return success
        
    except Exception as e:
        logger.error(f"任务执行失败: {e}", exc_info=True)
        return False
    finally:
        logger.info("任务执行结束")
        logger.info("=" * 60)

if __name__ == '__main__':
    main()
