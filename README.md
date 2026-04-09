# 主页读憨豆看Le

面向科学问题的本地文献调研工具：用 Edge 打开文献页面、复制具体内容交给大语言模型分析，不止摘要，支持引用扩展、全文下载与本地工作流。

Local literature research tool for scientific questions: it uses Edge to open paper pages, copies detailed on-page content for large language model analysis beyond abstracts, and supports citation expansion, full-text download, and local research workflows.

## 中文说明

### 项目定位

这是一个面向科研工作者的 Windows 桌面文献调研工具，服务于“围绕某个科学问题做连续、多轮、可追溯的文献调研”。

它不是普通的摘要检索工具。对于很多真实科研场景，只有摘要远远不够，必须尽可能拿到页面中的具体信息，必要时进一步下载全文。本项目的核心思路，就是调用 Edge 打开文献页面，自动复制页面中的可读内容，再把复制结果交给大语言模型进行结构化分析、相关性评分、研究脉络整理和后续扩展。

这也是它最大的特色和优势：不是只依赖数据库中的摘要字段，而是尽可能把研究者真正看到的文献页面内容送入模型。

### 为什么和常见文献 AI 工具有所不同

- 不只做摘要级检索，而是尽量读取文献页面中的具体内容
- 不只给一次性答案，而是把搜索、分析、扩展、下载串成闭环流程
- 不只停留在在线问答，而是落到本地文件、日志、报告和 Zotero 工作流
- 不只面向泛搜索，而是面向“围绕具体科学问题持续推进”的研究任务

### 核心亮点

- 基于科学问题驱动的多轮文献调研
- 用 Edge 打开文献页面并复制可读内容给 LLM 分析
- 支持引用网络扩展和高质量文献筛选
- 支持进一步下载全文并沉淀到本地流程
- 本地保存 URL、分析结果、日志、HTML 报告，方便复核与回溯
- 模块化 GUI，适合手动控制和后续 Agent 化改造

### 最初设想

这个项目最初的设想，是在没有人值守的时候，也能通过控制鼠标和键盘去执行文献调研流程，尤其适合围绕某个科学问题进行持续搜索、页面阅读、信息复制、模型分析、引用扩展和全文下载。

换句话说，它想模拟的不是“再做一个文献聊天框”，而是“让程序像研究者助手一样，真正去打开网页、读取页面、整理内容并推进调研任务”。

### 面向人群

- 围绕具体科学问题做文献调研的科研人员
- 需要批量筛选、比对和沉淀论文信息的研究生与博士后
- 希望把搜索、阅读、筛选、扩展、下载串起来的课题组
- 需要在本地保留研究过程和结果证据链的用户

### 适用场景

- 新方向快速摸底
- 针对具体科学问题做多轮文献扩展
- 批量筛选高相关论文
- 生成研究脉络、时间线、方法学分析报告
- 下载 PDF 并沉淀到 Zotero

### 快速开始

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

### 系统要求

- Windows 10/11
- Python 3.9+
- Microsoft Edge
- Zotero（PDF 下载功能需要）

## English

### Overview

This is a Windows desktop literature research tool for researchers who want to run continuous, multi-round, and traceable literature investigations around a specific scientific question.

It is not a typical abstract-only search tool. In many real research scenarios, abstracts are far from enough. Researchers need detailed information from the actual paper page, and sometimes they also need downstream access to full text. The core idea of this project is to use Edge to open paper pages, copy readable page content, and then send that copied content to a large language model for structured analysis, relevance scoring, literature synthesis, and follow-up expansion.

That is also its biggest advantage: it does not rely only on abstract fields in databases. Instead, it tries to send the actual page-level content visible to the researcher into the model.

### What Makes It Different

- It goes beyond abstract-level retrieval and tries to read detailed page content
- It does not stop at a one-shot answer, but connects search, analysis, expansion, and download into a loop
- It is not only an online chat interface, but a local workflow with files, logs, reports, and Zotero integration
- It is built for sustained research around a scientific question, not just generic search

### Key Features

- Multi-round literature investigation driven by a scientific question
- Edge-based page opening and content copying for LLM analysis
- Citation network expansion and high-quality paper filtering
- Support for further full-text download and local workflow integration
- Local persistence of URLs, analysis results, logs, and HTML reports for reviewability
- Modular GUI design that is friendly to manual use and future agent-oriented extensions

### Original Vision

The original vision of this project was to let the system perform literature investigation even without a person actively operating it, by controlling mouse and keyboard actions when needed. It is especially aimed at continuously searching, reading pages, copying information, analyzing content, expanding citations, and downloading full text around a given scientific question.

In other words, the goal is not just to build another literature chatbox, but to build a research assistant that actually opens pages, reads what is on the page, organizes the content, and keeps pushing the investigation forward.

### Target Users

- Researchers working on literature review around a concrete scientific question
- Graduate students and postdocs who need batch screening and structured paper notes
- Research groups that want to connect search, reading, filtering, expansion, and download
- Users who want a local, traceable evidence trail of their literature workflow

### Typical Use Cases

- Rapid survey of a new research direction
- Multi-round expansion around a specific scientific question
- Batch filtering of highly relevant papers
- Generating research landscape, timeline, and methodology reports
- Downloading PDFs and organizing them with Zotero

### Quick Start

Install dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Or run:

```bat
install.bat
```

Set the API key, preferably through an environment variable:

```powershell
$env:DEEPSEEK_API_KEY="your_api_key_here"
python modular_research_gui.py
```

You can also launch the GUI and enter the API key manually.

Launch the main GUI:

```bash
python modular_research_gui.py
```

Launch the PDF folder analysis tool:

```bash
python pdf_analysis_gui.py
```

### Requirements

- Windows 10/11
- Python 3.9+
- Microsoft Edge
- Zotero for the PDF download workflow

## Public Repo Notes

This public copy has already been sanitized:

- No real API key is included
- The tool reads `DEEPSEEK_API_KEY` from environment variables by default
- The original daily-use version was not modified

## Project Structure

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

## Workflow

1. Enter a scientific question
2. Generate English queries and run academic search
3. Save URL lists
4. Extract content from web pages or PDFs
5. Use an LLM for structured analysis and scoring
6. Generate high-quality literature reports
7. Expand through references and citations
8. Download PDFs into Zotero

## Notes

- `web_content_extractor.py` and the PDF download module rely heavily on Windows desktop automation
- Some websites may require institutional access, proxy settings, or additional permissions
- This repository currently works better as a research workflow tool than as a general-purpose Python package

## Author

Yuming Su / 苏禹铭 is an Assistant Researcher at the AI4EC Lab, Tan Kah Kee Innovation Laboratory (IKKEM), Xiamen, China.

Research interests include:

- Machine learning and large language models for chemistry
- Structure-activity relationship research
- Two-photon absorption related theory and data analysis
- Theory-driven and intelligent workflows for molecular and materials problems

More information, publications, and software projects:

- [Yuming Su Homepage](https://sym823808458.github.io/yumingsu_homepage/)

## License

This project is released under the [MIT License](LICENSE).

## Disclaimer

This project is intended for academic research and personal workflow organization. Please comply with the terms of use of websites, APIs, literature databases, and publisher platforms involved in your workflow.
