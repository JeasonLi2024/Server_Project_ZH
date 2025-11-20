## 将实施的变更
- 资源下载接口：在 `project/views.py` 导入 `build_media_url` 并重写下载URL构造逻辑（优先 `file.url`，否则 `build_media_url(file.real_path, request)`）。
- Milvus 连接：更新 `Project_Zhihui/settings.py` 中 `MILVUS_HOST` 默认值为 `10.129.22.101`，端口保持 `19530`。
- WebSocket 代理兼容：在 `authentication/jwt_middleware.py` 的中间件里自动去除 `settings.PROXY_PATH_PREFIX`，确保代理路径能匹配 `notification/routing.py` 的原始路由。

## 验证
- 资源下载：调用 `/api/v1/project/resource/<id>/download/` 返回正确的 `download_url`，无 NameError。
- 搜索API：`/api/v1/search/read-search/` 与 `.../read-search-v2/` 正常连接 Milvus 并返回结果。
- WebSocket：在域名代理下连接 `wss://llm.bupt.edu.cn/rch/zhihui/ws/notification/<user_id>/` 成功，日志包含用户连接信息。