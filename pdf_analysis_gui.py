#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
独立的PDF文件夹分析GUI - 重构版
读取PDF文件夹中所有子文件的PDF，转换为TXT，然后逐篇调用LLM分析生成JSON文件
与主GUI的内容分析栏输出格式严格一致

作者: Yuming Su
日期: 2025-08-29
"""

import tkinter as tk
from tkinter import messagebox, ttk, scrolledtext, filedialog, simpledialog
import os
import json
import csv
import datetime
import threading
import time
import logging

# 导入需要的模块
from pdf_processor import PDFProcessor
from enhanced_research_system import call_deepseek_api

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PDFAnalysisGUI:
    """独立的PDF文件夹分析GUI - 重构版"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("PDF文件夹分析工具 v2.0")
        self.root.geometry('900x700')
        self.root.configure(bg='#f0f0f0')
        
        # 初始化变量
        self.pdf_folder_path = ""
        self.output_dir = ""
        self.api_key = ""
        self.research_question = ""
        self.processing = False
        
        # 设置默认的分析prompt（与主GUI严格一致）
        self.default_analysis_prompt = """分析以下学术文献内容，提取关键信息并以JSON格式返回。
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
        
        # 设置GUI
        self.setup_gui()
    
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
        main_frame = ttk.Frame(scrollable_frame, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 绑定鼠标滚轮事件
        self._bind_mousewheel(main_canvas)
        
        # 标题
        title_label = tk.Label(main_frame, text="PDF文件夹分析工具 v2.0",
                              font=('Arial', 18, 'bold'), bg='#f0f0f0', fg='#2c3e50')
        title_label.pack(pady=(0, 10))
        
        subtitle_label = tk.Label(main_frame, text="逐篇分析PDF文件，输出JSON汇总和CSV格式",
                                 font=('Arial', 12), bg='#f0f0f0', fg='#7f8c8d')
        subtitle_label.pack(pady=(0, 20))
        
        # API配置区域
        api_frame = ttk.LabelFrame(main_frame, text="API配置", padding=10)
        api_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(api_frame, text="DeepSeek API密钥:").pack(anchor='w', pady=(0, 5))
        self.api_key_entry = ttk.Entry(api_frame, width=70, show="*")
        # 从环境变量预填充API密钥，公开仓库中不保留真实密钥
        self.api_key_entry.insert(0, os.getenv("DEEPSEEK_API_KEY", ""))
        self.api_key_entry.pack(fill=tk.X, pady=(0, 10))
        
        api_buttons_frame = ttk.Frame(api_frame)
        api_buttons_frame.pack(fill=tk.X)
        ttk.Button(api_buttons_frame, text="测试连接", command=self.test_api_connection).pack(side=tk.LEFT, padx=5)
        
        # 文件夹选择区域
        folder_frame = ttk.LabelFrame(main_frame, text="PDF文件夹选择", padding=10)
        folder_frame.pack(fill=tk.X, pady=(0, 15))
        
        folder_select_frame = ttk.Frame(folder_frame)
        folder_select_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(folder_select_frame, text="PDF文件夹:").pack(side=tk.LEFT, padx=(0, 10))
        self.folder_var = tk.StringVar()
        ttk.Entry(folder_select_frame, textvariable=self.folder_var, width=60).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(folder_select_frame, text="选择文件夹", command=self.select_pdf_folder).pack(side=tk.LEFT, padx=5)
        
        # 输出目录选择
        output_select_frame = ttk.Frame(folder_frame)
        output_select_frame.pack(fill=tk.X)
        
        ttk.Label(output_select_frame, text="输出目录:").pack(side=tk.LEFT, padx=(0, 10))
        self.output_var = tk.StringVar()
        ttk.Entry(output_select_frame, textvariable=self.output_var, width=60).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(output_select_frame, text="选择目录", command=self.select_output_dir).pack(side=tk.LEFT, padx=5)
        
        # 研究问题输入区域
        question_frame = ttk.LabelFrame(main_frame, text="研究问题", padding=10)
        question_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(question_frame, text="请输入研究问题（用于LLM分析）:").pack(anchor='w', pady=(0, 5))
        self.question_text = tk.Text(question_frame, height=3, width=80, font=('Arial', 10))
        self.question_text.pack(fill=tk.X, pady=(0, 10))
        self.question_text.insert("1.0", "请分析这些PDF文档的内容，提取关键信息")
        
        # 单一分析Prompt区域（与主GUI严格一致）
        prompt_frame = ttk.LabelFrame(main_frame, text="分析Prompt模板（与主GUI严格一致）", padding=10)
        prompt_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(prompt_frame, text="分析Prompt模板（{RESEARCH_QUESTION}和{PAPER_CONTENT}会被自动替换）:").pack(anchor='w', pady=(0, 5))
        self.prompt_text = tk.Text(prompt_frame, height=8, width=80, font=('Arial', 9))
        
        # 设置默认的分析prompt
        self.prompt_text.insert("1.0", self.default_analysis_prompt)
        self.prompt_text.pack(fill=tk.X, pady=(0, 10))
        
        # Prompt操作按钮
        prompt_buttons_frame = ttk.Frame(prompt_frame)
        prompt_buttons_frame.pack(fill=tk.X)
        ttk.Button(prompt_buttons_frame, text="重置为默认", command=self.reset_default_prompt).pack(side=tk.LEFT, padx=5)
        ttk.Button(prompt_buttons_frame, text="保存Prompt模板", command=self.save_prompt_template).pack(side=tk.LEFT, padx=5)
        ttk.Button(prompt_buttons_frame, text="加载Prompt模板", command=self.load_prompt_template).pack(side=tk.LEFT, padx=5)
        
        # 控制按钮区域
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.start_btn = ttk.Button(control_frame, text="开始逐篇分析", command=self.start_processing)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(control_frame, text="停止处理", command=self.stop_processing, state='disabled')
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="打开输出目录", command=self.open_output_dir).pack(side=tk.LEFT, padx=5)
        
        # 进度显示区域
        progress_frame = ttk.LabelFrame(main_frame, text="处理进度", padding=10)
        progress_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate', length=400)
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))
        
        self.progress_label = ttk.Label(progress_frame, text="就绪")
        self.progress_label.pack(anchor='w')
        
        # 日志显示区域
        log_frame = ttk.LabelFrame(main_frame, text="处理日志", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=80, font=('Consolas', 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state='disabled')
    
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
    
    def log_message(self, message):
        """添加日志消息"""
        try:
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            formatted_message = f"[{timestamp}] {message}"
            
            self.log_text.config(state='normal')
            self.log_text.insert(tk.END, formatted_message + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state='disabled')
            
            self.root.update_idletasks()
            
        except Exception as e:
            print(f"日志记录出错: {str(e)}")
    
    def test_api_connection(self):
        """测试API连接"""
        try:
            api_key = self.api_key_entry.get().strip()
            if not api_key:
                messagebox.showwarning("警告", "请输入API密钥")
                return
            
            self.log_message("测试API连接...")
            
            # 简单测试
            test_result = call_deepseek_api("测试连接", "medium", api_key)
            
            if test_result:
                messagebox.showinfo("成功", "API连接测试成功")
                self.log_message("API连接测试成功")
            else:
                messagebox.showerror("错误", "API连接测试失败")
                self.log_message("API连接测试失败")
                
        except Exception as e:
            messagebox.showerror("错误", f"API连接测试出错: {str(e)}")
            self.log_message(f"API连接测试出错: {str(e)}")
    
    def select_pdf_folder(self):
        """选择PDF文件夹"""
        try:
            folder_path = filedialog.askdirectory(
                title="选择包含PDF文件的文件夹",
                mustexist=True
            )
            
            if folder_path:
                self.folder_var.set(folder_path)
                self.pdf_folder_path = folder_path
                self.log_message(f"已选择PDF文件夹: {os.path.basename(folder_path)}")
                
                # 快速预览PDF数量
                self._preview_pdf_count(folder_path)
            
        except Exception as e:
            messagebox.showerror("错误", f"选择文件夹时出错: {str(e)}")
    
    def _preview_pdf_count(self, folder_path):
        """预览PDF文件数量"""
        try:
            processor = PDFProcessor()
            pdf_files = processor.find_all_pdfs(folder_path)
            self.log_message(f"预览：发现 {len(pdf_files)} 个PDF文件")
        except Exception as e:
            self.log_message(f"预览PDF文件时出错: {str(e)}")
    
    def select_output_dir(self):
        """选择输出目录"""
        try:
            output_dir = filedialog.askdirectory(
                title="选择输出目录",
                mustexist=False
            )
            
            if output_dir:
                self.output_var.set(output_dir)
                self.output_dir = output_dir
                self.log_message(f"已选择输出目录: {os.path.basename(output_dir)}")
            
        except Exception as e:
            messagebox.showerror("错误", f"选择输出目录时出错: {str(e)}")
    
    def start_processing(self):
        """开始处理"""
        try:
            # 验证输入
            if not self.pdf_folder_path or not os.path.exists(self.pdf_folder_path):
                messagebox.showwarning("警告", "请选择有效的PDF文件夹")
                return
            
            if not self.output_dir:
                messagebox.showwarning("警告", "请选择输出目录")
                return
            
            api_key = self.api_key_entry.get().strip()
            if not api_key:
                messagebox.showwarning("警告", "请输入API密钥")
                return
            
            research_question = self.question_text.get("1.0", "end-1c").strip()
            if not research_question:
                research_question = "PDF文档内容分析"
            
            # 确认开始处理
            if not messagebox.askyesno("确认处理", 
                f"将逐篇分析文件夹中的所有PDF文件：\n{self.pdf_folder_path}\n\n这可能需要较长时间，是否继续？"):
                return
            
            # 设置处理状态
            self.processing = True
            self.start_btn.config(state='disabled')
            self.stop_btn.config(state='normal')
            
            self.api_key = api_key
            self.research_question = research_question
            
            self.log_message("开始PDF逐篇分析流程...")
            
            # 在单独线程中执行处理
            process_thread = threading.Thread(target=self._execute_processing, daemon=True)
            process_thread.start()
            
        except Exception as e:
            messagebox.showerror("错误", f"启动处理时出错: {str(e)}")
            self._reset_buttons()
    
    def _execute_processing(self):
        """执行处理的具体逻辑"""
        try:
            # 步骤1: PDF转换为TXT
            self.root.after(0, lambda: self.log_message("=== 步骤1: PDF转换为TXT ==="))
            self.root.after(0, lambda: self.progress_label.config(text="正在转换PDF文件..."))
            
            processor = PDFProcessor()
            txt_output_dir = os.path.join(self.output_dir, "converted_txt")
            
            results = processor.process_pdf_folder(self.pdf_folder_path, txt_output_dir)
            
            if results.get('error'):
                self.root.after(0, lambda: messagebox.showerror("错误", f"PDF转换出错: {results['error']}"))
                return
            
            if results['successful_conversions'] == 0:
                self.root.after(0, lambda: messagebox.showwarning("警告", "没有成功转换任何PDF文件"))
                return
            
            self.root.after(0, lambda: self.log_message(f"PDF转换完成: 成功 {results['successful_conversions']}, 失败 {results['failed_conversions']}"))
            self.root.after(0, lambda: self.progress_bar.config(value=30))
            
            # 步骤2: 逐篇PDF分析（一篇一篇地分析）
            if not self.processing:
                return
            
            self.root.after(0, lambda: self.log_message("=== 步骤2: 逐篇PDF分析 ==="))
            self.root.after(0, lambda: self.progress_label.config(text="正在逐篇分析PDF文件..."))
            
            all_analysis_results = []
            total_txt_files = len(results['txt_files'])
            
            for i, txt_file in enumerate(results['txt_files']):
                if not self.processing:
                    break
                
                # 更新进度
                progress = 30 + (i / total_txt_files) * 65  # 从30%到95%
                self.root.after(0, lambda p=progress: self.progress_bar.config(value=p))
                
                pdf_name = os.path.splitext(os.path.basename(txt_file))[0]
                self.root.after(0, lambda name=pdf_name, idx=i+1, total=total_txt_files:
                               self.log_message(f"分析第 {idx}/{total} 个PDF: {name}"))
                
                # 分析单个PDF
                single_analysis = self._analyze_single_pdf(txt_file, pdf_name)
                if single_analysis:
                    all_analysis_results.append(single_analysis)
                    self.root.after(0, lambda name=pdf_name:
                                   self.log_message(f"✓ {name} 分析完成"))
                else:
                    self.root.after(0, lambda name=pdf_name:
                                   self.log_message(f"✗ {name} 分析失败"))
                
                # 小延迟避免API频率限制
                time.sleep(1)
            
            # 步骤3: 保存分析结果（只保存汇总）
            if not self.processing:
                return
            
            self.root.after(0, lambda: self.log_message("=== 步骤3: 保存分析结果 ==="))
            
            if all_analysis_results:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # 创建汇总报告（包含完整的分析结果）
                summary_report = self._create_summary_report(all_analysis_results)
                summary_output_path = os.path.join(self.output_dir, f"analysis_summary_{timestamp}.json")
                with open(summary_output_path, 'w', encoding='utf-8') as f:
                    json.dump(summary_report, f, ensure_ascii=False, indent=2)
                
                # 保存CSV格式
                csv_output_path = os.path.join(self.output_dir, f"analysis_results_{timestamp}.csv")
                self._save_results_to_csv(all_analysis_results, csv_output_path)
                
                self.root.after(0, lambda: self.log_message(f"汇总报告已保存: {summary_output_path}"))
                self.root.after(0, lambda: self.log_message(f"CSV结果已保存: {csv_output_path}"))
                self.root.after(0, lambda: self.progress_bar.config(value=100))
                self.root.after(0, lambda: self.progress_label.config(text="处理完成"))
                
                # 显示完成消息
                successful_analyses = len(all_analysis_results)
                high_quality_count = len([r for r in all_analysis_results 
                                        if r.get('success', False) and 
                                        float(r.get('relevance_score', 0)) >= 8])
                
                summary = f"PDF逐篇分析完成！\n\n"
                summary += f"处理的PDF文件: {results['total_pdfs']} 个\n"
                summary += f"成功转换: {results['successful_conversions']} 个\n"
                summary += f"成功分析: {successful_analyses} 个\n"
                summary += f"高质量文章(≥8分): {high_quality_count} 个\n"
                summary += f"输出目录: {self.output_dir}\n\n"
                summary += f"生成文件:\n"
                summary += f"- TXT文件目录: {txt_output_dir}\n"
                summary += f"- 汇总报告: {summary_output_path}\n"
                summary += f"- CSV结果: {csv_output_path}\n\n"
                summary += f"注意：汇总报告包含完整分析结果，CSV格式便于数据处理"
                
                self.root.after(0, lambda: messagebox.showinfo("处理完成", summary))
                self.root.after(0, lambda: self.log_message("=== 所有处理完成 ==="))
            else:
                self.root.after(0, lambda: messagebox.showerror("错误", "没有成功分析任何PDF文件"))
            
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: self.log_message(f"处理出错: {error_msg}"))
            self.root.after(0, lambda: messagebox.showerror("错误", f"处理出错: {error_msg}"))
        finally:
            self.root.after(0, self._reset_buttons)
    
    def _save_results_to_csv(self, all_analysis_results, csv_path):
        """将分析结果保存为CSV格式"""
        try:
            with open(csv_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                fieldnames = [
                    'source_pdf',
                    'title', 
                    'doi',
                    'authors',
                    'publication_year',
                    'journal',
                    'research_focus',
                    'key_methods',
                    'major_contributions',
                    'challenges',
                    'relevance_score',
                    'success',
                    'timestamp'
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for result in all_analysis_results:
                    # 处理作者列表为字符串
                    authors_str = ""
                    if isinstance(result.get('authors', []), list):
                        authors_str = "; ".join(result.get('authors', []))
                    else:
                        authors_str = str(result.get('authors', ''))
                    
                    csv_row = {
                        'source_pdf': result.get('source_pdf', ''),
                        'title': result.get('title', ''),
                        'doi': result.get('doi', ''),
                        'authors': authors_str,
                        'publication_year': result.get('publication_year', ''),
                        'journal': result.get('journal', ''),
                        'research_focus': result.get('research_focus', ''),
                        'key_methods': result.get('key_methods', ''),
                        'major_contributions': result.get('major_contributions', ''),
                        'challenges': result.get('challenges', ''),
                        'relevance_score': result.get('relevance_score', 0),
                        'success': result.get('success', False),
                        'timestamp': result.get('timestamp', '')
                    }
                    
                    writer.writerow(csv_row)
                    
            self.root.after(0, lambda: self.log_message(f"CSV文件已保存: {csv_path}"))
            
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: self.log_message(f"保存CSV文件出错: {error_msg}"))
    
    # [保持所有其他方法不变...]
    def _analyze_single_pdf(self, txt_file_path, pdf_name):
        """分析单个PDF文件 - 修复版本"""
        import json
        import re
        
        try:
            # 读取单个TXT文件
            with open(txt_file_path, 'r', encoding='utf-8') as f:
                txt_content = f.read()
            
            if not txt_content.strip():
                self.root.after(0, lambda name=pdf_name: 
                            self.log_message(f"TXT文件内容为空: {name}"))
                return None
            
            # 获取用户自定义的prompt模板
            prompt_template = self.prompt_text.get("1.0", "end-1c").strip()
            
            if not prompt_template:
                prompt_template = self.default_analysis_prompt
            
            # 清理TXT内容，跳过元数据部分
            content_lines = txt_content.split('\n')
            actual_content = []
            metadata_ended = False
            
            for line in content_lines:
                if not metadata_ended and line.startswith('#'):
                    continue
                metadata_ended = True
                actual_content.append(line)
            
            cleaned_content = '\n'.join(actual_content).strip()
            
            # 限制内容长度，确保不超过API限制
            if len(cleaned_content) > 10000:
                cleaned_content = cleaned_content[:10000] + "\n\n[内容已截断...]"
            
            # 构造专门用于文献分析的prompt
            final_prompt = f"""请分析以下学术文献并以严格的JSON格式返回结果。

研究问题: {self.research_question}

请提取以下信息并以JSON格式返回:
{{
    "doi": "文章的DOI号码",
    "title": "文章标题",
    "authors": ["作者1", "作者2"],
    "publication_year": "出版年份",
    "journal": "期刊名称",
    "research_focus": "研究的主要材料、反应或主题",
    "key_methods": "关键概念和使用的技术方法",
    "major_contributions": "主要发现和贡献",
    "challenges": "文中提到的未解决问题或研究局限性",
    "relevance_score": 8
}}

文章内容:
{cleaned_content}

请只返回JSON对象，不要包含任何解释或其他文本。relevance_score请根据与研究问题的相关性评分1-10。"""
            
            # 调用LLM API
            api_result = self._call_analysis_api(final_prompt)
            
            if api_result:
                # 解析API响应
                parsed_result = self._parse_analysis_response(api_result)
                
                if parsed_result and isinstance(parsed_result, dict):
                    # 构造与主GUI严格一致的分析结果格式
                    single_analysis = {
                        "url": f"file://{txt_file_path}",
                        "title": parsed_result.get("title", pdf_name),
                        "doi": parsed_result.get("doi", ""),
                        "authors": parsed_result.get("authors", []),
                        "publication_year": str(parsed_result.get("publication_year", "")),
                        "journal": parsed_result.get("journal", ""),
                        "research_focus": parsed_result.get("research_focus", ""),
                        "key_methods": parsed_result.get("key_methods", ""),
                        "major_contributions": parsed_result.get("major_contributions", ""),
                        "challenges": parsed_result.get("challenges", ""),
                        "relevance_score": float(parsed_result.get("relevance_score", 0)),
                        "success": True,
                        "timestamp": datetime.datetime.now().isoformat(),
                        "source_pdf": pdf_name,
                        "analysis_prompt": final_prompt,
                        "raw_llm_response": str(api_result)
                    }
                    
                    self.root.after(0, lambda name=pdf_name, score=single_analysis["relevance_score"]: 
                                self.log_message(f"✓ 分析完成: {name} (评分: {score})"))
                    
                    return single_analysis
                else:
                    self.root.after(0, lambda name=pdf_name: 
                                self.log_message(f"✗ 无法解析LLM响应: {name}"))
                    return None
            else:
                self.root.after(0, lambda name=pdf_name: 
                            self.log_message(f"✗ LLM API调用失败: {name}"))
                return None
                
        except Exception as error:
            error_msg = str(error)
            pdf_name_safe = pdf_name
            self.root.after(0, lambda msg=error_msg, name=pdf_name_safe: 
                        self.log_message(f"分析单个PDF出错 {name}: {msg}"))
            return None

    def _call_analysis_api(self, prompt):
        """调用分析API - 确保使用正确的分析模式"""
        try:
            import requests
            
            api_url = "https://api.deepseek.com/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个专业的学术文献分析助手。请严格按照要求分析文献并返回JSON格式的结果。"
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 2000
            }
            
            response = requests.post(api_url, headers=headers, json=data, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    content = result['choices'][0]['message']['content']
                    return content
            
            return None
            
        except Exception as e:
            self.root.after(0, lambda: self.log_message(f"API调用出错: {str(e)}"))
            return None

    def _parse_analysis_response(self, api_response):
        """解析分析响应，提取JSON内容"""
        import json
        import re
        
        try:
            if not api_response:
                return None
            
            # 如果响应是列表格式（搜索查询），说明调用了错误的API
            if isinstance(api_response, list) or (isinstance(api_response, str) and api_response.strip().startswith('[')):
                self.root.after(0, lambda: self.log_message("警告: 收到搜索查询响应，而非分析结果"))
                return None
            
            response_str = str(api_response).strip()
            
            # 尝试直接解析JSON
            try:
                return json.loads(response_str)
            except json.JSONDecodeError:
                pass
            
            # 提取JSON部分
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_str, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
            
            # 如果都失败了，尝试从文本中提取信息
            return self._extract_info_from_text(response_str)
            
        except Exception as e:
            self.root.after(0, lambda: self.log_message(f"解析响应出错: {str(e)}"))
            return None

    def _extract_info_from_text(self, text):
        """从文本中提取结构化信息作为备用方案"""
        import re
        
        try:
            result = {
                "title": "",
                "doi": "",
                "authors": [],
                "publication_year": "",
                "journal": "",
                "research_focus": "",
                "key_methods": "",
                "major_contributions": "",
                "challenges": "",
                "relevance_score": 5  # 默认中等相关性
            }
            
            # 简单的信息提取逻辑
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if 'title' in line.lower() and ':' in line:
                    result["title"] = line.split(':', 1)[1].strip().strip('"')
                elif 'doi' in line.lower() and ':' in line:
                    result["doi"] = line.split(':', 1)[1].strip().strip('"')
                elif 'relevance' in line.lower() and any(char.isdigit() for char in line):
                    numbers = re.findall(r'\d+', line)
                    if numbers:
                        score = int(numbers[0])
                        if 1 <= score <= 10:
                            result["relevance_score"] = score
            
            return result
            
        except Exception:
            return None
    
    def _create_summary_report(self, all_analysis_results):
        """创建汇总报告"""
        try:
            successful_analyses = [r for r in all_analysis_results if r.get('success', False)]
            high_quality_articles = [r for r in successful_analyses 
                                   if float(r.get('relevance_score', 0)) >= 8]
            
            summary_report = {
                "summary_info": {
                    "total_pdfs_analyzed": len(all_analysis_results),
                    "successful_analyses": len(successful_analyses),
                    "high_quality_articles": len(high_quality_articles),
                    "research_question": self.research_question,
                    "analysis_timestamp": datetime.datetime.now().isoformat(),
                    "processing_info": {
                        "pdf_folder": self.pdf_folder_path,
                        "output_dir": self.output_dir,
                        "api_model": "deepseek-chat"
                    }
                },
                "high_quality_articles": high_quality_articles,
                "all_analysis_results": all_analysis_results,  # 完整结果保存在汇总中
                "statistics": {
                    "avg_relevance_score": sum(float(r.get('relevance_score', 0)) for r in successful_analyses) / len(successful_analyses) if successful_analyses else 0,
                    "score_distribution": {
                        "9-10": len([r for r in successful_analyses if float(r.get('relevance_score', 0)) >= 9]),
                        "8-9": len([r for r in successful_analyses if 8 <= float(r.get('relevance_score', 0)) < 9]),
                        "7-8": len([r for r in successful_analyses if 7 <= float(r.get('relevance_score', 0)) < 8]),
                        "6-7": len([r for r in successful_analyses if 6 <= float(r.get('relevance_score', 0)) < 7]),
                        "<6": len([r for r in successful_analyses if float(r.get('relevance_score', 0)) < 6])
                    }
                }
            }
            
            return summary_report
            
        except Exception as e:
            self.root.after(0, lambda: self.log_message(f"创建汇总报告出错: {str(e)}"))
            return {
                "summary_info": {
                    "error": f"汇总报告创建失败: {str(e)}"
                },
                "all_analysis_results": all_analysis_results
            }
    
    def stop_processing(self):
        """停止处理"""
        self.processing = False
        self.log_message("用户停止处理")
        self._reset_buttons()
    
    def _reset_buttons(self):
        """重置按钮状态"""
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.processing = False
    
    def reset_default_prompt(self):
        """重置为默认prompt"""
        self.prompt_text.delete("1.0", tk.END)
        self.prompt_text.insert("1.0", self.default_analysis_prompt)
        self.log_message("已重置为默认Prompt模板")
    
    def save_prompt_template(self):
        """保存Prompt模板到文件"""
        try:
            file_path = filedialog.asksaveasfilename(
                title="保存Prompt模板",
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            
            if file_path:
                prompt_content = self.prompt_text.get("1.0", "end-1c")
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(prompt_content)
                self.log_message(f"Prompt模板已保存到: {file_path}")
                messagebox.showinfo("成功", f"Prompt模板已保存到:\n{file_path}")
        except Exception as e:
            messagebox.showerror("错误", f"保存Prompt模板时出错: {str(e)}")
    
    def load_prompt_template(self):
        """从文件加载Prompt模板"""
        try:
            file_path = filedialog.askopenfilename(
                title="加载Prompt模板",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            
            if file_path:
                with open(file_path, 'r', encoding='utf-8') as f:
                    prompt_content = f.read()
                
                self.prompt_text.delete("1.0", tk.END)
                self.prompt_text.insert("1.0", prompt_content)
                self.log_message(f"已加载Prompt模板: {os.path.basename(file_path)}")
                messagebox.showinfo("成功", f"已加载Prompt模板:\n{os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("错误", f"加载Prompt模板时出错: {str(e)}")
    
    def open_output_dir(self):
        """打开输出目录"""
        try:
            if self.output_dir and os.path.exists(self.output_dir):
                import platform
                if platform.system() == "Windows":
                    os.startfile(self.output_dir)
                elif platform.system() == "Darwin":
                    import subprocess
                    subprocess.Popen(["open", self.output_dir])
                else:
                    import subprocess
                    subprocess.Popen(["xdg-open", self.output_dir])
            else:
                messagebox.showwarning("警告", "请先选择输出目录")
        except Exception as e:
            messagebox.showerror("错误", f"打开输出目录时出错: {str(e)}")
    
    def run(self):
        """运行GUI"""
        self.root.mainloop()


def main():
    """主函数"""
    try:
        app = PDFAnalysisGUI()
        app.run()
    except Exception as e:
        print(f"程序启动出错: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
