# 审核历史记录功能接口文档

## 概述

审核历史记录功能提供了完整的需求审核和组织认证审核的历史记录查询、统计分析等功能。系统会自动记录所有审核相关的操作，包括状态变更、操作者信息、审核意见等详细信息。

## 接口列表

### 1. 需求审核历史查询接口

**接口地址：** `GET /api/v1/audit/requirements/{requirement_id}/history/`

**功能描述：** 获取指定需求的审核历史记录

**权限要求：** 
- 需要用户登录认证
- 只有需求发布者、组织管理员或组织所有者可以查看

**路径参数：**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| requirement_id | integer | 是 | 需求ID |

**查询参数：**
| 参数名 | 类型 | 必填 | 默认值 | 描述 |
|--------|------|------|--------|------|
| page | integer | 否 | 1 | 页码 |
| page_size | integer | 否 | 20 | 每页数量（最大100） |
| action | string | 否 | - | 筛选操作类型 |
| operator_id | integer | 否 | - | 筛选操作者ID |
| start_date | date | 否 | - | 开始日期（YYYY-MM-DD） |
| end_date | date | 否 | - | 结束日期（YYYY-MM-DD） |

**操作类型（action）可选值：**
- `submit` - 提交审核
- `approve` - 审核通过
- `reject` - 审核拒绝
- `resubmit` - 重新提交
- `withdraw` - 撤回申请
- `auto_approve` - 自动通过
- `batch_approve` - 批量通过
- `batch_reject` - 批量拒绝

**响应格式：**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "results": [
      {
        "id": 1,
        "requirement": 123,
        "operator_info": {
          "id": 456,
          "username": "admin",
          "real_name": "管理员",
          "role": "org_admin"
        },
        "action": "approve",
        "action_display": "审核通过",
        "old_status": "under_review",
        "old_status_display": "审核中",
        "new_status": "approved",
        "new_status_display": "已通过",
        "comment": "需求符合要求，审核通过",
        "review_details": {},
        "ip_address": "192.168.1.100",
        "user_agent": "Mozilla/5.0...",
        "created_at": "2024-01-15T10:30:00Z"
      }
    ],
    "pagination": {
      "current_page": 1,
      "total_pages": 5,
      "total_count": 100,
      "page_size": 20,
      "has_next": true,
      "has_previous": false
    }
  }
}
```

### 2. 组织审核历史查询接口

**接口地址：** `GET /api/v1/audit/organizations/{organization_id}/history/`

**功能描述：** 获取指定组织的认证审核历史记录

**权限要求：** 
- 需要用户登录认证
- 只有组织所有者可以查看

**路径参数：**
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| organization_id | integer | 是 | 组织ID |

**查询参数：**
| 参数名 | 类型 | 必填 | 默认值 | 描述 |
|--------|------|------|--------|------|
| page | integer | 否 | 1 | 页码 |
| page_size | integer | 否 | 20 | 每页数量（最大100） |
| action | string | 否 | - | 筛选操作类型 |
| operator_id | integer | 否 | - | 筛选操作者ID |
| start_date | date | 否 | - | 开始日期（YYYY-MM-DD） |
| end_date | date | 否 | - | 结束日期（YYYY-MM-DD） |

**操作类型（action）可选值：**
- `submit` - 提交认证
- `approve` - 认证通过
- `reject` - 认证拒绝
- `resubmit` - 重新提交
- `update_materials` - 更新材料
- `withdraw` - 撤回申请
- `auto_approve` - 自动通过
- `batch_approve` - 批量通过
- `batch_reject` - 批量拒绝
- `suspend` - 暂停认证
- `restore` - 恢复认证

**响应格式：**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "results": [
      {
        "id": 1,
        "organization": 789,
        "operator_info": {
          "id": 456,
          "username": "admin",
          "real_name": "管理员",
          "role": "admin"
        },
        "action": "approve",
        "action_display": "认证通过",
        "old_status": "under_review",
        "old_status_display": "审核中",
        "new_status": "verified",
        "new_status_display": "已认证",
        "comment": "组织材料完整，认证通过",
        "review_details": {},
        "ip_address": "192.168.1.100",
        "user_agent": "Mozilla/5.0...",
        "created_at": "2024-01-15T10:30:00Z"
      }
    ],
    "pagination": {
      "current_page": 1,
      "total_pages": 3,
      "total_count": 50,
      "page_size": 20,
      "has_next": true,
      "has_previous": false
    }
  }
}
```

### 3. 当前用户组织审核历史查询接口

**接口地址：** `GET /api/v1/audit/organizations/my/history/`

**功能描述：** 获取当前用户所属组织的认证审核历史记录

**权限要求：** 
- 需要用户登录认证
- 只有组织管理员或组织所有者可以查看
- 用户必须属于某个已审核通过的组织

**查询参数：**
| 参数名 | 类型 | 必填 | 默认值 | 描述 |
|--------|------|------|--------|------|
| page | integer | 否 | 1 | 页码 |
| page_size | integer | 否 | 20 | 每页数量（最大100） |
| action | string | 否 | - | 筛选操作类型 |
| operator_id | integer | 否 | - | 筛选操作者ID |
| start_date | date | 否 | - | 开始日期（YYYY-MM-DD） |
| end_date | date | 否 | - | 结束日期（YYYY-MM-DD） |

**响应格式：** 与组织审核历史查询接口相同

### 4. 审核统计信息接口

**接口地址：** `GET /api/v1/audit/audit/statistics/`

**功能描述：** 获取当前用户所属组织的审核统计信息

**权限要求：** 
- 需要用户登录认证
- 只有组织管理员或组织所有者可以查看
- 用户必须属于某个已审核通过的组织

**响应格式：**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "requirement_audit_stats": {
      "total_requirements": 150,
      "under_review": 10,
      "approved": 120,
      "rejected": 20,
      "audit_logs_count": 300
    },
    "organization_audit_stats": {
      "current_status": "verified",
      "audit_logs_count": 15
    }
  }
}
```

## 数据模型

### 需求审核日志模型（RequirementAuditLog）

| 字段名 | 类型 | 描述 |
|--------|------|------|
| id | AutoField | 主键ID |
| requirement | ForeignKey | 关联需求 |
| action | CharField | 审核操作类型 |
| status_transition | CharField | 状态变更类型 |
| old_status | CharField | 原状态 |
| new_status | CharField | 新状态 |
| operator | ForeignKey | 操作者 |
| operator_role | CharField | 操作者角色 |
| comment | TextField | 审核意见 |
| review_details | JSONField | 审核详情 |
| ip_address | GenericIPAddressField | IP地址 |
| user_agent | TextField | 用户代理 |
| created_at | DateTimeField | 创建时间 |

### 组织审核日志模型（OrganizationAuditLog）

| 字段名 | 类型 | 描述 |
|--------|------|------|
| id | AutoField | 主键ID |
| organization | ForeignKey | 关联组织 |
| action | CharField | 审核操作类型 |
| status_transition | CharField | 状态变更类型 |
| old_status | CharField | 原状态 |
| new_status | CharField | 新状态 |
| operator | ForeignKey | 操作者 |
| operator_role | CharField | 操作者角色 |
| comment | TextField | 审核意见 |
| review_details | JSONField | 审核详情 |
| submitted_materials | JSONField | 提交材料信息 |
| ip_address | GenericIPAddressField | IP地址 |
| user_agent | TextField | 用户代理 |
| created_at | DateTimeField | 创建时间 |

## 错误码说明

| 错误码 | 描述 | 解决方案 |
|--------|------|----------|
| 401 | 未授权访问 | 请先登录 |
| 403 | 权限不足 | 确认用户具有相应权限 |
| 404 | 资源不存在 | 检查请求的资源ID是否正确 |
| 400 | 请求参数错误 | 检查请求参数格式和值 |
| 500 | 服务器内部错误 | 联系系统管理员 |

## 使用示例

### 1. 查询需求审核历史

```bash
# 获取需求ID为123的审核历史，按时间倒序
curl -X GET \
  'http://localhost:8000/api/v1/audit/requirements/123/history/?page=1&page_size=10' \
  -H 'Authorization: Bearer your_access_token'
```

### 2. 筛选特定操作类型的审核记录

```bash
# 只查看审核通过的记录
curl -X GET \
  'http://localhost:8000/api/v1/audit/requirements/123/history/?action=approve' \
  -H 'Authorization: Bearer your_access_token'
```

### 3. 按日期范围筛选

```bash
# 查看2024年1月的审核记录
curl -X GET \
  'http://localhost:8000/api/v1/audit/requirements/123/history/?start_date=2024-01-01&end_date=2024-01-31' \
  -H 'Authorization: Bearer your_access_token'
```

### 4. 获取审核统计信息

```bash
# 获取当前用户组织的审核统计
curl -X GET \
  'http://localhost:8000/api/v1/audit/audit/statistics/' \
  -H 'Authorization: Bearer your_access_token'
```

## 注意事项

1. **权限控制**：所有接口都需要用户登录，并且有严格的权限控制
2. **分页限制**：每页最大返回100条记录，建议使用合适的页面大小
3. **日期格式**：日期参数必须使用YYYY-MM-DD格式
4. **数据完整性**：系统会自动记录操作者IP地址和用户代理信息
5. **性能优化**：查询接口已添加数据库索引，支持高效查询
6. **数据保留**：审核历史记录会永久保存，不会被删除

## 版本信息

- **当前版本**：v1.0
- **最后更新**：2024-01-15
- **兼容性**：Django 4.x, Django REST Framework 3.x