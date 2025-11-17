# 认证与手机号相关接口文档

## 基本说明
- 对外基础路径：`/rch/api/v1/auth/`
- 后端路由：`/api/v1/auth/`
- 返回结构统一：
```
{
  "code": 200|4xx|5xx,
  "message": "说明",
  "data": { ... },
  "errors": { ... }
}
```

## 1. 发送短信验证码
- 接口：`POST /rch/api/v1/auth/send-phone-code`
- 认证：无需登录
- 请求体：
```
{
  "phone": "1xxxxxxxxxx",
  "code_type": "register | login | reset_password | change_phone | bind_new_phone | verify_phone"
}
```
- 返回示例（成功）：
```
{
  "code": 200,
  "message": "验证码发送成功",
  "data": {
    "phone": "17209063396",
    "code_type": "login",
    "request_id": "dypnsapi-xxxxxx"
  }
}
```
- 返回示例（频率限制）：
```
{
  "code": 429,
  "message": "验证码发送过于频繁，请稍后再试"
}
```
- 返回示例（校验失败举例）：
```
{
  "code": 422,
  "message": "该手机号未注册",
  "errors": { "phone": ["该手机号未注册"] }
}
```
- 模板编号参考：`register/login=100001`、`change_phone=100002`、`reset_password=100003`、`bind_new_phone=100004`、`verify_phone=100005`

## 2. 用户注册（支持邮箱或手机号验证码）
- 接口：`POST /rch/api/v1/auth/register`
- 认证：无需登录
- 说明：验证方式二选一（邮箱+邮箱验证码）或（手机号+手机验证码）。基础字段包含 `username`、`password`、`confirm_password`、`user_type`。
- 请求体（学生，手机号注册示例）：
```
{
  "username": "user_2025",
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
- 请求体（组织用户，邮箱注册示例）：
```
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
- 返回示例（成功）：
```
{
  "code": 201,
  "message": "注册成功",
  "data": {
    "user": {
      "id": 1001,
      "username": "user_2025",
      "email": "",
      "user_type": "student",
      "user_type_display": "学生"
    },
    "tokens": {
      "access_token": "xxx",
      "refresh_token": "yyy"
    }
  }
}
```

## 3. 用户登录（密码 / 邮箱验证码 / 手机号验证码）
- 接口：`POST /rch/api/v1/auth/login`
- 认证：无需登录
- 请求体格式：
- 方式 A：密码登录
```
{
  "type": "password",
  "username_or_email_or_phone": "user_2025 | admin@corp.com | 17209063396",
  "password": "Abcdef12!"
}
```
- 方式 B：邮箱验证码登录
```
{
  "type": "email-verification",
  "email": "admin@corp.com",
  "email_code": "654321"
}
```
- 方式 C：手机号验证码登录
```
v
```
- 返回示例（成功）：
```
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "user": { /* 用户信息 */ },
    "auth": {
      "access": "xxx",
      "refresh": "yyy"
    }
  }
}
```

## 4. 修改绑定手机号（需登录）
- 接口：`PUT /rch/api/v1/auth/change_phone`
- 认证：需登录（`Authorization: Bearer <access>`）
- 模式：通过 `code_type` 区分
  - 绑定手机号（当前未绑定）：`code_type="bind_new_phone"`
  - 修改手机号（当前已绑定）：`code_type="change_phone"`
- 请求体：
```
{
  "phone": "13900000000",
  "phone_code": "123456",
  "code_type": "bind_new_phone | change_phone"
}
```
- 返回示例（成功）：
```
{
  "code": 200,
  "message": "手机号修改成功",
  "data": { "phone": "13900000000" }
}
```
- 返回示例（失败）：
```
{
  "code": 422,
  "message": "验证码无效或已过期",
  "errors": { "phone_code": ["验证码无效或已过期"] }
}
```
- 业务约束：
  - 已绑定时不可使用 `bind_new_phone`；未绑定时不可使用 `change_phone`
  - 新手机号不可与当前手机号相同，不可被其他用户占用

## 5. 其他说明
- 频率限制：同一手机号同一 `code_type` 60 秒内不可重复发送
- 有效期：短信验证码默认 5 分钟（可配置）
- 验证码消费：登录/绑定时验证码消费（不可复用）；安全验证场景可选择不消费
- 配置项：
  - `ALIYUN_SMS_SIGN_NAME`
  - `ALIYUN_SMS_TEMPLATE_REGISTER / LOGIN / CHANGE_PHONE / RESET_PASSWORD / BIND_NEW_PHONE / VERIFY_PHONE`
  - `PHONE_VERIFICATION_CODE_EXPIRE / PHONE_VERIFICATION_CODE_LENGTH / PHONE_CODE_INTERVAL_SECONDS`