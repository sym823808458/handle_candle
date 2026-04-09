# 主页读憨豆看Le

面向科学问题的本地文献调研工具：用 Edge 打开文献页面、复制具体内容交给大语言模型分析，不止摘要，支持引用扩展、全文下载与本地工作流。

## 项目定位

这是一个面向科研工作者的 Windows 桌面文献调研工具，服务于“围绕某个科学问题做连续、多轮、可追溯的文献调研”。

它不是普通的摘要检索工具。对于很多真实科研场景，只有摘要远远不够，必须尽可能拿到页面中的具体信息，必要时进一步下载全文。本项目的核心思路，就是调用 Edge 打开文献页面，自动复制页面中的可读内容，再把复制结果交给大语言模型进行结构化分析、相关性评分、研究脉络整理和后续扩展。

这也是它最大的特色和优势：不是只依赖数据库中的摘要字段，而是尽可能把研究者真正看到的文献页面内容送入模型。

## 为什么和常见文献 AI 工具有所不同

- 不只做摘要级检索，而是尽量读取文献页面中的具体内容
- 不只给一次性答案，而是把搜索、分析、扩展、下载串成闭环流程
- 不只停留在在线问答，而是落到本地文件、日志、报告和 Zotero 工作流
- 不只面向泛搜索，而是面向“围绕具体科学问题持续推进”的研究任务

## 核心亮点

- 基于科学问题驱动的多轮文献调研
- 用 Edge 打开文献页面并复制可读内容给 LLM 分析
- 支持引用网络扩展和高质量文献筛选
- 支持进一步下载全文并沉淀到本地流程
- 本地保存 URL、分析结果、日志、HTML 报告，方便复核与回溯
- 模块化 GUI，适合手动控制和后续 Agent 化改造

## 最初设想

这个项目最初的设想，是在没有人值守的时候，也能通过控制鼠标和键盘去执行文献调研流程，尤其适合围绕某个科学问题进行持续搜索、页面阅读、信息复制、模型分析、引用扩展和全文下载。

换句话说，它想模拟的不是“再做一个文献聊天框”，而是“让程序像研究者助手一样，真正去打开网页、读取页面、整理内容并推进调研任务”。

## 面向人群

- 围绕具体科学问题做文献调研的科研人员
- 需要批量筛选、比对和沉淀论文信息的研究生与博士后
- 希望把搜索、阅读、筛选、扩展、下载串起来的课题组
- 需要在本地保留研究过程和结果证据链的用户

## 适用场景

- 新方向快速摸底
- 针对具体科学问题做多轮文献扩展
- 批量筛选高相关论文
- 生成研究脉络、时间线、方法学分析报告
- 下载 PDF 并沉淀到 Zotero

## 快速开始

安装依赖：

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

或者直接运行：

```bat
install.bat
```

配置 API key，推荐使用环境变量：

```powershell
$env:DEEPSEEK_API_KEY="your_api_key_here"
python modular_research_gui.py
```

如果你不想设置环境变量，也可以直接启动 GUI，然后在界面中手动输入 API key。

启动主界面：

```bash
python modular_research_gui.py
```

启动 PDF 文件夹分析工具：

```bash
python pdf_analysis_gui.py
```

## 系统要求

- Windows 10/11
- Python 3.9+
- Microsoft Edge
- Zotero（PDF 下载功能需要）

## 公开仓库说明

这个公开副本已经做过脱敏处理：

- 不包含任何真实 API key
- 默认从环境变量 `DEEPSEEK_API_KEY` 读取密钥
- 原始日常使用版本未被修改

## 项目结构

```text
LLM_Literature_Research_Tool/
├── modular_research_gui.py
├── enhanced_research_system.py
├── web_content_extractor.py
├── high_quality_analyzer.py
├── pdf_analysis_gui.py
├── pdf_processor.py
├── pdfdownloaderzotero2.py
├── requirements.txt
├── start.bat
├── install.bat
└── LICENSE
```

## 工作流概览

1. 输入研究问题
2. 生成英文查询并执行学术搜索
3. 保存 URL 列表
4. 提取网页或 PDF 内容
5. 调用 LLM 做结构化分析与评分
6. 生成高质量文献深度报告
7. 基于引用或被引关系继续扩展
8. 批量下载 PDF 到 Zotero

## 当前实现特点

- 搜索与分析流程本地可控，适合研究者自己调参
- 支持特殊网络服务接入后的二次分析和整理
- 结果可复核，不是一次性黑箱回答
- 比很多只做联网问答的 Agent 更接近真实科研生产流程

## 注意事项

- `web_content_extractor.py` 和 PDF 下载模块高度依赖 Windows 桌面自动化
- 某些站点可能需要机构权限、代理或额外访问条件
- 这个仓库目前更适合作为“研究工作流工具”，而不是通用 Python 包

## 作者

Yuming Su / 苏禹铭，现任 Assistant Researcher，工作于中国厦门的 AI4EC Lab, Tan Kah Kee Innovation Laboratory (IKKEM)。

研究方向主要包括：

- 机器学习与大语言模型在化学中的应用
- 结构-活性关系研究
- 双光子吸收相关理论与数据分析
- 面向分子与材料问题的理论计算与智能工作流

更多个人信息、论文列表和软件工作可见：

- [Yuming Su Homepage](https://sym823808458.github.io/yumingsu_homepage/)

## License

本项目采用 [MIT License](LICENSE)。

## 免责声明

本项目仅供学术研究与个人工作流整理使用。请遵守目标网站、API 服务、文献数据库和期刊平台的使用条款。
