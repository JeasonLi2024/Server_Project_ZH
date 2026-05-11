# 认证与手机号相关接口文档（以当前代码为准）

## 1. 基本信息
- 后端基础路径：`/api/v1/auth/`
- 部署网关若有前缀（如 `/rch`），请在网关层拼接；Django 路由本身不包含该前缀。
- 统一响应结构（`common_utils.APIResponse`）：
```json
{
  "status": "success|error",
  "code": 200,
  "message": "说明",
  "data": {},
  "error": {}
}
```

## 2. 发送短信验证码
- 接口：`POST /api/v1/auth/send-phone-code/`
- 认证：无需登录（`AllowAny`）
- 请求体参数：
  - `phone`：字符串，最大长度 11，必填
  - `code_type`：必填，可选值：
    - `register`
    - `login`
    - `reset_password`
    - `change_phone`
    - `bind_new_phone`
    - `verify_phone`
- 业务校验（代码逻辑）：
  - 60 秒内同一 `phone + code_type` 不可重复发送（`phone_code_limit:*`）。
  - `register`：手机号必须未注册。
  - `login / reset_password / verify_phone`：手机号必须已注册。
  - `change_phone / bind_new_phone`：本接口不做“已注册/未注册”前置限制，仅发送验证码。
- 成功示例：
```json
{
  "status": "success",
  "code": 200,
  "message": "验证码发送成功",
  "data": {
    "phone": "17209063396",
    "code_type": "login",
    "request_id": "dypnsapi-xxxxxx"
  },
  "error": {}
}
```
- 失败示例（频控）：
```json
{
  "status": "error",
  "code": 429,
  "message": "验证码发送过于频繁，请稍后再试",
  "data": {},
  "error": {}
}
```
- 失败示例（业务校验）：
```json
{
  "status": "error",
  "code": 422,
  "message": "该手机号未注册",
  "data": {},
  "error": {
    "phone": [
      "该手机号未注册"
    ]
  }
}
```

## 3. 用户注册（邮箱验证码或手机号验证码）
- 接口：`POST /api/v1/auth/register/`
- 认证：无需登录（`AllowAny`）
- 说明：验证码二选一
  - 方案 A：`email + email_code`
  - 方案 B：`phone + phone_code`
- 重要：`email` 在序列化器中是必填字段，即使走手机号验证码方案也需要传。

### 3.1 公共必填参数
- `username`
- `email`
- `password`
- `confirm_password`
- `user_type`：`student | organization`

### 3.2 学生用户（`user_type=student`）额外必填
- `student_id`
- `school_id`
- `major`
- `education`
- `grade`

### 3.3 组织用户（`user_type=organization`）注册方式
- `registration_choice` 必填，可选：
  - `existing`：加入现有组织（需传 `organization_id`）
  - `new`：创建新组织（需传 `organization_name`、`organization_type`、`industry_or_discipline`）
  - `invitation`：邀请码注册（需传 `invitation_code`）
- 当 `registration_choice != invitation` 时，`position` 必填。

### 3.4 学生注册示例（手机号验证码）
```json
{
  "username": "user_2025",
  "email": "user_2025@example.com",
  "phone": "17209063396",
  "phone_code": "123456",
  "password": "Abcdef12!",
  "confirm_password": "Abcdef12!",
  "user_type": "student",
  "student_id": "2025210001",
  "school_id": 1,
  "major": "计算机科学与技术",
  "education": "undergraduate",
  "grade": "2025"
}
```

### 3.5 组织用户注册示例（创建新组织 + 邮箱验证码）
```json
{
  "username": "org_admin",
  "email": "admin@corp.com",
  "email_code": "654321",
  "password": "Abcdef12!",
  "confirm_password": "Abcdef12!",
  "user_type": "organization",
  "registration_choice": "new",
  "organization_name": "示例科技有限公司",
  "organization_type": "enterprise",
  "industry_or_discipline": "AI",
  "position": "负责人",
  "department": "技术中心"
}
```

### 3.6 成功响应示例
```json
{
  "status": "success",
  "code": 201,
  "message": "注册成功",
  "data": {
    "user": {
      "id": 1001,
      "username": "user_2025",
      "email": "user_2025@example.com",
      "user_type": "student",
      "user_type_display": "学生"
    },
    "tokens": {
      "access_token": "xxx",
      "refresh_token": "yyy"
    }
  },
  "error": {}
}
```

## 4. 用户登录（密码 / 邮箱验证码 / 手机验证码）
- 接口：`POST /api/v1/auth/login/`
- 认证：无需登录（`AllowAny`）
- `type` 可选：`password | email-verification | phone-verification`

### 4.1 密码登录
```json
{
  "type": "password",
  "username_or_email_or_phone": "user_2025",
  "password": "Abcdef12!"
}
```

### 4.2 邮箱验证码登录
```json
{
  "type": "email-verification",
  "email": "admin@corp.com",
  "email_code": "654321"
}
```

### 4.3 手机验证码登录
```json
{
  "type": "phone-verification",
  "phone": "17209063396",
  "phone_code": "123456"
}
```

### 4.4 成功响应示例
```json
{
  "status": "success",
  "code": 200,
  "message": "登录成功",
  "data": {
    "user": {
      "id": 1001,
      "username": "user_2025"
    },
    "auth": {
      "access": "xxx",
      "refresh": "yyy"
    }
  },
  "error": {}
}
```

## 5. 修改/绑定手机号（登录态）
- 接口：`PUT /api/v1/auth/change_phone/`
- 认证：需登录（JWT）
- 请求体：
  - `phone`：新手机号，必填
  - `phone_code`：验证码，必填
  - `code_type`：`bind_new_phone | change_phone`，必填
- 业务规则（代码逻辑）：
  - 新手机号不能与当前手机号相同。
  - `bind_new_phone` 只能用于“当前未绑定手机号”。
  - `change_phone` 只能用于“当前已绑定手机号”。
  - 新手机号不能被其他用户占用。
  - 验证码通过 `validate_phone_code(new_phone, phone_code, code_type)` 校验并消费。
- 成功示例：
```json
{
  "status": "success",
  "code": 200,
  "message": "手机号修改成功",
  "data": {
    "phone": "13900000000"
  },
  "error": {}
}
```
- 失败示例（验证码错误/过期等）：
```json
{
  "status": "error",
  "code": 422,
  "message": "验证码无效或已过期",
  "data": {},
  "error": {
    "phone_code": [
      "验证码无效或已过期"
    ]
  }
}
```

## 6. 实际流程建议（与代码匹配）
### 6.1 手机验证码登录流程
1. 调用 `POST /api/v1/auth/send-phone-code/`，`code_type=login`。
2. 用户收到短信后，调用 `POST /api/v1/auth/login/`，`type=phone-verification`。
3. 登录成功后获得 `access/refresh`。

### 6.2 首次绑定手机号流程（用户当前无手机号）
1. 调用 `POST /api/v1/auth/send-phone-code/`，`code_type=bind_new_phone`。
2. 调用 `PUT /api/v1/auth/change_phone/`，携带 `phone`、`phone_code`、`code_type=bind_new_phone`。

### 6.3 修改已绑定手机号流程
1. 调用 `POST /api/v1/auth/send-phone-code/`，`code_type=change_phone`。
2. 调用 `PUT /api/v1/auth/change_phone/`，携带 `phone`、`phone_code`、`code_type=change_phone`。

## 7. 配置项（短信验证码）
- `ALIYUN_SMS_SIGN_NAME`
- `ALIYUN_SMS_TEMPLATE_REGISTER`
- `ALIYUN_SMS_TEMPLATE_LOGIN`
- `ALIYUN_SMS_TEMPLATE_RESET_PASSWORD`
- `ALIYUN_SMS_TEMPLATE_CHANGE_PHONE`
- `ALIYUN_SMS_TEMPLATE_BIND_NEW_PHONE`
- `ALIYUN_SMS_TEMPLATE_VERIFY_PHONE`
- `PHONE_VERIFICATION_CODE_EXPIRE`
- `PHONE_VERIFICATION_CODE_LENGTH`
- `PHONE_CODE_INTERVAL_SECONDS`
