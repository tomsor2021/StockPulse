# StockPulse 腾讯云空间部署计划

## 一、项目分析

### 1.1 项目概况
- **项目名称**: StockPulse - 个人股票复盘系统
- **技术栈**: Python 3.x + Streamlit
- **数据库**: SQLite（本地文件 `StockPulse.db`）
- **入口文件**: `app.py`

### 1.2 核心依赖
```
streamlit>=1.35.0
akshare>=1.14.0
baostock>=0.9.0
plotly>=5.18.0
matplotlib>=3.8.0
bcrypt>=4.1.0
requests>=2.31.0
pandas>=2.1.0
numpy>=1.25.0
openpyxl>=3.1.0
```

### 1.3 当前运行方式
```bash
streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless=true
```

## 二、腾讯云空间部署方案

### 2.1 部署架构
腾讯云空间（云开发 CloudBase）提供免费的 Python 运行环境，支持 WSGI/ASGI 应用部署。

### 2.2 需要修改/新增的文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `server.py` | 新建 | WSGI 入口文件，适配腾讯云空间 |
| `app.yaml` | 新建 | 腾讯云空间配置文件 |
| `requirements.txt` | 修改 | 确保依赖版本兼容 |
| `config/settings.py` | 修改 | 调整数据库路径为云存储目录 |

### 2.3 部署步骤

#### 步骤一：创建 WSGI 入口文件 `server.py`
腾讯云空间需要 WSGI 入口文件来启动应用。Streamlit 支持通过 `streamlit.web.server.cli` 模块以 WSGI 方式运行。

#### 步骤二：创建云空间配置文件 `app.yaml`
配置运行环境、入口文件、端口等信息。

#### 步骤三：调整数据库路径
将 SQLite 数据库路径修改为腾讯云空间的持久化存储目录 `/tmp` 或 `/cloudbase`。

#### 步骤四：部署到腾讯云空间
使用腾讯云 CLI 或控制台进行部署。

## 三、详细配置

### 3.1 server.py 内容
```python
import os
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from streamlit.web.server.cli import main

if __name__ == "__main__":
    sys.argv = ["streamlit", "run", "app.py", "--server.port", "9000", "--server.headless", "true"]
    main()
```

### 3.2 app.yaml 内容
```yaml
env:
  - key: PYTHONPATH
    value: /app
command: python server.py
```

### 3.3 settings.py 修改
将数据库路径从项目根目录改为 `/tmp` 目录以实现持久化：
```python
# 修改前
DB_PATH = DB_DIR / "StockPulse.db"

# 修改后
DB_PATH = Path("/tmp") / "StockPulse.db"
```

## 四、潜在风险与注意事项

### 4.1 资源限制
- 腾讯云空间免费版 CPU: 0.25核
- 内存: 256MB
- 磁盘: 1GB
- **风险**: Streamlit + akshare 可能因资源不足导致运行缓慢或超时

### 4.2 依赖兼容性
- `akshare` 和 `baostock` 需要网络访问外部数据源
- **风险**: 云空间可能限制外部网络访问，导致数据获取失败

### 4.3 数据库持久化
- `/tmp` 目录在实例重启时可能会被清空
- **建议**: 使用云数据库（如腾讯云 MySQL）替代 SQLite

### 4.4 端口配置
- 腾讯云空间默认端口为 9000
- 需要在 `app.py` 和 `server.py` 中统一端口配置

## 五、部署验证

部署完成后，通过以下方式验证：
1. 访问云空间分配的域名
2. 检查登录页面是否正常显示
3. 创建测试用户并登录
4. 验证数据获取功能是否正常

## 六、备选方案

如果腾讯云空间部署遇到问题，可考虑：
1. **腾讯云轻量应用服务器**: 更稳定的运行环境，但需要付费
2. **Docker 部署**: 打包为容器后部署到腾讯云容器服务
3. **其他免费平台**: Heroku、Render 等支持 Python 应用的平台