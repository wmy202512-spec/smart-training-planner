# Smart Training Planner

<div align="center">

🏃 **AI 驱动的智能训练规划助手**

通过与 AI 教练对话，为您量身定制个性化运动训练计划

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.3+-green.svg)](https://flask.palletsprojects.com/)
[![Vue](https://img.shields.io/badge/Vue-3.0-brightgreen.svg)](https://vuejs.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## ✨ 特性

- 🤖 **AI 智能对话** - 与 AI 教练自然交流，描述您的运动目标和身体状况
- 📋 **个性化计划** - 自动生成适合您的训练计划（跳绳、跑步、力量训练等）
- 📅 **卡片式进度** - 直观的卡片界面，按天展示训练内容
- ✅ **打卡追踪** - 完成训练后打卡解锁，记录您的进步
- 📊 **多用户支持** - 独立账户系统，每个人都有自己的训练计划
- 🎯 **模板库** - 内置经典训练模板，全屏详情页展示，可折叠卡片查看每日训练安排

## 🎯 适用场景

- 🏃‍♂️ **跑步入门** - 从零开始的跑步训练计划
- 🪢 **跳绳挑战** - 16 天跳绳进阶计划
- 💪 **力量训练** - 居家健身、增肌塑形
- 🧘 **瑜伽拉伸** - 柔韧性提升计划
- 🚴 **有氧运动** - 骑行、游泳等多种运动

## 🚀 快速开始

### 环境要求

- Python 3.8+
- pip

### 安装步骤

1. **克隆仓库**
   ```bash
   git clone https://github.com/your-username/smart-training-planner.git
   cd smart-training-planner
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **初始化数据库**
   ```bash
   python import_data.py
   ```

4. **启动应用**
   ```bash
   python app.py
   ```

5. **访问应用**
   
   打开浏览器访问：`http://localhost:5051`

### 首次使用

1. 注册账号或使用默认口令登录
2. 点击"与 AI 教练对话"
3. 描述您的运动目标，例如：
   - "我想开始跑步，但是零基础"
   - "帮我制定一个 16 天的跳绳计划"
   - "我想在家练力量，每天 30 分钟"
4. AI 教练会为您生成个性化训练计划
5. 每天完成训练后打卡，解锁下一天的内容

## 📸 功能预览

### 训练计划卡片
- 按天展示训练内容
- 卡片式设计，清晰直观
- 完成打卡后自动解锁下一天

### AI 对话助手
- 自然语言交流
- 智能理解您的需求
- 实时生成训练计划

### 进度追踪
- 查看历史打卡记录
- 统计训练天数
- 多计划并行管理

## 🛠️ 技术栈

- **后端**: Flask 2.3+
- **前端**: Vue 3 + Element Plus
- **数据库**: SQLite
- **AI**: LLM API (支持自定义模型)

## 📂 项目结构

```
smart-training-planner/
├── app.py              # Flask 后端主程序
├── import_data.py      # 数据库初始化脚本
├── requirements.txt    # Python 依赖
├── training.db         # SQLite 数据库（自动生成）
├── templates/
│   └── index.html      # 前端页面
├── static/             # 静态资源
└── README.md           # 本文件
```

## 🔧 配置说明

### LLM 配置（必需）

在项目根目录创建 `.env` 文件，配置 LLM API：

```bash
# 复制示例文件
cp .env.example .env

# 编辑 .env 文件，填入您的配置
LLM_BASE_URL=your_llm_api_endpoint
LLM_API_KEY=your_api_key
LLM_MODEL=your_model_name
```

### 其他环境变量（可选）

```bash
# 自定义访问口令
export APP_PASSCODE="your_custom_passcode"

# Flask 密钥
export SECRET_KEY="your_secret_key"
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 💡 常见问题

**Q: 如何更换 AI 模型？**  
A: 修改 `app.py` 中的 `LLM_BASE`、`LLM_KEY` 和 `LLM_MODEL` 配置即可。

**Q: 数据存储在哪里？**  
A: 所有数据存储在本地 SQLite 数据库 `training.db` 中，完全私密。

**Q: 可以同时管理多个训练计划吗？**  
A: 可以！系统支持创建和管理多个并行的训练计划。

**Q: 如何备份我的训练数据？**  
A: 直接复制 `training.db` 文件即可备份所有数据。

## 📮 联系方式

如有问题或建议，欢迎通过 Issue 联系我们。

---

<div align="center">

**开始您的智能训练之旅吧！** 🎉

</div>
