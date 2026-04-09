#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
模块化LLM文献调研工具 - 新GUI架构
基于原有代码的严格重构，保持所有原有功能和prompt不变

作者: Yuming Su
日期: 2025-08-24
"""

import tkinter as tk
from tkinter import messagebox, ttk, scrolledtext, filedialog, simpledialog
import os
import json
import datetime
import threading
import webbrowser
import platform
import subprocess
import time
import logging

# 导入原有模块的核心功能
from enhanced_research_system import (
    EnhancedClosedLoopResearchSystem,
    translate_question_to_english,
    call_deepseek_api,
    search_bing_academic,
    extract_doi_from_url,
    query_crossref_references,
    query_crossref_citations
)
from web_content_extractor import WebContentExtractor, extract_web_content
from high_quality_analyzer import HighQualityAnalyzer
from pdfdownloaderzotero2 import ZoteroBatchSaver

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ModularResearchGUI:
    """模块化研究系统GUI - 5个独立功能栏"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("模块化LLM文献调研工具 v2.0.2")
        self.root.geometry('800x800')
        self.root.configure(bg='#f0f0f0')
        
        # 初始化核心组件
        self.research_system = EnhancedClosedLoopResearchSystem()
        self.web_extractor = WebContentExtractor()
        self.current_project_dir = None
        self.workflow_running = False
        self.workflow_thread = None
        
        # 尝试恢复上次的项目目录
        self._restore_last_project()
        
        # 设置GUI
        self.setup_gui()
    
    def _restore_last_project(self):
        """尝试恢复上次使用的项目目录"""
        try:
            config_file = os.path.join(os.path.expanduser("~"), ".llm_research_config.txt")
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    last_project = f.read().strip()
                    if last_project and os.path.exists(last_project) and os.path.isdir(last_project):
                        self.current_project_dir = last_project
                        if hasattr(self, 'research_system'):
                            self.research_system.project_dir = last_project
                        self._project_restored = True
                    else:
                        self._project_restored = False
            else:
                self._project_restored = False
        except Exception:
            # 如果恢复失败，忽略错误
            self._project_restored = False
    
    def _save_last_project(self):
        """保存当前项目目录供下次使用"""
        try:
            if self.current_project_dir:
                config_file = os.path.join(os.path.expanduser("~"), ".llm_research_config.txt")
                with open(config_file, 'w', encoding='utf-8') as f:
                    f.write(self.current_project_dir)
        except Exception:
            # 如果保存失败，忽略错误
            pass
    
    def setup_gui(self):
        """设置图形界面"""
        # 创建主滚动框架
        main_canvas = tk.Canvas(self.root, bg='#f0f0f0')
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=main_canvas.yview)
        scrollable_frame = ttk.Frame(main_canvas)
        
        # 配置滚动
        scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )
        
        main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=scrollbar.set)
        
        # 布局滚动组件
        main_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 主框架（现在在可滚动框架内）
        main_frame = ttk.Frame(scrollable_frame, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = tk.Label(main_frame, text="模块化LLM文献调研工具 v2.0.2",
                              font=('Arial', 18, 'bold'), bg='#f0f0f0', fg='#2c3e50')
        title_label.pack(pady=(0, 10))
        
        subtitle_label = tk.Label(main_frame, text="每个功能栏独立运行，支持工作流循环      Yuming Su",
                                 font=('Arial', 12), bg='#f0f0f0', fg='#7f8c8d')
        subtitle_label.pack(pady=(0, 20))
        
        # 创建笔记本控件
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # 按新的顺序设置标签页
        self.setup_config_tab(notebook)          # ⚙️ 全局配置区域
        self.setup_search_tab(notebook)          # 🔍 搜索工具栏
        self.setup_analysis_tab(notebook)        # 📊 内容分析栏
        self.setup_deep_analysis_tab(notebook)   # 🧠 深度分析栏
        self.setup_citation_network_tab(notebook) # 🔗 网络工具栏
        self.setup_pdf_download_tab(notebook)    # 📥 PDF下载栏
        
        # 绑定鼠标滚轮事件
        self._bind_mousewheel(main_canvas)
        
        # 更新项目显示（如果有恢复的项目）
        self.update_project_display()
    
    def _bind_mousewheel(self, canvas):
        """绑定鼠标滚轮事件"""
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def _bind_to_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        def _unbind_from_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
        
        canvas.bind('<Enter>', _bind_to_mousewheel)
        canvas.bind('<Leave>', _unbind_from_mousewheel)
    
    def setup_config_tab(self, notebook):
        """⚙️ 全局配置区域"""
        config_frame = ttk.Frame(notebook, padding=15)
        notebook.add(config_frame, text="⚙️ 系统配置")
        
        # API配置区域
        api_frame = ttk.LabelFrame(config_frame, text="API配置", padding=10)
        api_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(api_frame, text="DeepSeek API密钥:").pack(anchor='w', pady=(0, 5))
        self.api_key_entry = ttk.Entry(api_frame, width=70, show="*")
        self.api_key_entry.insert(0, self.research_system.api_key)
        self.api_key_entry.pack(fill=tk.X, pady=(0, 10))
        
        api_buttons_frame = ttk.Frame(api_frame)
        api_buttons_frame.pack(fill=tk.X)
        ttk.Button(api_buttons_frame, text="测试连接", command=self.test_api_connection).pack(side=tk.LEFT, padx=5)
        ttk.Button(api_buttons_frame, text="保存API密钥", command=self.save_api_key).pack(side=tk.LEFT, padx=5)
        
        # 模型选择
        ttk.Label(api_frame, text="默认模型:").pack(anchor='w', pady=(10, 5))
        self.model_var = tk.StringVar(value="deepseek-chat")
        model_combo = ttk.Combobox(api_frame, textvariable=self.model_var, 
                                  values=["deepseek-chat", "deepseek-reasoner"], 
                                  width=20, state="readonly")
        model_combo.pack(anchor='w')
        
        # 项目管理区域
        project_frame = ttk.LabelFrame(config_frame, text="项目管理", padding=10)
        project_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(project_frame, text="当前项目:").pack(anchor='w', pady=(0, 5))
        self.current_project_label = ttk.Label(project_frame, text="未选择项目", 
                                              font=('Arial', 10, 'bold'))
        self.current_project_label.pack(anchor='w', pady=(0, 10))
        
        project_buttons_frame = ttk.Frame(project_frame)
        project_buttons_frame.pack(fill=tk.X)
        ttk.Button(project_buttons_frame, text="新建项目", command=self.create_new_project).pack(side=tk.LEFT, padx=5)
        ttk.Button(project_buttons_frame, text="打开项目文件夹", command=self.open_project_folder).pack(side=tk.LEFT, padx=5)
        
        # 工作流控制区域
        workflow_frame = ttk.LabelFrame(config_frame, text="工作流控制", padding=10)
        workflow_frame.pack(fill=tk.X, pady=(0, 15))
        
        # 循环条件设置
        conditions_frame = ttk.Frame(workflow_frame)
        conditions_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(conditions_frame, text="循环终止条件:").pack(anchor='w', pady=(0, 5))
        
        condition_grid = ttk.Frame(conditions_frame)
        condition_grid.pack(fill=tk.X)
        
        ttk.Label(condition_grid, text="高质量文章数 ≥").grid(row=0, column=0, sticky='w', padx=(0, 5))
        self.target_articles_var = tk.StringVar(value="30")
        ttk.Entry(condition_grid, textvariable=self.target_articles_var, width=5).grid(row=0, column=1, padx=(0, 20))
        
        ttk.Label(condition_grid, text="或 迭代次数 ≥").grid(row=0, column=2, sticky='w', padx=(0, 5))
        self.max_iterations_var = tk.StringVar(value="5")
        ttk.Entry(condition_grid, textvariable=self.max_iterations_var, width=5).grid(row=0, column=3, padx=(0, 10))
        ttk.Label(condition_grid, text="次").grid(row=0, column=4, sticky='w')
        
        # 工作流控制按钮
        workflow_buttons_frame = ttk.Frame(workflow_frame)
        workflow_buttons_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.start_workflow_btn = ttk.Button(workflow_buttons_frame, text="启动自动循环", 
                                           command=self.start_auto_workflow)
        self.start_workflow_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_workflow_btn = ttk.Button(workflow_buttons_frame, text="停止循环", 
                                          command=self.stop_auto_workflow, state='disabled')
        self.stop_workflow_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(workflow_buttons_frame, text="单步执行", command=self.single_step_workflow).pack(side=tk.LEFT, padx=5)
        
        # 状态显示区域
        status_frame = ttk.LabelFrame(config_frame, text="系统状态", padding=10)
        status_frame.pack(fill=tk.BOTH, expand=True)
        
        self.status_text = scrolledtext.ScrolledText(status_frame, height=8, width=80, font=('Consolas', 9))
        self.status_text.pack(fill=tk.BOTH, expand=True)
        self.status_text.config(state='disabled')
        
        # 初始状态消息
        if hasattr(self, '_project_restored') and self._project_restored:
            project_name = os.path.basename(self.current_project_dir)
            self.update_status(f"系统已启动，已恢复上次项目: {project_name}")
        else:
            self.update_status("系统已启动，请配置API密钥并创建项目")
    
    def setup_search_tab(self, notebook):
        """🔍 搜索工具栏 - 科学问题 → urls.txt"""
        search_frame = ttk.Frame(notebook, padding=15)
        notebook.add(search_frame, text="🔍 搜索工具栏")
        
        # 科学问题输入区域
        question_frame = ttk.LabelFrame(search_frame, text="科学问题输入", padding=10)
        question_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(question_frame, text="请输入科学问题（支持中英文）:").pack(anchor='w', pady=(0, 5))
        self.search_question_text = tk.Text(question_frame, height=4, width=80, font=('Arial', 10))
        self.search_question_text.pack(fill=tk.X, pady=(0, 10))
        
        # 示例问题按钮
        example_frame = ttk.Frame(question_frame)
        example_frame.pack(fill=tk.X)
        ttk.Button(example_frame, text="示例1: 材料科学", 
                  command=lambda: self.load_search_example("材料科学")).pack(side=tk.LEFT, padx=5)
        ttk.Button(example_frame, text="示例2: 生物医学", 
                  command=lambda: self.load_search_example("生物医学")).pack(side=tk.LEFT, padx=5)
        ttk.Button(example_frame, text="示例3: 化学合成", 
                  command=lambda: self.load_search_example("化学合成")).pack(side=tk.LEFT, padx=5)
        
        # 搜索参数区域
        params_frame = ttk.LabelFrame(search_frame, text="搜索参数", padding=10)
        params_frame.pack(fill=tk.X, pady=(0, 15))
        
        params_grid = ttk.Frame(params_frame)
        params_grid.pack(fill=tk.X)
        
        ttk.Label(params_grid, text="搜索严谨度:").grid(row=0, column=0, sticky='w', padx=(0, 10))
        self.search_rigor_var = tk.StringVar(value="medium")
        rigor_combo = ttk.Combobox(params_grid, textvariable=self.search_rigor_var, 
                                  values=["strict", "medium", "broad"], width=10, state="readonly")
        rigor_combo.grid(row=0, column=1, sticky='w', padx=(0, 20))
        
        ttk.Label(params_grid, text="目标数量:").grid(row=0, column=2, sticky='w', padx=(0, 10))
        self.search_target_var = tk.StringVar(value="30")
        ttk.Entry(params_grid, textvariable=self.search_target_var, width=5).grid(row=0, column=3, sticky='w', padx=(0, 20))
        
        # 控制按钮区域
        search_buttons_frame = ttk.Frame(search_frame)
        search_buttons_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Button(search_buttons_frame, text="开始搜索", command=self.start_search).pack(side=tk.LEFT, padx=5)
        ttk.Button(search_buttons_frame, text="查看结果", command=self.view_search_results).pack(side=tk.LEFT, padx=5)
        ttk.Button(search_buttons_frame, text="导出URLs", command=self.export_search_urls).pack(side=tk.LEFT, padx=5)
        
        # 结果显示区域
        results_frame = ttk.LabelFrame(search_frame, text="搜索结果", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        self.search_results_text = scrolledtext.ScrolledText(results_frame, height=15, width=80, font=('Consolas', 9))
        self.search_results_text.pack(fill=tk.BOTH, expand=True)
        self.search_results_text.config(state='disabled')
    
    def setup_analysis_tab(self, notebook):
        """📊 内容分析栏 - urls.txt → analysis_results.json"""
        analysis_frame = ttk.Frame(notebook, padding=15)
        notebook.add(analysis_frame, text="📊 内容分析栏")
        
        # 输入文件选择区域
        input_frame = ttk.LabelFrame(analysis_frame, text="输入文件", padding=10)
        input_frame.pack(fill=tk.X, pady=(0, 15))
        
        file_select_frame = ttk.Frame(input_frame)
        file_select_frame.pack(fill=tk.X)
        
        ttk.Label(file_select_frame, text="URLs文件:").pack(side=tk.LEFT, padx=(0, 10))
        self.analysis_input_var = tk.StringVar()
        ttk.Entry(file_select_frame, textvariable=self.analysis_input_var, width=50).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(file_select_frame, text="选择文件", command=self.select_urls_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_select_frame, text="使用最新", command=self.use_latest_urls).pack(side=tk.LEFT, padx=5)
        
        # 添加PDF分析工具链接
        pdf_tool_frame = ttk.Frame(input_frame)
        pdf_tool_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(pdf_tool_frame, text="PDF文件夹分析:").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(pdf_tool_frame, text="打开PDF分析工具", command=self.open_pdf_analysis_tool).pack(side=tk.LEFT, padx=5)
        ttk.Label(pdf_tool_frame, text="(独立工具，用于批量处理PDF文件夹)",
                 font=('Arial', 9), foreground='gray').pack(side=tk.LEFT, padx=(10, 0))
        
        # 分析参数区域
        analysis_params_frame = ttk.LabelFrame(analysis_frame, text="分析参数", padding=10)
        analysis_params_frame.pack(fill=tk.X, pady=(0, 15))
        
        params_grid = ttk.Frame(analysis_params_frame)
        params_grid.pack(fill=tk.X)
        
        ttk.Label(params_grid, text="评分阈值:").grid(row=0, column=0, sticky='w', padx=(0, 10))
        self.analysis_threshold_var = tk.StringVar(value="8")
        ttk.Combobox(params_grid, textvariable=self.analysis_threshold_var, 
                    values=["6", "7", "8", "9"], width=5, state="readonly").grid(row=0, column=1, sticky='w', padx=(0, 20))
        
        ttk.Label(params_grid, text="Prompt模板:").grid(row=0, column=2, sticky='w', padx=(0, 10))
        self.analysis_prompt_var = tk.StringVar(value="默认模板")
        ttk.Combobox(params_grid, textvariable=self.analysis_prompt_var, 
                    values=["默认模板", "自定义模板"], width=15, state="readonly").grid(row=0, column=3, sticky='w')
        
        # Prompt编辑区域（使用原有的默认prompt）
        prompt_frame = ttk.LabelFrame(analysis_frame, text="分析Prompt（保持原有不变）", padding=10)
        prompt_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.analysis_prompt_text = tk.Text(prompt_frame, height=6, width=80, font=('Arial', 9))
        # 使用原有的默认批量分析prompt
        default_prompt = """分析以下学术文献内容，提取关键信息并以JSON格式返回。
我的科学问题是：{RESEARCH_QUESTION}

JSON字段应包含:
1. "doi": 文章的DOI号码
2. "title": 文章标题
3. "authors": 作者列表
4. "publication_year": 出版年份
5. "journal": 期刊名称
6. "research_focus": 研究的主要材料、反应或主题
7. "key_methods": 关键概念和使用的技术方法
8. "major_contributions": 主要发现和贡献
9. "challenges": 文中提到的未解决问题或研究局限性
10. "relevance_score": 对该主题的相关性评分(1-10)

文章内容:
{PAPER_CONTENT}

只返回单个JSON对象，无需额外解释。"""
        self.analysis_prompt_text.insert("1.0", default_prompt)
        self.analysis_prompt_text.pack(fill=tk.X)
        
        # 控制按钮区域
        analysis_buttons_frame = ttk.Frame(analysis_frame)
        analysis_buttons_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Button(analysis_buttons_frame, text="开始分析", command=self.start_content_analysis).pack(side=tk.LEFT, padx=5)
        ttk.Button(analysis_buttons_frame, text="查看日志", command=self.view_analysis_logs).pack(side=tk.LEFT, padx=5)
        
        # 进度显示区域
        progress_frame = ttk.LabelFrame(analysis_frame, text="分析进度", padding=10)
        progress_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.analysis_progress_bar = ttk.Progressbar(progress_frame, mode='determinate', length=400)
        self.analysis_progress_bar.pack(fill=tk.X, pady=(0, 5))
        
        self.analysis_status_label = ttk.Label(progress_frame, text="就绪")
        self.analysis_status_label.pack(anchor='w')
        
        # 结果显示区域
        analysis_results_frame = ttk.LabelFrame(analysis_frame, text="分析结果", padding=10)
        analysis_results_frame.pack(fill=tk.BOTH, expand=True)
        
        self.analysis_results_text = scrolledtext.ScrolledText(analysis_results_frame, height=10, width=80, font=('Consolas', 9))
        self.analysis_results_text.pack(fill=tk.BOTH, expand=True)
        self.analysis_results_text.config(state='disabled')
    
    def setup_deep_analysis_tab(self, notebook):
        """🧠 深度分析栏 - analysis_results.json → final_report.html"""
        deep_frame = ttk.Frame(notebook, padding=15)
        notebook.add(deep_frame, text="🧠 深度分析栏")
        
        # 输入文件选择区域
        deep_input_frame = ttk.LabelFrame(deep_frame, text="输入文件", padding=10)
        deep_input_frame.pack(fill=tk.X, pady=(0, 15))
        
        file_select_frame = ttk.Frame(deep_input_frame)
        file_select_frame.pack(fill=tk.X)
        
        ttk.Label(file_select_frame, text="分析结果JSON:").pack(side=tk.LEFT, padx=(0, 10))
        self.deep_input_var = tk.StringVar()
        ttk.Entry(file_select_frame, textvariable=self.deep_input_var, width=50).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(file_select_frame, text="选择文件", command=self.select_analysis_json).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_select_frame, text="使用最新", command=self.use_latest_analysis).pack(side=tk.LEFT, padx=5)
        
        # 分析类型选择区域
        type_frame = ttk.LabelFrame(deep_frame, text="分析类型", padding=10)
        type_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.deep_analysis_type_var = tk.StringVar(value="research_flow")
        ttk.Radiobutton(type_frame, text="研究脉络分析", variable=self.deep_analysis_type_var,
                       value="research_flow").pack(anchor='w')
        ttk.Radiobutton(type_frame, text="时间线分析", variable=self.deep_analysis_type_var,
                       value="timeline").pack(anchor='w')
        ttk.Radiobutton(type_frame, text="方法学分析", variable=self.deep_analysis_type_var,
                       value="methodology").pack(anchor='w')
        ttk.Radiobutton(type_frame, text="自定义模板", variable=self.deep_analysis_type_var,
                       value="custom").pack(anchor='w')
        
        # 筛选参数区域
        filter_frame = ttk.LabelFrame(deep_frame, text="筛选参数", padding=10)
        filter_frame.pack(fill=tk.X, pady=(0, 15))
        
        filter_grid = ttk.Frame(filter_frame)
        filter_grid.pack(fill=tk.X)
        
        ttk.Label(filter_grid, text="评分阈值:").grid(row=0, column=0, sticky='w', padx=(0, 10))
        self.deep_threshold_var = tk.StringVar(value="8")
        ttk.Combobox(filter_grid, textvariable=self.deep_threshold_var, 
                    values=["6", "7", "8", "9"], width=5, state="readonly").grid(row=0, column=1, sticky='w', padx=(0, 20))
        
        ttk.Label(filter_grid, text="最少文章数:").grid(row=0, column=2, sticky='w', padx=(0, 10))
        self.deep_min_articles_var = tk.StringVar(value="5")
        ttk.Entry(filter_grid, textvariable=self.deep_min_articles_var, width=5).grid(row=0, column=3, sticky='w')
        
        # 深度分析Prompt编辑区域
        deep_prompt_frame = ttk.LabelFrame(deep_frame, text="深度分析Prompt模板（可自定义）", padding=10)
        deep_prompt_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Prompt类型选择和操作按钮
        prompt_control_frame = ttk.Frame(deep_prompt_frame)
        prompt_control_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(prompt_control_frame, text="当前Prompt类型:").pack(side=tk.LEFT, padx=(0, 10))
        self.current_prompt_type_label = ttk.Label(prompt_control_frame, text="研究脉络分析",
                                                  font=('Arial', 10, 'bold'), foreground='blue')
        self.current_prompt_type_label.pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Button(prompt_control_frame, text="重置为默认", command=self.reset_deep_prompt).pack(side=tk.LEFT, padx=5)
        ttk.Button(prompt_control_frame, text="保存Prompt", command=self.save_deep_prompt).pack(side=tk.LEFT, padx=5)
        ttk.Button(prompt_control_frame, text="加载Prompt", command=self.load_deep_prompt).pack(side=tk.LEFT, padx=5)
        
        # Prompt编辑文本框
        ttk.Label(deep_prompt_frame, text="自定义深度分析Prompt（{JSON_DATA}会被自动替换为文献数据）:").pack(anchor='w', pady=(0, 5))
        self.deep_prompt_text = tk.Text(deep_prompt_frame, height=12, width=80, font=('Arial', 9))
        self.deep_prompt_text.pack(fill=tk.X, pady=(0, 10))
        
        # 绑定分析类型变化事件
        self.deep_analysis_type_var.trace('w', self.on_deep_analysis_type_changed)
        
        # 初始化默认prompt
        self.load_default_deep_prompt()
        
        # 控制按钮区域
        deep_buttons_frame = ttk.Frame(deep_frame)
        deep_buttons_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Button(deep_buttons_frame, text="开始深度分析", command=self.start_deep_analysis).pack(side=tk.LEFT, padx=5)
        ttk.Button(deep_buttons_frame, text="合并分析结果", command=self.merge_analysis_results).pack(side=tk.LEFT, padx=5)
        ttk.Button(deep_buttons_frame, text="预览报告", command=self.preview_deep_report).pack(side=tk.LEFT, padx=5)
        ttk.Button(deep_buttons_frame, text="打开HTML", command=self.open_deep_html).pack(side=tk.LEFT, padx=5)
        
        # 结果显示区域
        deep_results_frame = ttk.LabelFrame(deep_frame, text="深度分析结果", padding=10)
        deep_results_frame.pack(fill=tk.BOTH, expand=True)
        
        self.deep_results_text = scrolledtext.ScrolledText(deep_results_frame, height=15, width=80, font=('Consolas', 9))
        self.deep_results_text.pack(fill=tk.BOTH, expand=True)
        self.deep_results_text.config(state='disabled')
    
    def setup_citation_network_tab(self, notebook):
        """🔗 网络工具栏 - urls.txt → 扩展后的新urls.txt"""
        citation_frame = ttk.Frame(notebook, padding=15)
        notebook.add(citation_frame, text="🔗 网络工具栏")
        
        # 输入文件选择区域
        citation_input_frame = ttk.LabelFrame(citation_frame, text="输入文件", padding=10)
        citation_input_frame.pack(fill=tk.X, pady=(0, 15))
        
        file_select_frame = ttk.Frame(citation_input_frame)
        file_select_frame.pack(fill=tk.X)
        
        ttk.Label(file_select_frame, text="URLs文件:").pack(side=tk.LEFT, padx=(0, 10))
        self.citation_input_var = tk.StringVar()
        ttk.Entry(file_select_frame, textvariable=self.citation_input_var, width=50).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(file_select_frame, text="选择文件", command=self.select_citation_urls).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_select_frame, text="使用最新", command=self.use_latest_citation_urls).pack(side=tk.LEFT, padx=5)
        
        # 扩展参数区域
        citation_params_frame = ttk.LabelFrame(citation_frame, text="扩展参数", padding=10)
        citation_params_frame.pack(fill=tk.X, pady=(0, 15))
        
        # 扩展类型选择
        type_frame = ttk.Frame(citation_params_frame)
        type_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(type_frame, text="扩展类型:").pack(side=tk.LEFT, padx=(0, 10))
        self.citation_references_var = tk.BooleanVar(value=True)
        self.citation_citations_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(type_frame, text="引用文献", variable=self.citation_references_var).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(type_frame, text="被引文献", variable=self.citation_citations_var).pack(side=tk.LEFT, padx=5)
        
        # 筛选参数
        filter_frame = ttk.Frame(citation_params_frame)
        filter_frame.pack(fill=tk.X)
        
        ttk.Label(filter_frame, text="筛选数量:").grid(row=0, column=0, sticky='w', padx=(0, 10))
        self.citation_count_var = tk.StringVar(value="300")
        ttk.Entry(filter_frame, textvariable=self.citation_count_var, width=5).grid(row=0, column=1, sticky='w', padx=(0, 20))
        
        ttk.Label(filter_frame, text="相关性阈值:").grid(row=0, column=2, sticky='w', padx=(0, 10))
        self.citation_relevance_var = tk.StringVar(value="0.7")
        ttk.Entry(filter_frame, textvariable=self.citation_relevance_var, width=5).grid(row=0, column=3, sticky='w')
        
        # 控制按钮区域
        citation_buttons_frame = ttk.Frame(citation_frame)
        citation_buttons_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Button(citation_buttons_frame, text="开始扩展", command=self.start_citation_expansion).pack(side=tk.LEFT, padx=5)
        ttk.Button(citation_buttons_frame, text="预览结果", command=self.preview_citation_results).pack(side=tk.LEFT, padx=5)
        ttk.Button(citation_buttons_frame, text="保存新URLs", command=self.save_expanded_urls).pack(side=tk.LEFT, padx=5)
        
        # 结果显示区域
        citation_results_frame = ttk.LabelFrame(citation_frame, text="扩展结果", padding=10)
        citation_results_frame.pack(fill=tk.BOTH, expand=True)
        
        self.citation_results_text = scrolledtext.ScrolledText(citation_results_frame, height=15, width=80, font=('Consolas', 9))
        self.citation_results_text.pack(fill=tk.BOTH, expand=True)
        self.citation_results_text.config(state='disabled')
    
    def setup_pdf_download_tab(self, notebook):
        """📥 PDF下载栏 - urls.txt → Zotero中的PDF文件 (使用pdfdownloaderzotero2)"""
        pdf_frame = ttk.Frame(notebook, padding=15)
        notebook.add(pdf_frame, text="📥 PDF下载栏")
        
        # 输入文件选择区域
        pdf_input_frame = ttk.LabelFrame(pdf_frame, text="输入文件", padding=10)
        pdf_input_frame.pack(fill=tk.X, pady=(0, 15))
        
        file_select_frame = ttk.Frame(pdf_input_frame)
        file_select_frame.pack(fill=tk.X)
        
        ttk.Label(file_select_frame, text="URLs文件:").pack(side=tk.LEFT, padx=(0, 10))
        self.pdf_input_var = tk.StringVar()
        ttk.Entry(file_select_frame, textvariable=self.pdf_input_var, width=50).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(file_select_frame, text="选择文件", command=self.select_pdf_urls).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_select_frame, text="使用最新", command=self.use_latest_pdf_urls).pack(side=tk.LEFT, padx=5)
        
        # 下载参数区域 (简化版)
        pdf_params_frame = ttk.LabelFrame(pdf_frame, text="下载参数 (先易后难策略)", padding=10)
        pdf_params_frame.pack(fill=tk.X, pady=(0, 15))
        
        params_info = ttk.Label(pdf_params_frame, text="使用优化的先易后难策略，固定批次大小为9个URL，自动处理")
        params_info.pack(anchor='w')
        
        # Zotero状态检查
        zotero_frame = ttk.LabelFrame(pdf_frame, text="Zotero状态", padding=10)
        zotero_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.zotero_status_label = ttk.Label(zotero_frame, text="未检查", font=('Arial', 10, 'bold'))
        self.zotero_status_label.pack(anchor='w', pady=(0, 5))
        
        zotero_buttons_frame = ttk.Frame(zotero_frame)
        zotero_buttons_frame.pack(fill=tk.X)
        ttk.Button(zotero_buttons_frame, text="检查Zotero", command=self.check_zotero_status).pack(side=tk.LEFT, padx=5)
        ttk.Button(zotero_buttons_frame, text="打开Zotero", command=self.open_zotero).pack(side=tk.LEFT, padx=5)
        
        # 控制按钮区域
        pdf_buttons_frame = ttk.Frame(pdf_frame)
        pdf_buttons_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.start_pdf_btn = ttk.Button(pdf_buttons_frame, text="开始智能下载", command=self.start_pdf_download)
        self.start_pdf_btn.pack(side=tk.LEFT, padx=5)
        
        self.pause_pdf_btn = ttk.Button(pdf_buttons_frame, text="停止", command=self.pause_pdf_download, state='disabled')
        self.pause_pdf_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(pdf_buttons_frame, text="查看Zotero", command=self.view_zotero_library).pack(side=tk.LEFT, padx=5)
        
        # 进度显示区域
        pdf_progress_frame = ttk.LabelFrame(pdf_frame, text="下载进度", padding=10)
        pdf_progress_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.pdf_progress_bar = ttk.Progressbar(pdf_progress_frame, mode='determinate', length=400)
        self.pdf_progress_bar.pack(fill=tk.X, pady=(0, 5))
        
        progress_info_frame = ttk.Frame(pdf_progress_frame)
        progress_info_frame.pack(fill=tk.X)
        
        self.pdf_progress_label = ttk.Label(progress_info_frame, text="就绪")
        self.pdf_progress_label.pack(side=tk.LEFT)
        
        self.pdf_stats_label = ttk.Label(progress_info_frame, text="成功: 0 失败: 0")
        self.pdf_stats_label.pack(side=tk.RIGHT)
        
        # 结果显示区域
        pdf_results_frame = ttk.LabelFrame(pdf_frame, text="下载结果", padding=10)
        pdf_results_frame.pack(fill=tk.BOTH, expand=True)
        
        self.pdf_results_text = scrolledtext.ScrolledText(pdf_results_frame, height=10, width=80, font=('Consolas', 9))
        self.pdf_results_text.pack(fill=tk.BOTH, expand=True)
        self.pdf_results_text.config(state='disabled')
    
    # ==================== 工具方法 ====================
    
    def update_status(self, message):
        """更新状态显示"""
        try:
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            formatted_message = f"[{timestamp}] {message}"
            
            self.status_text.config(state='normal')
            self.status_text.insert(tk.END, formatted_message + "\n")
            self.status_text.see(tk.END)
            self.status_text.config(state='disabled')
            
            self.root.update_idletasks()
            
        except Exception as e:
            print(f"更新状态显示出错: {str(e)}")
    
    def update_project_display(self):
        """更新项目显示"""
        if self.current_project_dir:
            project_name = os.path.basename(self.current_project_dir)
            self.current_project_label.config(text=project_name)
        else:
            self.current_project_label.config(text="未选择项目")
    
    # ==================== 配置相关方法 ====================
    
    def test_api_connection(self):
        """测试API连接"""
        try:
            api_key = self.api_key_entry.get().strip()
            if not api_key:
                messagebox.showwarning("警告", "请输入API密钥")
                return
            
            # 使用原有的翻译功能测试连接
            test_result = translate_question_to_english("测试连接", api_key)
            if test_result:
                messagebox.showinfo("成功", "API连接测试成功")
                self.update_status("API连接测试成功")
            else:
                messagebox.showerror("错误", "API连接测试失败")
                
        except Exception as e:
            messagebox.showerror("错误", f"API连接测试出错: {str(e)}")
    
    def save_api_key(self):
        """保存API密钥"""
        try:
            api_key = self.api_key_entry.get().strip()
            if api_key:
                self.research_system.api_key = api_key
                messagebox.showinfo("成功", "API密钥已保存")
                self.update_status("API密钥已保存")
            else:
                messagebox.showwarning("警告", "请输入有效的API密钥")
        except Exception as e:
            messagebox.showerror("错误", f"保存API密钥出错: {str(e)}")
    
    def create_new_project(self):
        """创建新项目"""
        try:
            project_name = simpledialog.askstring("项目名称", "请输入项目名称（留空使用默认名称）:")
            
            # 使用原有的项目初始化功能
            project_dir = self.research_system.initialize_project(project_name)
            self.current_project_dir = project_dir
            
            # 保存项目目录供下次使用
            self._save_last_project()
            
            self.update_project_display()
            self.update_status(f"新项目已创建: {project_dir}")
            messagebox.showinfo("成功", f"项目已创建:\n{project_dir}")
            
        except Exception as e:
            messagebox.showerror("错误", f"创建项目时出错: {str(e)}")
    
    def select_existing_project(self):
        """选择现有项目"""
        try:
            project_dir = filedialog.askdirectory(title="选择现有项目文件夹")
            if project_dir:
                # 验证项目目录是否有效
                if os.path.exists(project_dir) and os.path.isdir(project_dir):
                    self.current_project_dir = project_dir
                    
                    # 确保研究系统对象存在并设置项目目录
                    if hasattr(self, 'research_system') and self.research_system:
                        self.research_system.project_dir = project_dir
                    
                    # 保存项目目录供下次使用
                    self._save_last_project()
                    
                    self.update_project_display()
                    self.update_status(f"已选择现有项目: {project_dir}")
                    
                    # 在单独线程中检测项目进度，避免界面卡死
                    progress_thread = threading.Thread(target=self._detect_project_progress_async, daemon=True)
                    progress_thread.start()
                    
                    messagebox.showinfo("成功", f"已选择现有项目:\n{project_dir}\n\n正在后台检测项目进度...")
                else:
                    messagebox.showerror("错误", "选择的目录无效或不存在")
        except Exception as e:
            error_msg = str(e)
            self.update_status(f"选择项目出错: {error_msg}")
            messagebox.showerror("错误", f"选择项目时出错: {error_msg}")
    
    def _detect_project_progress_async(self):
        """在后台线程中检测项目进度"""
        try:
            if not self.current_project_dir:
                return
            
            self.root.after(0, lambda: self.update_status("正在检测项目进度..."))
            
            progress_info = []
            
            # 1. 检测搜索结果 - 简化版本
            urls_dir = os.path.join(self.current_project_dir, "urls")
            if os.path.exists(urls_dir):
                try:
                    url_files = [f for f in os.listdir(urls_dir) if f.endswith('.txt') and not f.startswith('expanded_')]
                    if url_files:
                        # 找到最新的URL文件
                        latest_url_file = max([os.path.join(urls_dir, f) for f in url_files],
                                            key=lambda x: os.path.getmtime(x) if os.path.exists(x) else 0)
                        self.latest_urls_file = latest_url_file
                        progress_info.append(f"✓ 搜索结果: {os.path.basename(latest_url_file)}")
                        
                        # 自动设置输入路径
                        self.root.after(0, lambda: self.analysis_input_var.set(latest_url_file))
                        self.root.after(0, lambda: self.citation_input_var.set(latest_url_file))
                        self.root.after(0, lambda: self.pdf_input_var.set(latest_url_file))
                except Exception as e:
                    progress_info.append(f"⚠️ 搜索结果检测出错: {str(e)}")
            
            # 2. 检测分析结果 - 简化版本
            analysis_dir = os.path.join(self.current_project_dir, "analysis")
            if os.path.exists(analysis_dir):
                try:
                    json_files = [f for f in os.listdir(analysis_dir) if f.endswith('.json')]
                    if json_files:
                        # 找到最新的分析文件
                        latest_analysis_file = max([os.path.join(analysis_dir, f) for f in json_files],
                                                 key=lambda x: os.path.getmtime(x) if os.path.exists(x) else 0)
                        self.latest_analysis_file = latest_analysis_file
                        progress_info.append(f"✓ 分析结果: {os.path.basename(latest_analysis_file)}")
                        
                        # 自动设置到深度分析输入
                        self.root.after(0, lambda: self.deep_input_var.set(latest_analysis_file))
                except Exception as e:
                    progress_info.append(f"⚠️ 分析结果检测出错: {str(e)}")
            
            # 3. 检测深度分析报告 - 简化版本 (从temp_analysis目录)
            temp_analysis_dir = os.path.join(self.current_project_dir, "temp_analysis")
            if os.path.exists(temp_analysis_dir):
                try:
                    html_files = [f for f in os.listdir(temp_analysis_dir) if f.endswith('.html')]
                    if html_files:
                        # 找到最新的报告文件
                        latest_report_file = max([os.path.join(temp_analysis_dir, f) for f in html_files],
                                               key=lambda x: os.path.getmtime(x) if os.path.exists(x) else 0)
                        self.latest_deep_report = latest_report_file
                        progress_info.append(f"✓ 深度分析报告: {os.path.basename(latest_report_file)}")
                except Exception as e:
                    progress_info.append(f"⚠️ 报告检测出错: {str(e)}")
            
            # 4. 检测扩展URL文件 - 简化版本
            if os.path.exists(urls_dir):
                try:
                    expanded_files = [f for f in os.listdir(urls_dir) if f.startswith('expanded_urls_') and f.endswith('.txt')]
                    if expanded_files:
                        latest_expanded_file = max([os.path.join(urls_dir, f) for f in expanded_files],
                                                 key=lambda x: os.path.getmtime(x) if os.path.exists(x) else 0)
                        self.latest_expanded_urls_file = latest_expanded_file
                        progress_info.append(f"✓ 扩展URL: {os.path.basename(latest_expanded_file)}")
                except Exception as e:
                    progress_info.append(f"⚠️ 扩展URL检测出错: {str(e)}")
            
            # 显示进度信息
            if progress_info:
                progress_text = "项目进度检测完成:\n\n" + "\n".join(progress_info)
                progress_text += "\n\n相关文件已自动加载到对应功能栏"
                self.root.after(0, lambda: self.update_status("项目进度检测完成"))
                self.root.after(0, lambda: messagebox.showinfo("项目进度", progress_text))
            else:
                self.root.after(0, lambda: self.update_status("未检测到项目进度文件"))
                self.root.after(0, lambda: messagebox.showinfo("项目进度", "未检测到任何进度文件，这是一个空项目"))
                
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: self.update_status(f"检测项目进度出错: {error_msg}"))
            self.root.after(0, lambda: messagebox.showerror("错误", f"检测项目进度时出错: {error_msg}"))
    
    def open_project_folder(self):
        """打开项目文件夹"""
        try:
            if self.current_project_dir and os.path.exists(self.current_project_dir):
                if platform.system() == "Windows":
                    os.startfile(self.current_project_dir)
                elif platform.system() == "Darwin":
                    subprocess.Popen(["open", self.current_project_dir])
                else:
                    subprocess.Popen(["xdg-open", self.current_project_dir])
            else:
                messagebox.showwarning("警告", "请先创建或选择项目")
        except Exception as e:
            messagebox.showerror("错误", f"打开项目文件夹时出错: {str(e)}")
    
    # ==================== 工作流控制方法 ====================
    
    def start_auto_workflow(self):
        """启动自动循环工作流"""
        try:
            if not self.current_project_dir:
                messagebox.showwarning("警告", "请先创建或选择项目")
                return
            
            if not self.api_key_entry.get().strip():
                messagebox.showwarning("警告", "请先配置API密钥")
                return
            
            self.workflow_running = True
            self.start_workflow_btn.config(state='disabled')
            self.stop_workflow_btn.config(state='normal')
            
            self.update_status("启动自动循环工作流...")
            
            # 在单独线程中运行工作流
            self.workflow_thread = threading.Thread(target=self.run_auto_workflow, daemon=True)
            self.workflow_thread.start()
            
        except Exception as e:
            messagebox.showerror("错误", f"启动工作流时出错: {str(e)}")
            self.reset_workflow_buttons()
    
    def stop_auto_workflow(self):
        """停止自动循环工作流"""
        self.workflow_running = False
        self.reset_workflow_buttons()
        self.update_status("工作流已停止")
    
    def reset_workflow_buttons(self):
        """重置工作流按钮状态"""
        self.start_workflow_btn.config(state='normal')
        self.stop_workflow_btn.config(state='disabled')
    
    def single_step_workflow(self):
        """单步执行工作流"""
        messagebox.showinfo("提示", "单步执行功能：请手动依次使用各功能栏")
    
    def run_auto_workflow(self):
        """运行自动工作流（在单独线程中）"""
        try:
            # 检查前置条件
            if not self._check_workflow_prerequisites():
                return
            
            target_articles = int(self.target_articles_var.get())
            max_iterations = int(self.max_iterations_var.get())
            current_iteration = 0
            total_high_quality_articles = 0
            
            self.root.after(0, lambda: self.update_status("自动工作流启动，开始循环执行..."))
            
            while self.workflow_running and current_iteration < max_iterations:
                current_iteration += 1
                self.root.after(0, lambda i=current_iteration: self.update_status(f"===== 开始第 {i} 轮迭代 ====="))
                
                # 步骤2: 搜索工具栏
                if not self.workflow_running:
                    break
                self.root.after(0, lambda: self.update_status("步骤2: 执行搜索..."))
                if not self._workflow_execute_search():
                    break
                
                # 步骤3: 内容分析栏
                if not self.workflow_running:
                    break
                self.root.after(0, lambda: self.update_status("步骤3: 执行内容分析..."))
                analysis_results = self._workflow_execute_analysis()
                if not analysis_results:
                    break
                
                # 统计高质量文章数量
                high_quality_count = self._count_high_quality_articles(analysis_results)
                total_high_quality_articles += high_quality_count
                
                self.root.after(0, lambda h=high_quality_count, t=total_high_quality_articles:
                               self.update_status(f"本轮发现 {h} 篇高质量文章，累计 {t} 篇"))
                
                # 步骤4: 引用网络扩展
                if not self.workflow_running:
                    break
                self.root.after(0, lambda: self.update_status("步骤4: 执行引用网络扩展..."))
                if not self._workflow_execute_citation_expansion():
                    break
                
                # 检查终止条件
                if total_high_quality_articles >= target_articles:
                    self.root.after(0, lambda: self.update_status(f"达到目标文章数 {target_articles}，工作流完成！"))
                    break
                
                self.root.after(0, lambda i=current_iteration, t=total_high_quality_articles:
                               self.update_status(f"第 {i} 轮完成，累计高质量文章: {t} 篇"))
                
                # 轮次间等待
                if current_iteration < max_iterations and self.workflow_running:
                    time.sleep(3)
            
            # 工作流结束
            if current_iteration >= max_iterations:
                self.root.after(0, lambda: self.update_status(f"达到最大迭代次数 {max_iterations}，工作流完成！"))
            elif not self.workflow_running:
                self.root.after(0, lambda: self.update_status("工作流被用户停止"))
            
            # 工作流结束后合并所有分析结果并执行深度分析
            self.root.after(0, lambda: self.update_status("工作流完成，开始合并分析结果并执行深度分析..."))
            self._workflow_final_analysis()
            
            self.root.after(0, lambda: self.update_status(f"自动工作流完成，总计获得 {total_high_quality_articles} 篇高质量文章"))
            
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: self.update_status(f"工作流执行出错: {error_msg}"))
            self.root.after(0, lambda: messagebox.showerror("错误", f"工作流执行出错: {error_msg}"))
        finally:
            self.root.after(0, self.reset_workflow_buttons)
    
    def _check_workflow_prerequisites(self):
        """检查工作流前置条件"""
        # 检查项目目录
        if not self.current_project_dir:
            self.root.after(0, lambda: messagebox.showwarning("警告", "请先创建项目"))
            return False
        
        # 检查API密钥
        if not self.api_key_entry.get().strip():
            self.root.after(0, lambda: messagebox.showwarning("警告", "请先配置API密钥"))
            return False
        
        # 检查科学问题
        question = self.search_question_text.get("1.0", "end-1c").strip()
        if not question:
            self.root.after(0, lambda: messagebox.showwarning("警告", "请先在搜索工具栏输入科学问题"))
            return False
        
        return True
    
    def _workflow_execute_search(self):
        """工作流中执行搜索"""
        try:
            question = self.search_question_text.get("1.0", "end-1c").strip()
            target_count = int(self.search_target_var.get())
            
            # 更新研究系统配置
            self.research_system.api_key = self.api_key_entry.get().strip()
            self.research_system.project_dir = self.current_project_dir
            self.research_system.rigor_level = self.search_rigor_var.get()
            self.research_system.target_search_count = target_count  # 设置目标搜索数量
            
            # 设置研究问题，确保research_system能够正确处理
            self.research_system.research_question = question
            self.research_system.updated_question = question
            
            # 设置状态回调
            self.research_system.status_callback = self.update_status
            
            # 使用research_system的search_and_analyze方法，传递目标数量
            search_results = self.research_system.search_and_analyze(question, target_count)
            
            # 保存搜索结果
            self._save_search_results(search_results)
            
            return True
            
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: self.update_status(f"搜索执行失败: {error_msg}"))
            return False
    
    def _workflow_execute_analysis(self):
        """工作流中执行内容分析"""
        try:
            if not hasattr(self, 'latest_urls_file') or not os.path.exists(self.latest_urls_file):
                self.root.after(0, lambda: self.update_status("未找到URLs文件，跳过分析"))
                return None
            
            # 读取URLs
            urls = []
            with open(self.latest_urls_file, 'r', encoding='utf-8') as f:
                for line in f:
                    url = line.strip()
                    if url and url.startswith('http'):
                        urls.append(url)
            
            if not urls:
                return None
            
            # 准备分析参数
            research_question = self.search_question_text.get("1.0", "end-1c").strip()
            batch_prompt = self.analysis_prompt_text.get("1.0", "end-1c").strip()
            batch_prompt = batch_prompt.replace("{RESEARCH_QUESTION}", research_question)
            
            # 设置研究系统参数
            self.research_system.batch_analysis_prompt = batch_prompt
            
            # 准备搜索结果格式
            search_results = []
            for url in urls:
                search_results.append({
                    'url': url,
                    'title': 'UnknownName'
                })
            
            # 执行批量分析
            analysis_results = self.research_system.batch_analyze_content(search_results)
            self._save_analysis_results(analysis_results)
            
            return analysis_results
            
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: self.update_status(f"内容分析执行失败: {error_msg}"))
            return None
    
    def _workflow_execute_deep_analysis(self):
        """工作流中执行深度分析 - 默认使用自定义模板"""
        try:
            if not hasattr(self, 'latest_analysis_file') or not os.path.exists(self.latest_analysis_file):
                self.root.after(0, lambda: self.update_status("未找到分析结果文件，跳过深度分析"))
                return False
            
            # 读取分析结果
            with open(self.latest_analysis_file, 'r', encoding='utf-8') as f:
                analysis_results = json.load(f)
            
            # 筛选高质量文章
            threshold = int(self.deep_threshold_var.get())
            high_quality_articles = []
            for article in analysis_results:
                if article.get("success", False):
                    try:
                        score = float(article.get("relevance_score", 0))
                        if score >= threshold:
                            high_quality_articles.append(article)
                    except (ValueError, TypeError):
                        continue
            
            if not high_quality_articles:
                return True  # 没有高质量文章但不算失败
            
            # 创建临时的HighQualityAnalyzer实例
            temp_logs_dir = os.path.join(self.current_project_dir, "temp_analysis")
            os.makedirs(temp_logs_dir, exist_ok=True)
            
            analyzer = HighQualityAnalyzer(
                logs_path=temp_logs_dir,
                threshold=threshold,
                api_key=self.api_key_entry.get().strip()
            )
            
            # 工作流模式下强制使用自定义模板
            analysis_type = "custom"  # 强制使用自定义模板
            
            # 自动保存用户当前的prompt作为自定义模板
            if hasattr(self, 'deep_prompt_text'):
                current_prompt = self.deep_prompt_text.get("1.0", "end-1c").strip()
                if current_prompt:
                    # 保存当前prompt为自定义模板
                    self.save_custom_prompt_silently(current_prompt)
                    self.root.after(0, lambda: self.update_status("工作流模式：使用自定义模板，已自动保存当前prompt"))
                    
                    # 使用当前prompt进行分析
                    def get_custom_prompt(analysis_type):
                        return current_prompt
                    analyzer.get_analysis_prompt = get_custom_prompt
                else:
                    # 如果没有自定义prompt，使用默认的研究脉络分析prompt
                    self.root.after(0, lambda: self.update_status("工作流模式：使用默认研究脉络分析模板"))
            
            # 执行深度分析
            deep_analysis = analyzer.perform_deep_analysis(high_quality_articles, analysis_type)
            
            if deep_analysis:
                # 生成报告
                report_files = analyzer.generate_reports(high_quality_articles, deep_analysis, analysis_type)
                
                # 复制报告到项目目录 (使用temp_analysis目录)
                temp_analysis_dir = os.path.join(self.current_project_dir, "temp_analysis")
                os.makedirs(temp_analysis_dir, exist_ok=True)
                
                if report_files.get("deep_analysis"):
                    import shutil
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    final_report = os.path.join(temp_analysis_dir, f"{analysis_type}_report_{timestamp}.html")
                    shutil.copy2(report_files["deep_analysis"], final_report)
                    self.latest_deep_report = final_report
            
            return True
            
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: self.update_status(f"深度分析执行失败: {error_msg}"))
            return False
    
    def _workflow_execute_citation_expansion(self):
        """工作流中执行引用网络扩展"""
        try:
            if not hasattr(self, 'latest_urls_file') or not os.path.exists(self.latest_urls_file):
                self.root.after(0, lambda: self.update_status("未找到URLs文件，跳过引用网络扩展"))
                return False
            
            # 读取URLs
            urls = []
            with open(self.latest_urls_file, 'r', encoding='utf-8') as f:
                for line in f:
                    url = line.strip()
                    if url and url.startswith('http'):
                        urls.append(url)
            
            if not urls:
                return False
            
            all_citation_data = []
            
            # 从URLs提取DOI并查询引用网络
            for url in urls:
                if not self.workflow_running:
                    return False
                
                # 提取DOI
                doi = extract_doi_from_url(url)
                if doi:
                    # 查询引用文献和被引文献
                    if self.citation_references_var.get():
                        references = query_crossref_references(doi)
                        all_citation_data.extend(references)
                    
                    if self.citation_citations_var.get():
                        citations = query_crossref_citations(doi)
                        all_citation_data.extend(citations)
            
            if not all_citation_data:
                return True  # 没有找到引用数据但不算失败
            
            # 直接收集所有URL，不进行LLM筛选
            citation_urls = []
            unique_urls = set()  # 去重
            
            for citation in all_citation_data:
                if citation.get('url') and citation['url'] not in unique_urls:
                    citation_urls.append(citation['url'])
                    unique_urls.add(citation['url'])
            
            # 应用数量限制（如果设置了的话）
            target_count = int(self.citation_count_var.get())
            if target_count > 0 and len(citation_urls) > target_count:
                citation_urls = citation_urls[:target_count]
            
            if citation_urls:
                self.root.after(0, lambda count=len(citation_urls):
                            self.update_status(f"引用网络扩展完成，获得 {count} 个新的文献URL"))
                
                self._save_expanded_urls(citation_urls)
                
                # 关键修复：将扩展后的URLs传递给research_system，用于下一轮迭代
                self.research_system.previous_citation_urls = citation_urls
                
                # 同时更新latest_urls_file为扩展后的文件（备用机制）
                if hasattr(self, 'latest_expanded_urls_file'):
                    self.latest_urls_file = self.latest_expanded_urls_file
                
                self.root.after(0, lambda: self.update_status(f"已将 {len(citation_urls)} 个扩展URL传递给下一轮迭代"))
            else:
                self.root.after(0, lambda: self.update_status("引用网络扩展未找到有效URL"))
            
            return True
            
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: self.update_status(f"引用网络扩展执行失败: {error_msg}"))
            return False
    
    def _count_high_quality_articles(self, analysis_results):
        """统计高质量文章数量"""
        if not analysis_results:
            return 0
        
        threshold = float(self.analysis_threshold_var.get())
        count = 0
        
        for article in analysis_results:
            if article.get('success', False):
                try:
                    score = float(article.get('relevance_score', 0))
                    if score >= threshold:
                        count += 1
                except (ValueError, TypeError):
                    continue
        
        return count
    
    def _workflow_final_analysis(self):
        """工作流结束后的最终分析：合并所有分析结果并执行深度分析"""
        try:
            # 合并所有分析结果
            merged_file = self.merge_analysis_results_silently()
            if not merged_file:
                self.root.after(0, lambda: self.update_status("没有找到分析结果文件，跳过最终深度分析"))
                return
            
            # 使用合并后的文件执行深度分析
            self.latest_analysis_file = merged_file
            self.root.after(0, lambda: self.update_status("开始执行最终深度分析..."))
            
            # 执行深度分析
            self._execute_final_deep_analysis(merged_file)
            
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: self.update_status(f"最终分析出错: {error_msg}"))
    
    def _execute_final_deep_analysis(self, json_file):
        """执行最终深度分析"""
        try:
            # 读取合并后的分析结果
            with open(json_file, 'r', encoding='utf-8') as f:
                analysis_results = json.load(f)
            
            # 筛选高质量文章
            threshold = int(self.deep_threshold_var.get())
            high_quality_articles = []
            for article in analysis_results:
                if article.get("success", False):
                    try:
                        score = float(article.get("relevance_score", 0))
                        if score >= threshold:
                            high_quality_articles.append(article)
                    except (ValueError, TypeError):
                        continue
            
            if not high_quality_articles:
                self.root.after(0, lambda: self.update_status("没有找到高质量文章，跳过深度分析"))
                return
            
            self.root.after(0, lambda: self.update_status(f"筛选出 {len(high_quality_articles)} 篇高质量文章，开始深度分析..."))
            
            # 在单独线程中执行深度分析
            import threading
            analysis_thread = threading.Thread(target=self._run_final_deep_analysis,
                                             args=(high_quality_articles,), daemon=True)
            analysis_thread.start()
            
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: self.update_status(f"最终深度分析出错: {error_msg}"))
    
    def _run_final_deep_analysis(self, high_quality_articles):
        """在线程中运行最终深度分析"""
        try:
            # 创建临时的HighQualityAnalyzer实例
            temp_logs_dir = os.path.join(self.current_project_dir, "temp_analysis")
            os.makedirs(temp_logs_dir, exist_ok=True)
            
            analyzer = HighQualityAnalyzer(
                logs_path=temp_logs_dir,
                threshold=int(self.deep_threshold_var.get()),
                api_key=self.api_key_entry.get().strip()
            )
            
            # 使用自定义模板
            analysis_type = "custom"
            
            # 获取当前prompt
            if hasattr(self, 'deep_prompt_text'):
                current_prompt = self.deep_prompt_text.get("1.0", "end-1c").strip()
                if current_prompt:
                    # 保存当前prompt为自定义模板
                    self.save_custom_prompt_silently(current_prompt)
                    self.root.after(0, lambda: self.update_status("最终分析：使用自定义模板"))
                    
                    # 使用当前prompt进行分析
                    def get_custom_prompt(analysis_type):
                        return current_prompt
                    analyzer.get_analysis_prompt = get_custom_prompt
                else:
                    self.root.after(0, lambda: self.update_status("最终分析：使用默认研究脉络分析模板"))
            
            # 执行深度分析
            deep_analysis = analyzer.perform_deep_analysis(high_quality_articles, analysis_type)
            
            if deep_analysis:
                # 生成报告
                report_files = analyzer.generate_reports(high_quality_articles, deep_analysis, analysis_type)
                
                # 复制报告到项目目录
                temp_analysis_dir = os.path.join(self.current_project_dir, "temp_analysis")
                os.makedirs(temp_analysis_dir, exist_ok=True)
                
                if report_files.get("deep_analysis"):
                    import shutil
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    final_report = os.path.join(temp_analysis_dir, f"final_workflow_report_{timestamp}.html")
                    shutil.copy2(report_files["deep_analysis"], final_report)
                    self.latest_deep_report = final_report
                    
                    self.root.after(0, lambda: self.update_status("最终深度分析完成，报告已生成"))
                else:
                    self.root.after(0, lambda: self.update_status("深度分析完成，但报告生成失败"))
            else:
                self.root.after(0, lambda: self.update_status("最终深度分析失败"))
                
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: self.update_status(f"最终深度分析出错: {error_msg}"))
    
    def merge_analysis_results(self):
        """合并analysis文件夹下的所有JSON文件（GUI按钮调用）"""
        try:
            if not self.current_project_dir:
                messagebox.showwarning("警告", "请先创建或选择项目")
                return
            
            merged_file = self.merge_analysis_results_silently()
            if merged_file:
                messagebox.showinfo("成功", f"分析结果已合并到:\n{os.path.basename(merged_file)}")
                self.update_status(f"分析结果已合并: {os.path.basename(merged_file)}")
                # 自动设置为深度分析的输入文件
                self.deep_input_var.set(merged_file)
            else:
                messagebox.showwarning("警告", "没有找到可合并的分析结果文件")
                
        except Exception as e:
            messagebox.showerror("错误", f"合并分析结果时出错: {str(e)}")
    
    def merge_analysis_results_silently(self):
        """静默合并analysis文件夹下的所有JSON文件"""
        try:
            if not self.current_project_dir:
                return None
            
            analysis_dir = os.path.join(self.current_project_dir, "analysis")
            if not os.path.exists(analysis_dir):
                return None
            
            # 查找所有analysis_results_*.json文件
            json_files = []
            for filename in os.listdir(analysis_dir):
                if filename.startswith('analysis_results_') and filename.endswith('.json'):
                    json_files.append(os.path.join(analysis_dir, filename))
            
            if not json_files:
                return None
            
            # 按文件修改时间排序
            json_files.sort(key=lambda x: os.path.getmtime(x))
            
            # 合并所有JSON文件
            merged_data = []
            processed_urls = set()  # 用于去重
            
            for json_file in json_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # 去重处理
                    for item in data:
                        url = item.get('url', '')
                        if url and url not in processed_urls:
                            merged_data.append(item)
                            processed_urls.add(url)
                            
                except Exception as e:
                    logger.error(f"读取文件 {json_file} 出错: {str(e)}")
                    continue
            
            if not merged_data:
                return None
            
            # 保存合并后的文件
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            merged_file = os.path.join(analysis_dir, f"merged_analysis_results_{timestamp}.json")
            
            with open(merged_file, 'w', encoding='utf-8') as f:
                json.dump(merged_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"合并了 {len(json_files)} 个文件，总计 {len(merged_data)} 篇文章")
            return merged_file
            
        except Exception as e:
            logger.error(f"合并分析结果出错: {str(e)}")
            return None
    
    # ==================== 搜索工具栏方法 ====================
    
    def load_search_example(self, category):
        """加载示例问题"""
        examples = {
            "材料科学": "钙钛矿太阳能电池的稳定性问题及其解决方案有哪些最新进展？",
            "生物医学": "CRISPR-Cas9基因编辑技术在治疗遗传性疾病方面的最新应用和挑战是什么？",
            "化学合成": "绿色化学中催化剂的设计原理和在有机合成中的应用前景如何？"
        }
        
        if category in examples:
            self.search_question_text.delete("1.0", tk.END)
            self.search_question_text.insert("1.0", examples[category])
    
    def start_search(self):
        """开始搜索 - 严格使用原有功能"""
        try:
            if not self.current_project_dir:
                messagebox.showwarning("警告", "请先创建或选择项目")
                return
            
            question = self.search_question_text.get("1.0", "end-1c").strip()
            if not question:
                messagebox.showwarning("警告", "请输入科学问题")
                return
            
            # 更新研究系统配置
            self.research_system.api_key = self.api_key_entry.get().strip()
            self.research_system.project_dir = self.current_project_dir
            self.research_system.rigor_level = self.search_rigor_var.get()
            
            self.update_status("开始搜索流程...")
            
            # 在单独线程中执行搜索
            search_thread = threading.Thread(target=self._execute_search, args=(question,), daemon=True)
            search_thread.start()
            
        except Exception as e:
            messagebox.showerror("错误", f"启动搜索时出错: {str(e)}")
    
    def _execute_search(self, question):
        """执行搜索的具体逻辑 - 严格使用原有函数，增加目标数量限制"""
        try:
            # 1. 翻译问题为英文
            self.root.after(0, lambda: self.update_status("翻译科学问题..."))
            english_question = translate_question_to_english(question, self.research_system.api_key)
            
            # 2. 分解为搜索查询
            self.root.after(0, lambda: self.update_status("生成搜索查询..."))
            search_queries = call_deepseek_api(english_question, self.search_rigor_var.get(), self.research_system.api_key)
            
            # 3. 获取目标数量限制
            target_count = int(self.search_target_var.get())
            # page_count = int(self.search_pages_var.get())
            
            # 4. 执行学术搜索 - 带目标数量限制
            self.root.after(0, lambda: self.update_status(f"执行学术搜索（目标数量: {target_count}）..."))
            all_results = []
            unique_urls = {}
            
            for i, query in enumerate(search_queries):
                if len(unique_urls) >= target_count:
                    self.root.after(0, lambda: self.update_status(f"已达到目标数量 {target_count}，停止搜索"))
                    break
                
                self.root.after(0, lambda q=query, idx=i: self.update_status(f"搜索查询 {idx+1}/{len(search_queries)}: {q}"))
                results = search_bing_academic(query)
                
                # 实时去重并检查数量
                for item in results:
                    if item['url'] not in unique_urls:
                        unique_urls[item['url']] = item
                        if len(unique_urls) >= target_count:
                            self.root.after(0, lambda current=len(unique_urls):
                                          self.update_status(f"已达到目标数量 {current}，停止当前查询"))
                            break
                
                self.root.after(0, lambda current=len(unique_urls), target=target_count:
                              self.update_status(f"当前收集: {current}/{target} 个URL"))
            
            final_results = list(unique_urls.values())
            
            # 5. 保存到文件 - 使用原有的保存逻辑
            self.root.after(0, lambda: self.update_status("保存搜索结果..."))
            self._save_search_results(final_results)
            
            # 6. 更新界面显示
            result_text = f"搜索完成！\n"
            result_text += f"原始问题: {question}\n"
            result_text += f"英文翻译: {english_question}\n"
            result_text += f"生成查询: {len(search_queries)} 个\n"
            result_text += f"找到结果: {len(final_results)} 个唯一URL\n\n"
            
            for i, result in enumerate(final_results[:10], 1):
                result_text += f"{i}. {result['title'][:50]}...\n   {result['url']}\n\n"
            
            if len(final_results) > 10:
                result_text += f"... 还有 {len(final_results) - 10} 个结果\n"
            
            self.root.after(0, lambda: self._update_search_results(result_text))
            self.root.after(0, lambda: self.update_status(f"搜索完成，保存了 {len(final_results)} 个URL"))
            
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: self.update_status(f"搜索出错: {error_msg}"))
            self.root.after(0, lambda: messagebox.showerror("错误", f"搜索出错: {error_msg}"))
    
    def _save_search_results(self, results):
        """保存搜索结果 - 使用原有的保存逻辑"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 保存完整结果
            results_file = os.path.join(self.current_project_dir, "search_results", f"search_results_{timestamp}.txt")
            os.makedirs(os.path.dirname(results_file), exist_ok=True)
            
            with open(results_file, 'w', encoding='utf-8') as f:
                for item in results:
                    f.write(f"{item['title']} | {item['url']}\n")
            
            # 保存URL列表 - 这是其他功能栏需要的格式
            urls_file = os.path.join(self.current_project_dir, "urls", f"iteration_1_urls.txt")
            os.makedirs(os.path.dirname(urls_file), exist_ok=True)
            
            with open(urls_file, 'w', encoding='utf-8') as f:
                for item in results:
                    f.write(f"{item['url']}\n")
            
            self.latest_urls_file = urls_file
            
        except Exception as e:
            raise Exception(f"保存搜索结果出错: {str(e)}")
    
    def _update_search_results(self, text):
        """更新搜索结果显示"""
        self.search_results_text.config(state='normal')
        self.search_results_text.delete("1.0", tk.END)
        self.search_results_text.insert("1.0", text)
        self.search_results_text.config(state='disabled')
    
    def view_search_results(self):
        """查看搜索结果"""
        if hasattr(self, 'latest_urls_file') and os.path.exists(self.latest_urls_file):
            webbrowser.open(f"file://{os.path.abspath(self.latest_urls_file)}")
        else:
            messagebox.showwarning("警告", "没有找到搜索结果文件")
    
    def export_search_urls(self):
        """导出搜索URLs"""
        if hasattr(self, 'latest_urls_file') and os.path.exists(self.latest_urls_file):
            export_file = filedialog.asksaveasfilename(
                title="导出URLs",
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            if export_file:
                import shutil
                shutil.copy2(self.latest_urls_file, export_file)
                messagebox.showinfo("成功", f"URLs已导出到: {export_file}")
        else:
            messagebox.showwarning("警告", "没有找到可导出的URLs文件")
    
    # ==================== 内容分析栏方法 ====================
    
    def select_urls_file(self):
        """选择URLs文件"""
        file_path = filedialog.askopenfilename(
            title="选择URLs文件",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            self.analysis_input_var.set(file_path)
    
    def use_latest_urls(self):
        """使用最新的URLs文件"""
        if hasattr(self, 'latest_urls_file') and os.path.exists(self.latest_urls_file):
            self.analysis_input_var.set(self.latest_urls_file)
        else:
            messagebox.showwarning("警告", "没有找到最新的URLs文件，请先执行搜索")
    
    def open_pdf_analysis_tool(self):
        """打开PDF分析工具"""
        try:
            import subprocess
            import sys
            
            # 获取PDF分析工具的路径
            pdf_tool_path = os.path.join(os.path.dirname(__file__), "pdf_analysis_gui.py")
            
            if os.path.exists(pdf_tool_path):
                # 在新进程中启动PDF分析工具
                subprocess.Popen([sys.executable, pdf_tool_path])
                self.update_status("PDF分析工具已启动")
            else:
                messagebox.showerror("错误", f"找不到PDF分析工具: {pdf_tool_path}")
                
        except Exception as e:
            messagebox.showerror("错误", f"启动PDF分析工具时出错: {str(e)}")
    
    def start_content_analysis(self):
        """开始内容分析 - 严格使用原有功能"""
        try:
            urls_file = self.analysis_input_var.get().strip()
            if not urls_file or not os.path.exists(urls_file):
                messagebox.showwarning("警告", "请选择有效的URLs文件")
                return
            
            if not self.current_project_dir:
                messagebox.showwarning("警告", "请先创建或选择项目")
                return
            
            # 读取URLs
            urls = []
            with open(urls_file, 'r', encoding='utf-8') as f:
                for line in f:
                    url = line.strip()
                    if url and url.startswith('http'):
                        urls.append(url)
            
            if not urls:
                messagebox.showwarning("警告", "URLs文件中没有有效的URL")
                return
            
            self.update_status(f"开始分析 {len(urls)} 个URL...")
            
            # 在单独线程中执行分析
            analysis_thread = threading.Thread(target=self._execute_content_analysis, args=(urls,), daemon=True)
            analysis_thread.start()
            
        except Exception as e:
            messagebox.showerror("错误", f"启动内容分析时出错: {str(e)}")
    
    def _execute_content_analysis(self, urls):
        """执行内容分析 - 严格使用原有的批量分析功能"""
        try:
            # 准备分析参数
            research_question = self.search_question_text.get("1.0", "end-1c").strip()
            if not research_question:
                research_question = "学术文献相关性分析"
            
            # 获取分析prompt
            batch_prompt = self.analysis_prompt_text.get("1.0", "end-1c").strip()
            batch_prompt = batch_prompt.replace("{RESEARCH_QUESTION}", research_question)
            
            # 设置研究系统参数
            self.research_system.api_key = self.api_key_entry.get().strip()
            self.research_system.project_dir = self.current_project_dir
            self.research_system.batch_analysis_prompt = batch_prompt
            
            # 准备搜索结果格式
            search_results = []
            for url in urls:
                search_results.append({
                    'url': url,
                    'title': 'UnknownName'
                })
            
            # 执行批量分析 - 使用原有的batch_analyze_content方法
            self.root.after(0, lambda: self.update_status("开始批量分析内容..."))
            analysis_results = self.research_system.batch_analyze_content(search_results)
            
            # 保存分析结果
            self.root.after(0, lambda: self.update_status("保存分析结果..."))
            self._save_analysis_results(analysis_results)
            
            # 更新界面显示
            success_count = sum(1 for r in analysis_results if r.get('success', False))
            result_text = f"内容分析完成！\n"
            result_text += f"总计分析: {len(analysis_results)} 篇文章\n"
            result_text += f"成功分析: {success_count} 篇\n"
            result_text += f"失败: {len(analysis_results) - success_count} 篇\n\n"
            
            # 显示高分文章
            high_quality = [r for r in analysis_results if r.get('success', False) and 
                          float(r.get('relevance_score', 0)) >= float(self.analysis_threshold_var.get())]
            
            result_text += f"高质量文章 (≥{self.analysis_threshold_var.get()}分): {len(high_quality)} 篇\n\n"
            
            for i, article in enumerate(high_quality[:5], 1):
                result_text += f"{i}. {article.get('title', '未知标题')[:50]}...\n"
                result_text += f"   评分: {article.get('relevance_score', 0)}/10\n"
                result_text += f"   DOI: {article.get('doi', '未知')}\n\n"
            
            if len(high_quality) > 5:
                result_text += f"... 还有 {len(high_quality) - 5} 篇高质量文章\n"
            
            self.root.after(0, lambda: self._update_analysis_results(result_text))
            self.root.after(0, lambda: self.update_status(f"内容分析完成，找到 {len(high_quality)} 篇高质量文章"))
            
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: self.update_status(f"内容分析出错: {error_msg}"))
            self.root.after(0, lambda: messagebox.showerror("错误", f"内容分析出错: {error_msg}"))
    
    
    def _save_analysis_results(self, analysis_results):
        """保存分析结果"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 保存JSON格式
            json_file = os.path.join(self.current_project_dir, "analysis", f"analysis_results_{timestamp}.json")
            os.makedirs(os.path.dirname(json_file), exist_ok=True)
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(analysis_results, f, ensure_ascii=False, indent=2)
            
            self.latest_analysis_file = json_file
            
        except Exception as e:
            raise Exception(f"保存分析结果出错: {str(e)}")
    
    def _update_analysis_results(self, text):
        """更新分析结果显示"""
        self.analysis_results_text.config(state='normal')
        self.analysis_results_text.delete("1.0", tk.END)
        self.analysis_results_text.insert("1.0", text)
        self.analysis_results_text.config(state='disabled')
    
    def view_analysis_logs(self):
        """查看分析日志"""
        if self.current_project_dir:
            logs_dir = os.path.join(self.current_project_dir, "logs")
            if os.path.exists(logs_dir):
                if platform.system() == "Windows":
                    os.startfile(logs_dir)
                else:
                    webbrowser.open(f"file://{logs_dir}")
            else:
                messagebox.showwarning("警告", "没有找到日志文件夹")
        else:
            messagebox.showwarning("警告", "请先选择项目")
    
    # ==================== 深度分析栏方法 ====================
    
    def select_analysis_json(self):
        """选择分析结果JSON文件"""
        file_path = filedialog.askopenfilename(
            title="选择分析结果JSON文件",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file_path:
            self.deep_input_var.set(file_path)
    
    def use_latest_analysis(self):
        """使用最新的分析结果文件"""
        if hasattr(self, 'latest_analysis_file') and os.path.exists(self.latest_analysis_file):
            self.deep_input_var.set(self.latest_analysis_file)
        else:
            messagebox.showwarning("警告", "没有找到最新的分析结果文件，请先执行内容分析")
    
    def start_deep_analysis(self):
        """开始深度分析 - 严格使用原有的HighQualityAnalyzer"""
        try:
            json_file = self.deep_input_var.get().strip()
            if not json_file or not os.path.exists(json_file):
                messagebox.showwarning("警告", "请选择有效的分析结果JSON文件")
                return
            
            # 检查项目目录是否存在
            if not self.current_project_dir:
                messagebox.showwarning("警告", "请先创建或选择项目目录")
                return
            
            analysis_type = self.deep_analysis_type_var.get()
            threshold = int(self.deep_threshold_var.get())
            
            self.update_status(f"开始深度分析 ({analysis_type})...")
            
            # 在单独线程中执行深度分析
            deep_thread = threading.Thread(target=self._execute_deep_analysis,
                                          args=(json_file, analysis_type, threshold), daemon=True)
            deep_thread.start()
            
        except Exception as e:
            messagebox.showerror("错误", f"启动深度分析时出错: {str(e)}")
    
    def _execute_deep_analysis(self, json_file, analysis_type, threshold):
        """执行深度分析 - 使用原有的HighQualityAnalyzer类"""
        try:
            # 读取分析结果
            with open(json_file, 'r', encoding='utf-8') as f:
                analysis_results = json.load(f)
            
            # 筛选高质量文章
            high_quality_articles = []
            for article in analysis_results:
                if article.get("success", False):
                    try:
                        score = float(article.get("relevance_score", 0))
                        if score >= threshold:
                            high_quality_articles.append(article)
                    except (ValueError, TypeError):
                        continue
            
            if not high_quality_articles:
                self.root.after(0, lambda: messagebox.showwarning("警告", f"没有找到评分≥{threshold}的高质量文章"))
                return
            
            self.root.after(0, lambda: self.update_status(f"筛选出 {len(high_quality_articles)} 篇高质量文章，开始深度分析..."))
            
            # 创建临时的HighQualityAnalyzer实例
            if not self.current_project_dir:
                self.root.after(0, lambda: messagebox.showerror("错误", "项目目录未设置，无法创建临时分析目录"))
                return
            
            temp_logs_dir = os.path.join(self.current_project_dir, "temp_analysis")
            os.makedirs(temp_logs_dir, exist_ok=True)
            
            analyzer = HighQualityAnalyzer(
                logs_path=temp_logs_dir,
                threshold=threshold,
                api_key=self.api_key_entry.get().strip()
            )
            
            # 获取用户自定义的prompt
            custom_prompt = self.deep_prompt_text.get("1.0", "end-1c").strip()
            
            # 如果用户有自定义prompt，则使用自定义的；否则使用默认的
            if custom_prompt:
                # 临时替换analyzer中的prompt
                original_prompt = analyzer.get_analysis_prompt(analysis_type)
                # 创建一个临时的自定义prompt方法
                def get_custom_prompt(analysis_type):
                    return custom_prompt
                # 临时替换方法
                analyzer.get_analysis_prompt = get_custom_prompt
                self.root.after(0, lambda: self.update_status("使用自定义深度分析Prompt..."))
            else:
                self.root.after(0, lambda: self.update_status("使用默认深度分析Prompt..."))
            
            # 直接使用高质量文章进行深度分析
            deep_analysis = analyzer.perform_deep_analysis(high_quality_articles, analysis_type)
            
            if deep_analysis:
                # 生成报告
                report_files = analyzer.generate_reports(high_quality_articles, deep_analysis, analysis_type)
                
                # 复制报告到项目目录
                if not self.current_project_dir:
                    self.root.after(0, lambda: messagebox.showerror("错误", "项目目录未设置，无法保存报告"))
                    return
                
                temp_analysis_dir = os.path.join(self.current_project_dir, "temp_analysis")
                os.makedirs(temp_analysis_dir, exist_ok=True)
                
                if report_files.get("deep_analysis"):
                    import shutil
                    final_report = os.path.join(temp_analysis_dir, f"{analysis_type}_report.html")
                    shutil.copy2(report_files["deep_analysis"], final_report)
                    self.latest_deep_report = final_report
                
                # 更新界面显示
                result_text = f"深度分析完成！\n"
                result_text += f"分析类型: {analysis_type}\n"
                result_text += f"分析文章数: {len(high_quality_articles)}\n"
                result_text += f"报告已生成: {final_report}\n\n"
                result_text += "分析摘要:\n"
                result_text += deep_analysis[:500] + "...\n\n"
                result_text += "完整报告请点击'打开HTML'查看"
                
                self.root.after(0, lambda: self._update_deep_results(result_text))
                self.root.after(0, lambda: self.update_status("深度分析完成，报告已生成"))
            else:
                self.root.after(0, lambda: messagebox.showerror("错误", "深度分析失败"))
            
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: self.update_status(f"深度分析出错: {error_msg}"))
            self.root.after(0, lambda: messagebox.showerror("错误", f"深度分析出错: {error_msg}"))
    
    def _update_deep_results(self, text):
        """更新深度分析结果显示"""
        self.deep_results_text.config(state='normal')
        self.deep_results_text.delete("1.0", tk.END)
        self.deep_results_text.insert("1.0", text)
        self.deep_results_text.config(state='disabled')
    
    def preview_deep_report(self):
        """预览深度分析报告"""
        if hasattr(self, 'latest_deep_report') and os.path.exists(self.latest_deep_report):
            # 读取HTML文件的前几行作为预览
            try:
                with open(self.latest_deep_report, 'r', encoding='utf-8') as f:
                    content = f.read()[:1000]
                messagebox.showinfo("报告预览", content + "...")
            except Exception as e:
                messagebox.showerror("错误", f"预览报告出错: {str(e)}")
        else:
            messagebox.showwarning("警告", "没有找到可预览的报告，请先执行深度分析")
    
    def open_deep_html(self):
        """打开深度分析HTML报告"""
        if hasattr(self, 'latest_deep_report') and os.path.exists(self.latest_deep_report):
            webbrowser.open(f"file://{os.path.abspath(self.latest_deep_report)}")
        else:
            messagebox.showwarning("警告", "没有找到HTML报告，请先执行深度分析")
    
    def on_deep_analysis_type_changed(self, *args):
        """当深度分析类型改变时更新prompt"""
        self.load_default_deep_prompt()
    
    def load_default_deep_prompt(self):
        """加载默认的深度分析prompt"""
        analysis_type = self.deep_analysis_type_var.get()
        
        # 从high_quality_analyzer获取默认prompt
        from high_quality_analyzer import RESEARCH_FLOW_PROMPT, TIMELINE_ANALYSIS_PROMPT, METHODOLOGY_ANALYSIS_PROMPT
        
        prompts = {
            "research_flow": RESEARCH_FLOW_PROMPT,
            "timeline": TIMELINE_ANALYSIS_PROMPT,
            "methodology": METHODOLOGY_ANALYSIS_PROMPT,
            "custom": RESEARCH_FLOW_PROMPT  # 自定义模板默认使用研究脉络分析的prompt
        }
        
        type_names = {
            "research_flow": "研究脉络分析",
            "timeline": "时间线分析",
            "methodology": "方法学分析",
            "custom": "自定义"
        }
        
        # 如果是自定义模板，先尝试加载保存的自定义prompt
        if analysis_type == "custom":
            custom_prompt = self.load_saved_custom_prompt()
            if custom_prompt:
                self.deep_prompt_text.delete("1.0", tk.END)
                self.deep_prompt_text.insert("1.0", custom_prompt)
                self.current_prompt_type_label.config(text="自定义")
                return
        
        # 更新prompt文本
        default_prompt = prompts.get(analysis_type, RESEARCH_FLOW_PROMPT)
        self.deep_prompt_text.delete("1.0", tk.END)
        self.deep_prompt_text.insert("1.0", default_prompt)
        
        # 更新类型标签
        type_name = type_names.get(analysis_type, "研究脉络分析")
        self.current_prompt_type_label.config(text=type_name)
    
    def reset_deep_prompt(self):
        """重置深度分析prompt为默认值"""
        self.load_default_deep_prompt()
        messagebox.showinfo("成功", "已重置为默认Prompt模板")
    
    def save_deep_prompt(self):
        """保存深度分析prompt到文件"""
        try:
            analysis_type = self.deep_analysis_type_var.get()
            type_names = {
                "research_flow": "研究脉络分析",
                "timeline": "时间线分析",
                "methodology": "方法学分析",
                "custom": "自定义"
            }
            
            # 如果是自定义模板，直接保存到项目目录
            if analysis_type == "custom":
                self.save_custom_prompt()
                return
            
            default_filename = f"deep_analysis_{analysis_type}_prompt.txt"
            file_path = filedialog.asksaveasfilename(
                title=f"保存{type_names.get(analysis_type, '深度分析')}Prompt模板",
                defaultextension=".txt",
                initialvalue=default_filename,
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            
            if file_path:
                prompt_content = self.deep_prompt_text.get("1.0", "end-1c")
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(prompt_content)
                messagebox.showinfo("成功", f"深度分析Prompt模板已保存到:\n{file_path}")
                self.update_status(f"深度分析Prompt模板已保存: {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("错误", f"保存Prompt模板时出错: {str(e)}")
    
    def save_custom_prompt(self):
        """保存自定义prompt到项目目录"""
        try:
            if not self.current_project_dir:
                messagebox.showwarning("警告", "请先创建或选择项目")
                return
            
            prompt_content = self.deep_prompt_text.get("1.0", "end-1c")
            self.save_custom_prompt_silently(prompt_content)
            
            messagebox.showinfo("成功", "自定义Prompt模板已保存")
            self.update_status("自定义Prompt模板已保存")
            
        except Exception as e:
            messagebox.showerror("错误", f"保存自定义Prompt模板时出错: {str(e)}")
    
    def save_custom_prompt_silently(self, prompt_content):
        """静默保存自定义prompt（用于工作流模式）"""
        try:
            if not self.current_project_dir:
                return
            
            custom_prompt_file = os.path.join(self.current_project_dir, "temp_analysis", "custom_prompt.txt")
            os.makedirs(os.path.dirname(custom_prompt_file), exist_ok=True)
            
            with open(custom_prompt_file, 'w', encoding='utf-8') as f:
                f.write(prompt_content)
            
        except Exception as e:
            logger.error(f"静默保存自定义Prompt出错: {str(e)}")
    
    def load_saved_custom_prompt(self):
        """加载保存的自定义prompt"""
        try:
            if not self.current_project_dir:
                return None
            
            custom_prompt_file = os.path.join(self.current_project_dir, "temp_analysis", "custom_prompt.txt")
            if os.path.exists(custom_prompt_file):
                with open(custom_prompt_file, 'r', encoding='utf-8') as f:
                    return f.read()
            return None
            
        except Exception as e:
            logger.error(f"加载自定义Prompt出错: {str(e)}")
            return None
    
    def load_deep_prompt(self):
        """从文件加载深度分析prompt"""
        try:
            file_path = filedialog.askopenfilename(
                title="加载深度分析Prompt模板",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            
            if file_path:
                with open(file_path, 'r', encoding='utf-8') as f:
                    prompt_content = f.read()
                
                self.deep_prompt_text.delete("1.0", tk.END)
                self.deep_prompt_text.insert("1.0", prompt_content)
                messagebox.showinfo("成功", f"已加载深度分析Prompt模板:\n{os.path.basename(file_path)}")
                self.update_status(f"已加载深度分析Prompt模板: {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("错误", f"加载Prompt模板时出错: {str(e)}")
    
    # ==================== 引用网络栏方法 ====================
    
    def select_citation_urls(self):
        """选择引用网络URLs文件"""
        file_path = filedialog.askopenfilename(
            title="选择URLs文件",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            self.citation_input_var.set(file_path)
    
    def use_latest_citation_urls(self):
        """使用最新的URLs文件"""
        if hasattr(self, 'latest_urls_file') and os.path.exists(self.latest_urls_file):
            self.citation_input_var.set(self.latest_urls_file)
        else:
            messagebox.showwarning("警告", "没有找到最新的URLs文件，请先执行搜索")
    
    def start_citation_expansion(self):
        """开始引用网络扩展 - 严格使用原有功能"""
        try:
            urls_file = self.citation_input_var.get().strip()
            if not urls_file or not os.path.exists(urls_file):
                messagebox.showwarning("警告", "请选择有效的URLs文件")
                return
            
            # 读取URLs并提取DOI
            urls = []
            with open(urls_file, 'r', encoding='utf-8') as f:
                for line in f:
                    url = line.strip()
                    if url and url.startswith('http'):
                        urls.append(url)
            
            if not urls:
                messagebox.showwarning("警告", "URLs文件中没有有效的URL")
                return
            
            self.update_status(f"开始扩展引用网络，处理 {len(urls)} 个URL...")
            
            # 在单独线程中执行引用网络扩展
            citation_thread = threading.Thread(target=self._execute_citation_expansion, args=(urls,), daemon=True)
            citation_thread.start()
            
        except Exception as e:
            messagebox.showerror("错误", f"启动引用网络扩展时出错: {str(e)}")
    
    def _execute_citation_expansion(self, urls):
        """执行引用网络扩展 - 使用原有的引用网络功能，增强调试输出和智能筛选"""
        try:
            print("\n" + "="*80)
            print("🔗 开始网络工具栏引用扩展过程")
            print("="*80)
            print(f"📊 输入统计:")
            print(f"   - 待处理URL数量: {len(urls)}")
            print(f"   - 引用文献选项: {'✓' if self.citation_references_var.get() else '✗'}")
            print(f"   - 被引文献选项: {'✓' if self.citation_citations_var.get() else '✗'}")
            print(f"   - 筛选数量限制: {self.citation_count_var.get()}")
            
            all_citation_data = []
            processed_dois = []
            
            # 步骤a: 读取URLs文件，得到初始URL列表
            print(f"\n📋 步骤a: 处理初始URL列表")
            
            # 步骤b: 对每个URL，提取DOI
            print(f"\n🔍 步骤b: 从URLs提取DOI并查询引用网络")
            for i, url in enumerate(urls):
                self.root.after(0, lambda idx=i: self.update_status(f"处理URL {idx+1}/{len(urls)}..."))
                print(f"\n   [{i+1}/{len(urls)}] 处理URL: {url[:80]}...")
                
                # 提取DOI
                doi = extract_doi_from_url(url)
                if doi:
                    print(f"   ✅ 提取到DOI: {doi}")
                    processed_dois.append(doi)
                    self.root.after(0, lambda d=doi: self.update_status(f"查询DOI引用网络: {d}"))
                    
                    # 步骤c: 查询引用文献（参考文献）
                    if self.citation_references_var.get():
                        print(f"   📚 步骤c: 查询引用文献（它引用了谁）...")
                        references = query_crossref_references(doi)
                        print(f"   📚 找到引用文献: {len(references)} 篇")
                        all_citation_data.extend(references)
                    
                    # 步骤d: 查询被引文献（引用了这篇文章的文献）
                    if self.citation_citations_var.get():
                        print(f"   📝 步骤d: 查询被引文献（谁引用了它）...")
                        citations = query_crossref_citations(doi)
                        print(f"   📝 找到被引文献: {len(citations)} 篇")
                        all_citation_data.extend(citations)
                else:
                    print(f"   ❌ 未能提取DOI")
            
            # 步骤e: 合并并去重
            print(f"\n🔄 步骤e: 合并引用数据并去重")
            print(f"   - 处理的DOI数量: {len(processed_dois)}")
            print(f"   - 原始引用数据总数: {len(all_citation_data)}")
            
            if not all_citation_data:
                print("   ❌ 没有找到任何引用网络数据")
                self.root.after(0, lambda: messagebox.showwarning("警告", "没有找到引用网络数据"))
                return
            
            # 去重处理
            unique_citations = {}
            for citation in all_citation_data:
                key = citation.get('doi', '') or citation.get('url', '') or citation.get('title', '')
                if key and key not in unique_citations:
                    unique_citations[key] = citation
            
            deduplicated_citations = list(unique_citations.values())
            print(f"   - 去重后引用数据: {len(deduplicated_citations)} 篇")
            
            self.root.after(0, lambda: self.update_status(f"找到 {len(deduplicated_citations)} 个去重后的引用关系，开始智能筛选..."))
            
            # 步骤f: 智能筛选 - 读取高质量文章信息
            print(f"\n🧠 步骤f: 启动智能筛选（使用DeepSeek推理模式）")
            
            # 尝试读取最新的分析结果作为高质量文章参考
            high_quality_articles = []
            if hasattr(self, 'latest_analysis_file') and os.path.exists(self.latest_analysis_file):
                try:
                    with open(self.latest_analysis_file, 'r', encoding='utf-8') as f:
                        analysis_results = json.load(f)
                    
                    # 筛选高质量文章（评分≥8）
                    threshold = 8
                    for article in analysis_results:
                        if article.get("success", False):
                            try:
                                score = float(article.get("relevance_score", 0))
                                if score >= threshold:
                                    high_quality_articles.append(article)
                            except (ValueError, TypeError):
                                continue
                    
                    print(f"   ✅ 成功读取高质量文章: {len(high_quality_articles)} 篇（评分≥{threshold}）")
                    for i, article in enumerate(high_quality_articles[:3]):
                        print(f"      [{i+1}] {article.get('title', '未知标题')[:60]}... (评分: {article.get('relevance_score', 0)})")
                        
                except Exception as e:
                    print(f"   ⚠️ 读取分析结果失败: {str(e)}")
            else:
                print(f"   ⚠️ 未找到最新分析结果文件，将使用空的高质量文章列表")
            
            # 使用优化的智能筛选功能
            self.research_system.api_key = self.api_key_entry.get().strip()
            
            # 获取目标筛选数量
            target_count = int(self.citation_count_var.get())
            
            print(f"   🎯 开始DeepSeek推理模式筛选...")
            print(f"   📊 筛选参数:")
            print(f"      - 待筛选文献数: {len(deduplicated_citations)}")
            print(f"      - 参考高质量文章数: {len(high_quality_articles)}")
            print(f"      - 目标筛选数量: {target_count}")
            
            filtered_citations = self.research_system.intelligent_citation_filtering(
                deduplicated_citations,
                high_quality_articles,  # 传入真实的高质量文章
                target_count  # 传入目标筛选数量
            )
            
            print(f"   ✅ 智能筛选完成: {len(deduplicated_citations)} → {len(filtered_citations)} 篇")
            
            # 智能筛选已经应用了数量限制，这里直接使用结果
            final_citations = filtered_citations
            print(f"   📏 最终筛选结果: {len(final_citations)} 篇")
            
            # 步骤g: 生成URLs并保存
            print(f"\n💾 步骤g: 生成URLs并保存到新文件")
            citation_urls = []
            for citation in final_citations:
                if citation.get('url'):
                    citation_urls.append(citation['url'])
            
            print(f"   📊 最终统计:")
            print(f"      - 生成URL数量: {len(citation_urls)}")
            print(f"      - 成功率: {len(citation_urls)/len(final_citations)*100:.1f}%" if final_citations else "0%")
            
            # 保存扩展后的URLs
            self._save_expanded_urls(citation_urls)
            print(f"   ✅ URLs已保存到文件")
            
            # 更新界面显示
            result_text = f"🔗 引用网络扩展完成！\n"
            result_text += f"="*50 + "\n"
            result_text += f"📊 处理统计:\n"
            result_text += f"   原始URL数: {len(urls)}\n"
            result_text += f"   提取DOI数: {len(processed_dois)}\n"
            result_text += f"   找到引用关系: {len(all_citation_data)}\n"
            result_text += f"   去重后数量: {len(deduplicated_citations)}\n"
            result_text += f"   智能筛选后: {len(filtered_citations)}\n"
            result_text += f"   最终URL数: {len(citation_urls)}\n\n"
            
            result_text += f"🧠 智能筛选详情:\n"
            result_text += f"   参考高质量文章: {len(high_quality_articles)} 篇\n"
            result_text += f"   使用模型: DeepSeek-Reasoner\n"
            result_text += f"   筛选成功率: {len(filtered_citations)/len(deduplicated_citations)*100:.1f}%\n\n" if deduplicated_citations else "   筛选成功率: 0%\n\n"
            
            result_text += f"📋 筛选结果预览 (前5个):\n"
            for i, citation in enumerate(final_citations[:5], 1):
                result_text += f"   {i}. {citation.get('title', '未知标题')[:50]}...\n"
                result_text += f"      关系: {citation.get('relation', '未知')}\n"
                result_text += f"      年份: {citation.get('year', '未知')}\n"
                result_text += f"      URL: {citation.get('url', '未知')[:60]}...\n\n"
            
            if len(final_citations) > 5:
                result_text += f"   ... 还有 {len(final_citations) - 5} 个引用文献\n"
            
            print(f"\n🎉 引用网络扩展过程完成！")
            print("="*80)
            
            self.root.after(0, lambda: self._update_citation_results(result_text))
            self.root.after(0, lambda: self.update_status(f"引用网络扩展完成，生成 {len(citation_urls)} 个新URL"))
            
        except Exception as e:
            error_msg = str(e)
            print(f"\n❌ 引用网络扩展出错: {error_msg}")
            import traceback
            traceback.print_exc()
            self.root.after(0, lambda: self.update_status(f"引用网络扩展出错: {error_msg}"))
            self.root.after(0, lambda: messagebox.showerror("错误", f"引用网络扩展出错: {error_msg}"))
    
    def _save_expanded_urls(self, urls):
        """保存扩展后的URLs"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            expanded_urls_file = os.path.join(self.current_project_dir, "urls", f"expanded_urls_{timestamp}.txt")
            os.makedirs(os.path.dirname(expanded_urls_file), exist_ok=True)
            
            with open(expanded_urls_file, 'w', encoding='utf-8') as f:
                for url in urls:
                    f.write(f"{url}\n")
            
            self.latest_expanded_urls_file = expanded_urls_file
            
        except Exception as e:
            raise Exception(f"保存扩展URLs出错: {str(e)}")
    
    def _update_citation_results(self, text):
        """更新引用网络结果显示"""
        self.citation_results_text.config(state='normal')
        self.citation_results_text.delete("1.0", tk.END)
        self.citation_results_text.insert("1.0", text)
        self.citation_results_text.config(state='disabled')
    
    def preview_citation_results(self):
        """预览引用网络结果"""
        if hasattr(self, 'latest_expanded_urls_file') and os.path.exists(self.latest_expanded_urls_file):
            webbrowser.open(f"file://{os.path.abspath(self.latest_expanded_urls_file)}")
        else:
            messagebox.showwarning("警告", "没有找到扩展结果文件")
    
    def save_expanded_urls(self):
        """保存扩展后的URLs"""
        if hasattr(self, 'latest_expanded_urls_file') and os.path.exists(self.latest_expanded_urls_file):
            export_file = filedialog.asksaveasfilename(
                title="保存扩展URLs",
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            if export_file:
                import shutil
                shutil.copy2(self.latest_expanded_urls_file, export_file)
                messagebox.showinfo("成功", f"扩展URLs已保存到: {export_file}")
        else:
            messagebox.showwarning("警告", "没有找到可保存的扩展URLs文件")
    
    # ==================== PDF下载栏方法 ====================
    
    def select_pdf_urls(self):
        """选择PDF下载URLs文件"""
        file_path = filedialog.askopenfilename(
            title="选择URLs文件",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            self.pdf_input_var.set(file_path)
    
    def use_latest_pdf_urls(self):
        """使用最新的URLs文件"""
        if hasattr(self, 'latest_urls_file') and os.path.exists(self.latest_urls_file):
            self.pdf_input_var.set(self.latest_urls_file)
        elif hasattr(self, 'latest_expanded_urls_file') and os.path.exists(self.latest_expanded_urls_file):
            self.pdf_input_var.set(self.latest_expanded_urls_file)
        else:
            messagebox.showwarning("警告", "没有找到最新的URLs文件，请先执行搜索或引用网络扩展")
    
    def check_zotero_status(self):
        """检查Zotero状态"""
        try:
            # 检查Zotero是否运行
            import psutil
            zotero_running = False
            for proc in psutil.process_iter(['pid', 'name']):
                if 'zotero' in proc.info['name'].lower():
                    zotero_running = True
                    break
            
            if zotero_running:
                self.zotero_status_label.config(text="✅ Zotero正在运行", foreground="green")
                self.update_status("Zotero状态检查：正在运行")
            else:
                self.zotero_status_label.config(text="❌ Zotero未运行", foreground="red")
                self.update_status("Zotero状态检查：未运行，请启动Zotero")
                
        except ImportError:
            self.zotero_status_label.config(text="⚠️ 无法检查状态", foreground="orange")
            messagebox.showwarning("警告", "需要安装psutil库来检查Zotero状态")
        except Exception as e:
            self.zotero_status_label.config(text="❌ 检查失败", foreground="red")
            messagebox.showerror("错误", f"检查Zotero状态出错: {str(e)}")
    
    def open_zotero(self):
        """打开Zotero应用"""
        try:
            if platform.system() == "Windows":
                # 尝试常见的Zotero安装路径
                zotero_paths = [
                    r"C:\Program Files\Zotero\zotero.exe",
                    r"C:\Program Files (x86)\Zotero\zotero.exe",
                    r"C:\Users\{}\AppData\Local\Zotero\zotero.exe".format(os.getenv('USERNAME'))
                ]
                
                for path in zotero_paths:
                    if os.path.exists(path):
                        subprocess.Popen([path])
                        self.update_status("正在启动Zotero...")
                        return
                
                messagebox.showwarning("警告", "未找到Zotero安装路径，请手动启动Zotero")
            else:
                # macOS和Linux
                subprocess.Popen(["zotero"])
                
        except Exception as e:
            messagebox.showerror("错误", f"启动Zotero出错: {str(e)}")
    
    def start_pdf_download(self):
        """开始PDF下载 - 严格使用原有的ZoteroBatchSaver"""
        try:
            urls_file = self.pdf_input_var.get().strip()
            if not urls_file or not os.path.exists(urls_file):
                messagebox.showwarning("警告", "请选择有效的URLs文件")
                return
            
            # 读取URLs
            urls = []
            with open(urls_file, 'r', encoding='utf-8') as f:
                for line in f:
                    url = line.strip()
                    if url and url.startswith('http'):
                        urls.append(url)
            
            if not urls:
                messagebox.showwarning("警告", "URLs文件中没有有效的URL")
                return
            
            # 检查Zotero状态
            self.check_zotero_status()
            if "未运行" in self.zotero_status_label.cget("text"):
                if not messagebox.askyesno("确认", "Zotero未运行，是否继续？建议先启动Zotero"):
                    return
            
            self.update_status(f"开始下载 {len(urls)} 个PDF到Zotero...")
            
            # 设置下载状态标志
            self.pdf_download_running = True
            
            # 禁用开始按钮，启用暂停按钮
            self.start_pdf_btn.config(state='disabled')
            self.pause_pdf_btn.config(state='normal')
            
            # 在单独线程中执行PDF下载
            pdf_thread = threading.Thread(target=self._execute_pdf_download, args=(urls,), daemon=True)
            pdf_thread.start()
            
        except Exception as e:
            messagebox.showerror("错误", f"启动PDF下载时出错: {str(e)}")
    
    def _execute_pdf_download(self, urls):
        """执行PDF下载 - 使用pdfdownloaderzotero2的先易后难策略"""
        try:
            # 创建ZoteroBatchSaver实例 (使用pdfdownloaderzotero2)
            saver = ZoteroBatchSaver()  # 使用固定的最优批次大小9
            
            self.root.after(0, lambda: self.update_status("开始智能PDF下载 (先易后难策略)..."))
            
            # 使用新的先易后难策略处理所有URLs
            all_results = []
            total_batches = (len(urls) + saver.OPTIMAL_BATCH_SIZE - 1) // saver.OPTIMAL_BATCH_SIZE
            
            for batch_idx in range(0, len(urls), saver.OPTIMAL_BATCH_SIZE):
                if not hasattr(self, 'pdf_download_running') or not self.pdf_download_running:
                    break
                
                batch_urls = urls[batch_idx:batch_idx + saver.OPTIMAL_BATCH_SIZE]
                current_batch = batch_idx // saver.OPTIMAL_BATCH_SIZE + 1
                
                self.root.after(0, lambda b=current_batch, t=total_batches:
                               self.update_status(f"处理批次 {b}/{t} (先易后难策略)，包含 {len(batch_urls)} 个URL..."))
                
                try:
                    # 使用新的先易后难策略方法
                    batch_results = saver.process_batch_live_save_with_strategy(batch_urls)
                    all_results.extend(batch_results)
                    
                    # 更新进度
                    processed = min(batch_idx + saver.OPTIMAL_BATCH_SIZE, len(urls))
                    self.root.after(0, lambda p=processed: self._update_pdf_progress(p, len(urls)))
                    
                    # 显示批次摘要
                    success_in_batch = sum(1 for r in batch_results if r.success)
                    self.root.after(0, lambda s=success_in_batch, total=len(batch_results):
                                   self.update_status(f"批次 {current_batch} 完成: 成功 {s}/{total}"))
                    
                    # 批次间等待 (给浏览器恢复时间)
                    if batch_idx + saver.OPTIMAL_BATCH_SIZE < len(urls):
                        self.root.after(0, lambda: self.update_status("批次完成，等待浏览器恢复..."))
                        time.sleep(3)  # 固定等待时间
                        
                except Exception as e:
                    error_msg = str(e)
                    self.root.after(0, lambda: self.update_status(f"批次处理失败: {error_msg}"))
                    # 继续处理下一批次
                    continue
            
            # 统计最终结果
            success_count = sum(1 for r in all_results if r.success)
            failed_count = len(all_results) - success_count
            
            # 按阶段统计
            phase_one_count = sum(1 for r in all_results if r.success and r.save_phase == "第一阶段")
            phase_two_count = sum(1 for r in all_results if r.success and r.save_phase == "第二阶段")
            force_retry_count = sum(1 for r in all_results if r.success and r.save_phase == "强制重试")
            
            # 更新最终统计
            self.root.after(0, lambda s=success_count, f=failed_count:
                           self.pdf_stats_label.config(text=f"成功: {s} 失败: {f}"))
            
            # 完成后的处理
            result_text = f"智能PDF下载完成！(先易后难策略)\n"
            result_text += f"总计处理: {len(urls)} 个URL\n"
            result_text += f"成功下载: {success_count} 个\n"
            result_text += f"下载失败: {failed_count} 个\n"
            if success_count > 0:
                result_text += f"成功率: {success_count/(success_count+failed_count)*100:.1f}%\n\n"
                
                # 显示策略效果
                result_text += f"策略效果分析:\n"
                result_text += f"- 第一阶段(明确类型): {phase_one_count} 个\n"
                result_text += f"- 第二阶段(通用类型): {phase_two_count} 个\n"
                result_text += f"- 强制重试挽救: {force_retry_count} 个\n\n"
            
            # 显示成功的文献
            success_results = [r for r in all_results if r.success]
            if success_results:
                result_text += f"成功保存的文献 (前5个):\n"
                for i, r in enumerate(success_results[:5], 1):
                    phase_info = f"[{r.save_phase}]" if r.save_phase else ""
                    result_text += f"  {i}. {r.publisher} {phase_info} (加载:{r.load_time:.1f}s)\n"
                if len(success_results) > 5:
                    result_text += f"  ... 还有 {len(success_results) - 5} 篇成功保存\n"
            
            result_text += "\n所有成功下载的PDF已保存到Zotero库中"
            
            self.root.after(0, lambda: self._update_pdf_results(result_text))
            self.root.after(0, lambda: self.update_status(f"智能PDF下载完成，成功: {success_count}, 失败: {failed_count}"))
            
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: self.update_status(f"PDF下载出错: {error_msg}"))
            self.root.after(0, lambda: messagebox.showerror("错误", f"PDF下载出错: {error_msg}"))
        finally:
            # 重置按钮状态
            self.root.after(0, self._reset_pdf_buttons)
    
    def _update_pdf_progress(self, current, total):
        """更新PDF下载进度"""
        progress = (current / total) * 100
        self.pdf_progress_bar['value'] = progress
        self.pdf_progress_label.config(text=f"进度: {current}/{total} ({progress:.1f}%)")
    
    def _update_pdf_results(self, text):
        """更新PDF下载结果显示"""
        self.pdf_results_text.config(state='normal')
        self.pdf_results_text.delete("1.0", tk.END)
        self.pdf_results_text.insert("1.0", text)
        self.pdf_results_text.config(state='disabled')
    
    def _reset_pdf_buttons(self):
        """重置PDF下载按钮状态"""
        self.start_pdf_btn.config(state='normal')
        self.pause_pdf_btn.config(state='disabled')
        self.pdf_download_running = False
    
    def pause_pdf_download(self):
        """暂停PDF下载"""
        self.pdf_download_running = False
        self.update_status("PDF下载已暂停")
        self._reset_pdf_buttons()
    
    def view_zotero_library(self):
        """查看Zotero库"""
        try:
            # 尝试打开Zotero库页面
            webbrowser.open("zotero://select/library")
        except Exception:
            messagebox.showinfo("提示", "请手动打开Zotero查看下载的PDF文件")


def main():
    """主函数"""
    try:
        # 创建并运行GUI
        app = ModularResearchGUI()
        app.root.mainloop()
        
    except Exception as e:
        print(f"程序启动出错: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()