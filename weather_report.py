"""
微信天气推送服务
功能：从天气网站抓取数据，通过微信模板消息推送给指定用户
"""

import os
import json
import datetime
import requests
from typing import Optional, Tuple, Dict, Any
from bs4 import BeautifulSoup

# 常量定义（使用大写命名）
WEATHER_URLS = [
    "http://www.weather.com.cn/textFC/hb.shtml",   # 华北
    "http://www.weather.com.cn/textFC/db.shtml",   # 东北
    "http://www.weather.com.cn/textFC/hd.shtml",   # 华东
    "http://www.weather.com.cn/textFC/hz.shtml",   # 华中
    "http://www.weather.com.cn/textFC/hn.shtml",   # 华南
    "http://www.weather.com.cn/textFC/xb.shtml",   # 西北
    "http://www.weather.com.cn/textFC/xn.shtml",   # 西南
]

# 从环境变量获取配置（增加默认值）
APP_ID = os.environ.get("APP_ID", "")
APP_SECRET = os.environ.get("APP_SECRET", "")
OPEN_ID = os.environ.get("OPEN_ID", "")
WEATHER_TEMPLATE_ID = os.environ.get("TEMPLATE_ID", "")


class WeatherFetcher:
    """天气数据获取器"""
    
    @staticmethod
    def fetch_weather_data(city: str) -> Optional[Tuple[str, str, str, str]]:
        """
        获取指定城市的天气信息
        
        Args:
            city: 城市名称
            
        Returns:
            元组 (城市名, 温度范围, 天气类型, 风向风力)
            如果未找到则返回None
        """
        for url in WEATHER_URLS:
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                response.encoding = 'utf-8'
                
                soup = BeautifulSoup(response.text, 'html.parser')
                div_con_midtab = soup.find("div", class_="conMidtab")
                
                if not div_con_midtab:
                    continue
                
                # 在找到的区域内搜索城市
                result = WeatherFetcher._search_city_in_tables(div_con_midtab, city)
                if result:
                    return result
                    
            except requests.RequestException as e:
                print(f"请求天气数据失败 {url}: {e}")
                continue
        
        print(f"未找到城市 '{city}' 的天气信息")
        return None
    
    @staticmethod
    def _search_city_in_tables(div_con_midtab, target_city: str) -> Optional[Tuple[str, str, str, str]]:
        """在表格中搜索特定城市的天气信息"""
        tables = div_con_midtab.find_all("table")
        
        for table in tables:
            # 跳过表头
            rows = table.find_all("tr")[2:]
            
            for row in rows:
                cells = row.find_all("td")
                if len(cells) < 8:
                    continue
                
                # 获取城市名（从倒数第8个单元格）
                city_cell = cells[-8]
                city_name = city_cell.get_text(strip=True)
                
                if city_name == target_city:
                    return WeatherFetcher._extract_weather_data(cells, city_name)
        
        return None
    
    @staticmethod
    def _extract_weather_data(cells, city_name: str) -> Tuple[str, str, str, str]:
        """从表格单元格中提取天气数据"""
        # 提取各个数据字段
        high_temp = cells[-5].get_text(strip=True)
        low_temp = cells[-2].get_text(strip=True)
        weather_day = cells[-7].get_text(strip=True)
        weather_night = cells[-4].get_text(strip=True)
        wind_day = cells[-6].get_text(strip=True)
        wind_night = cells[-3].get_text(strip=True)
        
        # 处理温度显示
        if high_temp != "-" and low_temp != "-":
            temperature = f"{low_temp}~{high_temp}°C"
        else:
            temperature = f"{low_temp}°C" if low_temp != "-" else "温度数据缺失"
        
        # 处理天气类型（优先使用白天数据）
        weather_type = weather_day if weather_day != "-" else weather_night
        if weather_type == "-":
            weather_type = "天气数据缺失"
        
        # 处理风向风力
        if wind_day and wind_day != "--":
            wind = wind_day
        elif wind_night and wind_night != "--":
            wind = wind_night
        else:
            wind = "风力数据缺失"
        
        return city_name, temperature, weather_type, wind


class WeChatAPI:
    """微信API接口封装"""
    
    @staticmethod
    def get_access_token() -> Optional[str]:
        """
        获取微信access_token
        
        Returns:
            access_token字符串，失败返回None
        """
        if not APP_ID or not APP_SECRET:
            print("错误：APP_ID或APP_SECRET未配置")
            return None
        
        url = f"https://api.weixin.qq.com/cgi-bin/token"
        params = {
            "grant_type": "client_credential",
            "appid": APP_ID.strip(),
            "secret": APP_SECRET.strip()
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'access_token' in data:
                return data['access_token']
            else:
                print(f"获取access_token失败: {data}")
                return None
                
        except requests.RequestException as e:
            print(f"请求access_token失败: {e}")
            return None
    
    @staticmethod
    def send_weather_message(access_token: str, weather_data: Tuple, daily_note: str) -> bool:
        """
        发送天气模板消息
        
        Args:
            access_token: 微信访问令牌
            weather_data: 天气数据元组 (城市, 温度, 天气, 风力)
            daily_note: 每日寄语
            
        Returns:
            发送是否成功
        """
        if not access_token or not OPEN_ID or not WEATHER_TEMPLATE_ID:
            print("错误：必要的配置参数缺失")
            return False
        
        # 准备消息数据
        message_data = WeChatAPI._build_message_data(weather_data, daily_note)
        
        url = f"https://api.weixin.qq.com/cgi-bin/message/template/send"
        params = {"access_token": access_token}
        
        try:
            response = requests.post(url, params=params, json=message_data, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if result.get('errcode') == 0:
                print("消息发送成功")
                return True
            else:
                print(f"消息发送失败: {result}")
                return False
                
        except requests.RequestException as e:
            print(f"发送消息失败: {e}")
            return False
    
    @staticmethod
    def _build_message_data(weather_data: Tuple, daily_note: str) -> Dict[str, Any]:
        """构建微信模板消息数据"""
        today_str = datetime.date.today().strftime("%Y年%m月%d日")
        
        return {
            "touser": OPEN_ID.strip(),
            "template_id": WEATHER_TEMPLATE_ID.strip(),
            "url": "https://mp.weixin.qq.com",  # 更合适的跳转链接
            "data": {
                "date": {"value": today_str, "color": "#173177"},
                "region": {"value": weather_data[0], "color": "#173177"},
                "weather": {"value": weather_data[2], "color": "#173177"},
                "temp": {"value": weather_data[1], "color": "#FF0000"},
                "wind_dir": {"value": weather_data[3], "color": "#173177"},
                "today_note": {"value": daily_note, "color": "#FF00FF"}
            }
        }


class DailyInspiration:
    """每日寄语获取"""
    
    @staticmethod
    def get_daily_inspiration() -> str:
        """
        获取每日一句情话/寄语
        
        Returns:
            寄语字符串，失败时返回默认寄语
        """
        url = "https://api.lovelive.tools/api/SweetNothings/Serialization/Json"
        
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if data and 'returnObj' in data and data['returnObj']:
                return data['returnObj'][0]
        except Exception as e:
            print(f"获取每日寄语失败: {e}")
        
        # 备用寄语
        return "愿你的一天充满阳光和微笑！"


class WeatherReporter:
    """天气报告主控制器"""
    
    def __init__(self):
        self.weather_fetcher = WeatherFetcher()
        self.wechat_api = WeChatAPI()
        self.daily_inspiration = DailyInspiration()
    
    def report_weather(self, city: str) -> bool:
        """
        执行完整的天气报告流程
        
        Args:
            city: 城市名称
            
        Returns:
            是否成功执行
        """
        print(f"开始获取 {city} 的天气信息...")
        
        # 1. 获取天气数据
        weather_data = self.weather_fetcher.fetch_weather_data(city)
        if not weather_data:
            return False
        
        print(f"天气信息获取成功: {weather_data}")
        
        # 2. 获取access_token
        access_token = self.wechat_api.get_access_token()
        if not access_token:
            return False
        
        # 3. 获取每日寄语
        daily_note = self.daily_inspiration.get_daily_inspiration()
        print(f"每日寄语: {daily_note}")
        
        # 4. 发送微信消息
        success = self.wechat_api.send_weather_message(access_token, weather_data, daily_note)
        
        return success


def main():
    """主函数"""
    # 可以改为从命令行参数或配置文件读取城市
    city = "吉安"
    
    # 检查必要的环境变量
    required_env_vars = ["APP_ID", "APP_SECRET", "OPEN_ID", "TEMPLATE_ID"]
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"错误：缺少必要的环境变量: {', '.join(missing_vars)}")
        print("请设置以下环境变量:")
        for var in missing_vars:
            print(f"  export {var}='your_value'")
        return
    
    # 创建并运行天气报告器
    reporter = WeatherReporter()
    success = reporter.report_weather(city)
    
    if success:
        print("天气报告发送完成！")
    else:
        print("天气报告发送失败！")


if __name__ == '__main__':
    main()
