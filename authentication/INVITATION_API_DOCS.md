# 企业邀请码模块 API 文档（以当前代码为准）

## 1. 概述
- 模块：`authentication`
- 后端基础路径：`/api/v1/auth/invitation/`
- 邀请码相关接口总数：5 个
- 响应统一使用 `common_utils.APIResponse`

## 2. 统一响应格式
```json
{
  "status": "success|error",
  "code": 200,
  "message": "描述信息",
  "data": {},
  "error": {}
}
```

## 3. 接口列表
### 3.1 生成邀请码
- 接口：`POST /api/v1/auth/invitation/generate/`
- 认证：`IsAuthenticated`
- 权限：当前用户必须存在已审核通过的组织关系（`OrganizationUser.status=approved`），且权限为 `owner` 或 `admin`
- 请求体（可选参数）：
```json
{
  "expire_days": 30,
  "max_uses": 100
}
```
- 参数规则：
  - `expire_days`：1~365，默认 30
  - `max_uses`：1~1000，默认 100
- 业务行为：
  - 自动将当前组织已有 `active` 邀请码置为 `expired`
  - 新建一个 `active` 邀请码
- 成功响应示例（201）：
```json
{
  "status": "success",
  "code": 201,
  "message": "邀请码生成成功",
  "data": {
    "id": 1,
    "code": "QHNzj732qywYEVaV",
    "organization": 1,
    "organization_name": "示例科技有限公司",
    "status": "active",
    "status_display": "有效",
    "created_by": 1001,
    "created_by_username": "org_admin",
    "created_at": "2026-04-14T10:00:00+08:00",
    "expires_at": "2026-05-14T10:00:00+08:00",
    "updated_at": "2026-04-14T10:00:00+08:00",
    "used_count": 0,
    "max_uses": 100
  },
  "error": {}
}
```
- 常见失败：
  - `403`：`权限不足，只有企业创建者和管理员可以生成邀请码`
  - `422`：参数校验失败（如超范围）
  - `400`：`您不属于任何组织`

### 3.2 获取当前组织活跃邀请码
- 接口：`GET /api/v1/auth/invitation/get/`
- 认证：`IsAuthenticated`
- 权限：当前用户须属于某组织（`status=approved`）；组织成员可查
- 请求参数：无
- 成功响应示例（有活跃邀请码）：
```json
{
  "status": "success",
  "code": 200,
  "message": "获取邀请码成功",
  "data": {
    "id": 1,
    "code": "QHNzj732qywYEVaV",
    "organization": 1,
    "organization_name": "示例科技有限公司",
    "status": "active",
    "status_display": "有效",
    "created_by": 1001,
    "created_by_username": "org_admin",
    "created_at": "2026-04-14T10:00:00+08:00",
    "expires_at": "2026-05-14T10:00:00+08:00",
    "updated_at": "2026-04-14T10:00:00+08:00",
    "used_count": 2,
    "max_uses": 100
  },
  "error": {}
}
```
- 成功响应示例（无活跃邀请码）：
```json
{
  "status": "success",
  "code": 200,
  "message": "当前组织没有活跃的邀请码",
  "data": {},
  "error": {}
}
```
- 常见失败：
  - `400`：`您不属于任何组织`

### 3.3 获取邀请码历史
- 接口：`GET /api/v1/auth/invitation/history/`
- 认证：`IsAuthenticated`
- 权限：仅 `owner` 或 `admin`
- 请求参数：无（当前代码未实现分页与状态筛选）
- 成功响应示例：
```json
{
  "status": "success",
  "code": 200,
  "message": "获取邀请码历史成功",
  "data": {
    "invitation_codes": [
      {
        "id": 1,
        "code": "QHNzj732qywYEVaV",
        "organization": 1,
        "organization_name": "示例科技有限公司",
        "status": "active",
        "status_display": "有效",
        "created_by": 1001,
        "created_by_username": "org_admin",
        "created_at": "2026-04-14T10:00:00+08:00",
        "expires_at": "2026-05-14T10:00:00+08:00",
        "updated_at": "2026-04-14T10:00:00+08:00",
        "used_count": 2,
        "max_uses": 100
      }
    ],
    "count": 1
  },
  "error": {}
}
```
- 常见失败：
  - `403`：`权限不足，只有企业创建者和管理员可以查看邀请码历史`
  - `400`：`您不属于任何组织`

### 3.4 验证邀请码
- 接口：`POST /api/v1/auth/invitation/validate/`
- 认证：`IsAuthenticated`（该视图未覆写权限，受全局 `DEFAULT_PERMISSION_CLASSES=IsAuthenticated` 约束）
- 请求体：
```json
{
  "code": "QHNzj732qywYEVaV"
}
```
- 说明：
  - 仅验证，不消耗使用次数
  - 实际消费发生在注册流程中（`register` + `registration_choice=invitation`）
- 成功响应示例：
```json
{
  "status": "success",
  "code": 200,
  "message": "邀请码验证成功",
  "data": {
    "valid": true,
    "organization_id": 1,
    "organization_name": "示例科技有限公司",
    "organization_type": "enterprise",
    "invitation_code": {
      "code": "QHNzj732qywYEVaV",
      "expires_at": "2026-05-14T10:00:00+08:00",
      "used_count": 2,
      "max_uses": 100,
      "remaining_uses": 98
    }
  },
  "error": {}
}
```
- 失败说明：
  - 参数校验失败时通常返回 `422`
  - 业务无效（如过期、已禁用、次数耗尽）返回 `400`，`message` 为具体原因

### 3.5 禁用当前组织活跃邀请码
- 接口：`POST /api/v1/auth/invitation/disable/`
- 认证：`IsAuthenticated`
- 权限：仅 `owner` 或 `admin`
- 请求参数：无（当前代码忽略请求体，不按 code 精确禁用，而是禁用“当前组织活跃邀请码”）
- 成功响应示例：
```json
{
  "status": "success",
  "code": 200,
  "message": "邀请码已成功禁用",
  "data": {},
  "error": {}
}
```
- 常见失败：
  - `403`：`权限不足，只有企业创建者和管理员可以禁用邀请码`
  - `400`：`当前组织没有活跃的邀请码`
  - `400`：`您不属于任何组织`

## 4. 与注册接口的集成流程（代码真实行为）
### 4.1 邀请码注册使用的接口
- 实际注册接口是：`POST /api/v1/auth/register/`
- 不是：`/auth/register/enterprise/`（当前代码中不存在该路由）

### 4.2 邀请码注册关键参数
- `user_type`：`organization`
- `registration_choice`：`invitation`
- `invitation_code`：必填
- 同时仍需满足验证码校验二选一：
  - `email + email_code`，或
  - `phone + phone_code`（注意 `email` 字段本身在注册序列化器中仍是必填）

### 4.3 邀请码注册示例（组织用户）
```json
{
  "username": "new_member",
  "email": "new_member@example.com",
  "email_code": "654321",
  "password": "Abcdef12!",
  "confirm_password": "Abcdef12!",
  "user_type": "organization",
  "registration_choice": "invitation",
  "invitation_code": "QHNzj732qywYEVaV",
  "department": "技术中心"
}
```

### 4.4 注册后系统行为
1. 校验邀请码是否可用。
2. 调用 `use_invitation_code` 消费邀请码（`used_count + 1`）。
3. 创建 `OrganizationUser`：
   - `permission = member`
   - `status = approved`
   - `position` 未传时默认 `成员`

## 5. 业务与实现说明
- 邀请码字符由大小写字母和数字组成，默认长度 16（排除了易混淆字符 `0/O/l/I/1`）。
- 同一组织同一时刻只允许一个 `active` 邀请码（模型唯一约束 + 生成时主动过期旧码）。
- 过期判定基于 `expires_at` 与当前时间比较；达到 `max_uses` 后不可再使用。
