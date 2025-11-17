## 总体目标
- 生产域名 `https://llm.bupt.edu.cn` 下，项目作为子应用经前缀 `/rch/` 提供页面与 API 服务。
- 所有页面与接口请求同源、同前缀，避免混合内容与跨域；反向代理正确剥离前缀并转发到后端。

## 前端修改（前端小组）
- 基址配置：
  - 生产环境 API 基址统一使用同源相对路径：`/rch/api/v1/`
  - 页面路由 Base 统一以 `/rch/zhihui/` 或相应前缀（与当前部署一致）。
- 请求规范：
  - 仅使用相对路径（如 `fetch('/rch/api/v1/dashboard/study-direction/')`），不要硬编码 `http://10.129.x.x:8000/...`
  - 需要认证的请求设定：`credentials: 'include'`；禁止在生产页面下发向 HTTP 的直连请求。
- 生产环境变量：
  - `VITE_API_BASE=/rch/api/v1/`（或等价机制）
  - 页面跳转与静态资源前缀均带 `/rch/`，确保同源。
- 验收用例：
  - 在 `https://llm.bupt.edu.cn/rch/zhihui/home` 打开网络面板，验证接口 URL 全为 `https://llm.bupt.edu.cn/rch/api/v1/...`，无 `http://10.129...`；无 Mixed Content 与 CORS 报错。

## 后端修改（后端小组）
- 基础配置（`Project_Zhihui/settings.py`）：
  - `ALLOWED_HOSTS` 包含 `llm.bupt.edu.cn`
  - `CSRF_TRUSTED_ORIGINS = ['https://llm.bupt.edu.cn']`（已存在）
  - 识别代理：`USE_X_FORWARDED_HOST = True`、`SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')`
  - 若启用 CORS（django-cors-headers）：设置 `CORS_ALLOWED_ORIGINS = ['https://llm.bupt.edu.cn']` 与 `CORS_ALLOW_CREDENTIALS = True`
  - 生产建议：`DEBUG=False`，启用 `SECURE_SSL_REDIRECT/HSTS`
- 路由与服务：
  - 所有 API 入口保持 `/api/v1/...`；不要在后端添加 `/rch/` 前缀。
  - 确认 `dashboard` 路由 `api/v1/dashboard/study-direction/` 存在且可直接本地访问。
- 自检与联调：
  - `curl -I https://llm.bupt.edu.cn/rch/api/v1/dashboard/study-direction/`（经代理）应返回 200/JSON；响应头中 Host 为 `llm.bupt.edu.cn`，后端识别协议为 HTTPS。

## 反向代理检查（网络/运维小组）
- 前缀剥离与转发：
  - Nginx（示例）：
    - `location /rch/ { proxy_pass http://10.129.22.101:8000/; proxy_set_header X-Forwarded-Proto $scheme; proxy_set_header X-Forwarded-Host $host; }`
    - 注意 `proxy_pass` 结尾需 `/`，将 `/rch/api/v1/...` 转为后端 `/api/v1/...`
- HTTPS 与安全：
  - 有效证书配置在 `llm.bupt.edu.cn`；开启 HSTS（如需）；确保不出现从 HTTPS 页面到 HTTP 的直连
- WebSocket（如使用）：
  - `proxy_http_version 1.1; proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection "upgrade";`
- 预检与 CORS（若后端启用 CORS）：
  - 允许 `OPTIONS` 预检经 `/rch/` 正常转发到后端。
- 验收：
  - 通过浏览器访问生产页面与接口，网络面板验证：无跨域、无 Mixed Content；代理日志显示将 `/rch/...` 成功转发为后端根路径 `/...`。

## 常见问题与处理
- Mixed Content：页面为 HTTPS 而接口为 HTTP；前端仅用 `/rch/...` 同源相对路径。
- 404（Page not found）：`proxy_pass` 未带 `/` 或未剥离前缀；调整为带 `/` 并剥离 `/rch/`。
- CORS 阻止：后端未识别代理协议/主机或未配置 CORS/CSRF；按上文设置 `USE_X_FORWARDED_HOST`、`SECURE_PROXY_SSL_HEADER` 与 CORS/CSRF。
- Cookie 丢失：未同源或未设置 `credentials: 'include'`；改用同源 `/rch/...` 与包含凭据的请求。

## 验收清单（跨部门）
- 前端：接口地址统一改为 `/rch/api/v1/...`；页面与资源前缀一致；开启 `credentials: 'include'`。
- 后端：`ALLOWED_HOSTS/CSRF_TRUSTED_ORIGINS` 与代理头识别完成；在生产 `DEBUG=False`；路由可本地直达。
- 代理：`location /rch/` 正确剥离与转发；HTTPS 配置完成；必要的头与升级设置到位。
- 统一验证：在 `https://llm.bupt.edu.cn/rch/zhihui/home` 下，`study-direction` 等接口全部返回 200；无浏览器 Mixed Content/CORS 警告。