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

## 常见问题及解决方案

### 问题：页面空白，应用未启动

**可能原因：**

1. **依赖安装失败**：Streamlit Community Cloud 无法安装某些依赖
2. **配置文件错误**：`.streamlit/config.toml` 配置不正确
3. **数据库权限问题**：应用无法在 `/tmp` 目录创建数据库文件

**解决方案：**

1. **查看部署日志**：
   - 在 Streamlit Community Cloud 控制台，点击应用
   - 点击右上角三个点 → 「View logs」
   - 检查是否有错误信息

2. **简化依赖**：
   - 确保 `requirements.txt` 中没有不兼容的依赖
   - 移除 `bcrypt`（已移除）

3. **检查数据库路径**：
   - 应用会自动在 `/tmp` 目录创建数据库
   - 如果权限问题，添加环境变量 `TENCENT_CLOUDBASE=true`

### 问题：依赖安装失败

**解决方案：**

1. 检查 `requirements.txt` 是否包含所有必要依赖
2. 尝试降低某些依赖的版本要求
3. 查看日志中具体哪个依赖安装失败

### 问题：数据丢失

Streamlit Community Cloud 的免费版使用临时存储，重启后数据会丢失。如需持久化：
- 使用云数据库（如 CloudBase NoSQL）
- 使用外部数据库服务

## 环境变量（可选）

如需配置环境变量，在 Streamlit Community Cloud 控制台中：
1. 点击应用 → 「Settings」→ 「Secrets」
2. 添加以下变量：
   ```
   TENCENT_CLOUDBASE=true
   ```

## 升级维护

1. 在本地修改代码
2. 重新上传到 GitHub 仓库
3. Streamlit Community Cloud 会自动检测变更并重新部署

## 文件变更记录

### v1.1 - 修复部署问题

- 移除 `bcrypt` 依赖（可能导致安装失败）
- 修复 `.streamlit/config.toml` 配置
- 添加错误处理到 `streamlit_app.py`