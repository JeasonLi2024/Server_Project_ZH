from flask import Flask, request, jsonify

app = Flask(__name__)

# 初始化 pid 为 0
pid = 0

@app.route('/request', methods=['GET', 'POST'])
def handle_request():
    global pid
    try:
        # 每次请求时，pid 加 1
        pid += 1
        # 返回当前 pid 的值
        return jsonify({"pid": pid})
    except Exception as e:
        # 如果发生异常，返回错误信息
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4009)