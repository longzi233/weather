import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
from datetime import datetime
import requests
import json
import re

# 省会城市列表及其拼音名称（用于URL）
province_capitals = {
    "北京": "beijing",
    "上海": "shanghai",
    "天津": "tianjin",
    "重庆": "chongqing",
    "石家庄": "shijiazhuang",
    "太原": "taiyuan",
    "呼和浩特": "huhehaote",
    "沈阳": "shenyang",
    "长春": "changchun",
    "哈尔滨": "haerbin",
    "南京": "nanjing",
    "杭州": "hangzhou",
    "合肥": "hefei",
    "福州": "fuzhou",
    "南昌": "nanchang",
    "济南": "jinan",
    "郑州": "zhengzhou",
    "武汉": "wuhan",
    "长沙": "changsha",
    "广州": "guangzhou",
    "南宁": "nanning",
    "海口": "haikou",
    "成都": "chengdu",
    "贵阳": "guiyang",
    "昆明": "kunming",
    "拉萨": "lasa",
    "西安": "xian",
    "兰州": "lanzhou",
    "西宁": "xining",
    "银川": "yinchuan",
    "乌鲁木齐": "wulumuqi"
}

# API服务器配置
API_BASE_URL = "http://localhost:5000/api"  # Flask API服务器地址


def push_weather_data(city_pinyin, data):
    """
    推送天气数据到API服务器
    :param city_pinyin: 城市拼音名称
    :param data: 要推送的数据
    :return: 是否成功
    """
    try:
        url = f"{API_BASE_URL}/weather/{city_pinyin}"
        response = requests.post(url, json=data)
        if response.status_code == 200:
            print(f"{city_pinyin}数据推送成功")
            return True
        else:
            print(f"{city_pinyin}数据推送失败: {response.text}")
            return False
    except Exception as e:
        print(f"推送{city_pinyin}数据时出错: {e}")
        return False


def push_wind_data(data):
    """
    推送风场数据到API服务器
    :param data: 风场数据
    :return: 是否成功
    """
    try:
        url = f"{API_BASE_URL}/wind-data"
        response = requests.post(url, json=data)
        if response.status_code == 200:
            print("风场数据推送成功")
            return True
        else:
            print(f"风场数据推送失败: {response.text}")
            return False
    except Exception as e:
        print(f"推送风场数据时出错: {e}")
        return False


def generate_wind_data(city_data):
    """
    根据城市天气数据生成模拟风场数据
    :param city_data: 城市天气数据
    :return: 风场数据
    """
    wind_data = {
        "points": [],
        "timestamp": datetime.now().isoformat()
    }

    # 为每个城市生成一个风场点
    for city_name, data in city_data.items():
        if data:
            # 添加风场数据
            wind_data["points"].append({
                "city": city_name,
                "lon": get_city_longitude(city_name),
                "lat": get_city_latitude(city_name),
                "u": data.get("u", 0),  # 东西方向风速分量
                "v": data.get("v", 0),  # 南北方向风速分量
                "speed": data.get("wind_speed", 0),
                "direction": data.get("wind_direction", "未知"),
                "temp": data.get("current_temp", 0)
            })

    return wind_data


def parse_wind_info(wind_str):
    """
    解析风向风力字符串，返回风速和方向
    :param wind_str: 风向风力字符串，如"东北风 1级"
    :return: 包含u, v, speed, direction的字典
    """
    # 默认值
    result = {
        "u": 0,
        "v": 0,
        "speed": 0,
        "direction": "北风"
    }

    if not wind_str:
        return result

    # 提取风级
    speed_match = None
    if "级" in wind_str:
        try:
            speed_match = int(wind_str.split("级")[0][-1])
        except:
            pass

    # 计算风速 (近似公式: 风速 ≈ 风级 * 5 km/h)
    if speed_match is not None:
        result["speed"] = speed_match * 5

        # 将风速转换为u和v分量
        if "东" in wind_str:
            result["u"] = result["speed"] * 0.7  # 东风为正
        elif "西" in wind_str:
            result["u"] = -result["speed"] * 0.7  # 西风为负

        if "南" in wind_str:
            result["v"] = -result["speed"] * 0.7  # 南风为负
        elif "北" in wind_str:
            result["v"] = result["speed"] * 0.7  # 北风为正

        # 处理复合风向
        if "东北" in wind_str or "北东" in wind_str:
            result["u"] = result["speed"] * 0.5
            result["v"] = result["speed"] * 0.5
        elif "东南" in wind_str or "南东" in wind_str:
            result["u"] = result["speed"] * 0.5
            result["v"] = -result["speed"] * 0.5
        elif "西南" in wind_str or "南西" in wind_str:
            result["u"] = -result["speed"] * 0.5
            result["v"] = -result["speed"] * 0.5
        elif "西北" in wind_str or "北西" in wind_str:
            result["u"] = -result["speed"] * 0.5
            result["v"] = result["speed"] * 0.5

    # 记录风向
    result["direction"] = wind_str

    return result


def parse_temperature(temp_str):
    """
    解析温度字符串，返回数字温度值
    :param temp_str: 温度字符串，如"10℃"
    :return: 温度数值
    """
    try:
        if "℃" in temp_str:
            return float(temp_str.replace("℃", ""))
        return float(temp_str)
    except:
        return 0


def get_city_longitude(city_name):
    """
    获取城市的经度（简化版）
    """
    # 这里只是一个简化实现，实际应用中应该使用准确的地理坐标
    city_coordinates = {
        "北京": 116.41, "上海": 121.48, "天津": 117.20, "重庆": 106.54,
        "石家庄": 114.48, "太原": 112.53, "呼和浩特": 111.65, "沈阳": 123.43,
        "长春": 125.32, "哈尔滨": 126.63, "南京": 118.78, "杭州": 120.19,
        "合肥": 117.27, "福州": 119.30, "南昌": 115.89, "济南": 117.00,
        "郑州": 113.62, "武汉": 114.31, "长沙": 113.00, "广州": 113.23,
        "南宁": 108.37, "海口": 110.35, "成都": 104.06, "贵阳": 106.71,
        "昆明": 102.73, "拉萨": 91.11, "西安": 108.93, "兰州": 103.73,
        "西宁": 101.74, "银川": 106.27, "乌鲁木齐": 87.62
    }
    return city_coordinates.get(city_name, 116.41)  # 默认北京经度


def get_city_latitude(city_name):
    """
    获取城市的纬度（简化版）
    """
    # 这里只是一个简化实现，实际应用中应该使用准确的地理坐标
    city_coordinates = {
        "北京": 39.90, "上海": 31.22, "天津": 39.13, "重庆": 29.59,
        "石家庄": 38.03, "太原": 37.87, "呼和浩特": 40.82, "沈阳": 41.80,
        "长春": 43.90, "哈尔滨": 45.75, "南京": 32.04, "杭州": 30.26,
        "合肥": 31.86, "福州": 26.08, "南昌": 28.68, "济南": 36.65,
        "郑州": 34.72, "武汉": 30.52, "长沙": 28.21, "广州": 23.16,
        "南宁": 22.82, "海口": 20.02, "成都": 30.67, "贵阳": 26.57,
        "昆明": 25.04, "拉萨": 29.61, "西安": 34.27, "兰州": 36.03,
        "西宁": 36.56, "银川": 38.47, "乌鲁木齐": 43.82
    }
    return city_coordinates.get(city_name, 39.90)  # 默认北京纬度


def get_realtime_weather_data(url, driver):
    """
    获取实时天气数据
    :param url: 页面url
    :param driver: Selenium WebDriver实例
    :return: 返回实时天气数据字典
    """
    weather_data = {}

    try:
        # 使用Selenium打开页面
        print(f"正在访问: {url}")
        driver.get(url)

        # 等待页面加载完成
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "weather"))
            )
        except:
            print(f"页面加载超时: {url}")
            return weather_data

        # 获取页面源代码并用BeautifulSoup解析
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # 解析当前温度
        weather_dd = soup.find('dd', class_='weather')
        if weather_dd:
            # 当前温度
            now_temp = weather_dd.find('p', class_='now')
            if now_temp:
                temp_b = now_temp.find('b')
                if temp_b:
                    weather_data['current_temp'] = parse_temperature(temp_b.get_text(strip=True))

            # 天气状况
            weather_span = weather_dd.find('span')
            if weather_span:
                weather_b = weather_span.find('b')
                if weather_b:
                    weather_data['weather'] = weather_b.get_text(strip=True)

                # 温度范围
                temp_range = weather_span.get_text(strip=True)
                if '~' in temp_range:
                    temps = temp_range.split('~')
                    if len(temps) == 2:
                        weather_data['min_temp'] = parse_temperature(temps[0])
                        weather_data['max_temp'] = parse_temperature(temps[1].replace('℃', ''))

        # 解析湿度、风向、紫外线
        shidu_dd = soup.find('dd', class_='shidu')
        if shidu_dd:
            shidu_items = shidu_dd.find_all('b')
            for item in shidu_items:
                text = item.get_text(strip=True)
                if '湿度' in text:
                    humidity_match = re.search(r'湿度：(\d+%)', text)
                    if humidity_match:
                        weather_data['humidity'] = humidity_match.group(1)
                elif '风向' in text:
                    wind_match = re.search(r'风向：(.*)', text)
                    if wind_match:
                        wind_info = wind_match.group(1)
                        weather_data['wind_direction'] = wind_info
                        # 解析风向风力
                        wind_parsed = parse_wind_info(wind_info)
                        weather_data.update(wind_parsed)
                elif '紫外线' in text:
                    uv_match = re.search(r'紫外线：(.*)', text)
                    if uv_match:
                        weather_data['uv_index'] = uv_match.group(1)

        # 解析空气质量
        kongqi_dd = soup.find('dd', class_='kongqi')
        if kongqi_dd:
            # 空气质量
            h5 = kongqi_dd.find('h5')
            if h5:
                weather_data['air_quality'] = h5.get_text(strip=True).replace('空气质量：', '')

            # PM值
            h6 = kongqi_dd.find('h6')
            if h6:
                pm_text = h6.get_text(strip=True)
                pm_match = re.search(r'PM[:\s]*(\d+)', pm_text)
                if pm_match:
                    weather_data['pm25'] = int(pm_match.group(1))

            # 日出日落时间
            span = kongqi_dd.find('span')
            if span:
                sunrise_sunset = span.get_text(strip=True)
                if '日出' in sunrise_sunset and '日落' in sunrise_sunset:
                    parts = sunrise_sunset.split('\n')
                    if len(parts) >= 2:
                        sunrise = parts[0].replace('日出:', '').strip()
                        sunset = parts[1].replace('日落:', '').strip()
                        weather_data['sunrise'] = sunrise
                        weather_data['sunset'] = sunset

        print(f"成功获取实时天气数据: {weather_data}")

    except Exception as e:
        print(f"获取实时天气数据时发生错误: {e}")
        import traceback
        traceback.print_exc()

    return weather_data


def save_city_data(city_name, city_pinyin, data):
    """保存单个城市的数据到JSON文件并推送到API"""
    try:
        if not data:
            print(f"{city_name}没有数据可保存")
            return False

        print(f"准备保存 {city_name} 的实时天气数据")

        # 创建城市数据目录
        data_dir = "weather_data"
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        # 保存到JSON文件
        file_name = f"{city_pinyin}_realtime_weather.json"
        final_path = os.path.join(data_dir, file_name)

        with open(final_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"{city_name} 数据已保存到: {final_path}")

        # 推送数据到API服务器
        print(f"推送 {city_name} 数据到API服务器...")
        push_success = push_weather_data(city_pinyin, data)

        # 检查文件是否确实创建
        if os.path.exists(final_path):
            file_size = os.path.getsize(final_path)
            print(f"{city_name} 文件创建成功! 大小: {file_size} 字节")
            return push_success
        else:
            print(f"{city_name} 警告: 文件未创建")
            return False

    except Exception as e:
        print(f"保存 {city_name} 数据时出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_city_weather_data(city_name, city_pinyin, driver):
    """获取单个城市的实时天气数据"""
    print(f"\n开始获取 {city_name} 的实时天气数据...")

    # 构建URL
    url = f"https://www.tianqi.com/{city_pinyin}/"

    # 获取实时数据
    city_data = get_realtime_weather_data(url, driver)

    # 添加城市名称和时间戳
    city_data['city'] = city_name
    city_data['timestamp'] = datetime.now().isoformat()

    return city_data


# 主程序
def main():
    # 设置Chrome选项
    chrome_options = Options()
    # 如果需要在后台运行，取消下面的注释
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1080")

    # 初始化WebDriver
    driver = webdriver.Chrome(options=chrome_options)

    # 存储所有城市的数据，用于生成风场数据
    all_city_data = {}

    try:
        # 遍历所有省会城市
        for city_name, city_pinyin in province_capitals.items():
            # 获取城市数据
            city_data = get_city_weather_data(city_name, city_pinyin, driver)
            all_city_data[city_name] = city_data

            # 保存城市数据并推送到API
            if city_data:
                save_city_data(city_name, city_pinyin, city_data)
            else:
                print(f"{city_name} 未获取到数据，跳过保存")

            # 城市之间的延迟
            print(f"完成 {city_name} 数据采集，等待3秒后继续下一个城市...")
            time.sleep(3)

        # 生成并推送风场数据
        print("生成风场数据...")
        wind_data = generate_wind_data(all_city_data)
        push_wind_data(wind_data)

    finally:
        # 确保浏览器最终会被关闭
        driver.quit()
        print("所有城市数据采集完成!")


if __name__ == "__main__":
    main()