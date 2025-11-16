# 虚拟环境管理脚本
# 使用方法: .\venv_setup.ps1 [create|activate|install|check|freeze]

param(
    [Parameter(Mandatory=$false)]
    [string]$Action = "check"
)

$VenvName = "zhihui_venv"
$VenvPath = ".\$VenvName"

function Show-Help {
    Write-Host "虚拟环境管理脚本使用说明:" -ForegroundColor Green
    Write-Host "  .\venv_setup.ps1 create   - 创建新的虚拟环境" -ForegroundColor Yellow
    Write-Host "  .\venv_setup.ps1 activate - 激活虚拟环境" -ForegroundColor Yellow
    Write-Host "  .\venv_setup.ps1 install  - 安装依赖包" -ForegroundColor Yellow
    Write-Host "  .\venv_setup.ps1 check    - 检查当前环境状态" -ForegroundColor Yellow
    Write-Host "  .\venv_setup.ps1 freeze   - 导出当前环境的包列表" -ForegroundColor Yellow
    Write-Host "  .\venv_setup.ps1 help     - 显示帮助信息" -ForegroundColor Yellow
}

function Create-VirtualEnv {
    Write-Host "创建虚拟环境: $VenvName" -ForegroundColor Green
    if (Test-Path $VenvPath) {
        Write-Host "虚拟环境已存在: $VenvPath" -ForegroundColor Yellow
        return
    }
    
    python -m venv $VenvPath
    if ($LASTEXITCODE -eq 0) {
        Write-Host "虚拟环境创建成功!" -ForegroundColor Green
        Write-Host "激活命令: $VenvPath\Scripts\Activate.ps1" -ForegroundColor Cyan
    } else {
        Write-Host "虚拟环境创建失败!" -ForegroundColor Red
    }
}

function Activate-VirtualEnv {
    if (Test-Path "$VenvPath\Scripts\Activate.ps1") {
        Write-Host "激活虚拟环境: $VenvName" -ForegroundColor Green
        & "$VenvPath\Scripts\Activate.ps1"
    } else {
        Write-Host "虚拟环境不存在，请先创建: .\venv_setup.ps1 create" -ForegroundColor Red
    }
}

function Install-Dependencies {
    Write-Host "安装项目依赖..." -ForegroundColor Green
    if (Test-Path "requirements.txt") {
        pip install -r requirements.txt
        if ($LASTEXITCODE -eq 0) {
            Write-Host "依赖安装完成!" -ForegroundColor Green
        } else {
            Write-Host "依赖安装失败!" -ForegroundColor Red
        }
    } else {
        Write-Host "未找到 requirements.txt 文件!" -ForegroundColor Red
    }
}

function Check-Environment {
    Write-Host "=== 环境状态检查 ===" -ForegroundColor Green
    
    # 检查Python版本
    Write-Host "Python版本:" -ForegroundColor Cyan
    python --version
    
    # 检查虚拟环境
    if ($env:VIRTUAL_ENV) {
        Write-Host "当前虚拟环境: $env:VIRTUAL_ENV" -ForegroundColor Green
    } else {
        Write-Host "未在虚拟环境中运行" -ForegroundColor Yellow
    }
    
    # 检查pip版本
    Write-Host "pip版本:" -ForegroundColor Cyan
    pip --version
    
    # 检查依赖
    Write-Host "检查依赖完整性:" -ForegroundColor Cyan
    pip check
    
    # 显示已安装的核心包
    Write-Host "核心依赖包:" -ForegroundColor Cyan
    pip list | Select-String "Django|redis|celery|mysql"
}

function Freeze-Requirements {
    Write-Host "导出当前环境包列表..." -ForegroundColor Green
    pip freeze > requirements_current.txt
    Write-Host "包列表已保存到 requirements_current.txt" -ForegroundColor Green
}

# 主逻辑
switch ($Action.ToLower()) {
    "create" { Create-VirtualEnv }
    "activate" { Activate-VirtualEnv }
    "install" { Install-Dependencies }
    "check" { Check-Environment }
    "freeze" { Freeze-Requirements }
    "help" { Show-Help }
    default { 
        Write-Host "未知操作: $Action" -ForegroundColor Red
        Show-Help 
    }
}