# StockPulse Streamlit Community Cloud 部署指南

## 部署步骤

### 第一步：在 GitHub 创建仓库

1. 打开 https://github.com/new
2. 仓库名称：`stockpulse-app`
3. 选择「Public」
4. 勾选「Add a README file」
5. 点击「Create repository」

### 第二步：上传项目文件

1. 进入刚创建的仓库
2. 点击「Add file」→「Upload files」
3. 选择以下文件和文件夹上传：
   - `app.py`
   - `streamlit_app.py`
   - `requirements.txt`
   - `.streamlit/config.toml`
   - `auth/` (整个文件夹)
   - `components/` (整个文件夹)
   - `config/` (整个文件夹)
   - `data/` (整个文件夹)
   - `database/` (整个文件夹)
   - `reports/` (整个文件夹)
   - `utils/` (整个文件夹)
   - `views/` (整个文件夹)
   - `assets/` (整个文件夹)

4. 点击「Commit changes」

### 第三步：在 Streamlit Community Cloud 部署

1. 打开 https://share.streamlit.io/
2. 点击「Sign in」登录您的 GitHub 账户
3. 点击「New app」
4. 填写信息：
   - Repository: 选择您刚创建的仓库 (username/stockpulse-app)
   - Branch: main
   - Main file path: `streamlit_app.py`
5. 点击「Deploy!」

### 第四步：等待部署完成

- 首次部署可能需要几分钟
- 部署成功后，您将获得一个公开访问的 URL

## 注意事项

1. **数据库**：Streamlit Community Cloud 使用 SQLite 数据库，数据存储在 `/tmp` 目录下，重启后数据会丢失。如需持久化数据，建议连接外部数据库。

2. **依赖安装**：Streamlit 会自动安装 `requirements.txt` 中的依赖。

3. **访问权限**：应用部署后是公开访问的，任何人都可以访问。

4. **资源限制**：免费版有资源限制，包括内存、CPU 和部署时长。

## 环境变量（可选）

如需配置环境变量，在 Streamlit Community Cloud 控制台中：
1. 点击应用 → 「Settings」→ 「Secrets」
2. 添加以下变量（如需）：
   ```
   TENCENT_CLOUDBASE=true
   ```

## 故障排除

### 部署失败

1. 检查 `requirements.txt` 是否包含所有必要依赖
2. 检查 Python 版本兼容性
3. 查看部署日志获取详细错误信息

### 应用无法启动

1. 检查 `streamlit_app.py` 是否存在
2. 检查 `app.py` 是否有语法错误
3. 查看应用日志

### 数据丢失

Streamlit Community Cloud 的免费版使用临时存储，重启后数据会丢失。如需持久化：
- 使用云数据库（如 CloudBase NoSQL）
- 使用外部数据库服务

## 升级维护

1. 在本地修改代码
2. 重新上传到 GitHub 仓库
3. Streamlit Community Cloud 会自动检测变更并重新部署