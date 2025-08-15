# 校企对接平台 - 项目管理API文档

## 概述

本文档描述了校企对接平台项目管理相关API接口，包括项目的创建、查看、更新、删除以及项目成员管理等功能。

## 基础信息

- **基础URL**: `/api/v1/projects/`
- **认证方式**: JWT Bearer Token
- **内容类型**: `application/json`
- **字符编码**: `UTF-8`

## 响应格式

所有API响应都遵循统一的格式：

### 成功响应
```json
{
    "status": "success",
    "code": 200,
    "message": "操作成功",
    "data": {
        // 具体数据
    },
    "error": {}
}
```

### 失败响应
```json
{
    "status": "error",
    "code": 422,
    "message": "验证失败",
    "data": {},
    "error": {
        "field_name": ["错误信息"]
    }
}
```

## 数据模型

### Project 模型
- `id`: 项目ID (UUID)
- `name`: 项目名称
- `description`: 项目描述
- `creator`: 项目创建者信息
- `status`: 项目状态 (`planning`, `active`, `completed`, `cancelled`)
- `start_date`: 项目开始日期
- `end_date`: 项目结束日期
- `budget`: 项目预算
- `requirements`: 项目需求
- `skills_required`: 所需技能列表
- `created_at`: 创建时间
- `updated_at`: 更新时间

### ProjectMember 模型
- `id`: 成员ID
- `project`: 关联项目
- `user`: 关联用户信息
- `role`: 成员角色 (`owner`, `admin`, `member`, `viewer`)
- `status`: 成员状态 (`active`, `inactive`, `pending`)
- `joined_at`: 加入时间
- `left_at`: 离开时间

## API接口

### 1. 项目列表

**接口**: `GET /api/v1/projects/`
**描述**: 获取项目列表，支持分页和筛选
**权限**: 认证用户

#### 请求头
```
Authorization: Bearer <access_token>
```

#### 查询参数
- `page`: 页码 (默认: 1)
- `page_size`: 每页数量 (默认: 10, 最大: 100)
- `status`: 项目状态筛选
- `search`: 搜索关键词（项目名称、描述）
- `creator`: 创建者ID筛选
- `ordering`: 排序字段 (`created_at`, `-created_at`, `name`, `-name`)

#### 请求示例
```
GET /api/v1/projects/?page=1&page_size=10&status=active&search=AI&ordering=-created_at
```

#### 响应示例
```json
{
    "status": "success",
    "code": 200,
    "message": "操作成功",
    "data": {
        "count": 25,
        "next": "http://localhost:8000/api/v1/projects/?page=2",
        "previous": null,
        "results": [
            {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "AI智能客服系统",
                "description": "基于深度学习的智能客服系统开发项目",
                "creator": {
                    "id": "550e8400-e29b-41d4-a716-446655440001",
                    "username": "company_admin",
                    "real_name": "张经理",
                    "user_type": "company"
                },
                "status": "active",
                "status_display": "进行中",
                "start_date": "2024-01-01",
                "end_date": "2024-06-30",
                "budget": 500000.00,
                "requirements": "开发一个基于AI的智能客服系统，支持多轮对话",
                "skills_required": ["Python", "TensorFlow", "NLP", "Django"],
                "member_count": 5,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-02T10:30:00Z"
            }
        ]
    },
    "error": {}
}
```

### 2. 创建项目

**接口**: `POST /api/v1/projects/`
**描述**: 创建新项目
**权限**: 认证用户（企业用户或管理员）

#### 请求头
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

#### 请求参数
```json
{
    "name": "移动应用开发项目",
    "description": "开发一款跨平台移动应用，支持iOS和Android",
    "status": "planning",
    "start_date": "2024-03-01",
    "end_date": "2024-08-31",
    "budget": 800000.00,
    "requirements": "开发一款功能完整的移动应用，包括用户管理、内容展示、支付功能等",
    "skills_required": ["React Native", "JavaScript", "Node.js", "MongoDB"]
}
```

#### 响应示例
```json
{
    "status": "success",
    "code": 201,
    "message": "项目创建成功",
    "data": {
        "id": "550e8400-e29b-41d4-a716-446655440004",
        "name": "移动应用开发项目",
        "description": "开发一款跨平台移动应用，支持iOS和Android",
        "creator": {
            "id": "550e8400-e29b-41d4-a716-446655440001",
            "username": "company_admin",
            "real_name": "张经理",
            "user_type": "company"
        },
        "status": "planning",
        "status_display": "规划中",
        "start_date": "2024-03-01",
        "end_date": "2024-08-31",
        "budget": 800000.00,
        "requirements": "开发一款功能完整的移动应用，包括用户管理、内容展示、支付功能等",
        "skills_required": ["React Native", "JavaScript", "Node.js", "MongoDB"],
        "member_count": 1,
        "created_at": "2024-01-20T15:30:00Z",
        "updated_at": "2024-01-20T15:30:00Z"
    },
    "error": {}
}
```

### 3. 项目详情

**接口**: `GET /api/v1/projects/{project_id}/`
**描述**: 获取指定项目的详细信息
**权限**: 认证用户（项目成员或公开项目）

#### 请求头
```
Authorization: Bearer <access_token>
```

#### 响应示例
```json
{
    "status": "success",
    "code": 200,
    "message": "操作成功",
    "data": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "AI智能客服系统",
        "description": "基于深度学习的智能客服系统开发项目，旨在提升客户服务效率和质量",
        "creator": {
            "id": "550e8400-e29b-41d4-a716-446655440001",
            "username": "company_admin",
            "real_name": "张经理",
            "user_type": "company",
            "avatar": "http://localhost:8000/media/avatars/company_avatar.jpg"
        },
        "status": "active",
        "status_display": "进行中",
        "start_date": "2024-01-01",
        "end_date": "2024-06-30",
        "budget": 500000.00,
        "requirements": "开发一个基于AI的智能客服系统，支持多轮对话、情感分析、知识库检索等功能",
        "skills_required": ["Python", "TensorFlow", "NLP", "Django", "Redis", "PostgreSQL"],
        "member_count": 5,
        "current_user_role": "member",
        "current_user_status": "active",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-02T10:30:00Z"
    },
    "error": {}
}
```

### 4. 更新项目

**接口**: `PUT /api/v1/projects/{project_id}/`
**描述**: 更新指定项目的信息
**权限**: 项目创建者或管理员

#### 请求头
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

#### 请求参数
```json
{
    "name": "AI智能客服系统 v2.0",
    "description": "升级版AI智能客服系统，新增语音识别功能",
    "status": "active",
    "end_date": "2024-07-31",
    "budget": 600000.00,
    "requirements": "在原有功能基础上，新增语音识别和语音合成功能",
    "skills_required": ["Python", "TensorFlow", "NLP", "Django", "Redis", "PostgreSQL", "Speech Recognition"]
}
```

#### 响应示例
```json
{
    "status": "success",
    "code": 200,
    "message": "项目更新成功",
    "data": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "AI智能客服系统 v2.0",
        "description": "升级版AI智能客服系统，新增语音识别功能",
        "creator": {
            "id": "550e8400-e29b-41d4-a716-446655440001",
            "username": "company_admin",
            "real_name": "张经理",
            "user_type": "company"
        },
        "status": "active",
        "status_display": "进行中",
        "start_date": "2024-01-01",
        "end_date": "2024-07-31",
        "budget": 600000.00,
        "requirements": "在原有功能基础上，新增语音识别和语音合成功能",
        "skills_required": ["Python", "TensorFlow", "NLP", "Django", "Redis", "PostgreSQL", "Speech Recognition"],
        "member_count": 5,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-20T16:45:00Z"
    },
    "error": {}
}
```

### 5. 删除项目

**接口**: `DELETE /api/v1/projects/{project_id}/`
**描述**: 删除指定项目
**权限**: 项目创建者或管理员

#### 请求头
```
Authorization: Bearer <access_token>
```

#### 响应示例
```json
{
    "status": "success",
    "code": 200,
    "message": "项目删除成功",
    "data": {},
    "error": {}
}
```

### 6. 获取项目成员

**接口**: `GET /api/v1/projects/{project_id}/members/`
**描述**: 获取指定项目的成员列表
**权限**: 项目成员

#### 请求头
```
Authorization: Bearer <access_token>
```

#### 查询参数
- `page`: 页码 (默认: 1)
- `page_size`: 每页数量 (默认: 10)
- `role`: 角色筛选 (`owner`, `admin`, `member`, `viewer`)
- `status`: 状态筛选 (`active`, `inactive`, `pending`)

#### 响应示例
```json
{
    "status": "success",
    "code": 200,
    "message": "操作成功",
    "data": {
        "count": 5,
        "next": null,
        "previous": null,
        "results": [
            {
                "id": 1,
                "user": {
                    "id": "550e8400-e29b-41d4-a716-446655440001",
                    "username": "company_admin",
                    "real_name": "张经理",
                    "user_type": "company",
                    "avatar": "http://localhost:8000/media/avatars/company_avatar.jpg"
                },
                "role": "owner",
                "role_display": "项目负责人",
                "status": "active",
                "status_display": "活跃",
                "joined_at": "2024-01-01T00:00:00Z",
                "left_at": null
            },
            {
                "id": 2,
                "user": {
                    "id": "550e8400-e29b-41d4-a716-446655440005",
                    "username": "student_dev",
                    "real_name": "李同学",
                    "user_type": "student",
                    "avatar": "http://localhost:8000/media/avatars/student_avatar.jpg"
                },
                "role": "member",
                "role_display": "项目成员",
                "status": "active",
                "status_display": "活跃",
                "joined_at": "2024-01-05T10:00:00Z",
                "left_at": null
            }
        ]
    },
    "error": {}
}
```

### 7. 添加项目成员

**接口**: `POST /api/v1/projects/{project_id}/members/`
**描述**: 向指定项目添加成员
**权限**: 项目负责人或管理员

#### 请求头
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

#### 请求参数
```json
{
    "user_id": "550e8400-e29b-41d4-a716-446655440006",
    "role": "member"
}
```

#### 响应示例
```json
{
    "status": "success",
    "code": 201,
    "message": "成员添加成功",
    "data": {
        "id": 3,
        "user": {
            "id": "550e8400-e29b-41d4-a716-446655440006",
            "username": "new_student",
            "real_name": "王同学",
            "user_type": "student",
            "avatar": null
        },
        "role": "member",
        "role_display": "项目成员",
        "status": "active",
        "status_display": "活跃",
        "joined_at": "2024-01-20T17:00:00Z",
        "left_at": null
    },
    "error": {}
}
```

### 8. 移除项目成员

**接口**: `DELETE /api/v1/projects/{project_id}/members/{member_id}/`
**描述**: 移除指定项目成员
**权限**: 项目负责人或管理员

#### 请求头
```
Authorization: Bearer <access_token>
```

#### 响应示例
```json
{
    "status": "success",
    "code": 200,
    "message": "成员移除成功",
    "data": {},
    "error": {}
}
```

### 9. 更新成员角色

**接口**: `PATCH /api/v1/projects/{project_id}/members/{member_id}/`
**描述**: 更新项目成员角色
**权限**: 项目负责人

#### 请求头
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

#### 请求参数
```json
{
    "role": "admin"
}
```

#### 响应示例
```json
{
    "status": "success",
    "code": 200,
    "message": "成员角色更新成功",
    "data": {
        "id": 2,
        "user": {
            "id": "550e8400-e29b-41d4-a716-446655440005",
            "username": "student_dev",
            "real_name": "李同学",
            "user_type": "student"
        },
        "role": "admin",
        "role_display": "管理员",
        "status": "active",
        "status_display": "活跃",
        "joined_at": "2024-01-05T10:00:00Z",
        "left_at": null
    },
    "error": {}
}
```

### 10. 离开项目

**接口**: `POST /api/v1/projects/{project_id}/leave/`
**描述**: 离开项目（项目负责人不能离开）
**权限**: 项目成员

#### 请求头
```
Authorization: Bearer <access_token>
```

#### 响应示例
```json
{
    "status": "success",
    "code": 200,
    "message": "已成功离开项目",
    "data": {},
    "error": {}
}
```

## 权限说明

### 角色权限
- **owner**: 项目负责人，拥有所有权限
- **admin**: 管理员，可以管理项目和成员（除了删除项目和修改负责人）
- **member**: 普通成员，可以查看项目信息和参与项目
- **viewer**: 观察者，只能查看项目基本信息

### 操作权限
- **创建项目**: 任何认证用户
- **查看项目**: 项目成员或公开项目
- **更新项目**: owner、admin
- **删除项目**: 仅owner
- **添加成员**: owner、admin
- **移除成员**: owner、admin（不能移除owner，admin不能移除其他admin）
- **更新角色**: 仅owner
- **离开项目**: 除owner外的所有成员

## 错误响应

### 常见错误码
- **400**: 请求参数错误
- **401**: 未认证
- **403**: 权限不足
- **404**: 资源不存在
- **422**: 验证失败

### 错误响应示例
```json
{
    "status": "error",
    "code": 403,
    "message": "您没有权限执行此操作",
    "data": {},
    "error": {
        "detail": "只有项目负责人可以删除项目"
    }
}
```

```json
{
    "status": "error",
    "code": 422,
    "message": "验证失败",
    "data": {},
    "error": {
        "name": ["项目名称不能为空"],
        "end_date": ["结束日期不能早于开始日期"]
    }
}
```

## 使用示例

### JavaScript 示例

#### 创建项目
```javascript
const createProject = async (projectData) => {
    const response = await fetch('/api/v1/projects/', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(projectData)
    });
    
    const result = await response.json();
    if (result.status === 'success') {
        console.log('项目创建成功:', result.data);
    } else {
        console.error('创建失败:', result.message);
    }
};

// 使用示例
createProject({
    name: "新项目",
    description: "项目描述",
    status: "planning",
    budget: 100000,
    skills_required: ["Python", "Django"]
});
```

#### 获取项目列表
```javascript
const getProjects = async (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    const response = await fetch(`/api/v1/projects/?${queryString}`, {
        headers: {
            'Authorization': `Bearer ${accessToken}`
        }
    });
    
    const result = await response.json();
    return result.data;
};

// 使用示例
getProjects({ search: 'AI', status: 'active', page: 1 });
```

### Python 示例

#### 创建项目
```python
import requests

def create_project(access_token, project_data):
    url = "http://localhost:8000/api/v1/projects/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, json=project_data, headers=headers)
    result = response.json()
    
    if result["status"] == "success":
        print("项目创建成功:", result["data"])
    else:
        print("创建失败:", result["message"])

# 使用示例
project_data = {
    "name": "新项目",
    "description": "项目描述",
    "status": "planning",
    "budget": 100000,
    "skills_required": ["Python", "Django"]
}
create_project(access_token, project_data)
```

#### 添加项目成员
```python
def add_project_member(access_token, project_id, user_id, role="member"):
    url = f"http://localhost:8000/api/v1/projects/{project_id}/members/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    data = {
        "user_id": user_id,
        "role": role
    }
    
    response = requests.post(url, json=data, headers=headers)
    result = response.json()
    
    if result["status"] == "success":
        print("成员添加成功:", result["data"])
    else:
        print("添加失败:", result["message"])
```