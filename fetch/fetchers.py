import requests
import numpy as np
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from utils import location

load_dotenv()

def fetch_current(date: datetime, lat: float, lot: float):
    base_url = os.environ.get('CURRENT_API_URL')

    target_date = date.strftime("%Y%m%d")
    target_hour = date.strftime("%H")
    target_minute = date.strftime("%M")
    
    min_y = int(np.floor(lat))
    max_y = int(np.ceil(lat))
    min_x = int(np.floor(lot))
    max_x = int(np.ceil(lot))

    params = {
        "ServiceKey": os.environ.get('CURRENT_API_KEY'),
        "Date": target_date,
        "Hour": target_hour,
        "Minute": target_minute,
        "MaxX": max_x,
        "MinX": min_x,
        "MaxY": max_y,
        "MinY": min_y,
        "ResultType": "json"
    }

    response = requests.get(base_url, params=params)
    print(response.url)

    if response.status_code != 200:
        raise Exception(f"API 요청 실패: {response.status_code}")

    try:
        data = response.json()
    except ValueError as e:
        raise Exception(f"JSON 파싱 실패: {response.text}")

    if 'result' not in data or 'data' not in data['result']:
        raise Exception("응답 데이터 형식이 올바르지 않습니다")

    # 요청한 위경도와 가장 가까운 데이터 찾기
    min_distance = float('inf')
    closest_data = None

    for d in data['result']['data']:
        if 'current_dir' not in d or 'current_speed' not in d:
            continue
        if 'pre_lat' not in d or 'pre_lon' not in d:
            continue
        
        # 위경도 간의 거리 계산 (유클리드 거리)
        data_lat = float(d['pre_lat'])
        data_lon = float(d['pre_lon'])
        distance = np.sqrt((lat - data_lat)**2 + (lot - data_lon)**2)
        
        if distance < min_distance:
            min_distance = distance
            closest_data = d

    if closest_data is None:
        raise Exception("유효한 데이터가 없습니다")

    return float(closest_data['current_dir']), float(closest_data['current_speed'])

def fetch_wind(lat: float, lot: float):
    base_url = os.environ.get('WIND_API_URL')

    nearest = location.find_nearest_location(lat, lot)

    params = {
        "serviceKey": os.environ.get('WIND_API_KEY'),
        "obsCode": nearest.code,
        "min": 60,
        "numOfRows": 300,
        "type": "json"
    }

    response = requests.get(base_url, params=params)
    print(response.url)

    if response.status_code != 200:
        raise Exception(f"API 요청 실패: {response.status_code}")

    try:
        data = response.json()
    except ValueError as e:
        raise Exception(f"JSON 파싱 실패: {response.text}")

    # header 검증
    if 'header' not in data:
        raise Exception("응답 데이터 형식이 올바르지 않습니다")
    
    if data['header']['resultCode'] != "00":
        raise Exception(f"API 오류: {data['header'].get('resultMsg', 'Unknown error')}")

    # body 검증
    if 'body' not in data or 'items' not in data['body'] or 'item' not in data['body']['items']:
        raise Exception("응답 데이터 형식이 올바르지 않습니다")

    items = data['body']['items']['item']
    
    total_wind_dir = 0.0
    total_wind_speed = 0.0
    cnt = 0

    for item in items:
        if 'wndrct' not in item or 'wspd' not in item:
            continue
        if item['wndrct'] is None or item['wspd'] is None:
            continue
        total_wind_dir += float(item['wndrct'])
        total_wind_speed += float(item['wspd'])
        cnt += 1

    if cnt == 0:
        raise Exception("유효한 데이터가 없습니다")

    return total_wind_dir / cnt, total_wind_speed / cnt