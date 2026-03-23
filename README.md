# 🏭 HALO+ 新质生产力评价系统 (HALO+ Evaluation System)

![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30%2B-FF4B4B)
![License](https://img.shields.io/badge/license-MIT-green)

👉 **[点击访问在线交互系统 (Live Demo)](https://halo-evaluation-system.streamlit.app/)**

## 📖 项目简介
**HALO+ 新质生产力评价系统**是一个基于量化研究模型开发的云端 SaaS 平台。本项目旨在打破传统财务评价指标的局限，通过构建 **H.A.（资本/硬资产）、L.O.（产业链/专利）、I（智能化）、E（ESG生态）** 四大核心维度，对全市场 A 股企业及中小微企业的“新质生产力”水平进行多维度的量化评估、趋势回溯与排名优选。

系统前端采用赛博朋克/科幻金融风 UI 设计，底层基于 Python 与 Pandas 构建高性能数据计算引擎，为金融机构、行业研究员及企业管理者提供专业的数据诊断与决策支持工作台。

## ✨ 核心功能模块

* **🔍 1. 单体企业深度诊断**
  * 支持全市场 A 股名称/代码模糊搜索。
  * 自动呈现历年 HALO+ 综合得分折线趋势图。
  * 动态雷达图剖析四大维度长短板，并展示全市场与申万细分行业双维度绝对排名。
* **📂 2. 批量客户库智能筛查**
  * 支持直接从 Excel 复制粘贴企业名单（免文件上传极简交互）。
  * 动态阈值滑动条：自定义“合格分数线”，系统自动剔除无效名单并输出高分优质企业库，支持一键导出。
* **🏆 3. 多维百分位排名与隐形冠军挖掘**
  * **Top X% 百分位选股器**：支持按“全市场”或“指定申万细分行业”筛选前 X% 的头部企业。
  * **“专精特新”挖掘机制**：独创算法过滤市场巨头，精准定位技术硬核（L.O.、I 高分）但资金受限（H.A. 较弱）的“隐形冠军”潜力股。
* **💻 4. 本地数据在线计算引擎 (SaaS 模式)**
  * 提供标准数据上传模板。用户上传私域财务及经营数据后，系统调用内置量化模型自动进行极值标准化（Min-Max Normalization）与加权运算。
  * **隐私保护**：计算过程仅在本地浏览器进行，确保核心商业数据不触网、不泄露。

## ⚙️ 快速本地部署 (Local Installation)

如果您希望在本地环境中运行此系统，请按照以下步骤操作：

1. **克隆代码仓库**
```bash
git clone [https://github.com/TwinkleStella/halo-dashboard.git](https://github.com/TwinkleStella/halo-dashboard.git)
cd halo-dashboard
安装核心依赖库

Bash
pip install -r requirements.txt
数据文件准备
请确保项目根目录下包含以下基础数据文件（由于数据隐私限制，部分核心底稿未开源）：

HALO_total_score.csv：系统主数据库（包含企业代码、名称、年份及各项得分）。

申万行业分类_cleaned.csv：行业映射字典。

启动 Streamlit 交互系统

Bash
streamlit run app.py
启动后，浏览器将自动打开 http://localhost:8501 访问系统。

📁 项目结构 (Project Structure)
Plaintext
halo-dashboard/
├── .streamlit/
│   └── config.toml           # 强制暗黑模式及科幻蓝绿主题 UI 配置文件
├── app.py                    # 核心系统程序：包含四大功能模块与前后端交互逻辑
├── requirements.txt          # Python 第三方依赖环境清单
├── HALO_total_score.csv      # 底层量化计算结果主库 (运行依赖)
└── 申万行业分类_cleaned.csv  # 行业名称及代码映射字典 (运行依赖)
📜 声明与开源协议 (License)
本项目为学术研究与探索性质的量化评价系统展示。
本项目采用 MIT License 协议开源。
