## 目标

* 将 CAS 的 `service` 改为项目前端登录页（开发：`http://localhost:5173/login`，部署：`https://llm.bupt.edu.cn/rch/login`）。

* 保持后端仅 `/api/v1` 路由不变，前端在登录页接收 `ticket` 并调用后端验证接口。

## 修改项

* 更新 `Project_Zhihui/settings.py`：将 `BUPT_CAS_SERVICE_URL` 默认值改为 `http://localhost:5173/login`。

* 更新文档 `cas_auth/API_DOCS.md`：

  * 说明“前端登录页作为 service”的流程与时机。

  * 前端在登录成功后从 URL 读取 `ticket`，以“与登录时完全一致的 service”调用后端 `GET /api/v1/cas/callback?ticket=...&service=...`。

  * 保留 `/rch/api/v1/...` 的对外调用路径提示。

* 接口逻辑保持：

  * `cas_login` 支持查询参 `service` 覆盖默认；否则用配置默认值。

  * `cas_callback` 接收 `ticket` 与 `service` 并完成校验与发令牌，并且也将`service添加默认值。`

## 使用与验证

* 前端登录页：跳转 CAS 登录使用 `service=http://localhost:5173/login`。

* 登录成功：统一认证回到该登录页，前端读取 `ticket` 并调用后端回调，传入同一个 `service`。

* 验证通过：保存令牌并按角色跳转不同详情页。

