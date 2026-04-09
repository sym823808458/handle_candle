#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
网页内容提取器 - 基于handle_candle12.py的成熟方案
使用pywinauto从浏览器中提取网页内容，避免反爬虫限制

作者: Yuming Su
日期: 2025-06-10
"""

import os
import re
import time
import random
import logging
import webbrowser
import pyperclip

# 尝试导入pywinauto
try:
    from pywinauto.application import Application
    from pywinauto import Desktop
    from pywinauto.keyboard import send_keys
    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False
    print("pywinauto不可用。正在尝试安装...")
    import subprocess
    subprocess.call(['pip', 'install', 'pywinauto'])
    try:
        from pywinauto.application import Application
        from pywinauto import Desktop
        from pywinauto.keyboard import send_keys
        PYWINAUTO_AVAILABLE = True
    except ImportError:
        print("安装pywinauto失败。内容分析功能将不可用。")

logger = logging.getLogger(__name__)

def extract_webpage_content(url, status_callback=None):
    """
    使用pywinauto从浏览器中提取网页内容，增强版
    基于handle_candle12.py的成熟方案
    
    参数:
        url: 要提取内容的网页URL
        status_callback: 状态更新回调函数
    返回:
        提取的网页内容文本
    """
    if not PYWINAUTO_AVAILABLE:
        print("pywinauto不可用，无法获取网页内容")
        if status_callback:
            status_callback("无法获取网页内容：pywinauto不可用")
        return None
    
    if status_callback:
        status_callback(f"正在获取网页内容: {url}")
    
    # 保存剪贴板原始内容
    original_clipboard = pyperclip.paste()
    
    # 打开URL
    try:
        # 清空剪贴板
        pyperclip.copy("")
        
        webbrowser.open(url, new=2)
        if status_callback:
            status_callback("等待页面加载...")
        
        # 增加等待时间以确保页面完全加载
        time.sleep(12)  # 等待页面加载
    except Exception as e:
        print(f"打开URL出错: {e}")
        if status_callback:
            status_callback(f"打开URL失败: {e}")
        return None
    
    # 尝试连接到Edge浏览器窗口
    try:
        # 查找所有窗口
        windows = Desktop(backend="uia").windows()
        
        # 寻找Edge浏览器窗口
        edge_window = None
        for w in windows:
            if "Edge" in w.window_text() or "Microsoft" in w.window_text():
                edge_window = w
                print(f"找到Edge窗口: {w.window_text()}")
                break
        
        if not edge_window:
            print("未找到Edge窗口")
            try:
                # 尝试通过应用程序名称直接连接
                app = Application(backend="uia").connect(title_re=".*Edge.*", timeout=10)
                edge_window = app.top_window()
                print(f"通过应用程序名称找到Edge窗口: {edge_window.window_text()}")
            except Exception as e:
                print(f"通过应用程序名称连接Edge失败: {e}")
                if status_callback:
                    status_callback("未找到Edge浏览器窗口")
                return None
        
        # 提取窗口标题用于验证
        window_title = edge_window.window_text()
        print(f"当前窗口标题: {window_title}")
        
        # 方法1: 传统全选复制法
        def try_copy_method_1():
            # 执行全选和复制操作
            edge_window.set_focus()
            time.sleep(1)  # 等待窗口获得焦点
            
            # 清空剪贴板
            pyperclip.copy("")
            
            # 先点击页面，确保焦点在正文区域
            try:
                # 尝试找到正文区域并点击
                content_elements = edge_window.descendants(control_type="Document")
                if content_elements:
                    content_elements[0].click_input()
                    print("已点击内容区域")
                else:
                    # 点击窗口中心位置
                    rect = edge_window.rectangle()
                    center_x = (rect.left + rect.right) // 2
                    center_y = (rect.top + rect.bottom) // 2
                    import pywinauto.mouse
                    pywinauto.mouse.click(coords=(center_x, center_y))
                    print("已点击窗口中心")
            except Exception as click_error:
                print(f"点击操作出错: {click_error}")
            
            time.sleep(0.5)
            
            # 发送Ctrl+A (全选)
            edge_window.type_keys("^a")
            time.sleep(1)  # 增加等待时间
            
            # 发送Ctrl+C (复制)
            edge_window.type_keys("^c")
            time.sleep(1)  # 增加等待时间
            
            # 从剪贴板获取内容
            content = pyperclip.paste()
            
            print(f"方法1获取内容长度: {len(content)} 字符")
            return content
        
        # 方法2: 使用键盘模拟全选和复制
        def try_copy_method_2():
            edge_window.set_focus()
            time.sleep(1)
            
            # 清空剪贴板
            pyperclip.copy("")
            
            # 使用pywinauto的send_keys模块
            send_keys('^a')  # Ctrl+A
            time.sleep(1.5)
            send_keys('^c')  # Ctrl+C
            time.sleep(1.5)
            
            content = pyperclip.paste()
            print(f"方法2获取内容长度: {len(content)} 字符")
            return content
        
        # 方法3: 使用菜单栏的编辑选项
        def try_copy_method_3():
            edge_window.set_focus()
            time.sleep(1)
            
            # 清空剪贴板
            pyperclip.copy("")
            
            # 尝试使用键盘快捷键打开菜单
            send_keys('{VK_MENU}')  # Alt键
            time.sleep(0.5)
            send_keys('e')  # 编辑菜单
            time.sleep(0.5)
            send_keys('a')  # 全选
            time.sleep(1)
            send_keys('^c')  # Ctrl+C
            time.sleep(1)
            
            content = pyperclip.paste()
            print(f"方法3获取内容长度: {len(content)} 字符")
            return content
        
        # 尝试所有方法
        content = try_copy_method_2()
        
        # 如果内容太短，尝试第一种方法
        if len(content) < 1000:
            print("方法2内容太短，尝试方法1")
            content2 = try_copy_method_1()
            
            # 选择更长的内容
            if len(content2) > len(content):
                content = content2
                print("使用方法1的内容")
        
        # 如果内容仍然太短，尝试第三种方法
        if len(content) < 1000:
            print("方法1内容仍然太短，尝试方法3")
            content3 = try_copy_method_3()
            
            # 选择更长的内容
            if len(content3) > len(content):
                content = content3
                print("使用方法3的内容")
        
        # 验证内容是否包含网页标题中的关键词
        # 从标题中提取关键词
        title_keywords = []
        for word in window_title.split():
            if len(word) > 3 and word.lower() not in ["edge", "microsoft", "个人", "和", "另外", "页面"]:
                title_keywords.append(word.lower())
        
        # 检查内容中是否包含标题关键词
        content_valid = False
        if title_keywords:
            content_lower = content.lower()
            for keyword in title_keywords:
                if keyword in content_lower:
                    content_valid = True
                    print(f"内容包含标题关键词: {keyword}")
                    break
        
        # 检查内容的有效性
        if not content_valid and len(content) > 1000:
            print("内容长度足够，但未找到标题关键词。仍然认为有效。")
            content_valid = True
        
        if content_valid and len(content) > 500:
            # 清理HTML标签
            clean_content = re.sub(r'<[^>]+>', ' ', content)
            # 清理多余空白
            clean_content = re.sub(r'\s+', ' ', clean_content).strip()
            
            if status_callback:
                status_callback(f"成功获取内容，长度: {len(clean_content)} 字符")
            
            # 自动关闭浏览器窗口
            try:
                close_browser_window()
                if status_callback:
                    status_callback("已自动关闭浏览器窗口")
            except Exception as close_error:
                print(f"关闭浏览器窗口时出错: {close_error}")
            
            return clean_content
        else:
            print(f"获取的内容无效，长度: {len(content)}, 有效性: {content_valid}")
            if status_callback:
                status_callback(f"获取的网页内容无效，长度: {len(content)}")
            
            # 即使内容无效也尝试关闭浏览器窗口
            try:
                close_browser_window()
                if status_callback:
                    status_callback("已自动关闭浏览器窗口")
            except Exception as close_error:
                print(f"关闭浏览器窗口时出错: {close_error}")
            
            return None
        
    except Exception as e:
        print(f"获取网页内容出错: {e}")
        if status_callback:
            status_callback(f"获取网页内容出错: {e}")
        # 恢复原始剪贴板
        pyperclip.copy(original_clipboard)
        return None
    finally:
        # 恢复原始剪贴板
        pyperclip.copy(original_clipboard)

def close_browser_window():
    """关闭当前活动的浏览器窗口"""
    try:
        # 查找所有窗口
        windows = Desktop(backend="uia").windows()
        
        # 寻找Edge浏览器窗口
        found = False
        for w in windows:
            if "Edge" in w.window_text() or "Microsoft" in w.window_text():
                # 关闭窗口
                w.close()
                print("已关闭Edge窗口")
                found = True
                time.sleep(0.5)  # 等待窗口关闭
        
        if not found:
            print("未找到需要关闭的Edge窗口")
        return found
    except Exception as e:
        print(f"关闭浏览器窗口出错: {e}")
        return False

def analyze_webpage_content(url, research_question, api_key=None, status_callback=None):
    """
    使用pywinauto从Edge浏览器中提取网页内容并使用DeepSeek分析相关性
    基于handle_candle12.py的成熟方案
    """
    if not PYWINAUTO_AVAILABLE:
        print("pywinauto不可用，无法进行网页内容分析")
        if status_callback:
            status_callback("无法分析网页内容：pywinauto不可用")
        return None
    
    if not api_key:
        api_key = os.getenv("DEEPSEEK_API_KEY", "")
    
    if status_callback:
        status_callback(f"正在分析网页内容: {url}")
    
    # 首先提取网页内容
    content = extract_webpage_content(url, status_callback)
    
    if not content or len(content) < 500:
        if status_callback:
            status_callback("获取的网页内容太短或为空")
        return None
    
    # 使用DeepSeek API分析内容相关性
    try:
        from openai import OpenAI
        
        print("调用DeepSeek API分析内容相关性")
        if status_callback:
            status_callback("正在分析网页内容相关性...")
        
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        
        # 移除内容长度限制，保留完整内容用于分析
        # 注释掉原有的截断逻辑，让AI分析完整内容
        max_length = 6000
        if len(content) > max_length:
            half_length = max_length // 2
            content = content[:half_length] + "\n...[content truncated]...\n" + content[-half_length:]
        
        # 构建提示词
        ai_prompt = f"""
        Evaluate if the following content from a scientific webpage is relevant to this research question:
        
        Research Question: {research_question}
        
        Webpage Content:
        {content}
        
        Rate relevance from 1-10 (where 10 is highly relevant) and explain your reasoning in 2-3 sentences.
        Format your response as:
        {{
            "relevance_score": X,
            "explanation": "Your explanation here"
        }}
        """
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You evaluate if academic content is relevant to research questions."},
                {"role": "user", "content": ai_prompt}
            ],
            temperature=0.3
        )
        
        analysis = response.choices[0].message.content
        print(f"分析结果: {analysis}")
        
        try:
            # 尝试解析JSON响应
            match = re.search(r'\{\s*"relevance_score":\s*(\d+),\s*"explanation":\s*"([^"]+)"\s*\}', analysis)
            if match:
                score = int(match.group(1))
                explanation = match.group(2)
                result = {"score": score, "explanation": explanation}
            else:
                # 如果未能解析JSON，尝试提取关键信息
                score_match = re.search(r'relevance_score"?\s*:?\s*(\d+)', analysis)
                score = int(score_match.group(1)) if score_match else None
                
                # 提取解释文本
                explanation_lines = [line for line in analysis.split('\n') if len(line.strip()) > 20 and not line.strip().startswith('{') and not line.strip().startswith('}')]
                explanation = ' '.join(explanation_lines) if explanation_lines else "无法提取解释"
                
                result = {"score": score, "explanation": explanation}
            
            print(f"解析后的分析结果: {result}")
            return result
            
        except Exception as e:
            print(f"解析分析结果出错: {e}")
            return {"score": None, "explanation": f"无法解析分析结果: {analysis[:100]}..."}
    
    except Exception as e:
        print(f"分析网页内容出错: {e}")
        if status_callback:
            status_callback(f"分析网页内容出错: {e}")
        return None

class WebContentExtractor:
    """网页内容提取器 - 基于pywinauto的实现"""
    
    def __init__(self):
        self.pywinauto_available = PYWINAUTO_AVAILABLE
    
    def extract_content(self, url, max_retries=3):
        """
        从URL提取完整的文章内容
        
        Args:
            url: 文章URL
            max_retries: 最大重试次数（暂时未使用，保持接口兼容性）
            
        Returns:
            dict: 包含标题、摘要、正文、作者等信息的字典
        """
        logger.info(f"开始提取网页内容: {url}")
        
        if not self.pywinauto_available:
            return self._create_error_content(url, "pywinauto不可用")
        
        try:
            # 使用pywinauto方法提取内容
            content = extract_webpage_content(url)
            
            if content and len(content) > 500:
                # 尝试从内容中提取结构化信息
                content_data = {
                    'url': url,
                    'title': self._extract_title_from_content(content),
                    'abstract': self._extract_abstract_from_content(content),
                    'full_text': content,
                    'authors': self._extract_authors_from_content(content),
                    'keywords': self._extract_keywords_from_content(content),
                    'doi': self._extract_doi_from_content(content, url),
                    'publication_info': self._extract_publication_info_from_content(content),
                    'success': True,
                    'extraction_method': 'pywinauto_browser'
                }
                
                logger.info(f"成功提取内容: {url}")
                return content_data
            else:
                return self._create_error_content(url, "无法获取足够的内容")
                
        except Exception as e:
            logger.error(f"内容提取失败: {url} - {str(e)}")
            return self._create_error_content(url, str(e))
    
    def _extract_title_from_content(self, content):
        """从内容中提取标题"""
        try:
            # 取内容的前几行作为可能的标题
            lines = content.split('\n')
            for line in lines[:10]:
                line = line.strip()
                if len(line) > 10 and len(line) < 200:
                    # 检查是否像标题
                    if not line.endswith('.') or line.count('.') <= 2:
                        return line
            
            # 如果没找到合适的，返回第一行
            if lines:
                return lines[0].strip()[:100]
                
        except Exception as e:
            logger.error(f"从内容提取标题失败: {str(e)}")
        
        return "未能提取标题"
    
    def _extract_abstract_from_content(self, content):
        """从内容中提取摘要"""
        try:
            # 查找包含"abstract"的段落
            lines = content.split('\n')
            abstract_start = -1
            
            for i, line in enumerate(lines):
                if 'abstract' in line.lower() and len(line.strip()) < 50:
                    abstract_start = i + 1
                    break
            
            if abstract_start > 0 and abstract_start < len(lines):
                # 提取abstract后的几行
                abstract_lines = []
                for i in range(abstract_start, min(abstract_start + 10, len(lines))):
                    line = lines[i].strip()
                    if len(line) > 20:
                        abstract_lines.append(line)
                        if len(' '.join(abstract_lines)) > 300:
                            break
                
                if abstract_lines:
                    return ' '.join(abstract_lines)
            
            # 如果没找到abstract，返回前几句
            sentences = content.split('.')[:5]
            return '. '.join(sentences) + '.'
            
        except Exception as e:
            logger.error(f"从内容提取摘要失败: {str(e)}")
        
        return "未能提取摘要"
    
    def _extract_authors_from_content(self, content):
        """从内容中提取作者"""
        try:
            # 查找作者模式
            author_patterns = [
                r'Authors?:\s*([^\n\r]+)',
                r'By:\s*([^\n\r]+)',
                r'Written by:\s*([^\n\r]+)',
            ]
            
            for pattern in author_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    author_text = matches[0].strip()
                    # 清理作者名
                    if ';' in author_text:
                        authors = [a.strip() for a in author_text.split(';')]
                    elif ' and ' in author_text:
                        authors = [a.strip() for a in author_text.split(' and ')]
                    elif ',' in author_text and len(author_text.split(',')) <= 10:
                        authors = [a.strip() for a in author_text.split(',')]
                    else:
                        authors = [author_text]
                    
                    # 过滤和清理
                    cleaned_authors = []
                    for author in authors[:10]:  # 限制作者数量
                        author = author.strip()
                        if len(author) > 2 and len(author) < 80:
                            cleaned_authors.append(author)
                    
                    if cleaned_authors:
                        return '; '.join(cleaned_authors)
                        
        except Exception as e:
            logger.error(f"从内容提取作者失败: {str(e)}")
        
        return "未能提取作者信息"
    
    def _extract_keywords_from_content(self, content):
        """从内容中提取关键词"""
        try:
            # 查找关键词部分
            keywords_match = re.search(r'keywords?:\s*([^\n\r]+)', content, re.IGNORECASE)
            if keywords_match:
                return keywords_match.group(1).strip()
                
        except Exception as e:
            logger.error(f"从内容提取关键词失败: {str(e)}")
        
        return ""
    
    def _extract_doi_from_content(self, content, url):
        """从内容或URL中提取DOI"""
        try:
            # 从内容中查找DOI
            doi_pattern = re.compile(r'doi:\s*(10\.\d+/[^\s]+)', re.I)
            doi_match = doi_pattern.search(content)
            if doi_match:
                return doi_match.group(1)
            
            # 从URL提取
            doi_match = re.search(r'10\.\d+/[^\s]+', url)
            if doi_match:
                return doi_match.group(0)
                
        except Exception as e:
            logger.error(f"从内容提取DOI失败: {str(e)}")
        
        return ""
    
    def _extract_publication_info_from_content(self, content):
        """从内容中提取发表信息"""
        try:
            pub_info = {}
            
            # 尝试提取期刊信息
            journal_patterns = [
                r'published in\s+([^\n\r,]+)',
                r'journal:\s*([^\n\r,]+)',
                r'source:\s*([^\n\r,]+)'
            ]
            
            for pattern in journal_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    pub_info['journal'] = match.group(1).strip()
                    break
            
            # 尝试提取年份
            year_pattern = r'(19|20)\d{2}'
            year_matches = re.findall(year_pattern, content)
            if year_matches:
                # 取最近的年份
                years = [int(y) for y in year_matches if int(y) >= 1990 and int(y) <= 2025]
                if years:
                    pub_info['year'] = str(max(years))
            
            return pub_info
            
        except Exception as e:
            logger.error(f"从内容提取发表信息失败: {str(e)}")
        
        return {}
    
    def _create_error_content(self, url, error_msg):
        """创建错误内容"""
        return {
            'url': url,
            'title': "内容提取失败",
            'abstract': f"无法提取内容: {error_msg}",
            'full_text': f"由于技术原因无法提取完整内容。错误信息: {error_msg}",
            'authors': "未知",
            'keywords': "",
            'doi': "",
            'publication_info': {},
            'success': False,
            'extraction_method': 'error',
            'error': error_msg
        }

def extract_web_content(url, max_retries=3):
    """
    便捷函数：提取网页内容
    
    Args:
        url: 网页URL
        max_retries: 最大重试次数
        
    Returns:
        dict: 提取的内容数据
    """
    extractor = WebContentExtractor()
    return extractor.extract_content(url, max_retries)

if __name__ == "__main__":
    # 测试代码
    test_urls = [
        "https://www.nature.com/articles/s41586-023-06906-8",
        "https://www.science.org/doi/10.1126/science.abq7652"
    ]
    
    for url in test_urls:
        print(f"\n测试URL: {url}")
        content = extract_web_content(url)
        print(f"标题: {content['title']}")
        print(f"摘要长度: {len(content['abstract'])}")
        print(f"正文长度: {len(content['full_text'])}")
        print(f"提取成功: {content['success']}")
        print(f"提取方法: {content['extraction_method']}")
