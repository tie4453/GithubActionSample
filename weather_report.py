import os
import requests
import json
from bs4 import BeautifulSoup
import logging
import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 配置信息
Configure = {
    "APP_ID": os.environ.get("APP_ID"),
    "APP_SECRET": os.environ.get("APP_SECRET"),
    "OPEN_ID": os.environ.get("OPEN_ID"),
    "TEMPLATE_ID": os.environ.get("TEMPLATE_ID"),
    "CITY": "吉安"
}

def get_weather(my_city):
    """
    从中国天气网获取指定城市的天气信息
    Args:
        my_city (str): 要查询的城市名称
    Returns:
        tuple: (城市名, 温度, 天气类型, 风力) 或 None
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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.3',
            'Referer': 'http://www.weather.com.cn/'
        }
        
        for url in urls:
            try:
                resp = requests.get(url, headers=headers, timeout=5)
                resp.raise_for_status()
                text = resp.content.decode("utf-8")
                soup = BeautifulSoup(text, 'html5lib')
                div_conMidtab = soup.find("div", class_="conMidtab")
                if div_conMidtab is None:
                    continue
                tables = div_conMidtab.find_all("table")
                for table in tables:
                    trs = table.find_all("tr")[2:]  # 跳过前两行
                    for tr in trs:
                        tds = tr.find_all("td")
                        city_td = tds[-8]
                        this_city = list(city_td.stripped_strings)[0]
                        if this_city == my_city:
                            high_temp = list(tds[-5].stripped_strings)[0] if tds[-5] else '-'
                            low_temp = list(tds[-2].stripped_strings)[0] if tds[-2] else '-'
                            weather_typ_day = list(tds[-7].stripped_strings)[0] if tds[-7] else '-'
                            weather_type_night = list(tds[-4].stripped_strings)[0] if tds[-4] else '-'
                            wind_day = list(tds[-6].stripped_strings) if tds[-6] else []
                            wind_day = wind_day[0] + wind_day[1] if len(wind_day) > 1 else ''
                            wind_night = list(tds[-3].stripped_strings) if tds[-3] else []
                            wind_night = wind_night[0] + wind_night[1] if len(wind_night) > 1 else ''

                            temp = f"{low_temp}——{high_temp}摄氏度" if high_temp != "-" else f"{low_temp}摄氏度"
                            weather_typ = weather_typ_day if weather_typ_day != "-" else weather_type_night
                            wind = wind_day if wind_day != "--" else wind_night

                            return (this_city, temp, weather_typ, wind)
            except requests.exceptions.RequestException as e:
                logging.error(f"获取天气数据失败：{e}", exc_info=True)
        return None
    except Exception as e:
        logging.error(f"天气获取逻辑错误：{e}", exc_info=True)
        return None

def get_access_token():
    """
    获取微信公众号access_token
    Returns:
        str: access_token 或 None
    """
    try:
        app_id = Configure["APP_ID"]
        app_secret = Configure["APP_SECRET"]
        if not app_id or not app_secret:
            logging.error("未配置APP_ID或APP_SECRET")
            return None
        url = f'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={app_id}&secret={app_secret}'
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        result = response.json()
        if 'errcode' in result and result['errcode'] != 0:
            logging.error(f"获取access_token失败：{result['errmsg']}")
            return None
        return result.get('access_token')
    except requests.exceptions.RequestException as e:
        logging.error(f"获取access_token失败：{e}", exc_info=True)
        return None
    except Exception as e:
        logging.error(f"获取access_token逻辑错误：{e}", exc_info=True)
        return None

def get_daily_love():
    """
    获取每日情话
    Returns:
        str: 情话内容
    """
    try:
        url = "https://api.lovelive.tools/api/SweetNothings/Serialization/Json"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ',
            'Referer': 'https://api.lovelive.tools/'
        }
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()
        sentence = data.get('returnObj', [])[0] if data.get('returnObj', []) else ""
        daily_love = sentence if sentence else "每天都要开心哦！"
        return daily_love
    except requests.exceptions.RequestException as e:
        logging.error(f"获取情话失败：{e}", exc_info=True)
        return "每天都要开心哦！"
    except Exception as e:
        logging.error(f"情话获取逻辑错误：{e}", exc_info=True)
        return "每天都要开心哦！"

def send_weather(access_token, weather_info):
    """
    发送天气预报
    Args:
        access_token (str): 微信公众号access_token
        weather_info (tuple): 天气信息（城市名, 温度, 天气类型, 风力）
    Returns:
        bool: 是否成功发送
    """
    try:
        if not weather_info:
            logging.error("天气信息为空")
            return False
        today = datetime.date.today()
        today_str = today.strftime("%Y年%m月%d日")
        body = {
            "touser": Configure["OPEN_ID"],
            "template_id": Configure["TEMPLATE_ID"],
            "url": "https://weixin.qq.com",
            "data": {
                "date": {
                    "value": today_str
                },
                "region": {
                    "value": weather_info[0]
                },
                "weather": {
                    "value": weather_info[2]
                },
                "temp": {
                    "value": weather_info[1]
                },
                "wind_dir": {
                    "value": weather_info[3]
                },
                "today_note": {
                    "value": get_daily_love()
                }
            }
        }
        if not access_token:
            logging.error("access_token为空")
            return False
        url = f'https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}'
        response = requests.post(url, json=body, timeout=10)
        response.raise_for_status()
        result = response.json()
        if result.get('errcode') == 0:
            logging.info("天气预报发送成功")
            return True
        else:
            logging.error(f"发送失败：{result.get('errmsg', '未知错误')}")
            return False
    except requests.exceptions.RequestException as e:
        logging.error(f"发送天气预报失败：{e}", exc_info=True)
        return False
    except Exception as e:
        logging.error(f"发送天气预报逻辑错误：{e}", exc_info=True)
        return False

def weather_report():
    """
    主函数，执行完整的天气报告流程
    """
    try:
        logging.info("开始执行天气报告任务")
        # 检查配置
        for key, value in Configure.items():
            if not value:
                logging.error(f"配置项{key}未设置")
                return
        
        # 1. 获取天气信息
        weather_info = get_weather(Configure["CITY"])
        if not weather_info:
            logging.error("无法获取天气信息")
            return
        logging.info(f"获取到天气信息：{weather_info}")

        # 2. 获取access_token
        access_token = get_access_token()
        if not access_token:
            logging.error("无法获取access_token")
            return

        # 3. 发送天气预报
        success = send_weather(access_token, weather_info)
        if success:
            logging.info("天气预报发送完成")
        else:
            logging.error("天气预报发送失败")
    except Exception as e:
        logging.error(f"主程序错误：{e}", exc_info=True)

if __name__ == '__main__':
    weather_report()
