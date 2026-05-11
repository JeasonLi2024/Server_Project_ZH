# CAS统一认证系统接口文档（按当前代码实现）

## 1. 适用范围与路径
- 模块目录：`cas_auth/`
- 后端路由前缀：`/api/v1/cas/`
- 反向代理前缀（如部署启用）：`/rch/api/v1/cas/`
- 当前代码接口数量：5 个
  - `GET /login/`
  - `GET /callback/`
  - `GET|POST /logout/`
  - `GET /status/`
  - `GET /user-info/`

### 1.1 内外网地址映射（部署时）
| 场景 | 典型地址 |
|---|---|
| CAS服务器地址 | `https://auth.bupt.edu.cn/authserver` |
| 前端域名（当前环境） | `https://zhihui.bupt.edu.cn` |
| 对外API前缀（网关） | `https://<对外域名>/rch/api/v1/cas/` |
| 后端真实路由（Django） | `/api/v1/cas/` |

说明：
- 若网关配置了 `PROXY_PATH_PREFIX=/rch`，前端应统一走 `/rch/api/v1/...`。
- 后端代码中的 URL 匹配不带 `/rch`，该前缀由网关层处理。

### 1.2 当前环境结论（按现有代码与配置）
- 当前 `.env` 配置为 `PROXY_PATH_PREFIX=`（空），应用层未启用 `/rch` 前缀。
- Django 在代码层实际匹配路径是 `/api/v1/cas/...`。
- 文档中出现的 `/rch/api/v1/cas/...` 仅在“部署网关已配置路径前缀转发”时成立。
- 因此联调时请按实际入口二选一：
  - 直连后端：`/api/v1/cas/...`
  - 经过网关且网关加了 `/rch`：`/rch/api/v1/cas/...`

## 2. 统一响应格式
所有接口使用 `common_utils.APIResponse`：

```json
{
  "status": "success|error",
  "code": 200,
  "message": "说明",
  "data": {},
  "error": {}
}
```

## 3. 配置项与实际网络地址
### 3.1 必要配置
- `BUPT_CAS_ENABLED`：是否启用 CAS
- `BUPT_CAS_SERVER_URL`：CAS 服务器根地址（用于拼接 `/login`、`/logout`、`/serviceValidate` 或 `/p3/serviceValidate`）
- `BUPT_CAS_SERVICE_URL`：默认 `service`（回调/业务页面地址）
- `BUPT_CAS_VERSION`：`2.0` 或 `3.0`
- `FRONTEND_URL`：CAS 登出后默认回跳地址（当 `logout` 未传 `service` 时使用）

### 3.2 代码默认值（settings.py）
- `BUPT_CAS_SERVER_URL` 默认：`https://auth.bupt.edu.cn/authserver`
- `BUPT_CAS_SERVICE_URL` 默认：`http://10.160.64.18:18088/login`
- `BUPT_CAS_VERSION` 默认：`3.0`
- `FRONTEND_URL` 默认：`http://10.160.64.18:18088`

### 3.3 当前环境配置（.env）
- `BUPT_CAS_SERVER_URL`：`https://auth.bupt.edu.cn/authserver`
- `BUPT_CAS_SERVICE_URL`：`https://zhihui.bupt.edu.cn/login`
- `BUPT_CAS_VERSION`：`3.0`
- `FRONTEND_URL`：`https://zhihui.bupt.edu.cn`

说明：
- 对接时 `service` 参数必须与 CAS 发放 ticket 时使用的 service 保持一致（统一认证系统集成文档要求）。
- `service` 需进行 URL 编码（`urllib.parse.urlencode` 已在服务层实现）。

## 4. CAS标准接口映射（对照统一认证系统集成文档）
- 登录跳转：`{BUPT_CAS_SERVER_URL}/login?service=...`
- 登出跳转：`{BUPT_CAS_SERVER_URL}/logout?service=...`
- 票据验证：
  - CAS 2.0：`{BUPT_CAS_SERVER_URL}/serviceValidate`
  - CAS 3.0：`{BUPT_CAS_SERVER_URL}/p3/serviceValidate`

本项目由 `BUPTCASService.validate_ticket()` 根据 `BUPT_CAS_VERSION` 自动选择验证端点。

## 5. 接口说明
### 5.1 获取 CAS 登录地址
- 接口：`GET /api/v1/cas/login/`
- 对外：`GET /rch/api/v1/cas/login/`（如网关前缀为 `/rch`）
- 权限：`AllowAny`
- 查询参数：
  - `service`（可选）：不传时使用 `BUPT_CAS_SERVICE_URL`
- 行为：
  - 生成 `login_url`
  - 写入 `CASAuthLog(action=login, status=pending)`
- 成功响应示例：

```json
{
  "status": "success",
  "code": 200,
  "message": "请重定向到CAS登录页面",
  "data": {
    "login_url": "https://auth.bupt.edu.cn/authserver/login?service=https%3A%2F%2Fzhihui.bupt.edu.cn%2Flogin",
    "service_url": "https://zhihui.bupt.edu.cn/login"
  },
  "error": {}
}
```

- 失败响应：
  - `503`：`CAS认证未启用`

### 5.2 CAS 回调（票据验证 + 用户同步 + JWT签发）
- 接口：`GET /api/v1/cas/callback/`
- 对外：`GET /rch/api/v1/cas/callback/`
- 权限：`AllowAny`
- 查询参数：
  - `ticket`（必填）
  - `service`（可选，不传默认 `BUPT_CAS_SERVICE_URL`；建议与登录阶段一致）
- 行为：
  1. 调用 CAS 票据验证接口，解析 XML。
  2. 在本地同步用户（创建或更新）。
  3. 写入认证日志（`CASAuthLog` + `authentication.LoginLog`）。
  4. 返回 JWT：`access`、`refresh`。
- 成功响应示例：

```json
{
  "status": "success",
  "code": 200,
  "message": "CAS认证成功",
  "data": {
    "user": {
      "id": 123,
      "username": "2021211001",
      "email": "2021211001@bupt.cn",
      "user_type": "student"
    },
    "auth": {
      "access": "eyJ...",
      "refresh": "eyJ..."
    },
    "cas_info": {
      "user_id": "2021211001",
      "is_new_user": false,
      "auth_source": "cas"
    }
  },
  "error": {}
}
```

- 常见失败：
  - `400`：缺少 ticket（`缺少CAS票据`）
  - `401`：CAS 验证失败（`CAS认证失败: ...`）
  - `400`：用户同步失败（`用户信息同步失败: ...`）
  - `500`：回调处理异常（`CAS认证处理失败，请稍后重试`）
  - `503`：CAS 未启用

### 5.3 CAS 登出（含 JWT 黑名单）
- 接口：`GET|POST /api/v1/cas/logout/`
- 对外：`GET|POST /rch/api/v1/cas/logout/`
- 权限：`AllowAny`
- 参数：
  - `service`（可选）：GET 查询或 POST 表单/JSON，默认 `FRONTEND_URL`
  - `refresh_token`（可选）：用于黑名单单个 token
- `refresh_token`提取顺序：
  1. 请求体 `refresh_token`
  2. Cookie `refresh_token`
  3. 请求头 `X-Refresh-Token`
- 行为：
  - 若可识别登录用户，执行 JWT 黑名单逻辑：
    - 有 refresh_token：仅拉黑该 token
    - 无 refresh_token：拉黑该用户全部未拉黑的 outstanding token
  - 无论 token 处理是否异常，CAS 登出流程继续
  - 记录 `CASAuthLog(action=logout, status=success)`
- 成功响应示例：

```json
{
  "status": "success",
  "code": 200,
  "message": "请重定向到CAS登出页面",
  "data": {
    "logout_url": "https://auth.bupt.edu.cn/authserver/logout?service=https%3A%2F%2Fzhihui.bupt.edu.cn",
    "service_url": "https://zhihui.bupt.edu.cn"
  },
  "error": {}
}
```

- 失败响应：
  - `503`：`CAS认证未启用`

### 5.4 CAS 状态查询
- 接口：`GET /api/v1/cas/status/`
- 对外：`GET /rch/api/v1/cas/status/`
- 权限：`AllowAny`
- 返回字段：
  - `cas_enabled`
  - `cas_server_url`（未启用时为 `null`）
  - `cas_version`
  - `service_url`（未启用时为 `null`）
  - `user_cas_info`（仅登录态且存在组织档案时返回）
- 成功响应示例：

```json
{
  "status": "success",
  "code": 200,
  "message": "CAS状态信息",
  "data": {
    "cas_enabled": true,
    "cas_server_url": "https://auth.bupt.edu.cn/authserver",
    "cas_version": "3.0",
    "service_url": "https://zhihui.bupt.edu.cn/login",
    "user_cas_info": null
  },
  "error": {}
}
```

### 5.5 当前用户 CAS 信息
- 接口：`GET /api/v1/cas/user-info/`
- 对外：`GET /rch/api/v1/cas/user-info/`
- 权限：`IsAuthenticated`
- 返回内容：
  - `cas_user_id`
  - `auth_source`
  - `last_cas_login`
  - `is_cas_user`
  - `recent_auth_logs`（最近 5 条 CASAuthLog）
- 成功响应示例：

```json
{
  "status": "success",
  "code": 200,
  "message": "用户CAS信息",
  "data": {
    "cas_user_id": "2021211001",
    "auth_source": "cas",
    "last_cas_login": "2026-04-14T08:00:00+08:00",
    "is_cas_user": true,
    "recent_auth_logs": [
      {
        "action": "登录",
        "status": "成功",
        "created_at": "2026-04-14T08:00:00+08:00",
        "ip_address": "10.0.0.1"
      }
    ]
  },
  "error": {}
}
```

- 常见失败：
  - `404`：`用户组织信息不存在`
  - `500`：`获取用户信息失败`

## 6. 用户同步与身份判定（核心实现）
`cas_auth/services.py::sync_cas_user` 的核心规则如下：

### 6.1 CAS主键与邮箱规则
- 以 `<cas:user>` 作为系统 `username`
- CAS 自动创建用户邮箱规则：`{username}@bupt.cn`

### 6.2 教师/学生识别
- 优先使用本地档案匹配：
  - `OrganizationUser.employee_id == employeeNumber 或 user_id` -> 倾向教师
  - `Student.student_id == employeeNumber 或 user_id` -> 倾向学生
- 编码规则识别（10位数字）：
  - 第 5 位是 `8` 或 `9` -> 教职工（教师分支）
- 若规则不明确但本地已有组织档案，也按教师处理

### 6.3 学生分支落库行为
- `user.user_type = student`
- 确保存在 `Student` 档案
- `student.verification` 强制/补齐为 `cas`
- `grade` 默认取学号前四位（非数字则兜底 `2024`）
- `school` 默认定位 `BUPT_UNIVERSITY_ID`（默认 13）

### 6.4 教师分支落库行为
- `user.user_type = organization`
- 确保存在 `OrganizationUser` 档案
- `organization` 指向 `BUPT_ORGANIZATION_ID`（默认 1）
- `permission = member`
- `status = approved`
- `auth_source = cas`
- `cas_user_id = username`
- `employee_id = employeeNumber 或 username`
- `last_cas_login = 当前时间`

## 7. 与“学生认证”模块的关联点（最新）
CAS 登录成功并进入学生分支后，学生档案会设置 `verification='cas'`。这会直接影响 `authentication` 模块中的教育邮箱认证接口：

- `POST /api/v1/auth/student-edu/send-code/`
- `POST /api/v1/auth/student-edu/verify/`

上述两个接口在代码中对 `verification='cas'` 会返回：
- `422`：`CAS认证学生无需进行教育邮箱认证`

因此，前端应在用户信息中识别 CAS 学生状态，避免引导其走教育邮箱认证流程。

## 8. 端到端登录流程（推荐前端实现）
### 8.1 登录流程
1. 前端调用 `GET /rch/api/v1/cas/login/?service=<前端登录页URL>` 获取 `login_url`。
2. 浏览器跳转 `login_url` 到统一认证中心。
3. 用户认证通过后，CAS 重定向到前端 `service`，并携带 `ticket`。
4. 前端读取 `ticket`，调用 `GET /rch/api/v1/cas/callback/?ticket=...&service=...`。
5. 后端验证 ticket、同步用户、签发 JWT。
6. 前端保存 `access`/`refresh`，进入业务页面。

### 8.2 登出流程
1. 前端调用 `GET 或 POST /rch/api/v1/cas/logout/`（建议携带 `refresh_token`）。
2. 后端进行 JWT 黑名单处理并返回 `logout_url`。
3. 前端清理本地 token 并跳转 `logout_url`。
4. CAS 登出后回跳 `service_url`。

## 9. 前端调用示例
### 9.1 获取登录地址并跳转
```javascript
const service = encodeURIComponent("https://zhihui.bupt.edu.cn/login");
const res = await fetch(`/rch/api/v1/cas/login/?service=${service}`);
const data = await res.json();
if (data.code === 200) {
  window.location.href = data.data.login_url;
}
```

### 9.2 处理回调并换取JWT
```javascript
const params = new URLSearchParams(window.location.search);
const ticket = params.get("ticket");
if (ticket) {
  const service = encodeURIComponent("https://zhihui.bupt.edu.cn/login");
  const res = await fetch(`/rch/api/v1/cas/callback/?ticket=${encodeURIComponent(ticket)}&service=${service}`);
  const data = await res.json();
  if (data.code === 200) {
    localStorage.setItem("access_token", data.data.auth.access);
    localStorage.setItem("refresh_token", data.data.auth.refresh);
  }
}
```

### 9.3 登出并跳转CAS
```javascript
const refreshToken = localStorage.getItem("refresh_token");
const res = await fetch("/rch/api/v1/cas/logout/", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    service: "https://zhihui.bupt.edu.cn",
    refresh_token: refreshToken
  })
});
const data = await res.json();
if (data.code === 200) {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  window.location.href = data.data.logout_url;
}
```
