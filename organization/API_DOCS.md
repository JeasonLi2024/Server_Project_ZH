# 企业用户组织切换功能 API 文档

## 概述

本文档详细描述了企业用户组织切换功能的所有API接口，包括用户退出组织、申请加入组织、审核申请等核心功能。

## 基础信息

- **基础URL**: `/api/organization/`
- **认证方式**: Bearer Token（需要用户登录）
- **响应格式**: JSON
- **字符编码**: UTF-8

## 响应格式说明

所有API接口都遵循统一的响应格式（基于 `common_utils.py` 中的 `APIResponse` 类）：

### 成功响应
```json
{
    "success": true,
    "message": "操作成功",
    "data": {
        // 具体数据内容
    },
    "code": 200
}
```

### 错误响应
```json
{
    "success": false,
    "message": "错误信息",
    "errors": "详细错误描述",
    "code": 400
}
```

## API 接口列表

### 1. 用户退出组织

**接口描述**: 用户主动退出当前所在的组织

- **URL**: `POST /api/organization/leave/`
- **认证**: 需要登录
- **权限**: 普通用户（组织所有者不能退出）

#### 请求参数
无需请求参数

#### 响应示例

**成功响应**:
```json
{
    "success": true,
    "message": "您已成功退出组织 北京邮电大学",
    "data": {
        "organization_name": "北京邮电大学",
        "leave_time": "2024-01-15T10:30:00Z"
    },
    "code": 200
}
```

**错误响应**:
```json
{
    "success": false,
    "message": "您当前没有加入任何组织",
    "code": 400
}
```

#### 错误码说明
- `400`: 用户没有加入任何组织
- `403`: 组织所有者不能退出组织
- `500`: 服务器内部错误

---

### 2. 申请加入组织

**接口描述**: 用户申请加入指定的组织

- **URL**: `POST /api/organization/apply-join/`
- **认证**: 需要登录
- **权限**: 普通用户（未加入任何组织）

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| organization_id | integer | 是 | 目标组织ID |
| application_reason | string | 是 | 申请理由（至少10个字符） |

#### 请求示例
```json
{
    "organization_id": 123,
    "application_reason": "我是北京邮电大学的在校学生，希望能够加入学校的官方组织，参与相关的学术活动和项目。"
}
```

#### 响应示例

**成功响应**:
```json
{
    "success": true,
    "message": "已成功提交加入 北京邮电大学 的申请，请等待审核",
    "data": {
        "application_id": 456,
        "organization_name": "北京邮电大学",
        "application_time": "2024-01-15T10:30:00Z",
        "status": "pending"
    },
    "code": 200
}
```

**错误响应**:
```json
{
    "success": false,
    "message": "您已加入其他组织，请先退出当前组织",
    "code": 400
}
```

#### 错误码说明
- `400`: 参数错误、已加入其他组织、已有待审核申请等
- `404`: 目标组织不存在
- `500`: 服务器内部错误

---

### 3. 获取我的加入申请列表

**接口描述**: 获取当前用户提交的所有加入申请记录

- **URL**: `GET /api/organization/my-applications/`
- **认证**: 需要登录
- **权限**: 普通用户

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| status | string | 否 | 申请状态过滤（pending/approved/rejected/cancelled） |
| page | integer | 否 | 页码（默认1） |
| page_size | integer | 否 | 每页数量（默认10） |

#### 请求示例
```
GET /api/organization/my-applications/?status=pending&page=1&page_size=10
```

#### 响应示例

**成功响应**:
```json
{
    "success": true,
    "message": "申请列表获取成功",
    "data": {
        "applications": [
            {
                "id": 456,
                "organization": {
                    "id": 123,
                    "name": "北京邮电大学",
                    "organization_type": "university",
                    "logo": "https://example.com/media/logos/bupt.png"
                },
                "application_reason": "我是北京邮电大学的在校学生...",
                "status": "pending",
                "status_display": "待审核",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        ],
        "pagination": {
            "current_page": 1,
            "total_pages": 1,
            "total_count": 1,
            "page_size": 10,
            "has_next": false,
            "has_previous": false
        }
    },
    "code": 200
}
```

#### 申请状态说明
- `pending`: 待审核
- `approved`: 已通过
- `rejected`: 已拒绝
- `cancelled`: 已取消

---

### 4. 取消加入申请

**接口描述**: 取消指定的待审核加入申请

- **URL**: `POST /api/organization/applications/{application_id}/cancel/`
- **认证**: 需要登录
- **权限**: 申请人本人

#### 路径参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| application_id | integer | 是 | 申请记录ID |

#### 请求参数
无需请求参数

#### 响应示例

**成功响应**:
```json
{
    "success": true,
    "message": "申请已取消",
    "data": {
        "application_id": 456,
        "status": "cancelled"
    },
    "code": 200
}
```

**错误响应**:
```json
{
    "success": false,
    "message": "只能取消待审核的申请",
    "code": 400
}
```

#### 错误码说明
- `400`: 申请状态不允许取消
- `404`: 申请记录不存在
- `500`: 服务器内部错误

---

### 5. 获取组织的加入申请列表（管理员）

**接口描述**: 组织管理员获取本组织的所有加入申请

- **URL**: `GET /api/organization/join-applications/`
- **认证**: 需要登录
- **权限**: 组织管理员或所有者

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| status | string | 否 | 申请状态过滤（默认pending） |
| page | integer | 否 | 页码（默认1） |
| page_size | integer | 否 | 每页数量（默认10） |

#### 请求示例
```
GET /api/organization/join-applications/?status=pending&page=1&page_size=10
```

#### 响应示例

**成功响应**:
```json
{
    "success": true,
    "message": "申请列表获取成功",
    "data": {
        "applications": [
            {
                "id": 456,
                "applicant": {
                    "id": 789,
                    "username": "student001",
                    "real_name": "张三",
                    "email": "student001@bupt.edu.cn",
                    "avatar": "https://example.com/media/avatars/student001.png"
                },
                "application_reason": "我是北京邮电大学的在校学生...",
                "status": "pending",
                "status_display": "待审核",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        ],
        "pagination": {
            "current_page": 1,
            "total_pages": 1,
            "total_count": 1,
            "page_size": 10,
            "has_next": false,
            "has_previous": false
        },
        "organization": {
            "id": 123,
            "name": "北京邮电大学"
        }
    },
    "code": 200
}
```

#### 错误码说明
- `400`: 用户没有加入任何组织
- `403`: 没有权限查看申请列表
- `500`: 服务器内部错误

---

### 6. 审核加入申请

**接口描述**: 组织管理员审核用户的加入申请

- **URL**: `POST /api/organization/applications/{application_id}/review/`
- **认证**: 需要登录
- **权限**: 组织管理员或所有者

#### 路径参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| application_id | integer | 是 | 申请记录ID |

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| action | string | 是 | 审核操作（approve/reject） |
| review_comment | string | 否 | 审核意见 |

#### 请求示例
```json
{
    "action": "approve",
    "review_comment": "申请材料齐全，符合加入条件，同意加入。"
}
```

#### 响应示例

**成功响应（批准）**:
```json
{
    "success": true,
    "message": "已批准 student001 的加入申请",
    "data": {
        "application_id": 456,
        "status": "approved",
        "action": "approve",
        "review_comment": "申请材料齐全，符合加入条件，同意加入。",
        "reviewed_at": "2024-01-15T14:30:00Z"
    },
    "code": 200
}
```

**成功响应（拒绝）**:
```json
{
    "success": true,
    "message": "已拒绝 student001 的加入申请",
    "data": {
        "application_id": 456,
        "status": "rejected",
        "action": "reject",
        "review_comment": "申请理由不充分，暂不符合加入条件。",
        "reviewed_at": "2024-01-15T14:30:00Z"
    },
    "code": 200
}
```

**错误响应**:
```json
{
    "success": false,
    "message": "该申请已被处理",
    "code": 400
}
```

#### 错误码说明
- `400`: 无效的审核操作、申请已被处理、申请人已加入其他组织等
- `403`: 没有权限审核申请
- `404`: 申请记录不存在
- `500`: 服务器内部错误

---

### 7. 通过邀请码加入组织

**接口描述**: 用户通过邀请码直接加入组织（免审核）

- **URL**: `POST /api/organization/join-by-invitation/`
- **认证**: 需要登录
- **权限**: 普通用户（未加入任何组织）

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| invitation_code | string | 是 | 邀请码 |

#### 请求示例
```json
{
    "invitation_code": "BUPT2024INVITE001"
}
```

#### 响应示例

**成功响应**:
```json
{
    "success": true,
    "message": "成功加入组织 北京邮电大学",
    "data": {
        "organization": {
            "id": 123,
            "name": "北京邮电大学",
            "organization_type": "university",
            "logo": "https://example.com/media/logos/bupt.png"
        },
        "join_time": "2024-01-15T10:30:00Z"
    },
    "code": 200
}
```

**错误响应**:
```json
{
    "success": false,
    "message": "邀请码无效或已过期",
    "code": 400
}
```

#### 错误码说明
- `400`: 邀请码无效、已过期、已达使用上限、用户已加入其他组织等
- `500`: 服务器内部错误

---

## 通知机制

### 通知触发时机

1. **申请提交时**: 向组织管理员发送新申请通知
2. **申请审核时**: 向申请人发送审核结果通知
3. **用户退出时**: 记录操作日志（可选择是否通知管理员）

### 通知类型

| 通知类型 | 接收者 | 触发时机 | 模板变量 |
|----------|--------|----------|----------|
| organization_join_application_submitted | 组织管理员 | 用户提交申请 | applicant_name, organization_name, application_reason, application_time |
| organization_join_application_approved | 申请人 | 申请被批准 | organization_name, reviewer_name, review_comment, review_time |
| organization_join_application_rejected | 申请人 | 申请被拒绝 | organization_name, reviewer_name, review_comment, review_time |

---

## 数据模型

### OrganizationJoinApplication（组织加入申请）

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | AutoField | 主键 |
| applicant | ForeignKey | 申请人（User） |
| organization | ForeignKey | 目标组织（Organization） |
| application_reason | TextField | 申请理由 |
| status | CharField | 申请状态（pending/approved/rejected/cancelled） |
| reviewer | ForeignKey | 审核人（User，可为空） |
| review_comment | TextField | 审核意见（可为空） |
| reviewed_at | DateTimeField | 审核时间（可为空） |
| created_at | DateTimeField | 创建时间 |
| updated_at | DateTimeField | 更新时间 |

### 状态流转

```
pending（待审核）
    ├── approved（已通过）
    ├── rejected（已拒绝）
    └── cancelled（已取消）
```

---

## 权限控制

### 用户权限

| 操作 | 普通用户 | 组织成员 | 组织管理员 | 组织所有者 |
|------|----------|----------|------------|------------|
| 退出组织 | ❌ | ✅ | ✅ | ❌ |
| 申请加入组织 | ✅ | ❌ | ❌ | ❌ |
| 查看我的申请 | ✅ | ✅ | ✅ | ✅ |
| 取消申请 | ✅ | ✅ | ✅ | ✅ |
| 查看组织申请列表 | ❌ | ❌ | ✅ | ✅ |
| 审核申请 | ❌ | ❌ | ✅ | ✅ |
| 通过邀请码加入 | ✅ | ❌ | ❌ | ❌ |

### 业务规则

1. **用户只能加入一个组织**: 用户在任何时候只能属于一个组织
2. **所有者不能退出**: 组织所有者不能直接退出组织，需要先转让所有权
3. **只能申请已认证组织**: 用户只能申请加入状态为 `verified` 的组织
4. **重复申请限制**: 用户不能向同一组织重复提交待审核的申请
5. **审核权限**: 只有组织管理员和所有者可以审核申请
6. **邀请码限制**: 邀请码有使用次数限制和有效期限制

---

## 错误处理

### 常见错误码

| 错误码 | 说明 | 解决方案 |
|--------|------|----------|
| 400 | 请求参数错误 | 检查请求参数格式和内容 |
| 401 | 未认证 | 检查认证token是否有效 |
| 403 | 权限不足 | 检查用户权限和组织角色 |
| 404 | 资源不存在 | 检查资源ID是否正确 |
| 500 | 服务器内部错误 | 联系技术支持 |

### 错误处理建议

1. **客户端应该处理所有可能的错误响应**
2. **对于网络错误，建议实现重试机制**
3. **对于权限错误，应该引导用户到正确的页面**
4. **对于参数错误，应该显示具体的错误信息**

---

## 使用示例

### JavaScript 示例

```javascript
// 申请加入组织
async function applyJoinOrganization(organizationId, reason) {
    try {
        const response = await fetch('/api/organization/apply-join/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                organization_id: organizationId,
                application_reason: reason
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            console.log('申请提交成功:', result.message);
            return result.data;
        } else {
            console.error('申请失败:', result.message);
            throw new Error(result.message);
        }
    } catch (error) {
        console.error('网络错误:', error);
        throw error;
    }
}

// 审核申请
async function reviewApplication(applicationId, action, comment) {
    try {
        const response = await fetch(`/api/organization/applications/${applicationId}/review/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                action: action,
                review_comment: comment
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            console.log('审核完成:', result.message);
            return result.data;
        } else {
            console.error('审核失败:', result.message);
            throw new Error(result.message);
        }
    } catch (error) {
        console.error('网络错误:', error);
        throw error;
    }
}
```

### Python 示例

```python
import requests

class OrganizationAPI:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
    
    def apply_join_organization(self, organization_id, reason):
        """申请加入组织"""
        url = f"{self.base_url}/api/organization/apply-join/"
        data = {
            'organization_id': organization_id,
            'application_reason': reason
        }
        
        response = requests.post(url, json=data, headers=self.headers)
        result = response.json()
        
        if result['success']:
            return result['data']
        else:
            raise Exception(result['message'])
    
    def get_my_applications(self, status=None, page=1, page_size=10):
        """获取我的申请列表"""
        url = f"{self.base_url}/api/organization/my-applications/"
        params = {'page': page, 'page_size': page_size}
        if status:
            params['status'] = status
        
        response = requests.get(url, params=params, headers=self.headers)
        result = response.json()
        
        if result['success']:
            return result['data']
        else:
            raise Exception(result['message'])
    
    def review_application(self, application_id, action, comment=None):
        """审核申请"""
        url = f"{self.base_url}/api/organization/applications/{application_id}/review/"
        data = {'action': action}
        if comment:
            data['review_comment'] = comment
        
        response = requests.post(url, json=data, headers=self.headers)
        result = response.json()
        
        if result['success']:
            return result['data']
        else:
            raise Exception(result['message'])

# 使用示例
api = OrganizationAPI('https://api.example.com', 'your_token_here')

# 申请加入组织
try:
    result = api.apply_join_organization(123, "我希望加入这个组织...")
    print(f"申请ID: {result['application_id']}")
except Exception as e:
    print(f"申请失败: {e}")

# 审核申请
try:
    result = api.review_application(456, 'approve', '申请通过')
    print(f"审核完成: {result['status']}")
except Exception as e:
    print(f"审核失败: {e}")
```

---

## 版本信息

- **文档版本**: 1.0.0
- **API版本**: v1
- **最后更新**: 2024-01-15
- **维护者**: 开发团队

---

## 联系方式

如有问题或建议，请联系：
- **技术支持**: tech-support@example.com
- **API文档**: https://docs.example.com/api
- **问题反馈**: https://github.com/example/issues