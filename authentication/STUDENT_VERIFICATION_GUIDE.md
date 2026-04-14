# 学生认证功能实现说明（CAS + 教育邮箱双轨）

## 1. 目标与范围

本文档说明学生认证能力的完整实现，覆盖：

- CAS 学生自动认证
- 普通学生教育邮箱两步认证（发码 + 验码）
- 教育邮箱后台审核开关（自动通过/人工复核）
- 学生认证态字段在各接口中的回传
- 生产环境域名白名单配置建议
- 典型异常场景与鲁棒性分析

适用模块：

- `cas_auth`
- `authentication`
- `user`
- `studentproject`


## 2. 数据模型设计

文件：`user/models.py`

- `Student.verification`：
  - `unverified`：未认证
  - `cas`：CAS认证
  - `edu_email_pending`：教育邮箱待审核
  - `edu_email`：教育邮箱认证通过
- `Student.edu_email`：
  - 教育邮箱，唯一，可空

对应迁移：

- `user/migrations/0003_student_verification_student_edu_email.py`
- `user/migrations/0005_alter_student_verification.py`

验证码类型扩展：

- `EmailVerificationCode.code_type` 新增 `student_edu_verify`
- 迁移：`authentication/migrations/0003_emailverificationcode_student_edu_verify.py`


## 3. 认证流程总览

### 3.1 CAS 学生

- 通过 CAS 登录后，`cas_auth/services.py` 学生分支自动写入 `verification=cas`。

### 3.2 普通学生（教育邮箱）

- 第一步：`POST /api/v1/auth/student-edu/send-code/` 发送验证码
- 第二步：`POST /api/v1/auth/student-edu/verify/` 验证码校验并落库
- 删除：`DELETE /api/v1/auth/student-edu/` 删除教育邮箱认证信息

### 3.3 审核开关行为

- `STUDENT_EDU_EMAIL_REVIEW_ENABLED=False`：
  - 验码成功直接 `verification=edu_email`
- `STUDENT_EDU_EMAIL_REVIEW_ENABLED=True`：
  - 验码成功进入 `verification=edu_email_pending`
  - 管理员后台审核通过后改为 `edu_email`


## 4. 学生认证接口说明

### 4.1 发码接口

- `POST /api/v1/auth/student-edu/send-code/`
- 认证要求：登录态 + 学生用户

请求示例：

```json
{
  "email": "alice@bupt.edu.cn"
}
```

成功响应示例：

```json
{
  "status": "success",
  "code": 200,
  "message": "验证码发送成功",
  "data": {
    "student_verification": {
      "email": "alice@bupt.edu.cn",
      "code_type": "student_edu_verify"
    }
  },
  "error": {}
}
```

### 4.2 验码接口

- `POST /api/v1/auth/student-edu/verify/`
- 认证要求：登录态 + 学生用户

请求示例：

```json
{
  "email": "alice@bupt.edu.cn",
  "email_code": "123456"
}
```

成功响应示例（自动通过）：

```json
{
  "status": "success",
  "code": 200,
  "message": "教育邮箱认证成功",
  "data": {
    "student_verification": {
      "verification": "edu_email",
      "verification_display": "教育邮箱认证",
      "edu_email": "alice@bupt.edu.cn",
      "review_required": false
    }
  },
  "error": {}
}
```

成功响应示例（后台审核模式）：

```json
{
  "status": "success",
  "code": 200,
  "message": "教育邮箱认证成功，待后台审核",
  "data": {
    "student_verification": {
      "verification": "edu_email_pending",
      "verification_display": "教育邮箱待审核",
      "edu_email": "alice@bupt.edu.cn",
      "review_required": true
    }
  },
  "error": {}
}
```

### 4.3 删除接口

- `DELETE /api/v1/auth/student-edu/`

行为：

- 清空 `edu_email`
- 若 `verification in ['edu_email', 'edu_email_pending']`，回退到 `unverified`


## 5. 序列化器补全与返回字段影响

### 5.1 已补全的 Student 序列化器

- `user/serializers.py`
  - `StudentProfileSerializer`
  - `UserProfileSerializer.get_student_profile()`
- `studentproject/serializers.py`
  - `StudentBasicSerializer`
  - `StudentContactSerializer`
  - `StudentMaskedContactSerializer`

新增返回字段（按场景）：

- `verification`
- `verification_display`
- `edu_email`（公开或脱敏）

### 5.2 所有受影响接口（返回中新增学生认证态信息）

1) `POST /api/v1/auth/login/`
- `data.user.student_profile` 新增认证态字段（学生用户时）。

2) `GET /api/v1/cas/callback/`
- `data.user.student_profile` 新增认证态字段（CAS 学生常为 `cas`）。

3) `GET /api/v1/user/profile/`
- `data.student_profile` 新增认证态字段。

4) `PATCH /api/v1/user/update-profile/`
- 返回更新后的 `data.student_profile` 新增认证态字段。

5) `GET /api/v1/studentproject/projects/`
- `data.projects[].leader` 新增认证态字段（leader 为学生时）。

6) `GET /api/v1/studentproject/projects/{project_id}/`
- `data.leader`、`data.participants[].student` 新增认证态字段。

7) `GET /api/v1/studentproject/projects/{project_id}/participants/`
- `data.participants[].student`、`data.pending_applications[].student` 新增认证态字段。

8) `GET /api/v1/studentproject/projects/{project_id}/participants/{participant_id}/`
- `data.student` 新增认证态字段。

### 5.3 典型返回示例

示例A：`GET /api/v1/user/profile/`

```json
{
  "status": "success",
  "code": 200,
  "message": "操作成功",
  "data": {
    "id": 101,
    "username": "2021123456",
    "user_type": "student",
    "student_profile": {
      "id": 77,
      "student_id": "2021123456",
      "verification": "edu_email_pending",
      "verification_display": "教育邮箱待审核",
      "edu_email": "alice@bupt.edu.cn"
    }
  },
  "error": {}
}
```

示例B：`GET /api/v1/studentproject/projects/{project_id}/participants/`

```json
{
  "status": "success",
  "code": 200,
  "message": "操作成功",
  "data": {
    "participants": [
      {
        "id": 11,
        "student": {
          "id": 77,
          "student_id": "2021123456",
          "verification": "cas",
          "verification_display": "CAS认证",
          "edu_email": null
        },
        "role": "member",
        "status": "approved"
      }
    ]
  },
  "error": {}
}
```


## 6. 生产配置建议（白名单 + 审核开关）

代码读取项：

- `STUDENT_EDU_EMAIL_DOMAIN_WHITELIST`
- `STUDENT_EDU_EMAIL_REVIEW_ENABLED`

### 6.1 单校部署（推荐）

```python
STUDENT_EDU_EMAIL_DOMAIN_WHITELIST = [
    "bupt.edu.cn",
    "mail.bupt.edu.cn",
    "student.bupt.edu.cn",
]
STUDENT_EDU_EMAIL_REVIEW_ENABLED = True
```

### 6.2 多校部署（高校通用）

```python
STUDENT_EDU_EMAIL_DOMAIN_WHITELIST = [
    "edu.cn",
    "edu",
]
STUDENT_EDU_EMAIL_REVIEW_ENABLED = True
```

匹配规则：

- 支持精确匹配与子域匹配
- 自动归一化（小写、去前导 `.` 与 `@`）


## 7. 后台审核操作说明

文件：`user/admin.py`

- 后台 `Student` 管理页已展示 `verification` 与 `edu_email`
- 可按 `verification` 过滤待审核用户（`edu_email_pending`）

建议审核动作：

- 通过：`verification` 改为 `edu_email`
- 拒绝：`verification` 改为 `unverified`，并清空 `edu_email`


## 8. 场景与鲁棒性分析

1) CAS 学生首次登录：
- 自动 `cas`，不依赖 edu 邮箱。

2) CAS 学生尝试 edu 认证：
- 接口拒绝，避免来源冲突。

3) 普通学生注册邮箱是教育邮箱：
- 不自动认证，必须走发码+验码。

4) 教育邮箱重复绑定：
- 应用层校验 + DB 唯一约束双保险。

5) 后台审核模式：
- 验码通过后先 `edu_email_pending`，不会直接成为已认证。

6) 匿名滥用防护：
- `student_edu_verify` 不暴露给匿名通用发码接口。


## 9. 发布与回归建议

迁移：

```bash
python3 manage.py migrate user
python3 manage.py migrate authentication
```

检查：

```bash
python3 manage.py check
python3 manage.py makemigrations --check
```

灰度验证：

- CAS 学生登录后认证态
- 普通学生发码/验码（自动通过与审核模式）
- 后台审核通过/拒绝路径
- 删除教育邮箱后的状态回退
