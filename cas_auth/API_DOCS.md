# CAS统一认证系统接口文档

## 概述

CAS（Central Authentication Service）统一认证系统提供了完整的单点登录（SSO）解决方案，支持与北京邮电大学统一认证平台的集成。系统实现了CAS 2.0和CAS 3.0协议标准，提供用户身份验证、票据验证、用户信息同步等功能，并能够自动区分学生和教师身份，将用户信息存储到相应的数据表中。

## 接口列表

### 1. CAS登录入口接口

**接口地址：** `GET /api/cas/login/`

**功能描述：** 获取CAS登录URL，用于重定向用户到CAS认证服务器进行身份验证

**权限要求：** 
- 无需用户登录认证
- 公开访问接口

**查询参数：**
| 参数名 | 类型 | 必填 | 默认值 | 描述 |
|--------|------|------|--------|------|
| service | string | 否 | 系统配置的回调URL | 认证成功后的回调地址 |

**响应格式：**
```json
{
  "code": 200,
  "message": "请重定向到CAS登录页面",
  "data": {
    "login_url": "https://auth.bupt.edu.cn/authserver/login?service=http%3A//localhost%3A8000/api/cas/callback/",
    "service_url": "http://localhost:8000/api/cas/callback/"
  }
}
```

### 2. CAS认证回调处理接口

**接口地址：** `GET /api/cas/callback/`

**功能描述：** 处理CAS认证服务器的回调请求，验证票据并完成用户登录

**权限要求：** 
- 无需用户登录认证
- 由CAS服务器回调访问

**查询参数：**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| ticket | string | 是 | CAS服务器颁发的认证票据 |
| service | string | 否 | 服务URL，用于票据验证 |

**响应格式：**
```json
{
  "code": 200,
  "message": "CAS认证成功",
  "data": {
    "user": {
      "id": 123,
      "username": "2021211001",
      "real_name": "张三",
      "email": "zhangsan@bupt.edu.cn",
      "is_active": true,
      "organization_profile": {
        "employee_id": null,
        "auth_source": "cas",
        "cas_user_id": "2021211001",
        "last_cas_login": "2024-01-15T10:30:00Z"
      },
      "student_profile": {
        "student_id": "2021211001",
        "school": "计算机学院",
        "major": "计算机科学与技术",
        "grade": "2021"
      }
    },
    "auth": {
      "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
      "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
    },
    "cas_info": {
      "user_id": "2021211001",
      "is_new_user": false,
      "auth_source": "cas"
    }
  }
}
```

### 3. CAS登出接口

**接口地址：** `GET /api/cas/logout/` 或 `POST /api/cas/logout/`

**功能描述：** 获取CAS登出URL，用于重定向用户到CAS服务器完成全局登出。同时会自动黑名单化用户的JWT token以确保安全登出。

**权限要求：** 
- 无需用户登录认证
- 公开访问接口

**查询参数（GET）/ 表单参数（POST）：**
| 参数名 | 类型 | 必填 | 默认值 | 描述 |
|--------|------|------|--------|------|
| service | string | 否 | 前端首页URL | 登出后的重定向地址 |
| refresh_token | string | 否 | - | 刷新令牌（可选，支持请求体、Cookie、请求头多种方式传递） |

**请求头（可选）：**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| Authorization | string | Bearer token（用于识别当前用户） |
| X-Refresh-Token | string | 刷新令牌（备选传递方式） |

**Cookie（可选）：**
| 参数名 | 类型 | 描述 |
|--------|------|------|
| refresh_token | string | 刷新令牌（备选传递方式） |

**安全机制：**
- 如果提供了refresh_token，仅黑名单化该特定token
- 如果未提供refresh_token，将黑名单化用户所有有效的JWT token
- 即使token处理失败，也不会影响CAS登出流程

**响应格式：**
```json
{
  "code": 200,
  "message": "请重定向到CAS登出页面",
  "data": {
    "logout_url": "https://auth.bupt.edu.cn/authserver/logout?service=http%3A//localhost%3A3000",
    "service_url": "http://localhost:3000"
  }
}
```

**使用说明：**
1. 前端调用此接口获取CAS登出URL
2. 系统自动处理JWT token黑名单化
3. 前端重定向用户到返回的logout_url
4. 用户在CAS服务器完成登出后，会被重定向到service_url

### 4. CAS配置状态查询接口

**接口地址：** `GET /api/cas/status/`

**功能描述：** 获取CAS系统的配置状态和当前用户的CAS认证信息

**权限要求：** 
- 无需用户登录认证
- 公开访问接口（已登录用户可获取更多信息）

**响应格式：**
```json
{
  "code": 200,
  "message": "CAS状态信息",
  "data": {
    "cas_enabled": true,
    "cas_server_url": "https://auth.bupt.edu.cn/authserver",
    "cas_version": "3.0",
    "service_url": "http://localhost:8000/api/cas/callback/",
    "user_cas_info": {
      "cas_user_id": "2021211001",
      "auth_source": "cas",
      "last_cas_login": "2024-01-15T10:30:00Z"
    }
  }
}
```

### 5. 用户CAS认证信息查询接口

**接口地址：** `GET /api/cas/user-info/`

**功能描述：** 获取当前登录用户的CAS认证详细信息和最近的认证日志

**权限要求：** 
- 需要用户登录认证
- 只能查看自己的CAS信息

**响应格式：**
```json
{
  "code": 200,
  "message": "用户CAS信息",
  "data": {
    "cas_user_id": "2021211001",
    "auth_source": "cas",
    "last_cas_login": "2024-01-15T10:30:00Z",
    "is_cas_user": true,
    "recent_auth_logs": [
      {
        "action": "登录",
        "status": "成功",
        "created_at": "2024-01-15T10:30:00Z",
        "ip_address": "192.168.1.100"
      },
      {
        "action": "票据验证",
        "status": "成功",
        "created_at": "2024-01-15T10:29:58Z",
        "ip_address": "192.168.1.100"
      }
    ]
  }
}
```

## 数据模型

### CAS认证日志模型（CASAuthLog）

| 字段名 | 类型 | 描述 |
|--------|------|------|
| id | AutoField | 主键ID |
| user | ForeignKey | 关联用户（认证成功后） |
| cas_user_id | CharField | CAS用户ID |
| action | CharField | 操作类型（login/logout/validate） |
| status | CharField | 状态（success/failed/pending） |
| ticket | CharField | CAS票据 |
| service_url | URLField | 服务URL |
| ip_address | GenericIPAddressField | IP地址 |
| user_agent | TextField | 用户代理 |
| error_message | TextField | 错误信息 |
| response_data | JSONField | CAS服务器响应数据 |
| created_at | DateTimeField | 创建时间 |

### 用户组织信息模型（OrganizationUser）- CAS相关字段

| 字段名 | 类型 | 描述 |
|--------|------|------|
| cas_user_id | CharField | CAS系统返回的用户唯一标识 |
| auth_source | CharField | 认证来源（manual/cas） |
| employee_id | CharField | 教师工号 |
| last_cas_login | DateTimeField | 最后CAS登录时间 |

### 学生信息模型（Student）- CAS相关字段

| 字段名 | 类型 | 描述 |
|--------|------|------|
| student_id | CharField | 学号 |
| school | CharField | 学院 |
| major | CharField | 专业 |
| grade | CharField | 年级 |

## CAS认证流程

### 1. 首次登录流程

1. **前端发起登录**：调用 `/api/cas/login/` 获取CAS登录URL
2. **重定向到CAS**：前端将用户重定向到CAS认证服务器
3. **用户认证**：用户在CAS服务器完成身份验证
4. **CAS回调**：CAS服务器重定向到 `/api/cas/callback/` 并携带ticket
5. **票据验证**：后端验证ticket并获取用户信息
6. **用户同步**：根据CAS返回的信息创建或更新用户数据
7. **返回令牌**：返回JWT访问令牌给前端

### 2. 身份识别逻辑

系统会根据CAS返回的属性自动识别用户身份：

- **学生身份识别**：
  - CAS属性包含 `studentId`、`学号` 等字段
  - 或者 `cas_user_id` 为纯数字且长度符合学号格式

- **教师身份识别**：
  - CAS属性包含 `employeeNumber`、`工号` 等字段
  - 或者 `cas_user_id` 包含字母或特殊字符

### 3. 数据存储策略

- **学生用户**：信息存储在 `User` 和 `Student` 表中
- **教师用户**：信息存储在 `User` 和 `OrganizationUser` 表中
- **CAS日志**：所有认证操作记录在 `CASAuthLog` 表中

## 错误码说明

| 错误码 | 描述 | 解决方案 |
|--------|------|----------|
| 400 | 请求参数错误 | 检查ticket参数是否存在 |
| 401 | CAS认证失败 | 票据无效或已过期，重新登录 |
| 403 | 权限不足 | 确认用户具有相应权限 |
| 404 | 用户信息不存在 | 检查用户是否已正确同步 |
| 503 | CAS服务不可用 | CAS认证未启用或配置错误 |
| 500 | 服务器内部错误 | 联系系统管理员 |

## 配置说明

### 环境变量配置

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| BUPT_CAS_ENABLED | 是否启用CAS认证 | False |
| BUPT_CAS_SERVER_URL | CAS服务器地址 | https://auth.bupt.edu.cn/authserver |
| BUPT_CAS_SERVICE_URL | 回调服务地址 | http://localhost:8000/api/cas/callback/ |
| BUPT_CAS_VERSION | CAS协议版本 | 3.0 |
| FRONTEND_URL | 前端应用地址 | http://localhost:3000 |
| CAS_TIMEOUT | CAS请求超时时间 | 30 |
| CAS_VERIFY_SSL | 是否验证SSL证书 | True |

## 使用示例

### 1. 前端集成CAS登录

```javascript
// 获取CAS登录URL
const response = await fetch('/api/cas/login/');
const data = await response.json();

if (data.code === 200) {
    // 重定向到CAS登录页面
    window.location.href = data.data.login_url;
}
```

### 2. 处理CAS回调

```javascript
// CAS回调页面处理
const urlParams = new URLSearchParams(window.location.search);
const ticket = urlParams.get('ticket');

if (ticket) {
    // 后端会自动处理ticket验证和用户登录
    // 前端只需要从回调中获取认证结果
    const response = await fetch(`/api/cas/callback/${window.location.search}`);
    const data = await response.json();
    
    if (data.code === 200) {
        // 保存访问令牌
        localStorage.setItem('access_token', data.data.auth.access);
        localStorage.setItem('refresh_token', data.data.auth.refresh);
        
        // 跳转到主页
        window.location.href = '/dashboard';
    }
}
```

### 3. CAS登出

```javascript
// 获取CAS登出URL
const response = await fetch('/api/cas/logout/');
const data = await response.json();

if (data.code === 200) {
    // 清除本地令牌
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    
    // 重定向到CAS登出页面
    window.location.href = data.data.logout_url;
}
```

### 4. 检查CAS状态

```bash
# 检查CAS配置状态
curl -X GET 'http://localhost:8000/api/cas/status/' \
  -H 'Content-Type: application/json'
```

### 5. 获取用户CAS信息

```bash
# 获取当前用户的CAS认证信息
curl -X GET 'http://localhost:8000/api/cas/user-info/' \
  -H 'Authorization: Bearer your_access_token'
```

## 注意事项

1. **安全性**：
   - 所有CAS通信都应使用HTTPS
   - 票据（ticket）具有时效性，通常几分钟内过期
   - 系统会记录所有认证操作的IP地址和用户代理

2. **兼容性**：
   - 支持CAS 2.0和CAS 3.0协议
   - 兼容北京邮电大学统一认证平台
   - 支持学生和教师身份的自动识别

3. **性能优化**：
   - CAS认证日志表已添加索引优化查询性能
   - 用户信息同步使用数据库事务确保数据一致性

4. **错误处理**：
   - 所有CAS操作都有详细的日志记录
   - 认证失败时会记录具体的错误信息
   - 支持重试机制和降级处理

5. **数据同步**：
   - 首次CAS登录会自动创建用户账户
   - 后续登录会更新用户的CAS相关信息
   - 支持学生和教师信息的分别存储

## 版本信息

- **当前版本**：v1.0
- **最后更新**：2024-01-15
- **兼容性**：Django 4.x, Django REST Framework 3.x, CAS 2.0/3.0
- **依赖项**：requests, xml.etree.ElementTree, djangorestframework-simplejwt