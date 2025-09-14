# data_server.py
from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 存储气象数据的目录
DATA_DIR = "weather_data"

@app.route('/api/weather/<city>', methods=['GET', 'POST'])
def weather_data(city):
    if request.method == 'POST':
        # 接收爬虫推送的数据
        data = request.json
        # 保存数据到文件
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(f"{DATA_DIR}/{city}.json", 'w') as f:
            json.dump(data, f)
        return jsonify({"status": "success", "message": "Data updated"})
    else:
        # 提供数据给前端
        try:
            with open(f"{DATA_DIR}/{city}.json", 'r') as f:
                data = json.load(f)
            return jsonify(data)
        except FileNotFoundError:
            return jsonify({"error": "Data not found"}), 404

@app.route('/api/wind-data', methods=['GET', 'POST'])
def wind_data():
    if request.method == 'POST':
        # 接收风场数据
        data = request.json
        with open(f"{DATA_DIR}/wind_data.json", 'w') as f:
            json.dump(data, f)
        return jsonify({"status": "success", "message": "Wind data updated"})
    else:
        # 提供风场数据
        try:
            with open(f"{DATA_DIR}/wind_data.json", 'r') as f:
                data = json.load(f)
            return jsonify(data)
        except FileNotFoundError:
            return jsonify({"error": "Wind data not found"}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)