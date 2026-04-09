# 主页读憨豆看Le

一个面向科研工作者的 Windows 桌面文献调研工具，专门服务于“围绕某个科学问题做连续、多轮、可追溯的文献调研”。

它不是普通的摘要检索工具。对于国内很多真正需要文献具体信息的使用场景，只有摘要远远不够，必须尽可能拿到页面中的细节信息，甚至进一步下载全文。本项目的核心思路，就是调用 Edge 打开文献页面，自动复制页面中的可读内容，再把复制结果交给大语言模型进行结构化分析、相关性评分、研究脉络整理和后续扩展。

这也是它最大的特色和优势：不是只依赖数据库中的摘要字段，而是尽可能把研究者真正看到的文献页面内容送入模型。

这个公开副本已经做过脱敏处理：
- 不包含任何真实 API key
- 默认从环境变量 `DEEPSEEK_API_KEY` 读取密钥
- 原始日常使用版本未被修改

## 面向人群

- 围绕具体科学问题做文献调研的科研人员
- 需要批量筛选、比对和沉淀论文信息的研究生与博士后
- 希望把搜索、阅读、筛选、扩展、下载串起来的课题组
- 需要在本地保留研究过程和结果证据链的用户

## 适用场景

- 新方向快速摸底
- 针对具体科学问题做多轮文献扩展
- 批量筛选高相关论文
- 生成研究脉络 / 时间线 / 方法学报告
- 下载 PDF 并沉淀到 Zotero

## 主要特性

- 模块化 GUI：搜索、分析、深度报告、引用网络、PDF 下载彼此独立
- 闭环工作流：支持按轮次自动执行和逐轮扩展
- 本地可追溯：URL、分析结果、日志、HTML 报告都落盘保存
- 可定制 Prompt：适合按具体研究领域微调
- Zotero 集成：适合真实科研工作流，而不只是在线问答
- 支持从文献网页中复制具体内容，而不只依赖摘要信息
- 支持进一步下载全文并沉淀到本地文献管理流程

## 最大特色

本工具最初的设想，是在没有人值守的时候，也能通过控制鼠标和键盘去执行文献调研流程，尤其适合围绕某个科学问题进行持续搜索、页面阅读、信息复制、模型分析、引用扩展和全文下载。

和很多只做“联网回答”或“摘要级检索”的工具不同，这个项目更强调：

- 让程序像人一样打开文献页面并读取可见内容
- 将复制到的具体页面信息交给大语言模型，而不只是摘要
- 在本地完成可追踪的批量分析和结果沉淀
- 在需要时继续向全文获取和 PDF 管理延伸

## 系统要求

- Windows 10/11
- Python 3.9+
- Microsoft Edge
- Zotero（PDF 下载功能需要）

## 安装

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

也可以直接运行：

```bat
install.bat
```

## API Key 配置

推荐使用环境变量，而不是把密钥写进代码。

PowerShell:

```powershell
$env:DEEPSEEK_API_KEY="your_api_key_here"
python modular_research_gui.py
```

如果你不想设置环境变量，也可以直接启动 GUI，然后在界面中手动输入 API key。

## 启动方式

主界面：

```bash
python modular_research_gui.py
```

或：

```bat
start.bat
```

PDF 文件夹分析工具：

```bash
python pdf_analysis_gui.py
```

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
└── install.bat
```

## 工作流概览

1. 输入研究问题
2. 生成英文查询并执行学术搜索
3. 保存 URL 列表
4. 提取网页或 PDF 内容
5. 调用 LLM 做结构化分析与评分
6. 生成高质量文献深度报告
7. 基于引用 / 被引关系继续扩展
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

## GitHub 分享建议

- 在创建 GitHub 仓库时，把这个目录作为独立仓库上传
- 不要提交 `.env`、运行日志、项目输出目录和临时缓存
- 如果你后面准备公开发布，建议再补一份 `LICENSE`

## 作者

Yuming Su / 苏禹铭，现任 Assistant Researcher，工作于中国厦门的 AI4EC Lab, Tan Kah Kee Innovation Laboratory (IKKEM)。

研究方向主要包括：

- 机器学习与大语言模型在化学中的应用
- 结构-活性关系研究
- 双光子吸收相关理论与数据分析
- 面向分子与材料问题的理论计算与智能工作流

如果你想了解更完整的个人信息、论文列表和软件工作，可以访问个人主页：

- [Yuming Su Homepage](https://sym823808458.github.io/yumingsu_homepage/)

## 免责声明

本项目仅供学术研究与个人工作流整理使用。请遵守目标网站、API 服务、文献数据库和期刊平台的使用条款。
