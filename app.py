from functools import wraps
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from cachetools import TTLCache
import lib2
import json
import asyncio

from google.protobuf.json_format import MessageToJson

app = Flask(__name__)
CORS(app)  # Habilita CORS

cache = TTLCache(maxsize=100, ttl=300)

def cached_endpoint(ttl=300):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = (request.path, tuple(request.args.items()))
            if cache_key in cache:
                return cache[cache_key]
            else:
                result = func(*args, **kwargs)
                cache[cache_key] = result
                return result
        return wrapper
    return decorator


@app.route('/')
def serve_html():
    return send_from_directory('.', 'index.html')


@app.route('/api/account')
@cached_endpoint()
def get_account_info():
    region = request.args.get('region')
    uid = request.args.get('uid')

    if not uid or not region:
        return jsonify({
            "error": "Invalid request",
            "message": "Parameters 'uid' and 'region' are required."
        }), 400

    data = asyncio.run(lib2.GetAccountInformation(uid, "7", region, "/GetPlayerPersonalShow"))
    return json.dumps(data, indent=2, ensure_ascii=False), 200, {
        'Content-Type': 'application/json; charset=utf-8'
    }



if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
