# 环境设置指南

本项目提供了多种环境设置方式，适用于不同的开发和部署场景。

## 文件说明

### 1. `environment.yml` - Conda环境配置文件
**用途**: Conda环境的声明式配置文件
**适用场景**: 
- ✅ **远程Linux服务器部署**（推荐）
- ✅ 跨平台环境一致性
- ✅ 包含复杂系统依赖的项目

**使用方法**:
```bash
# 创建环境
conda env create -f environment.yml

# 激活环境
conda activate project_zhihui

# 更新环境
conda env update -f environment.yml
```

### 2. `conda_setup.sh` - Conda自动化设置脚本
**用途**: Linux/macOS下的Conda环境自动化设置
**适用场景**:
- ✅ **远程服务器一键部署**（推荐）
- ✅ 自动化CI/CD流程
- ✅ 批量服务器部署

**使用方法**:
```bash
# 赋予执行权限
chmod +x conda_setup.sh

# 创建并验证环境
./conda_setup.sh create

# 仅验证环境
./conda_setup.sh verify

# 清理环境
./conda_setup.sh clean
```

### 3. `venv_setup.ps1` - Windows虚拟环境脚本
**用途**: Windows开发环境的虚拟环境管理
**适用场景**:
- ✅ **Windows本地开发**
- ✅ 不使用Conda的Windows环境
- ✅ 轻量级开发环境

**使用方法**:
```powershell
# 创建虚拟环境
.\venv_setup.ps1 create

# 激活环境
.\venv_setup.ps1 activate

# 安装依赖
.\venv_setup.ps1 install

# 检查环境
.\venv_setup.ps1 check
```

## 推荐使用场景

### 🖥️ 本地开发环境

#### Windows开发者
```powershell
# 使用PowerShell脚本
.\venv_setup.ps1 create
.\venv_setup.ps1 activate
.\venv_setup.ps1 install
```

#### Linux/macOS开发者
```bash
# 使用Conda（推荐）
conda env create -f environment.yml
conda activate project_zhihui
```

### 🚀 远程服务器部署

#### 生产/测试服务器（推荐）
```bash
# 一键部署
chmod +x conda_setup.sh
./conda_setup.sh create
```

#### 简单部署
```bash
# 手动使用配置文件
conda env create -f environment.yml
conda activate project_zhihui
```

## 文件对比

| 特性 | environment.yml | conda_setup.sh | venv_setup.ps1 |
|------|----------------|----------------|----------------|
| 平台 | 跨平台 | Linux/macOS | Windows |
| 环境管理 | Conda | Conda | venv |
| 自动化程度 | 中等 | 高 | 高 |
| 系统依赖处理 | ✅ | ✅ | ❌ |
| 错误处理 | 基础 | 完善 | 完善 |
| 交互式操作 | ❌ | ✅ | ✅ |
| 环境验证 | ❌ | ✅ | ✅ |

## 最佳实践建议

### 1. **开发阶段**
- Windows: 使用 `venv_setup.ps1`
- Linux/macOS: 使用 `environment.yml` + conda命令

### 2. **部署阶段**
- 服务器部署: 使用 `conda_setup.sh`（一键部署）
- 容器化部署: 使用 `environment.yml`

### 3. **团队协作**
- 统一使用 `environment.yml` 确保环境一致性
- 提供平台特定的脚本便于快速上手

## 环境选择决策树

```
是否为远程服务器部署？
├── 是 → 使用 conda_setup.sh（自动化）
│   └── 或 environment.yml（手动）
└── 否 → 本地开发
    ├── Windows → venv_setup.ps1
    └── Linux/macOS → environment.yml + conda
```

## 维护说明

### 更新依赖时
1. 修改 `requirements.txt` 或 `requirements.in`
2. 更新 `environment.yml` 中的pip依赖
3. 测试所有脚本的兼容性

### 添加系统依赖时
1. 在 `environment.yml` 中添加conda依赖
2. 在 `conda_setup.sh` 中添加安装逻辑
3. 在文档中说明Windows下的手动安装步骤

## 故障排除

### 常见问题
1. **权限问题**: 确保脚本有执行权限
2. **路径问题**: 在项目根目录执行脚本
3. **依赖冲突**: 删除现有环境重新创建
4. **网络问题**: 配置conda/pip镜像源

### 环境重置
```bash
# Conda环境
conda env remove -n project_zhihui
./conda_setup.sh create

# venv环境
rm -rf zhihui_venv  # Linux/macOS
Remove-Item -Recurse zhihui_venv  # Windows
.\venv_setup.ps1 create
```