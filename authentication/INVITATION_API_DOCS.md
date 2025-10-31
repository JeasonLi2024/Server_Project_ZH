# 企业邀请码模块 API 文档

## 概述

企业邀请码模块提供了完整的邀请码管理功能，包括邀请码的生成、验证、使用、查看和管理。该模块支持企业管理员生成邀请码，新用户通过邀请码快速注册并加入对应的企业组织。

## 基础信息

- **模块路径**: `authentication/`
- **URL前缀**: `/auth/invitation/`
- **认证方式**: JWT Token认证
- **数据格式**: JSON（统一使用 common_utils.APIResponse 格式）

### 统一响应格式

所有接口都使用统一的响应格式：

#### 成功响应
```json
{
    "status": "success",
    "code": 200,
    "message": "操作成功的描述信息",
    "data": {}, // 具体的数据内容
    "error": {}
}
```

#### 错误响应
```json
{
    "status": "error",
    "code": 400, // HTTP状态码：400, 403, 404, 500 等
    "message": "错误描述信息",
    "data": {},
    "error": {} // 错误详细信息
}
```

#### 验证错误响应
```json
{
    "status": "error",
    "code": 422,
    "message": "验证失败的描述信息",
    "data": {},
    "error": {
        "field_name": ["具体的验证错误信息"]
    }
}
```

## API接口列表

### 1. 生成邀请码

**接口地址**: `POST /auth/invitation/generate/`

**功能描述**: 企业管理员生成新的邀请码，自动过期该组织的旧邀请码

**请求头**:
```
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json
```

**请求参数**:
```json
{
    "expire_days": 30,        // 可选，过期天数，默认30天
    "max_uses": 100          // 可选，最大使用次数，默认100次
}
```

**参数说明**:
- `expire_days` (int, 可选): 邀请码有效期天数，范围1-365天，默认30天
- `max_uses` (int, 可选): 邀请码最大使用次数，范围1-1000次，默认100次

**成功响应** (201):
```json
{
    "status": "success",
    "code": 201,
    "message": "邀请码生成成功",
    "data": {
        "id": 1,
        "code": "ABC123DEF456",
        "organization": 1,
        "created_by": 1,
        "created_at": "2024-01-01T10:00:00Z",
        "expires_at": "2024-01-08T10:00:00Z",
        "max_uses": 100,
        "used_count": 0,
        "is_active": true
    },
    "error": {}
}
```

**错误响应**:
```json
{
    "status": "error",
    "code": 403,
    "message": "权限不足，只有企业创建者和管理员可以生成邀请码",
    "data": {},
    "error": {}
}
```

**错误码说明**:
- `NO_ORGANIZATION`: 用户不属于任何组织
- `PERMISSION_DENIED`: 权限不足（非管理员）
- `INVALID_PARAMETERS`: 参数无效

---

### 2. 获取组织邀请码列表

**接口地址**: `GET /auth/invitation/codes/`

**功能描述**: 获取当前用户所属组织的所有邀请码列表

**请求头**:
```
Authorization: Bearer <JWT_TOKEN>
```

**请求参数**: 无

**成功响应** (200):
```json
{
    "status": "success",
    "code": 200,
    "message": "获取邀请码成功",
    "data": {
        "id": 1,
        "code": "QHNzj732qywYEVaV",
        "organization": 1,
        "created_by": 1,
        "created_at": "2024-12-25T10:30:00Z",
        "expires_at": "2025-01-24T10:30:00Z",
        "max_uses": 100,
        "used_count": 15,
        "is_active": true
    },
    "error": {}
}
```

**无邀请码响应**:
```json
{
    "status": "success",
    "code": 200,
    "message": "当前组织没有活跃的邀请码",
    "data": null,
    "error": {}
}
```

**错误响应**:
```json
{
    "status": "error",
    "code": 400,
    "message": "您不属于任何组织",
    "data": {},
    "error": {}
}
```

---

### 3. 查看邀请码历史记录

**接口地址**: `GET /auth/invitation/history/`

**功能描述**: 查看组织的邀请码历史记录，包括已过期和已禁用的邀请码

**请求头**:
```
Authorization: Bearer <JWT_TOKEN>
```

**请求参数**:
```
?page=1&page_size=20&status=all
```

**查询参数**:
- `page` (int, 可选): 页码，默认1
- `page_size` (int, 可选): 每页数量，默认20，最大100
- `status` (string, 可选): 状态筛选，可选值: `all`、`active`、`expired`、`disabled`

**成功响应** (200):
```json
{
    "status": "success",
    "code": 200,
    "message": "获取邀请码历史成功",
    "data": {
        "count": 25,
        "next": "http://api.example.com/auth/invitation/history/?page=2",
        "previous": null,
        "results": [
            {
                "id": 1,
                "code": "ABC123DEF456",
                "organization": 1,
                "created_by": 1,
                "created_at": "2024-01-01T10:00:00Z",
                "expires_at": "2024-01-08T10:00:00Z",
                "max_uses": 100,
                "used_count": 100,
                "is_active": false
            },
            {
                "id": 2,
                "code": "XYZ789GHI012",
                "organization": 1,
                "created_by": 1,
                "created_at": "2024-01-02T10:00:00Z",
                "expires_at": "2024-01-09T10:00:00Z",
                "max_uses": 50,
                "used_count": 25,
                "is_active": true
            }
        ]
    },
    "error": {}
}
```

---

### 4. 验证邀请码

**接口地址**: `POST /auth/invitation/validate/`

**功能描述**: 验证邀请码的有效性，不消耗使用次数

**请求头**:
```
Content-Type: application/json
```

**请求参数**:
```json
{
    "code": "QHNzj732qywYEVaV"
}
```

**参数说明**:
- `code` (string, 必填): 要验证的邀请码

**成功响应** (200):
```json
{
    "status": "success",
    "code": 200,
    "message": "邀请码验证成功",
    "data": {
        "valid": true,
        "organization_id": 1,
        "organization_name": "测试企业",
        "organization_type": "enterprise",
        "invitation_code": {
            "code": "ABC123DEF456",
            "expires_at": "2024-01-08T10:00:00Z",
            "used_count": 5,
            "max_uses": 100,
            "remaining_uses": 95
        }
    },
    "error": {}
}
```

**错误响应**:
```json
{
    "status": "error",
    "code": 400,
    "message": "邀请码已过期",
    "data": {},
    "error": {}
}
```

**错误码说明**:
- `CODE_NOT_FOUND`: 邀请码不存在
- `CODE_EXPIRED`: 邀请码已过期
- `CODE_DISABLED`: 邀请码已禁用
- `CODE_EXHAUSTED`: 邀请码使用次数已达上限

---

### 5. 禁用邀请码

**接口地址**: `POST /auth/invitation/disable/`

**功能描述**: 禁用指定的邀请码，只有组织管理员可以操作

**请求头**:
```
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json
```

**请求参数**:
```json
{
    "code": "QHNzj732qywYEVaV"
}
```

**参数说明**:
- `code` (string, 必填): 要禁用的邀请码

**成功响应** (200):
```json
{
    "status": "success",
    "code": 200,
    "message": "邀请码已成功禁用",
    "data": {},
    "error": {}
}
```

**错误响应**:
```json
{
    "status": "error",
    "code": 400,
    "message": "当前组织没有活跃的邀请码",
    "data": {},
    "error": {}
}
```

---

## 注册流程集成

### 企业注册时使用邀请码

**接口地址**: `POST /auth/register/enterprise/`

**功能描述**: 企业用户注册，支持使用邀请码

**请求参数**:
```json
{
    "username": "new_user",
    "password": "secure_password",
    "email": "user@example.com",
    "phone": "13800138000",
    "real_name": "张三",
    "invitation_code": "QHNzj732qywYEVaV",  // 可选，邀请码
    "verification_code": "123456"            // 可选，短信验证码
}
```

**注册逻辑**:
1. 如果提供了`invitation_code`，系统会验证邀请码并自动加入对应组织
2. 如果未提供`invitation_code`，则需要提供`verification_code`进行短信验证
3. 邀请码注册成功后，用户自动成为该组织的普通成员

---

## 使用步骤指南

### 管理员操作流程

1. **生成邀请码**
   ```bash
   curl -X POST "http://api.example.com/auth/invitation/generate/" \
        -H "Authorization: Bearer YOUR_JWT_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"expire_days": 30, "max_uses": 100}'
   ```

2. **查看邀请码列表**
   ```bash
   curl -X GET "http://api.example.com/auth/invitation/codes/" \
        -H "Authorization: Bearer YOUR_JWT_TOKEN"
   ```

3. **分享邀请码**
   - 将生成的邀请码分享给需要加入组织的用户
   - 可以通过邮件、微信、QQ等方式分享

4. **管理邀请码**
   - 查看使用情况：通过历史记录接口查看
   - 禁用邀请码：如果需要停止使用某个邀请码

### 新用户注册流程

1. **获取邀请码**
   - 从组织管理员处获取邀请码

2. **验证邀请码**（可选）
   ```bash
   curl -X POST "http://api.example.com/auth/invitation/validate/" \
        -H "Content-Type: application/json" \
        -d '{"code": "QHNzj732qywYEVaV"}'
   ```

3. **使用邀请码注册**
   ```bash
   curl -X POST "http://api.example.com/auth/register/enterprise/" \
        -H "Content-Type: application/json" \
        -d '{
          "username": "new_user",
          "password": "secure_password",
          "email": "user@example.com",
          "phone": "13800138000",
          "real_name": "张三",
          "invitation_code": "QHNzj732qywYEVaV"
        }'
   ```

### 前端集成示例

```javascript
// 1. 生成邀请码
async function generateInvitationCode(expireDays = 30, maxUses = 100) {
    const response = await fetch('/auth/invitation/generate/', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${getJWTToken()}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            expire_days: expireDays,
            max_uses: maxUses
        })
    });
    
    const result = await response.json();
    if (result.status === 'success') {
        console.log('邀请码:', result.data.code);
        return result.data;
    } else {
        throw new Error(result.message);
    }
}

// 2. 验证邀请码
async function validateInvitationCode(code) {
    const response = await fetch('/auth/invitation/validate/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ code })
    });
    
    const result = await response.json();
    return result;
}

// 3. 使用邀请码注册
async function registerWithInvitationCode(userData) {
    const response = await fetch('/auth/register/enterprise/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(userData)
    });
    
    const result = await response.json();
    return result;
}
```

## 安全注意事项

1. **权限控制**
   - 只有组织管理员可以生成和禁用邀请码
   - 普通用户只能查看组织的邀请码列表

2. **邀请码安全**
   - 邀请码为16位随机字符串，具有足够的安全性
   - 支持过期时间和使用次数限制
   - 自动过期机制防止邀请码滥用

3. **数据保护**
   - 敏感信息不会在API响应中暴露
   - 所有操作都有完整的日志记录

## 错误处理

所有API接口都遵循统一的错误响应格式：

```json
{
    "status": "error",
    "code": 400,
    "message": "错误描述信息",
    "data": {},
    "error": {
        "field": ["具体错误信息"]
    }
}
```

常见错误码：
- `AUTHENTICATION_REQUIRED`: 需要登录
- `PERMISSION_DENIED`: 权限不足
- `INVALID_PARAMETERS`: 参数无效
- `NO_ORGANIZATION`: 用户不属于任何组织
- `CODE_NOT_FOUND`: 邀请码不存在
- `CODE_EXPIRED`: 邀请码已过期
- `CODE_DISABLED`: 邀请码已禁用
- `CODE_EXHAUSTED`: 邀请码使用次数已达上限

## 定时任务

系统提供了以下定时任务来维护邀请码数据：

1. **清理过期邀请码**: 每天凌晨2点执行，将过期的active状态邀请码更新为expired状态
2. **清理旧记录**: 每周执行，删除90天前的过期或禁用邀请码记录
3. **过期提醒**: 每天检查即将在24小时内过期的邀请码，发送提醒通知

这些任务通过Celery定时任务系统自动执行，无需手动干预。