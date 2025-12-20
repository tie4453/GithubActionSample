import os
import requests
import json
from bs4 import BeautifulSoup
import logging
import datetime
import time
from typing import Optional, Dict, Any, Tuple, List
from enum import Enum
import random
import hashlib

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 配置信息
class Config:
    """配置管理类"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self):
        """从环境变量加载配置"""
        self.APP_ID = os.environ.get("APP_ID", "")
        self.APP_SECRET = os.environ.get("APP_SECRET", "")
        self.OPEN_ID = os.environ.get("OPEN_ID", "")
        self.TEMPLATE_ID = os.environ.get("TEMPLATE_ID", "")
        
        # 城市配置，支持多个城市
        city_str = os.environ.get("CITIES", "吉安")
        self.CITIES = [city.strip() for city in city_str.split(",")]
        
        # 其他配置
        self.ENABLE_AQI = os.environ.get("ENABLE_AQI", "true").lower() == "true"
        self.ENABLE_LIFE_INDEX = os.environ.get("ENABLE_LIFE_INDEX", "true").lower() == "true"
        self.ENABLE_HOURLY_FORECAST = os.environ.get("ENABLE_HOURLY_FORECAST", "false").lower() == "true"
        
        # 检查必要配置
        self._validate_config()
    
    def _validate_config(self):
        """验证配置是否完整"""
        required_configs = ["APP_ID", "APP_SECRET", "OPEN_ID", "TEMPLATE_ID"]
        missing = []
        for key in required_configs:
            if not getattr(self, key, ""):
                missing.append(key)
        
        if missing:
            logger.warning(f"缺少必要的环境变量: {', '.join(missing)}")
            logger.warning("请设置以下环境变量:")
            for key in missing:
                logger.warning(f"  {key}")
        
        if not self.CITIES:
            logger.warning("未配置城市，使用默认城市: 吉安")
            self.CITIES = ["吉安"]

# 星期几枚举
class Weekday(Enum):
    MONDAY = "星期一"
    TUESDAY = "星期二"
    WEDNESDAY = "星期三"
    THURSDAY = "星期四"
    FRIDAY = "星期五"
    SATURDAY = "星期六"
    SUNDAY = "星期日"

def get_current_weekday() -> str:
    """获取当前星期几"""
    today = datetime.date.today()
    weekday_num = today.weekday()  # 0=周一, 6=周日
    return list(Weekday)[weekday_num].value

def get_date_info() -> Dict[str, str]:
    """获取日期相关信息"""
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    tomorrow = today + datetime.timedelta(days=1)
    
    # 农历转换（简化版，实际使用需要农历库）
    lunar_info = get_simple_lunar_date(today)
    
    return {
        "date": today.strftime("%Y年%m月%d日"),
        "weekday": get_current_weekday(),
        "yesterday": yesterday.strftime("%Y-%m-%d"),
        "tomorrow": tomorrow.strftime("%Y-%m-%d"),
        "lunar_date": lunar_info,
        "day_of_year": today.timetuple().tm_yday,
        "week_number": today.isocalendar()[1]
    }

def get_simple_lunar_date(date_obj: datetime.date) -> str:
    """获取简化的农历日期（实际使用时可接入农历库）"""
    # 这里返回一个占位符，实际可以使用lunarcalendar等库
    return "农历信息"

def get_extended_weather(city_name: str) -> Dict[str, Any]:
    """
    获取扩展的天气信息，包括更多实用数据
    
    Args:
        city_name: 城市名称
        
    Returns:
        包含扩展天气信息的字典
    """
    try:
        # 这里可以接入更多天气API，如和风天气、OpenWeather等
        # 当前仍使用中国天气网，但可以添加更多信息
        
        weather_data = get_weather_from_website(city_name)
        if not weather_data:
            return None
        
        # 添加更多计算的信息
        temp_range = weather_data.get("temperature", "0-0℃").replace("℃", "").split("-")
        if len(temp_range) == 2:
            try:
                low_temp = int(temp_range[0])
                high_temp = int(temp_range[1])
                
                # 计算温差
                temp_diff = high_temp - low_temp
                
                # 根据温度给出穿衣建议
                dressing_advice = get_dressing_advice(high_temp, low_temp)
                
                # 获取紫外线指数（模拟）
                uv_index = get_uv_index(weather_data.get("weather_type", ""))
                
                # 获取空气质量（模拟，实际可接入API）
                aqi_info = get_aqi_info(city_name)
                
                # 生活指数
                life_indices = get_life_indices(weather_data.get("weather_type", ""), 
                                              high_temp, low_temp)
                
                # 小时预报（简化版）
                hourly_forecast = get_hourly_forecast(weather_data.get("weather_type", ""))
                
                weather_data.update({
                    "temp_diff": f"{temp_diff}℃",
                    "dressing_advice": dressing_advice,
                    "uv_index": uv_index,
                    "aqi": aqi_info,
                    "life_indices": life_indices,
                    "hourly_forecast": hourly_forecast,
                    "update_time": datetime.datetime.now().strftime("%H:%M")
                })
                
            except ValueError:
                logger.warning(f"温度解析失败: {weather_data.get('temperature')}")
        
        return weather_data
        
    except Exception as e:
        logger.error(f"获取扩展天气失败: {e}")
        return None

def get_weather_from_website(city_name: str) -> Dict[str, Any]:
    """
    从中国天气网获取天气信息
    
    Returns:
        天气信息字典
    """
    try:
        urls = [
            "http://www.weather.com.cn/textFC/hb.shtml",
            "http://www.weather.com.cn/textFC/db.shtml",
            "http://www.weather.com.cn/textFC/hd.shtml",
            "http://www.weather.com.cn/textFC/hz.shtml",
            "http://www.weather.com.cn/textFC/hn.shtml",
            "http://www.weather.com.cn/textFC/xb.shtml",
            "http://www.weather.com.cn/textFC/xn.shtml"
        ]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'http://www.weather.com.cn/',
            'Accept-Language': 'zh-CN,zh;q=0.9'
        }
        
        for url in urls:
            try:
                resp = requests.get(url, headers=headers, timeout=8)
                resp.encoding = 'utf-8'
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # 查找所有天气表格
                tables = soup.find_all('table')
                
                for table in tables:
                    rows = table.find_all('tr')
                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) >= 8:
                            city_cell = cols[-8]
                            city_text = city_cell.get_text(strip=True)
                            
                            # 城市名称匹配（支持模糊匹配）
                            if city_name in city_text or city_text in city_name:
                                # 提取天气信息
                                high_temp = cols[-5].get_text(strip=True) if len(cols) > 5 else '-'
                                low_temp = cols[-2].get_text(strip=True) if len(cols) > 2 else '-'
                                weather_day = cols[-7].get_text(strip=True) if len(cols) > 7 else '-'
                                weather_night = cols[-4].get_text(strip=True) if len(cols) > 4 else '-'
                                
                                # 风力信息
                                wind_day = cols[-6].get_text(strip=True) if len(cols) > 6 else '-'
                                wind_night = cols[-3].get_text(strip=True) if len(cols) > 3 else '-'
                                
                                # 湿度信息（某些版本可能提供）
                                humidity = '-'
                                if len(cols) > 9:
                                    humidity = cols[-9].get_text(strip=True)
                                
                                # 构建天气数据
                                temperature = f"{low_temp}~{high_temp}℃"
                                weather_type = weather_day if weather_day != '-' else weather_night
                                wind = wind_day if wind_day != '-' else wind_night
                                
                                return {
                                    "city": city_text,
                                    "temperature": temperature,
                                    "weather_type": weather_type,
                                    "wind": wind,
                                    "humidity": humidity,
                                    "high_temp": high_temp.replace('℃', ''),
                                    "low_temp": low_temp.replace('℃', '')
                                }
                                
            except Exception as e:
                logger.debug(f"尝试URL {url} 失败: {e}")
                continue
                
        return None
        
    except Exception as e:
        logger.error(f"获取天气失败: {e}")
        return None

def get_dressing_advice(high_temp: int, low_temp: int) -> str:
    """根据温度给出穿衣建议"""
    avg_temp = (high_temp + low_temp) / 2
    
    if avg_temp >= 28:
        return "天气炎热，建议穿短袖、短裤、薄裙"
    elif 23 <= avg_temp < 28:
        return "天气较热，建议穿短袖、薄外套"
    elif 18 <= avg_temp < 23:
        return "温度适宜，建议穿单层棉麻面料的短套装、T恤衫"
    elif 10 <= avg_temp < 18:
        return "天气微凉，建议穿套装、夹衣、风衣、休闲装"
    elif 0 <= avg_temp < 10:
        return "天气较冷，建议穿厚外套、毛衣、毛呢大衣"
    else:
        return "天气寒冷，建议穿羽绒服、棉衣、厚毛衣"

def get_uv_index(weather_type: str) -> str:
    """获取紫外线指数（简化版）"""
    weather_type_lower = weather_type.lower()
    
    if any(word in weather_type_lower for word in ['晴', '多云', '少云']):
        uv_levels = ["中等", "强", "很强"]
        return f"紫外线{random.choice(uv_levels)}"
    elif any(word in weather_type_lower for word in ['阴', '雨', '雪']):
        return "紫外线弱"
    else:
        return "紫外线中等"

def get_aqi_info(city_name: str) -> Dict[str, str]:
    """获取空气质量信息（简化版，实际可接入API）"""
    # 模拟空气质量数据
    aqi_levels = ["优", "良", "轻度污染", "中度污染", "重度污染"]
    aqi_values = [random.randint(10, 50), random.randint(51, 100), 
                  random.randint(101, 150), random.randint(151, 200),
                  random.randint(201, 300)]
    
    level = random.choice(aqi_levels)
    idx = aqi_levels.index(level)
    value = aqi_values[idx]
    
    return {
        "level": level,
        "value": str(value),
        "primary_pollutant": random.choice(["PM2.5", "PM10", "O3", "NO2"])
    }

def get_life_indices(weather_type: str, high_temp: int, low_temp: int) -> Dict[str, str]:
    """获取生活指数"""
    indices = {}
    
    # 洗车指数
    if "雨" in weather_type or "雪" in weather_type:
        indices["car_wash"] = "不适宜"
    else:
        indices["car_wash"] = "适宜"
    
    # 运动指数
    if "雨" in weather_type or "雪" in weather_type or high_temp > 35 or low_temp < 0:
        indices["sport"] = "较不宜"
    else:
        indices["sport"] = "适宜"
    
    # 感冒指数
    if high_temp - low_temp > 10:
        indices["cold"] = "易发"
    else:
        indices["cold"] = "少发"
    
    # 舒适度指数
    if 18 <= (high_temp + low_temp) / 2 <= 26:
        indices["comfort"] = "舒适"
    else:
        indices["comfort"] = "不舒适"
    
    # 钓鱼指数（随机）
    fishing = ["适宜", "较适宜", "不宜"]
    indices["fishing"] = random.choice(fishing)
    
    return indices

def get_hourly_forecast(weather_type: str) -> List[Dict[str, str]]:
    """获取小时预报（简化版）"""
    forecast = []
    current_hour = datetime.datetime.now().hour
    
    for i in range(4):  # 未来4小时的简化预报
        hour = (current_hour + i) % 24
        temp_change = random.randint(-2, 2)
        
        forecast.append({
            "time": f"{hour:02d}:00",
            "temp": f"{20 + temp_change}℃",  # 基准20度
            "weather": weather_type,
            "wind": f"{random.randint(1, 3)}级"
        })
    
    return forecast

def get_daily_tips(date_info: Dict[str, str]) -> List[str]:
    """获取每日小贴士"""
    tips = []
    
    # 根据星期几的贴士
    weekday_tips = {
        "星期一": ["新的一周开始啦，加油！", "周一综合症？来杯咖啡提提神"],
        "星期二": ["工作渐入佳境，保持节奏", "记得起身活动，保护颈椎"],
        "星期三": ["一周过半，坚持就是胜利", "适当放松，劳逸结合"],
        "星期四": ["黎明前的黑暗，加油", "可以开始规划周末活动了"],
        "星期五": ["明天就周末啦，坚持一下", "晚上可以适当放松一下"],
        "星期六": ["周末愉快！好好休息", "适合户外活动的好时机"],
        "星期日": ["周末最后一天，好好享受", "明天要上班，记得早睡哦"]
    }
    
    if date_info["weekday"] in weekday_tips:
        tips.append(random.choice(weekday_tips[date_info["weekday"]]))
    
    # 通用健康贴士
    health_tips = [
        "每天八杯水，健康永相随",
        "早睡早起身体好",
        "多吃蔬菜水果，补充维生素",
        "适当运动，增强免疫力",
        "保持好心情，健康最重要"
    ]
    tips.append(random.choice(health_tips))
    
    # 天气相关贴士
    weather_tips = [
        "出门记得看天气，有备无患",
        "天气变化大，注意增减衣物",
        "空气质量不佳时，减少户外活动"
    ]
    tips.append(random.choice(weather_tips))
    
    return tips

def get_access_token():
    """
    获取微信公众号access_token
    Returns:
        str: access_token 或 None
    """
    try:
        config = Config()
        app_id = config.APP_ID
        app_secret = config.APP_SECRET
        
        if not app_id or not app_secret:
            logger.error("未配置APP_ID或APP_SECRET")
            return None
            
        url = f'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={app_id}&secret={app_secret}'
        response = requests.get(url, timeout=8)
        response.raise_for_status()
        result = response.json()
        
        if 'access_token' in result:
            logger.info("获取access_token成功")
            return result.get('access_token')
        else:
            error_msg = result.get('errmsg', '未知错误')
            logger.error(f"获取access_token失败：{error_msg}")
            return None
            
    except Exception as e:
        logger.error(f"获取access_token失败：{e}")
        return None

def get_daily_love(date_info: Dict[str, str]) -> str:
    """
    获取每日情话，增加更多来源
    
    Returns:
        str: 情话内容
    """
    try:
        # 多个情话API源
        api_sources = [
            {
                "url": "https://api.lovelive.tools/api/SweetNothings",
                "parser": lambda data: data.get('returnObj', '') if isinstance(data, dict) else data
            },
            {
                "url": "https://v1.hitokoto.cn/",
                "parser": lambda data: f"{data.get('hitokoto', '')} ——{data.get('from', '')}"
            },
            {
                "url": "https://api.uomg.com/api/rand.qinghua",
                "parser": lambda data: data.get('content', '') if isinstance(data, dict) else ''
            }
        ]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
        
        for api in api_sources:
            try:
                response = requests.get(api["url"], headers=headers, timeout=5)
                response.raise_for_status()
                data = response.json()
                
                sentence = api["parser"](data)
                if sentence and len(sentence.strip()) > 0:
                    # 添加日期相关的个性化
                    if "星期" in date_info["weekday"]:
                        sentence = f"{date_info['weekday']}的问候：{sentence}"
                    
                    # 限制长度
                    if len(sentence) > 100:
                        sentence = sentence[:97] + "..."
                    
                    logger.info(f"获取情话成功：{sentence[:30]}...")
                    return sentence
                    
            except Exception as e:
                logger.debug(f"情话API {api['url']} 失败：{e}")
                continue
        
        # 如果所有API都失败，使用备用情话
        backup_sentences = [
            f"{date_info['weekday']}也要保持好心情呀！",
            "每天都要开心哦！",
            "记得微笑，今天又是美好的一天！",
            "照顾好自己，比什么都重要~",
            "愿你今天有阳光般的好心情！"
        ]
        
        return random.choice(backup_sentences)
        
    except Exception as e:
        logger.error(f"获取情话失败：{e}")
        return "每天都要开心哦！"

def send_weather_message(access_token: str, weather_data: Dict[str, Any], 
                        date_info: Dict[str, str], city_name: str) -> bool:
    """
    发送天气预报消息
    
    Returns:
        bool: 是否成功发送
    """
    try:
        config = Config()
        
        if not weather_data:
            logger.error("天气数据为空")
            return False
        
        # 获取情话
        daily_love = get_daily_love(date_info)
        
        # 获取小贴士
        daily_tips = get_daily_tips(date_info)
        tips_text = "；".join(daily_tips[:3])  # 取前3条
        
        # 构建消息数据
        message_data = {
            "touser": config.OPEN_ID,
            "template_id": config.TEMPLATE_ID,
            "url": "https://mp.weixin.qq.com",
            "data": {
                # 基础信息
                "date": {
                    "value": f"{date_info['date']} {date_info['weekday']}",
                    "color": "#173177"
                },
                "city": {
                    "value": city_name,
                    "color": "#173177"
                },
                # 天气信息
                "weather": {
                    "value": weather_data.get("weather_type", "未知"),
                    "color": "#FF0000"
                },
                "temperature": {
                    "value": weather_data.get("temperature", "未知"),
                    "color": "#FF4500"
                },
                "wind": {
                    "value": weather_data.get("wind", "未知"),
                    "color": "#4682B4"
                },
                "humidity": {
                    "value": weather_data.get("humidity", "未知"),
                    "color": "#4682B4"
                },
                # 扩展信息
                "temp_diff": {
                    "value": weather_data.get("temp_diff", "未知"),
                    "color": "#FF6347"
                },
                "uv_index": {
                    "value": weather_data.get("uv_index", "未知"),
                    "color": "#FF8C00"
                },
                # 空气质量
                "aqi": {
                    "value": f"{weather_data.get('aqi', {}).get('level', '未知')} ({weather_data.get('aqi', {}).get('value', '')})",
                    "color": "#32CD32" if weather_data.get('aqi', {}).get('level') == '优' else "#FFD700"
                },
                # 生活指数
                "dressing": {
                    "value": weather_data.get("dressing_advice", "请根据温度穿衣"),
                    "color": "#8A2BE2"
                },
                "car_wash": {
                    "value": weather_data.get("life_indices", {}).get("car_wash", "未知"),
                    "color": "#1E90FF"
                },
                "sport": {
                    "value": weather_data.get("life_indices", {}).get("sport", "未知"),
                    "color": "#1E90FF"
                },
                # 温馨提示
                "love_note": {
                    "value": daily_love,
                    "color": "#FF69B4"
                },
                "daily_tips": {
                    "value": tips_text,
                    "color": "#2E8B57"
                },
                "update_time": {
                    "value": f"更新时间：{weather_data.get('update_time', '')}",
                    "color": "#808080"
                }
            }
        }
        
        # 发送请求
        url = f'https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}'
        response = requests.post(url, json=message_data, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        if result.get('errcode') == 0:
            logger.info(f"天气预报发送成功 (消息ID: {result.get('msgid')})")
            return True
        else:
            error_msg = result.get('errmsg', '未知错误')
            logger.error(f"发送失败：{error_msg}")
            return False
            
    except Exception as e:
        logger.error(f"发送天气预报失败：{e}")
        return False

def main():
    """主函数"""
    try:
        logger.info("=" * 60)
        logger.info("天气预报推送服务启动")
        logger.info(f"启动时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)
        
        # 初始化配置
        config = Config()
        
        # 检查必要配置
        required_configs = ["APP_ID", "APP_SECRET", "OPEN_ID", "TEMPLATE_ID"]
        for key in required_configs:
            if not getattr(config, key, ""):
                logger.error(f"缺少必要配置: {key}")
                return False
        
        logger.info(f"服务配置: 城市={config.CITIES}, AQI={config.ENABLE_AQI}, 生活指数={config.ENABLE_LIFE_INDEX}")
        
        # 获取日期信息
        date_info = get_date_info()
        logger.info(f"当前日期: {date_info['date']} {date_info['weekday']}")
        
        # 获取access_token
        access_token = get_access_token()
        if not access_token:
            logger.error("获取access_token失败")
            return False
        
        # 遍历所有城市
        success_count = 0
        for city in config.CITIES:
            logger.info(f"开始处理城市: {city}")
            
            # 获取天气信息
            weather_data = get_extended_weather(city)
            if not weather_data:
                logger.error(f"获取{city}天气信息失败")
                continue
            
            logger.info(f"获取到{city}天气: {weather_data.get('weather_type', '未知')} {weather_data.get('temperature', '未知')}")
            
            # 发送消息
            success = send_weather_message(access_token, weather_data, date_info, city)
            if success:
                success_count += 1
                logger.info(f"{city}天气预报发送成功")
            else:
                logger.error(f"{city}天气预报发送失败")
            
            # 城市间延迟，避免请求过快
            if len(config.CITIES) > 1 and city != config.CITIES[-1]:
                time.sleep(2)
        
        # 汇总结果
        logger.info("=" * 60)
        logger.info(f"任务完成: 成功{success_count}/{len(config.CITIES)}个城市")
        logger.info(f"完成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)
        
        return success_count > 0
        
    except Exception as e:
        logger.error(f"主程序错误: {e}", exc_info=True)
        return False

if __name__ == '__main__':
    # 设置环境变量示例（实际使用时请设置真实值）：
    # export APP_ID="your_app_id"
    # export APP_SECRET="your_app_secret"
    # export OPEN_ID="your_open_id"
    # export TEMPLATE_ID="your_template_id"
    # export CITIES="吉安,南昌"  # 支持多个城市
    # export ENABLE_AQI="true"
    # export ENABLE_LIFE_INDEX="true"
    
    success = main()
    exit(0 if success else 1)
