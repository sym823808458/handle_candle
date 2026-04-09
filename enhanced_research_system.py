# /*
#  * @Author: Yuming Su
#  * @Date: 2025-06-10
#  * 增强版闭环科学研究工作流系统
#  * 集成原有handle_candle功能，实现完整的闭环研究流程
# */

import os
import re
import csv
import pandas as pd
import requests
import tkinter as tk
from tkinter import messagebox, ttk, scrolledtext, filedialog, simpledialog
from bs4 import BeautifulSoup
import json
from openai import OpenAI
import time
import random
import threading
import datetime
import webbrowser
from urllib.parse import quote
import pyperclip
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def estimate_tokens(text):
    """
    估算文本的token数量
    简单估算：1个token约等于4个字符（对于英文）或1.5个字符（对于中文）
    """
    if not text:
        return 0
    
    # 计算中文字符数量
    chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
    # 计算其他字符数量
    other_chars = len(text) - chinese_chars
    
    # 估算token数：中文字符按1.5个字符/token，其他按4个字符/token
    estimated_tokens = int(chinese_chars / 1.5 + other_chars / 4)
    return estimated_tokens

def smart_truncate_content(content, max_tokens=50000):
    """
    智能截断内容，保留重要部分
    
    参数:
        content: 要截断的内容
        max_tokens: 最大token数量
    
    返回:
        截断后的内容
    """
    if not content:
        return content
    
    current_tokens = estimate_tokens(content)
    
    if current_tokens <= max_tokens:
        return content
    
    print(f"⚠️ 内容过长 ({current_tokens} tokens)，开始智能截断到 {max_tokens} tokens...")
    
    # 分割内容为不同部分
    lines = content.split('\n')
    
    # 识别重要部分
    title_lines = []
    abstract_lines = []
    intro_lines = []
    method_lines = []
    result_lines = []
    conclusion_lines = []
    other_lines = []
    
    current_section = "other"
    
    for line in lines:
        line_lower = line.lower().strip()
        
        # 识别标题
        if any(keyword in line_lower for keyword in ['标题:', 'title:', '作者:', 'author:', 'doi:', 'url:']):
            title_lines.append(line)
            current_section = "title"
        # 识别摘要
        elif any(keyword in line_lower for keyword in ['摘要:', 'abstract:', 'summary:']):
            abstract_lines.append(line)
            current_section = "abstract"
        # 识别引言/介绍
        elif any(keyword in line_lower for keyword in ['introduction', 'background', '引言', '背景']):
            intro_lines.append(line)
            current_section = "intro"
        # 识别方法
        elif any(keyword in line_lower for keyword in ['method', 'experimental', 'procedure', '方法', '实验']):
            method_lines.append(line)
            current_section = "method"
        # 识别结果
        elif any(keyword in line_lower for keyword in ['result', 'finding', '结果', '发现']):
            result_lines.append(line)
            current_section = "result"
        # 识别结论
        elif any(keyword in line_lower for keyword in ['conclusion', 'discussion', '结论', '讨论']):
            conclusion_lines.append(line)
            current_section = "conclusion"
        else:
            # 根据当前部分分类
            if current_section == "title":
                title_lines.append(line)
            elif current_section == "abstract":
                abstract_lines.append(line)
            elif current_section == "intro":
                intro_lines.append(line)
            elif current_section == "method":
                method_lines.append(line)
            elif current_section == "result":
                result_lines.append(line)
            elif current_section == "conclusion":
                conclusion_lines.append(line)
            else:
                other_lines.append(line)
    
    # 按重要性保留内容
    preserved_content = []
    remaining_tokens = max_tokens
    
    # 1. 保留标题和基本信息（最高优先级）
    title_content = '\n'.join(title_lines)
    title_tokens = estimate_tokens(title_content)
    if title_tokens <= remaining_tokens:
        preserved_content.append(title_content)
        remaining_tokens -= title_tokens
    
    # 2. 保留摘要（高优先级）
    abstract_content = '\n'.join(abstract_lines)
    abstract_tokens = estimate_tokens(abstract_content)
    if abstract_tokens <= remaining_tokens:
        preserved_content.append(abstract_content)
        remaining_tokens -= abstract_tokens
    elif remaining_tokens > 1000:  # 如果还有足够空间，截断摘要
        truncated_abstract = truncate_to_tokens(abstract_content, min(remaining_tokens - 500, 5000))
        preserved_content.append(truncated_abstract + "\n...[摘要已截断]...")
        remaining_tokens -= estimate_tokens(truncated_abstract)
    
    # 3. 保留结论（高优先级）
    conclusion_content = '\n'.join(conclusion_lines)
    conclusion_tokens = estimate_tokens(conclusion_content)
    if conclusion_tokens <= remaining_tokens:
        preserved_content.append(conclusion_content)
        remaining_tokens -= conclusion_tokens
    elif remaining_tokens > 1000:
        truncated_conclusion = truncate_to_tokens(conclusion_content, min(remaining_tokens - 500, 3000))
        preserved_content.append(truncated_conclusion + "\n...[结论已截断]...")
        remaining_tokens -= estimate_tokens(truncated_conclusion)
    
    # 4. 保留结果（中等优先级）
    if remaining_tokens > 2000:
        result_content = '\n'.join(result_lines)
        result_tokens = estimate_tokens(result_content)
        if result_tokens <= remaining_tokens:
            preserved_content.append(result_content)
            remaining_tokens -= result_tokens
        elif remaining_tokens > 1000:
            truncated_result = truncate_to_tokens(result_content, min(remaining_tokens - 500, 3000))
            preserved_content.append(truncated_result + "\n...[结果已截断]...")
            remaining_tokens -= estimate_tokens(truncated_result)
    
    # 5. 保留方法（中等优先级）
    if remaining_tokens > 1500:
        method_content = '\n'.join(method_lines)
        method_tokens = estimate_tokens(method_content)
        if method_tokens <= remaining_tokens:
            preserved_content.append(method_content)
            remaining_tokens -= method_tokens
        elif remaining_tokens > 1000:
            truncated_method = truncate_to_tokens(method_content, min(remaining_tokens - 500, 2000))
            preserved_content.append(truncated_method + "\n...[方法已截断]...")
            remaining_tokens -= estimate_tokens(truncated_method)
    
    # 6. 保留引言（较低优先级）
    if remaining_tokens > 1000:
        intro_content = '\n'.join(intro_lines)
        intro_tokens = estimate_tokens(intro_content)
        if intro_tokens <= remaining_tokens:
            preserved_content.append(intro_content)
            remaining_tokens -= intro_tokens
        elif remaining_tokens > 500:
            truncated_intro = truncate_to_tokens(intro_content, min(remaining_tokens - 200, 1500))
            preserved_content.append(truncated_intro + "\n...[引言已截断]...")
            remaining_tokens -= estimate_tokens(truncated_intro)
    
    final_content = '\n\n'.join(preserved_content)
    final_tokens = estimate_tokens(final_content)
    
    print(f"✅ 内容截断完成: {current_tokens} → {final_tokens} tokens")
    
    return final_content

def truncate_to_tokens(text, target_tokens):
    """
    将文本截断到指定的token数量
    """
    if not text:
        return text
    
    current_tokens = estimate_tokens(text)
    if current_tokens <= target_tokens:
        return text
    
    # 按比例截断
    ratio = target_tokens / current_tokens
    target_chars = int(len(text) * ratio * 0.9)  # 留一些余量
    
    return text[:target_chars]

# 全局变量
DEFAULT_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

# DOI转URL的基础URL映射（来自原始代码）
BASE_URLS = {
    "10.1021": "https://pubs.acs.org/doi/pdf/",
    "10.1038": "https://www.nature.com/articles/",
    "10.1073": 'https://www.pnas.org/doi/pdf/',
    "10.1002": 'https://onlinelibrary.wiley.com/doi/epdf/',
    "10.1007": 'https://link.springer.com/content/pdf/',
    "10.1016": 'https://doi.org/',
    "10.1039": 'https://doi.org/',
    "10.1055": 'https://www.thieme-connect.de/products/ejournals/pdf/',
    "10.1063": 'https://doi.org/',
    "10.1070": 'https://iopscience.iop.org/article/',
    "10.1071": 'https://www.publish.csiro.au/ch/pdf/',
    "10.1080": 'https://www.tandfonline.com/doi/pdf/',
    "10.1088": 'https://iopscience.iop.org/article/',
    "10.1093": 'https://doi.org/',
    "10.1098": 'https://royalsocietypublishing.org/doi/pdf/',
    "10.1126": 'https://www.science.org/doi/pdf/',
    "10.1186": 'https://sustainablechemicalprocesses.springeropen.com/counter/pdf/',
    "10.1146": 'https://www.annualreviews.org/doi/pdf/',
    "10.1103": 'https://journals.aps.org/pra/pdf/',
    "10.1145": 'https://dl.acm.org/doi/pdf/',
    "10.1109": 'https://doi.org/',
    "10.1364": 'https://doi.org/',
    'arXiv':  "https://arxiv.org/pdf/",
    "10.1557": 'https://link.springer.com/content/pdf/'
}

# 用户代理列表（来自原始代码）
user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'
]

def get_random_headers():
    """获取随机请求头"""
    return {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0'
    }

def doi_to_url(doi):
    """
    将DOI转换为可用于下载的URL（来自原始代码）
    """
    try:
        # 提取DOI前缀
        if 'arXiv:' in doi:
            doi_prefix = 'arXiv'
        else:
            doi_prefix = doi.split('/')[0]

        # 使用前缀获取基础URL
        base_url = BASE_URLS.get(doi_prefix)
        
        if not base_url:
            logger.warning(f"未识别的DOI前缀: {doi_prefix}")
            return None
            
        # 构建最终URL
        final_url = base_url + doi
        
        # 根据不同出版商添加特定参数
        if doi_prefix in ["10.1021", "10.1073", "10.1080", "10.1098", "10.1126", "10.1002"]:
            final_url += ""
        elif doi_prefix in ["10.1007", "10.1557"]:
            final_url += ".pdf?pdf=button"
        elif doi_prefix in ["10.1055", "10.1186"]:
            final_url += ".pdf"
        elif doi_prefix in ["10.1070", "10.1088"]:
            final_url += "/pdf"
        elif doi_prefix == "10.1038":
            # Nature特殊处理
            final_url += ".pdf"
            parts = final_url.split('/')
            if len(parts) > 2:
                del parts[-2]
                final_url = '/'.join(parts)
        elif doi_prefix == "10.1071":
            # CSIRO特殊处理
            parts = final_url.split('/')
            if len(parts) > 2:
                del parts[-2]
                final_url = '/'.join(parts)
                
        # 一些网站需要网页访问，无法直接生成PDF URL，返回基本URL
        if doi_prefix in ["10.1039", "10.1109", "10.1016", "10.1063", "10.1093", "10.1002", "10.1364"]:
            final_url = f"https://doi.org/{doi}"
            
        logger.info(f"DOI {doi} 转换为URL: {final_url}")
        return final_url
        
    except Exception as e:
        logger.error(f"DOI转URL出错: {str(e)}")
        return None

def extract_doi_from_url(url):
    """
    从URL中提取DOI（来自原始代码）
    """
    logger.info(f"尝试从URL提取DOI: {url}")
    
    # 直接从doi.org链接提取
    if 'doi.org' in url:
        try:
            doi_part = url.split('doi.org/')[-1]
            logger.info(f"从doi.org链接提取DOI: {doi_part}")
            return doi_part
        except:
            logger.info("从doi.org链接提取DOI失败")
            pass
    
    # 从其他URL模式提取DOI
    patterns = [
        r'(?:doi/|/doi/full/|/doi/pdf/|/doi/epdf/|/link.springer.com/article/)(\S+)',
        r'doi=([^&]+)',
        r'doi/([^/\s]+/[^/\s]+)'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, url)
        if matches:
            logger.info(f"使用模式 '{pattern}' 找到DOI: {matches[0]}")
            return matches[0]
    
    # 处理特殊情况 - Nature
    if 'nature.com' in url:
        last_part = url.split("/")[-1]
        if '-' in last_part and not last_part.endswith(('.pdf', '.html')):
            doi = f"10.1038/{last_part}"
            try:
                logger.info(f"尝试Nature特殊情况DOI: {doi}")
                response = requests.get(f"https://doi.org/{doi}", headers=get_random_headers())
                if response.status_code == 200 and "DOI Not Found" not in response.text:
                    logger.info(f"确认Nature DOI有效: {doi}")
                    return doi
            except:
                logger.info("检查Nature DOI有效性失败")
                pass
    
    # 处理特殊情况 - RSC
    if 'pubs.rsc.org' in url:
        last_part = url.split("/")[-1]
        if not last_part.endswith(('.pdf', '.html')):
            doi = f"10.1039/{last_part}"
            try:
                logger.info(f"尝试RSC特殊情况DOI: {doi}")
                response = requests.get(f"https://doi.org/{doi}", headers=get_random_headers())
                if response.status_code == 200 and "DOI Not Found" not in response.text:
                    logger.info(f"确认RSC DOI有效: {doi}")
                    return doi
            except:
                logger.info("检查RSC DOI有效性失败")
                pass
    
    logger.info("未能从URL提取DOI")
    return None

def translate_question_to_english(question, api_key=None):
    """
    使用DeepSeek API将科学问题翻译为英文（来自原始代码）
    """
    if not api_key:
        api_key = DEFAULT_API_KEY
    
    # 检测问题是否包含中文字符
    def contains_chinese(text):
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                return True
        return False
    
    # 如果不包含中文字符且看起来已经是英文，直接返回
    if not contains_chinese(question) and all(c.isascii() for c in question):
        logger.info("问题已经是英文，无需翻译")
        return question
    
    try:
        logger.info(f"检测到非英文问题，进行翻译: {question}")
        
        # 初始化OpenAI客户端与DeepSeek端点
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a professional scientific translator. Translate the given scientific question into English accurately and professionally."},
                {"role": "user", "content": f"""
                Translate the following scientific question into English. Maintain all technical terms intact.
                Only provide the translation, without any explanations or comments.
                
                Question: {question}
                """}
            ],
            temperature=0.1,
            max_tokens=200
        )
        
        translated = response.choices[0].message.content.strip()
        
        logger.info(f"问题翻译完成: {question} -> {translated}")
        return translated
        
    except Exception as e:
        logger.error(f"翻译问题出错: {e}")
        # 失败时返回原始问题
        return question

def call_deepseek_api(scientific_question, rigor_level="medium", api_key=None):
    """
    调用DeepSeek API分解科学问题为搜索查询（来自原始代码）
    """
    if not api_key:
        api_key = DEFAULT_API_KEY
    
    # 根据严谨度设置提示词
    if rigor_level == "strict":
        instruction = "Break down this scientific question into 2-3 highly specific, focused search queries. Prioritize precision over breadth. Target the most directly relevant papers only."
        num_queries = "2-3"
    elif rigor_level == "medium":
        instruction = "Break down this scientific question into 4-6 specific search queries. Balance precision and breadth to find about 30 relevant papers."
        num_queries = "4-6"
    else:  # broad
        instruction = "Break down this scientific question into 8-10 search queries covering various aspects and related topics. Aim for breadth to find at least 100 relevant papers in English."
        num_queries = "8-10"
    
    logger.info(f"正在调用DeepSeek API生成搜索查询，严谨度：{rigor_level}")
    
    # 构建完整提示词
    prompt = f"""
    {instruction}
    
    Question: {scientific_question}
    
    Format your response as a JSON array of strings, each representing a search query.
    Create {num_queries} search queries optimized for Bing Academic Search.
    Example: ["query 1", "query 2", "query 3"]
    """
    
    # Initialize OpenAI client with DeepSeek endpoint
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a scientific research assistant skilled at breaking down complex questions into searchable queries in English."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        content = response.choices[0].message.content
        logger.info(f"DeepSeek API响应: {content}")
        
        # Try to parse the JSON array from the response
        try:
            # Look for array pattern in the response
            match = re.search(r'\[\s*"[^"]*"(?:\s*,\s*"[^"]*")*\s*\]', content)
            if match:
                queries = json.loads(match.group(0))
                logger.info(f"成功解析JSON查询: {queries}")
            else:
                # If no proper JSON array found, try to extract lines that look like queries
                lines = [line.strip() for line in content.split('\n') if line.strip()]
                queries = [line.strip('"').strip('"').strip('`') for line in lines if len(line) > 10 and not line.startswith(('```', '[', ']', '{', '}'))]
                queries = [q for q in queries if ':' not in q[:15]]  # Remove lines that start like "Query 1: "
                logger.info(f"未找到JSON格式，提取查询行: {queries}")
                if not queries:
                    logger.info("无法提取查询，使用原始问题")
                    queries = [scientific_question]
        except json.JSONDecodeError:
            logger.info("无法解析JSON响应，使用原始问题")
            queries = [scientific_question]
            
        return queries
    except Exception as e:
        logger.error(f"调用DeepSeek API出错: {e}")
        return [scientific_question]  # Fall back to the original question if API fails

def search_bing_academic(query, page_count=2, status_callback=None):
    """
    搜索Bing学术并返回结果（来自原始代码）
    """
    query = quote(query)
    results = []
    
    if status_callback:
        status_callback(f"正在搜索: {query}")
    
    logger.info(f"搜索Bing学术: {query}")
    
    # 构建Bing学术搜索URL
    urls = [f"https://cn.bing.com/academic/search?q={query}&first={i*10+1}" for i in range(page_count)]
    
    # 可能包含学术文献的域名
    academic_domains = [
        'www.nature.com', 'pubs.rsc.org', 'pubs.acs.org', 
        'onlinelibrary.wiley.com', 'link.springer.com', 
        'www.science.org', 'www.sciencedirect.com', 'www.pnas.org',
        'academic.oup.com', 'journals.aps.org', 'ieeexplore.ieee.org',
        'jamanetwork.com', 'nejm.org', 'cell.com', 'aaas.org',
        'tandfonline.com', 'sagepub.com', 'sciencemag.org'
    ]
    
    for url in urls:
        try:
            logger.info(f"请求URL: {url}")
            response = requests.get(url, headers=get_random_headers(), timeout=10)
            logger.info(f"状态码: {response.status_code}")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找搜索结果中的所有链接
            links = soup.select('a')
            logger.info(f"找到 {len(links)} 个链接")
            
            for link in links:
                href = link.get('href', '')
                # 检查是否是学术网站链接
                for domain in academic_domains:
                    if domain in href:
                        # 尝试获取链接的标题
                        title = link.get_text().strip()
                        if title:
                            results.append({'url': href, 'title': title})
                            logger.info(f"找到学术链接: {title[:30]}... | {href}")
                        else:
                            results.append({'url': href, 'title': '未获取到标题'})
                            logger.info(f"找到学术链接(无标题): {href}")
                        break
                # 直接检查DOI链接
                if 'doi.org' in href:
                    title = link.get_text().strip()
                    if title:
                        results.append({'url': href, 'title': title})
                        logger.info(f"找到DOI链接: {title[:30]}... | {href}")
                    else:
                        results.append({'url': href, 'title': '未获取到标题'})
                        logger.info(f"找到DOI链接(无标题): {href}")
            
            # 添加延迟以避免被封
            delay = random.uniform(1.5, 3)
            logger.info(f"等待 {delay:.2f} 秒后继续...")
            time.sleep(delay)
            
        except Exception as e:
            logger.error(f"搜索URL出错 {url}: {e}")
    
    logger.info(f"总共找到 {len(results)} 个结果")
    return results

def query_crossref_references(doi, status_callback=None):
    """
    查询文献引用的其他文献（它引用了谁）
    """
    if status_callback:
        status_callback(f"正在查询DOI [{doi}] 引用的文献...")
    
    # 构建Crossref API URL
    url = f"https://api.crossref.org/works/{doi}"
    
    try:
        # 添加邮箱以获得更好的响应优先级
        headers = get_random_headers()
        headers['User-Agent'] = 'ScienceSearchApp/1.0 (mailto:your_email@example.com)'
        
        response = requests.get(url, headers=headers, timeout=20)
        data = response.json()
        
        if 'message' not in data:
            if status_callback:
                status_callback(f"无法获取DOI [{doi}] 的数据")
            return []
        
        message = data['message']
        references = []
        
        # 提取引用文献
        if 'reference' in message:
            for ref in message['reference']:
                ref_doi = ref.get('DOI', '')
                
                title = ''
                if 'unstructured' in ref:
                    title = ref['unstructured']
                elif 'article-title' in ref:
                    title = ref['article-title']
                
                # 提取年份
                year = ''
                if 'year' in ref:
                    year = ref['year']
                
                # 提取作者
                authors = ''
                if 'author' in ref:
                    authors = ref['author']
                
                if ref_doi:  # 如果有DOI
                    references.append({
                        'doi': ref_doi,
                        'title': title,
                        'year': year,
                        'authors': authors,
                        'url': doi_to_url(ref_doi) or f"https://doi.org/{ref_doi}",
                        'relation': 'referenced_by'  # 表示"被查询文献引用"
                    })
                elif title:  # 如果没有DOI但有标题
                    references.append({
                        'doi': '',
                        'title': title,
                        'year': year,
                        'authors': authors,
                        'url': '',
                        'relation': 'referenced_by'  # 表示"被查询文献引用"
                    })
        
        if status_callback:
            status_callback(f"获取到 [{doi}] 引用的 {len(references)} 篇文献")
        
        return references
    
    except Exception as e:
        if status_callback:
            status_callback(f"查询引用文献出错: {str(e)}")
        logger.error(f"查询Crossref引用文献出错: {str(e)}")
        return []

def query_crossref_citations(doi, status_callback=None):
    """
    查询引用了该文献的其他文献（谁引用了它）
    """
    if status_callback:
        status_callback(f"正在查询引用DOI [{doi}] 的文献...")
    
    # 构建Crossref API URL查询引用情况
    url = f"https://api.crossref.org/works?filter=reference.DOI:{doi}&rows=100"
    
    try:
        # 添加邮箱以获得更好的响应优先级
        headers = get_random_headers()
        headers['User-Agent'] = 'ScienceSearchApp/1.0 (mailto:your_email@example.com)'
        
        response = requests.get(url, headers=headers, timeout=20)
        data = response.json()
        
        if 'message' not in data:
            if status_callback:
                status_callback(f"无法获取引用DOI [{doi}] 的文献数据")
            return []
        
        message = data['message']
        citations = []
        
        # 提取引用该文献的其他文献
        if 'items' in message:
            for item in message['items']:
                citing_doi = item.get('DOI', '')
                
                # 提取标题
                title = ''
                if 'title' in item and item['title']:
                    title = item['title'][0]
                
                # 提取年份
                year = ''
                if 'published' in item and 'date-parts' in item['published']:
                    year_parts = item['published']['date-parts']
                    if year_parts and year_parts[0]:
                        year = year_parts[0][0]
                
                # 提取作者
                authors = []
                if 'author' in item:
                    for author in item['author']:
                        if 'family' in author and 'given' in author:
                            authors.append(f"{author['family']}, {author['given']}")
                        elif 'family' in author:
                            authors.append(author['family'])
                
                authors_str = '; '.join(authors)
                
                if citing_doi:
                    citations.append({
                        'doi': citing_doi,
                        'title': title,
                        'year': year,
                        'authors': authors_str,
                        'url': doi_to_url(citing_doi) or f"https://doi.org/{citing_doi}",
                        'relation': 'cites'  # 表示"引用了查询文献"
                    })
        
        if status_callback:
            status_callback(f"获取到引用 [{doi}] 的 {len(citations)} 篇文献")
        
        return citations
    
    except Exception as e:
        if status_callback:
            status_callback(f"查询被引用文献出错: {str(e)}")
        logger.error(f"查询Crossref被引用文献出错: {str(e)}")
        return []

class EnhancedClosedLoopResearchSystem:
    """增强版闭环科学研究工作流系统"""
    
    def __init__(self):
        self.api_key = DEFAULT_API_KEY
        self.project_dir = None
        self.current_iteration = 0
        self.max_iterations = 10
        self.target_article_count = 50
        self.relevance_threshold = 8
        self.rigor_level = "medium"  # 添加严谨度设置
        self.high_quality_articles = []
        self.research_question = ""
        self.updated_question = ""
        self.batch_analysis_prompt = ""
        self.deep_thinking_prompt = ""
        self.workflow_status = "ready"
        self.status_callback = None
        
        # 全局去重机制
        self.processed_dois = set()  # 已处理的DOI集合
        self.processed_urls = set()  # 已处理的URL集合
        self.processed_url_hashes = set()  # 已处理的URL哈希集合（用于无DOI的文章）
        self.analysis_cache = {}  # 分析结果缓存 {doi: analysis_result}
        self.deduplication_stats = {
            "total_found": 0,
            "duplicates_by_doi": 0,
            "duplicates_by_url": 0,
            "duplicates_by_hash": 0,
            "cache_hits": 0,
            "unique_processed": 0
        }
        
        # 工作流数据存储
        self.workflow_data = {
            "iterations": [],
            "total_articles_found": 0,
            "high_quality_articles": [],
            "research_evolution": [],
            "citation_network": [],
            "knowledge_gaps": []
        }
    
    def initialize_project(self, project_name=None):
        """初始化项目目录结构"""
        if not project_name:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            project_name = f"closed_loop_research_{timestamp}"
        
        self.project_dir = os.path.join(os.getcwd(), project_name)
        
        # 创建项目子目录
        subdirs = [
            "iterations",      # 每轮迭代的结果
            "analysis",        # 分析结果
            "logs",           # 日志文件
            "search_results",  # 搜索结果
            "urls",           # URL文件
            "temp_analysis"   # 临时分析目录
        ]
        
        for subdir in subdirs:
            os.makedirs(os.path.join(self.project_dir, subdir), exist_ok=True)
        
        logger.info(f"项目目录已创建: {self.project_dir}")
        
        # 初始化去重数据库
        self.initialize_deduplication_database()
        
        return self.project_dir
    
    def set_parameters(self, research_question, batch_prompt, deep_prompt, 
                      target_count, threshold):
        """设置工作流参数"""
        self.research_question = research_question
        self.updated_question = research_question
        self.batch_analysis_prompt = batch_prompt
        self.deep_thinking_prompt = deep_prompt
        self.target_article_count = target_count
        self.relevance_threshold = threshold
        
        logger.info(f"工作流参数已设置 - 目标文章数: {target_count}, 阈值: {threshold}")
    
    def initialize_deduplication_database(self):
        """初始化去重数据库，从现有日志中恢复已处理的DOI和URL"""
        try:
            if not self.project_dir:
                return
            
            logs_dir = os.path.join(self.project_dir, "logs")
            if not os.path.exists(logs_dir):
                return
            
            index_file = os.path.join(logs_dir, "log_index.csv")
            if os.path.exists(index_file):
                with open(index_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        doi = row.get('DOI', '').strip()
                        if doi:
                            self.processed_dois.add(doi.lower())
                
                logger.info(f"从日志索引恢复了 {len(self.processed_dois)} 个已处理的DOI")
            
            # 扫描现有的分析结果文件，恢复缓存
            analysis_dir = os.path.join(self.project_dir, "analysis")
            if os.path.exists(analysis_dir):
                for filename in os.listdir(analysis_dir):
                    if filename.endswith('.json'):
                        try:
                            filepath = os.path.join(analysis_dir, filename)
                            with open(filepath, 'r', encoding='utf-8') as f:
                                analysis_results = json.load(f)
                            
                            for result in analysis_results:
                                if isinstance(result, dict):
                                    doi = result.get('doi', '').strip()
                                    url = result.get('url', '').strip()
                                    
                                    if doi:
                                        self.analysis_cache[doi.lower()] = result
                                    if url:
                                        self.processed_urls.add(url)
                                        
                        except Exception as e:
                            logger.warning(f"恢复分析缓存失败 {filename}: {str(e)}")
                
                logger.info(f"从分析结果恢复了 {len(self.analysis_cache)} 个缓存条目")
                
        except Exception as e:
            logger.error(f"初始化去重数据库出错: {str(e)}")
    
    def load_deduplication_database(self):
        """加载去重数据库，从CSV文件中读取已处理的文章记录"""
        try:
            if not self.project_dir:
                return
            
            dedup_db_file = os.path.join(self.project_dir, "logs", "deduplication_database.csv")
            if os.path.exists(dedup_db_file):
                with open(dedup_db_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        doi = row.get('DOI', '').strip()
                        url = row.get('URL', '').strip()
                        
                        if doi:
                            self.processed_dois.add(doi.lower())
                        if url:
                            self.processed_urls.add(url)
                            url_hash = self.generate_url_hash(url)
                            self.processed_url_hashes.add(url_hash)
                
                logger.info(f"从去重数据库加载了 {len(self.processed_dois)} 个DOI和 {len(self.processed_urls)} 个URL")
            else:
                logger.info("去重数据库文件不存在，将创建新的数据库")
                
        except Exception as e:
            logger.error(f"加载去重数据库出错: {str(e)}")
    
    def record_article_to_database(self, url, doi, title):
        """
        将文章记录到去重数据库CSV文件中
        优化版本：只在工作流结束时批量写入，避免频繁IO操作
        """
        try:
            if not self.project_dir:
                return
            
            # 使用内存缓存，避免频繁写入CSV
            if not hasattr(self, '_pending_records'):
                self._pending_records = []
            
            # 添加到待写入记录
            url_hash = self.generate_url_hash(url) if url else ''
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            record = {
                'DOI': doi if doi else '',
                'URL': url if url else '',
                'Title': title if title else '',
                'URL_Hash': url_hash,
                'Timestamp': timestamp,
                'Iteration': getattr(self, 'current_iteration', 0)
            }
            
            self._pending_records.append(record)
            logger.debug(f"文章已加入待写入队列: {title[:50]}...")
            
        except Exception as e:
            logger.error(f"记录文章到队列出错: {str(e)}")
    
    def flush_database_records(self):
        """批量写入待处理的数据库记录，减少IO操作"""
        try:
            if not hasattr(self, '_pending_records') or not self._pending_records:
                return
            
            if not self.project_dir:
                return
            
            dedup_db_file = os.path.join(self.project_dir, "logs", "deduplication_database.csv")
            
            # 检查文件是否存在
            file_exists = os.path.exists(dedup_db_file)
            
            with open(dedup_db_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'DOI', 'URL', 'Title', 'URL_Hash', 'Timestamp', 'Iteration'
                ])
                
                # 如果是新文件，写入表头
                if not file_exists:
                    writer.writeheader()
                
                # 批量写入所有待处理记录
                writer.writerows(self._pending_records)
            
            logger.info(f"批量写入 {len(self._pending_records)} 条记录到去重数据库")
            
            # 清空待写入队列
            self._pending_records = []
            
        except Exception as e:
            logger.error(f"批量写入数据库出错: {str(e)}")
    
    def check_duplicate_before_extraction(self, url, doi, title):
        """
        在网页内容提取之前检查文章是否重复
        
        参数:
            url: 文章URL
            doi: 文章DOI（可选）
            title: 文章标题（可选）
            
        返回:
            (is_duplicate, reason) - 简化返回，重复文章直接跳过
        """
        try:
            self.deduplication_stats["total_found"] += 1
            
            # 1. 优先检查DOI去重
            if doi and doi.strip():
                doi_lower = doi.strip().lower()
                if doi_lower in self.processed_dois:
                    self.deduplication_stats["duplicates_by_doi"] += 1
                    return True, f"重复DOI: {doi}"
            
            # 2. 检查URL去重
            if url and url.strip():
                if url in self.processed_urls:
                    self.deduplication_stats["duplicates_by_url"] += 1
                    return True, f"重复URL: {url[:50]}..."
                
                # 3. 检查URL哈希去重（用于处理URL参数变化的情况）
                url_hash = self.generate_url_hash(url)
                if url_hash in self.processed_url_hashes:
                    self.deduplication_stats["duplicates_by_hash"] += 1
                    return True, f"重复URL哈希: {url_hash}"
            
            # 4. 如果都不重复，标记为唯一
            self.deduplication_stats["unique_processed"] += 1
            return False, "唯一文章"
            
        except Exception as e:
            logger.error(f"检查重复文章出错: {str(e)}")
            return False, "检查失败"
    
    def generate_url_hash(self, url):
        """为URL生成唯一哈希值，用于无DOI文章的去重"""
        import hashlib
        return hashlib.md5(url.encode('utf-8')).hexdigest()[:16]
    
    def is_duplicate_article(self, url, doi=None, title=None):
        """
        检查文章是否为重复
        
        参数:
            url: 文章URL
            doi: 文章DOI（可选）
            title: 文章标题（可选）
            
        返回:
            (is_duplicate, reason, cached_result)
        """
        try:
            self.deduplication_stats["total_found"] += 1
            
            # 1. 优先检查DOI去重
            if doi and doi.strip():
                doi_lower = doi.strip().lower()
                if doi_lower in self.processed_dois:
                    self.deduplication_stats["duplicates_by_doi"] += 1
                    cached_result = self.analysis_cache.get(doi_lower)
                    if cached_result:
                        self.deduplication_stats["cache_hits"] += 1
                    return True, f"重复DOI: {doi}", cached_result
            
            # 2. 检查URL去重
            if url and url.strip():
                if url in self.processed_urls:
                    self.deduplication_stats["duplicates_by_url"] += 1
                    return True, f"重复URL: {url[:50]}...", None
                
                # 3. 检查URL哈希去重（用于处理URL参数变化的情况）
                url_hash = self.generate_url_hash(url)
                if url_hash in self.processed_url_hashes:
                    self.deduplication_stats["duplicates_by_hash"] += 1
                    return True, f"重复URL哈希: {url_hash}", None
            
            # 4. 如果都不重复，标记为唯一
            self.deduplication_stats["unique_processed"] += 1
            return False, "唯一文章", None
            
        except Exception as e:
            logger.error(f"检查重复文章出错: {str(e)}")
            return False, "检查失败", None
    
    def mark_article_as_processed(self, url, doi=None, analysis_result=None):
        """
        将文章标记为已处理
        
        参数:
            url: 文章URL
            doi: 文章DOI（可选）
            analysis_result: 分析结果（可选）
        """
        try:
            # 标记DOI为已处理
            if doi and doi.strip():
                doi_lower = doi.strip().lower()
                self.processed_dois.add(doi_lower)
                
                # 缓存分析结果
                if analysis_result:
                    self.analysis_cache[doi_lower] = analysis_result
            
            # 标记URL为已处理
            if url and url.strip():
                self.processed_urls.add(url)
                url_hash = self.generate_url_hash(url)
                self.processed_url_hashes.add(url_hash)
            
        except Exception as e:
            logger.error(f"标记文章为已处理出错: {str(e)}")
    
    def get_deduplication_stats(self):
        """获取去重统计信息"""
        return {
            "processed_dois_count": len(self.processed_dois),
            "processed_urls_count": len(self.processed_urls),
            "cached_results_count": len(self.analysis_cache),
            "stats": self.deduplication_stats.copy()
        }
    
    def print_deduplication_summary(self):
        """打印去重统计摘要"""
        stats = self.get_deduplication_stats()
        
        print("\n" + "="*80)
        print("🔄 全局去重统计摘要")
        print("="*80)
        print(f"📊 总发现文章数: {stats['stats']['total_found']}")
        print(f"🔍 唯一文章数: {stats['stats']['unique_processed']}")
        print(f"❌ 重复文章数: {stats['stats']['total_found'] - stats['stats']['unique_processed']}")
        print(f"   - DOI重复: {stats['stats']['duplicates_by_doi']}")
        print(f"   - URL重复: {stats['stats']['duplicates_by_url']}")
        print(f"   - 哈希重复: {stats['stats']['duplicates_by_hash']}")
        print(f"💾 缓存命中数: {stats['stats']['cache_hits']}")
        print(f"📝 已处理DOI数: {stats['processed_dois_count']}")
        print(f"🔗 已处理URL数: {stats['processed_urls_count']}")
        print(f"💿 缓存结果数: {stats['cached_results_count']}")
        
        if stats['stats']['total_found'] > 0:
            duplicate_rate = (stats['stats']['total_found'] - stats['stats']['unique_processed']) / stats['stats']['total_found'] * 100
            cache_hit_rate = stats['stats']['cache_hits'] / stats['stats']['total_found'] * 100
            print(f"📈 重复率: {duplicate_rate:.1f}%")
            print(f"⚡ 缓存命中率: {cache_hit_rate:.1f}%")
        
        print("="*80)
    
    def log_deduplication_stats(self):
        """输出去重统计信息"""
        stats = self.get_deduplication_stats()
        
        print("\n" + "="*60)
        print("🔄 去重统计信息")
        print("="*60)
        print(f"📊 总发现文章数: {stats['stats']['total_found']}")
        print(f"🔍 唯一文章数: {stats['stats']['unique_processed']}")
        print(f"❌ 重复文章数: {stats['stats']['total_found'] - stats['stats']['unique_processed']}")
        print(f"   - DOI重复: {stats['stats']['duplicates_by_doi']}")
        print(f"   - URL重复: {stats['stats']['duplicates_by_url']}")
        print(f"   - 哈希重复: {stats['stats']['duplicates_by_hash']}")
        print(f"💾 缓存命中数: {stats['stats']['cache_hits']}")
        
        if stats['stats']['total_found'] > 0:
            duplicate_rate = (stats['stats']['total_found'] - stats['stats']['unique_processed']) / stats['stats']['total_found'] * 100
            cache_hit_rate = stats['stats']['cache_hits'] / stats['stats']['total_found'] * 100
            print(f"📈 重复率: {duplicate_rate:.1f}%")
            print(f"⚡ 缓存命中率: {cache_hit_rate:.1f}%")
        
        print("="*60)
    
    def start_closed_loop_workflow(self):
        """启动闭环工作流"""
        self.workflow_status = "running"
        self.current_iteration = 0
        
        if self.status_callback:
            self.status_callback("开始闭环研究工作流...")
        
        try:
            while (len(self.high_quality_articles) < self.target_article_count and 
                   self.current_iteration < self.max_iterations):
                
                self.current_iteration += 1
                
                if self.status_callback:
                    self.status_callback(f"开始第 {self.current_iteration} 轮迭代...")
                
                # 执行单轮迭代
                iteration_result = self.execute_iteration()
                
                # 保存迭代结果
                self.save_iteration_result(iteration_result)
                
                # 检查是否满足停止条件
                if self.check_stop_condition():
                    break
                
                # 更新研究策略
                self.update_research_strategy()
            
            # 批量写入所有待处理的数据库记录
            self.flush_database_records()
            
            # 生成最终报告
            self.generate_final_report()
            
            self.workflow_status = "completed"
            if self.status_callback:
                self.status_callback("闭环研究工作流完成！")
                
        except Exception as e:
            self.workflow_status = "error"
            logger.error(f"工作流执行出错: {str(e)}")
            # 确保即使出错也要写入数据库
            self.flush_database_records()
            if self.status_callback:
                self.status_callback(f"工作流执行出错: {str(e)}")
    
    def execute_iteration(self):
        """执行单轮迭代"""
        iteration_data = {
            "iteration": self.current_iteration,
            "timestamp": datetime.datetime.now().isoformat(),
            "research_question": self.updated_question,
            "search_results": [],
            "analysis_results": [],
            "high_quality_count": 0,
            "citation_expansion": [],
            "knowledge_update": ""
        }
        
        try:
            # 步骤1: 搜索与分析
            if self.status_callback:
                self.status_callback(f"第{self.current_iteration}轮 - 执行搜索与分析...")
            
            search_results = self.search_and_analyze(self.updated_question)
            iteration_data["search_results"] = search_results
            
            # 保存搜索结果到文件
            self.save_search_results(search_results)
            
            # 步骤2: 批量分析内容
            if self.status_callback:
                self.status_callback(f"第{self.current_iteration}轮 - 批量分析内容...")
            
            analysis_results = self.batch_analyze_content(search_results)
            iteration_data["analysis_results"] = analysis_results
            
            # 步骤3: 筛选高分文章
            if self.status_callback:
                self.status_callback(f"第{self.current_iteration}轮 - 筛选高质量文章...")
            
            high_quality = self.filter_high_quality_articles(analysis_results)
            iteration_data["high_quality_count"] = len(high_quality)
            self.high_quality_articles.extend(high_quality)
            
            # 步骤4: 深度思考分析
            if self.status_callback:
                self.status_callback(f"第{self.current_iteration}轮 - 深度思考分析...")
            
            deep_analysis = self.deep_thinking_analysis(high_quality)
            iteration_data["knowledge_update"] = deep_analysis
            
            # 步骤5: 引用网络扩展
            if self.status_callback:
                self.status_callback(f"第{self.current_iteration}轮 - 扩展引用网络...")
            
            citation_expansion = self.expand_citation_network(high_quality)
            iteration_data["citation_expansion"] = citation_expansion
            
            # 保存引用网络URL供下一轮使用
            self.previous_citation_urls = citation_expansion
            
            # 打印闭环研究线索来源总结
            if self.current_iteration > 0:  # 从第二轮开始显示
                self.print_closed_loop_sources()
            
            return iteration_data
            
        except Exception as e:
            logger.error(f"第{self.current_iteration}轮迭代执行出错: {str(e)}")
            iteration_data["error"] = str(e)
            return iteration_data
    
    def search_and_analyze(self, question, target_count=None):
        """搜索与分析模块 - 使用真实的搜索功能，支持多种搜索策略和目标数量限制"""
        try:
            # 先翻译问题为英文
            english_question = translate_question_to_english(question, self.api_key)
            
            # 调用DeepSeek API分解搜索问题，使用设置的严谨度
            search_queries = call_deepseek_api(english_question, self.rigor_level, self.api_key)
            
            # 添加基于作者的搜索查询（如果有的话）
            if hasattr(self, 'author_keywords') and self.author_keywords:
                if self.status_callback:
                    self.status_callback(f"添加基于作者的搜索查询: {self.author_keywords}")
                
                # 为每个作者关键词生成搜索查询
                for author in self.author_keywords[:3]:  # 限制前3个作者
                    author_query = f"{author} {english_question.split()[0:3]}"  # 作者名 + 问题关键词
                    search_queries.append(author_query)
                    
                    # 添加更具体的作者相关查询
                    specific_query = f'author:"{author}" {english_question}'
                    search_queries.append(specific_query)
            
            # 执行真实的搜索 - 带目标数量限制
            all_results = []
            unique_urls = {}
            
            # 如果没有指定目标数量，使用默认值
            if target_count is None:
                target_count = getattr(self, 'target_search_count', 100)  # 默认100个
            
            for i, query in enumerate(search_queries):
                if len(unique_urls) >= target_count:
                    if self.status_callback:
                        self.status_callback(f"已达到目标数量 {target_count}，停止搜索")
                    break
                
                if self.status_callback:
                    self.status_callback(f"搜索查询 {i+1}/{len(search_queries)}: {query}")
                
                results = search_bing_academic(query, page_count=3, status_callback=self.status_callback)
                
                # 实时去重并检查数量
                for item in results:
                    if item['url'] not in unique_urls:
                        unique_urls[item['url']] = item
                        if len(unique_urls) >= target_count:
                            if self.status_callback:
                                self.status_callback(f"已达到目标数量 {len(unique_urls)}，停止当前查询")
                            break
                
                if self.status_callback:
                    self.status_callback(f"当前收集: {len(unique_urls)}/{target_count} 个URL")
            
            # 添加上一轮引用网络扩展的URL（如果有的话）
            if hasattr(self, 'previous_citation_urls') and self.previous_citation_urls:
                remaining_slots = target_count - len(unique_urls)
                if remaining_slots > 0:
                    if self.status_callback:
                        self.status_callback(f"添加上一轮引用网络扩展的URL（最多 {remaining_slots} 个）")
                    
                    added_count = 0
                    for url in self.previous_citation_urls:
                        if added_count >= remaining_slots:
                            break
                        if url not in unique_urls:
                            # 为引用网络URL创建结果项
                            unique_urls[url] = {
                                'url': url,
                                'title': '引用网络扩展文献',
                                'source': 'citation_network'
                            }
                            added_count += 1
                    
                    if self.status_callback:
                        self.status_callback(f"添加了 {added_count} 个引用网络URL")
            
            final_results = list(unique_urls.values())
            
            if self.status_callback:
                self.status_callback(f"搜索完成，找到 {len(final_results)} 个唯一结果")
            
            return final_results
            
        except Exception as e:
            logger.error(f"搜索分析出错: {str(e)}")
            return []
    
    def save_search_results(self, search_results):
        """保存搜索结果到文件"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 保存完整结果
            results_file = os.path.join(self.project_dir, "search_results", f"iteration_{self.current_iteration}_{timestamp}.txt")
            with open(results_file, 'w', encoding='utf-8') as f:
                for item in search_results:
                    f.write(f"{item['title']} | {item['url']}\n")
            
            # 保存URL列表
            urls_file = os.path.join(self.project_dir, "urls", f"iteration_{self.current_iteration}_urls.txt")
            with open(urls_file, 'w', encoding='utf-8') as f:
                for item in search_results:
                    f.write(f"{item['url']}\n")
            
            # # 提取并保存DOI
            # dois = []
            # for item in search_results:
            #     doi = extract_doi_from_url(item['url'])
            #     if doi:
            #         dois.append({'doi': doi, 'title': item['title'], 'url': item['url']})
            
            # if dois:
            #     dois_file = os.path.join(self.project_dir, "search_results", f"iteration_{self.current_iteration}_dois.csv")
            #     with open(dois_file, 'w', newline='', encoding='utf-8') as f:
            #         writer = csv.writer(f)
            #         writer.writerow(['DOI', 'Title', 'URL'])
            #         for item in dois:
            #             writer.writerow([item['doi'], item['title'], item['url']])
            
            # logger.info(f"搜索结果已保存: {len(search_results)} 个结果, {len(dois)} 个DOI")
            
        except Exception as e:
            logger.error(f"保存搜索结果出错: {str(e)}")
    
    def batch_analyze_content(self, search_results):
        """批量分析内容模块 - 使用优化的全局去重机制，在网页提取前进行去重检查"""
        analysis_results = []
        
        try:
            # 导入网页内容提取器
            from web_content_extractor import extract_web_content
            
            client = OpenAI(api_key=self.api_key, base_url="https://api.deepseek.com")
            
            print(f"\n🔍 开始批量分析 {len(search_results)} 篇文献...")
            print("="*80)
            
            # 重置去重统计
            self.deduplication_stats = {
                "total_found": 0,
                "duplicates_by_doi": 0,
                "duplicates_by_url": 0,
                "duplicates_by_hash": 0,
                "unique_processed": 0,
                "cache_hits": 0
            }
            
            # 加载去重数据库
            self.load_deduplication_database()
            
            # 第一阶段：预提取去重检查
            print("执行预提取去重检查...")
            articles_to_process = []
            skipped_articles = []
            
            for i, result in enumerate(search_results):
                try:
                    url = result['url']
                    title = result['title']
                    
                    # 尝试从URL提取DOI
                    doi = extract_doi_from_url(url)
                    
                    # 检查是否重复
                    is_duplicate, reason = self.check_duplicate_before_extraction(url, doi, title)
                    
                    if is_duplicate:
                        print(f"\n⏭️  [{i+1}/{len(search_results)}] 跳过重复文章（未提取网页内容）:")
                        print(f"   标题: {title[:80]}...")
                        print(f"   URL: {url[:80]}...")
                        print(f"   DOI: {doi if doi else '未找到DOI'}")
                        print(f"   原因: {reason}")
                        
                        skipped_articles.append({
                            'title': title,
                            'url': url,
                            'doi': doi,
                            'reason': reason
                        })
                        continue
                    
                    # 标记为唯一，需要处理
                    articles_to_process.append({
                        'index': i,
                        'result': result,
                        'doi': doi
                    })
                    
                    # 立即记录到数据库以防止同批次重复
                    self.record_article_to_database(url, doi, f"URL_{len(articles_to_process)}")
                    
                    # 添加到已处理集合
                    if doi:
                        self.processed_dois.add(doi.lower())
                    self.processed_urls.add(url)
                    url_hash = self.generate_url_hash(url)
                    self.processed_url_hashes.add(url_hash)
                    
                except Exception as e:
                    logger.error(f"预处理文章 {i+1} 出错: {str(e)}")
                    # 出错时仍然加入处理队列，避免遗漏
                    articles_to_process.append({
                        'index': i,
                        'result': result,
                        'doi': None
                    })
            
            print(f"\n📊 优化去重预处理结果:")
            print(f"   总文章数: {len(search_results)}")
            print(f"   跳过重复: {len(skipped_articles)}")
            print(f"   待处理: {len(articles_to_process)}")
            print(f"   节省网页提取: {len(skipped_articles)} 次")
            print("="*80)
            
            # 第二阶段：处理唯一文章
            if articles_to_process:
                for idx, article_info in enumerate(articles_to_process):
                    try:
                        i = article_info['index']
                        result = article_info['result']
                        doi = article_info['doi']
                        
                        if self.status_callback:
                            self.status_callback(f"分析文章 {idx+1}/{len(articles_to_process)}: {result['title'][:50]}...")
                        
                        print(f"\n📄 [{idx+1}/{len(articles_to_process)}] 开始分析唯一文章:")
                        print(f"   原序号: [{i+1}/{len(search_results)}]")
                        print(f"   标题: {result['title'][:80]}...")
                        print(f"   URL: {result['url']}")
                        if doi:
                            print(f"   DOI: {doi}")
                        
                        # 真实的网页内容提取
                        if self.status_callback:
                            self.status_callback(f"正在提取网页内容: {result['url']}")
                        
                        web_content = extract_web_content(result['url'], max_retries=2)
                        
                        # 构建完整的文章内容
                        if web_content['success']:
                            paper_content = f"""
标题: {web_content['title']}
作者: {web_content['authors']}
DOI: {web_content['doi']}
URL: {web_content['url']}
关键词: {web_content['keywords']}
发表信息: {web_content['publication_info']}

摘要:
{web_content['abstract']}

正文内容:
{web_content['full_text']}
"""
                            extraction_status = "成功提取完整内容"
                        else:
                            # 如果提取失败，使用基本信息
                            paper_content = f"""
标题: {result['title']}
URL: {result['url']}
内容提取状态: 失败 - {web_content.get('error', '未知错误')}

基本信息:
{web_content['full_text']}
"""
                            extraction_status = f"内容提取失败: {web_content.get('error', '未知错误')}"
                        
                        if self.status_callback:
                            self.status_callback(f"内容提取完成: {extraction_status}")
                        
                        # 智能截断内容以避免token超限
                        truncated_paper_content = smart_truncate_content(paper_content, max_tokens=50000)
                        
                        # 使用自定义prompt分析内容
                        final_prompt = self.batch_analysis_prompt.replace("{PAPER_CONTENT}", truncated_paper_content)
                        
                        # 估算prompt的token数量
                        prompt_tokens = estimate_tokens(final_prompt)
                        print(f"📏 Prompt token估算: {prompt_tokens} tokens")
                        
                        # 如果prompt仍然太长，进一步截断
                        if prompt_tokens > 55000:
                            print(f"⚠️ Prompt仍然过长，进一步截断...")
                            further_truncated_content = smart_truncate_content(paper_content, max_tokens=30000)
                            final_prompt = self.batch_analysis_prompt.replace("{PAPER_CONTENT}", further_truncated_content)
                            prompt_tokens = estimate_tokens(final_prompt)
                            print(f"📏 重新截断后token估算: {prompt_tokens} tokens")
                        
                        try:
                            response = client.chat.completions.create(
                                model="deepseek-chat",
                                messages=[
                                    {"role": "system", "content": "You are an expert academic research assistant."},
                                    {"role": "user", "content": final_prompt}
                                ],
                                temperature=0.3,
                                max_tokens=8000
                            )
                            
                            analysis_text = response.choices[0].message.content
                            
                        except Exception as api_error:
                            # 如果仍然出现token超限错误，使用最小化内容重试
                            if "maximum context length" in str(api_error).lower() or "invalid_request_error" in str(api_error).lower():
                                print(f"❌ API调用失败，尝试最小化内容重试...")
                                print(f"   错误信息: {str(api_error)[:200]}...")
                                
                                # 使用最小化的内容
                                minimal_content = f"""
标题: {web_content.get('title', result['title'])}
作者: {web_content.get('authors', '未知')}
DOI: {web_content.get('doi', '')}
URL: {result['url']}

摘要:
{web_content.get('abstract', '未提取到摘要')[:2000]}

正文内容（截断）:
{web_content.get('full_text', '未提取到正文')[:5000]}
...[内容因token限制已大幅截断]...
"""
                                
                                minimal_prompt = self.batch_analysis_prompt.replace("{PAPER_CONTENT}", minimal_content)
                                minimal_tokens = estimate_tokens(minimal_prompt)
                                print(f"📏 最小化内容token估算: {minimal_tokens} tokens")
                                
                                try:
                                    response = client.chat.completions.create(
                                        model="deepseek-chat",
                                        messages=[
                                            {"role": "system", "content": "You are an expert academic research assistant. Note: The paper content has been truncated due to length limitations."},
                                            {"role": "user", "content": minimal_prompt}
                                        ],
                                        temperature=0.3,
                                        max_tokens=4000
                                    )
                                    
                                    analysis_text = response.choices[0].message.content
                                    print(f"✅ 最小化内容分析成功")
                                    
                                except Exception as retry_error:
                                    print(f"❌ 最小化内容分析也失败: {str(retry_error)[:200]}...")
                                    # 如果还是失败，创建一个基本的分析结果
                                    analysis_text = f"""
{{
    "doi": "{web_content.get('doi', '')}",
    "title": "{web_content.get('title', result['title'])}",
    "authors": "{web_content.get('authors', '未知')}",
    "publication_year": "未知",
    "journal": "未知",
    "research_focus": "内容分析失败 - token超限",
    "key_methods": "无法分析",
    "major_contributions": "无法分析",
    "challenges": "无法分析",
    "relevance_score": 3
}}
"""
                            else:
                                # 其他类型的错误，重新抛出
                                raise api_error
                        
                        # 保存详细的分析日志
                        doi = web_content.get('doi', '') or extract_doi_from_url(result["url"]) or ""
                        self.save_analysis_log(
                            doi=doi,
                            url=result["url"],
                            title=result["title"],
                            extracted_content=paper_content,
                            prompt_used=final_prompt,
                            ai_response=analysis_text,
                            iteration=self.current_iteration
                        )
                        
                        # 尝试解析JSON结果
                        try:
                            json_match = re.search(r'(\{[\s\S]*\})', analysis_text)
                            if json_match:
                                analysis_data = json.loads(json_match.group(1))
                                analysis_data["url"] = result["url"]
                                analysis_data["success"] = True
                                
                                # 尝试提取DOI
                                if not analysis_data.get("doi"):
                                    analysis_data["doi"] = doi
                                
                                # 打印每篇文章的相关性评分
                                relevance_score = analysis_data.get("relevance_score", "未知")
                                title_short = result["title"][:60] + "..." if len(result["title"]) > 60 else result["title"]
                                print(f"📊 文章分析完成: {title_short}")
                                print(f"   🎯 相关性评分: {relevance_score}/10")
                                print(f"   🔗 URL: {result['url']}")
                                if analysis_data.get("research_focus"):
                                    print(f"   🔬 研究焦点: {analysis_data.get('research_focus', '')[:80]}...")
                                print("-" * 80)
                                
                                analysis_results.append(analysis_data)
                            else:
                                # 创建基本结构
                                analysis_results.append({
                                    "url": result["url"],
                                    "title": result["title"],
                                    "doi": doi,
                                    "success": False,
                                    "error": "无法解析JSON",
                                    "relevance_score": 5
                                })
                                
                                # 打印解析失败的文章
                                title_short = result["title"][:60] + "..." if len(result["title"]) > 60 else result["title"]
                                print(f"⚠️ 文章分析失败: {title_short}")
                                print(f"   ❌ 错误: 无法解析JSON")
                                print(f"   🎯 默认评分: 5/10")
                                print("-" * 80)
                                
                        except json.JSONDecodeError:
                            analysis_results.append({
                                "url": result["url"],
                                "title": result["title"],
                                "doi": doi,
                                "success": False,
                                "error": "JSON解析失败",
                                "relevance_score": 5
                            })
                            
                            # 打印JSON解析失败的文章
                            title_short = result["title"][:60] + "..." if len(result["title"]) > 60 else result["title"]
                            print(f"⚠️ 文章分析失败: {title_short}")
                            print(f"   ❌ 错误: JSON解析失败")
                            print(f"   🎯 默认评分: 5/10")
                            print("-" * 80)
                        
                        time.sleep(1)  # 避免API限制
                        
                    except Exception as e:
                        # 处理单个文章分析失败的情况
                        print(f"❌ 文章分析出错: {result['title'][:60]}...")
                        print(f"   错误信息: {str(e)[:200]}...")
                        
                        # 创建失败的分析结果
                        failed_result = {
                            "url": result["url"],
                            "title": result["title"],
                            "doi": doi or "",
                            "success": False,
                            "error": f"分析出错: {str(e)[:100]}",
                            "relevance_score": 3
                        }
                        
                        # 标记为已处理，避免重复尝试
                        self.mark_article_as_processed(result["url"], doi, failed_result)
                        
                        analysis_results.append(failed_result)
                        print("-" * 80)
            
            # 输出去重统计信息
            self.log_deduplication_stats()
            
            # 保存分析结果
            self.save_analysis_results(analysis_results)
            
            # 批量写入数据库记录
            self.flush_database_records()
            
            # 输出去重统计信息
            self.log_deduplication_stats()
            
            # 保存分析结果
            self.save_analysis_results(analysis_results)
            
            logger.info(f"批量分析完成，成功分析 {len(analysis_results)} 个内容")
            return analysis_results
            
        except Exception as e:
            logger.error(f"批量分析出错: {str(e)}")
            # 确保即使出错也要写入数据库
            self.flush_database_records()
            return []
    
    def save_analysis_results(self, analysis_results):
        """保存分析结果到文件 - 只保存analysis_results格式"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 只保存JSON格式，使用analysis_results_*命名
            json_file = os.path.join(self.project_dir, "analysis", f"analysis_results_{timestamp}.json")
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(analysis_results, f, ensure_ascii=False, indent=2)
            
            logger.info(f"分析结果已保存: {len(analysis_results)} 个结果到 {os.path.basename(json_file)}")
            
        except Exception as e:
            logger.error(f"保存分析结果出错: {str(e)}")
    
    def save_analysis_log(self, doi, url, title, extracted_content, prompt_used, ai_response, iteration):
        """
        保存每篇文章的详细分析日志 - 改进的文件命名策略
        
        参数:
            doi: 文章DOI
            url: 文章URL
            title: 文章标题
            extracted_content: 从网页提取的完整内容
            prompt_used: 使用的分析prompt
            ai_response: AI的分析回答
            iteration: 当前迭代轮次
        """
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 改进的文件命名策略
            if doi and doi.strip():
                # 优先使用DOI作为文件名
                safe_doi = self.create_safe_filename(doi)
                filename = f"{safe_doi}_iter{iteration:02d}_{timestamp}.txt"
            elif url:
                # 如果没有DOI，使用URL哈希
                url_hash = self.generate_url_hash(url)
                safe_title = self.create_safe_filename(title)[:30] if title else "unknown_title"
                filename = f"{safe_title}_{url_hash}_iter{iteration:02d}_{timestamp}.txt"
            else:
                # 最后备选：使用标题和时间戳
                safe_title = self.create_safe_filename(title)[:50] if title else "unknown_article"
                filename = f"{safe_title}_iter{iteration:02d}_{timestamp}.txt"
            
            log_file_path = os.path.join(self.project_dir, "logs", filename)
            
            # 检查文件是否已存在（避免重复保存）
            if os.path.exists(log_file_path):
                logger.info(f"日志文件已存在，跳过保存: {filename}")
                return
            
            # 构建详细的日志内容
            log_content = f"""
文章分析详细日志

基本信息:
- 文章标题: {title}
- DOI: {doi if doi else '未找到DOI'}
- URL: {url}
- 分析时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 迭代轮次: {iteration}
- 日志文件: {filename}

从网页提取的原始内容:

{extracted_content}

使用的分析Prompt:

{prompt_used}

DeepSeek AI的分析回答:

{ai_response}

日志结束
"""
            
            # 保存日志文件
            with open(log_file_path, 'w', encoding='utf-8') as f:
                f.write(log_content)
            
            logger.info(f"分析日志已保存: {log_file_path}")
            
            # 同时保存一个索引文件，方便查找
            self.update_log_index(doi, title, filename, iteration, timestamp)
            
        except Exception as e:
            logger.error(f"保存分析日志出错: {str(e)}")
    
    def create_safe_filename(self, text):
        """
        创建安全的文件名，移除或替换不安全的字符
        """
        if not text:
            return "unknown"
        
        # 移除或替换不安全的字符
        safe_chars = []
        for char in text:
            if char.isalnum() or char in '-_.':
                safe_chars.append(char)
            elif char in ' /\\:*?"<>|':
                safe_chars.append('_')
            else:
                safe_chars.append('_')
        
        safe_name = ''.join(safe_chars)
        
        # 移除连续的下划线
        while '__' in safe_name:
            safe_name = safe_name.replace('__', '_')
        
        # 移除开头和结尾的下划线
        safe_name = safe_name.strip('_')
        
        return safe_name if safe_name else "unknown"
    
    def update_log_index(self, doi, title, filename, iteration, timestamp):
        """
        更新日志索引文件，方便查找和管理日志
        """
        try:
            index_file = os.path.join(self.project_dir, "logs", "log_index.csv")
            
            # 检查索引文件是否存在，如果不存在则创建
            file_exists = os.path.exists(index_file)
            
            with open(index_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # 如果是新文件，写入表头
                if not file_exists:
                    writer.writerow([
                        'DOI', 'Title', 'Filename', 'Iteration', 'Timestamp', 
                        'Created_Time', 'File_Path'
                    ])
                
                # 写入日志记录
                writer.writerow([
                    doi if doi else '',
                    title,
                    filename,
                    iteration,
                    timestamp,
                    datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    os.path.join("logs", filename)
                ])
            
            logger.info(f"日志索引已更新: {index_file}")
            
        except Exception as e:
            logger.error(f"更新日志索引出错: {str(e)}")
    
    def find_article_logs(self, doi=None, title_keyword=None, iteration=None):
        """
        根据DOI、标题关键词或迭代轮次查找文章日志
        
        参数:
            doi: 要查找的DOI
            title_keyword: 标题中的关键词
            iteration: 迭代轮次
            
        返回:
            匹配的日志文件路径列表
        """
        try:
            index_file = os.path.join(self.project_dir, "logs", "log_index.csv")
            
            if not os.path.exists(index_file):
                return []
            
            matching_logs = []
            
            with open(index_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    match = True
                    
                    # 检查DOI匹配
                    if doi and row['DOI'].lower() != doi.lower():
                        match = False
                    
                    # 检查标题关键词匹配
                    if title_keyword and title_keyword.lower() not in row['Title'].lower():
                        match = False
                    
                    # 检查迭代轮次匹配
                    if iteration is not None and int(row['Iteration']) != iteration:
                        match = False
                    
                    if match:
                        log_path = os.path.join(self.project_dir, row['File_Path'])
                        if os.path.exists(log_path):
                            matching_logs.append({
                                'doi': row['DOI'],
                                'title': row['Title'],
                                'filename': row['Filename'],
                                'iteration': int(row['Iteration']),
                                'timestamp': row['Timestamp'],
                                'file_path': log_path
                            })
            
            return matching_logs
            
        except Exception as e:
            logger.error(f"查找文章日志出错: {str(e)}")
            return []
    
    def read_article_log(self, log_file_path):
        """
        读取指定的文章日志文件
        
        参数:
            log_file_path: 日志文件路径
            
        返回:
            日志内容字典，包含提取的内容、prompt和AI回答
        """
        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析日志内容的各个部分
            sections = content.split('=' * 80)
            
            log_data = {
                'full_content': content,
                'extracted_content': '',
                'prompt_used': '',
                'ai_response': ''
            }
            
            for i, section in enumerate(sections):
                if '从网页提取的原始内容:' in section and i + 1 < len(sections):
                    log_data['extracted_content'] = sections[i + 1].strip()
                elif '使用的分析Prompt:' in section and i + 1 < len(sections):
                    log_data['prompt_used'] = sections[i + 1].strip()
                elif 'DeepSeek AI的分析回答:' in section and i + 1 < len(sections):
                    log_data['ai_response'] = sections[i + 1].strip()
            
            return log_data
            
        except Exception as e:
            logger.error(f"读取文章日志出错: {str(e)}")
            return None
    
    def filter_high_quality_articles(self, analysis_results):
        """筛选高质量文章"""
        high_quality = []
        
        for article in analysis_results:
            if article.get("success", False):
                relevance_score = article.get("relevance_score", 0)
                try:
                    score = float(relevance_score)
                    if score >= self.relevance_threshold:
                        high_quality.append(article)
                except (ValueError, TypeError):
                    continue
        
        if self.status_callback:
            self.status_callback(f"筛选出 {len(high_quality)} 篇高质量文章（评分≥{self.relevance_threshold}）")
        
        return high_quality
    
    def deep_thinking_analysis(self, high_quality_articles):
        """深度思考分析"""
        if not high_quality_articles:
            return "没有高质量文章可供分析"
        
        try:
            client = OpenAI(api_key=self.api_key, base_url="https://api.deepseek.com")
            
            # 准备分析数据
            articles_summary = []
            for article in high_quality_articles:
                summary = {
                    "title": article.get("title", ""),
                    "authors": article.get("authors", ""),
                    "year": article.get("publication_year", ""),
                    "research_focus": article.get("research_focus", ""),
                    "major_contributions": article.get("major_contributions", ""),
                    "relevance_score": article.get("relevance_score", 0),
                    "doi": article.get("doi", "")
                }
                articles_summary.append(summary)
            
            # 构建深度分析prompt
            analysis_prompt = self.deep_thinking_prompt.replace(
                "{HIGH_QUALITY_ARTICLES}", 
                json.dumps(articles_summary, ensure_ascii=False, indent=2)
            )
            
            # 调用DeepSeek Reasoner进行深度分析
            try:
                response = client.chat.completions.create(
                    model="deepseek-reasoner",
                    messages=[
                        {"role": "system", "content": "You are an expert research analyst with deep thinking capabilities."},
                        {"role": "user", "content": analysis_prompt}
                    ],
                    temperature=0.1,
                    max_tokens=16000
                )
            except Exception:
                # 如果Reasoner不可用，使用标准模型
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "You are an expert research analyst."},
                        {"role": "user", "content": analysis_prompt}
                    ],
                    temperature=0.2,
                    max_tokens=16000
                )
            
            analysis_result = response.choices[0].message.content
            
            # 更新研究问题
            self.update_research_question(analysis_result)
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"深度思考分析出错: {str(e)}")
            return f"深度分析出错: {str(e)}"
    
    def update_research_question(self, analysis_result):
        """基于分析结果更新研究问题和搜索策略"""
        try:
            client = OpenAI(api_key=self.api_key, base_url="https://api.deepseek.com")
            
            # 提取高质量文章的作者信息用于搜索策略
            top_authors = self.extract_top_authors_from_articles()
            
            update_prompt = f"""
            基于以下深度分析结果，更新和优化原始研究问题，并制定下一轮搜索策略。
            
            原始研究问题: {self.research_question}
            当前研究问题: {self.updated_question}
            
            深度分析结果:
            {analysis_result}
            
            高质量文章的主要作者: {top_authors}
            
            请提供：
            1. 更新后的研究问题
            2. 更新的理由
            3. 下一步研究建议
            4. 基于作者的搜索关键词（从最相关文章的最后一位作者中提取）
            5. 基于引用网络的搜索策略
            
            以JSON格式返回：
            {{
                "updated_question": "更新后的研究问题",
                "update_reason": "更新理由",
                "next_steps": "下一步建议",
                "author_based_keywords": ["作者1姓名", "作者2姓名", "作者3姓名"],
                "citation_based_strategy": "基于引用网络的搜索策略描述"
            }}
            """
            
            response = client.chat.completions.create(
                model="deepseek-reasoner",
                messages=[
                    {"role": "system", "content": "You are a research strategy advisor with expertise in academic search optimization."},
                    {"role": "user", "content": update_prompt}
                ],
                temperature=0.3
            )
            
            result = response.choices[0].message.content
            
            # 解析更新结果
            try:
                json_match = re.search(r'(\{[\s\S]*\})', result)
                if json_match:
                    update_data = json.loads(json_match.group(1))
                    old_question = self.updated_question
                    self.updated_question = update_data.get("updated_question", self.updated_question)
                    
                    # 保存搜索策略信息
                    self.author_keywords = update_data.get("author_based_keywords", [])
                    self.citation_strategy = update_data.get("citation_based_strategy", "")
                    
                    if self.status_callback:
                        self.status_callback(f"研究问题已更新，新增作者关键词搜索策略")
                    
                    # 记录研究演进
                    self.workflow_data["research_evolution"].append({
                        "iteration": self.current_iteration,
                        "old_question": old_question,
                        "new_question": self.updated_question,
                        "reason": update_data.get("update_reason", ""),
                        "next_steps": update_data.get("next_steps", ""),
                        "author_keywords": self.author_keywords,
                        "citation_strategy": self.citation_strategy
                    })
            except json.JSONDecodeError:
                logger.warning("无法解析研究问题更新结果")
                
        except Exception as e:
            logger.error(f"更新研究问题出错: {str(e)}")
    
    def extract_top_authors_from_articles(self):
        """从高质量文章中提取主要作者信息"""
        try:
            authors_info = []
            for article in self.high_quality_articles[-10:]:  # 取最近的10篇高质量文章
                authors = article.get("authors", "")
                if authors and authors != "未知":
                    # 提取最后一位作者（通常是通讯作者）
                    author_list = [a.strip() for a in authors.split(';') if a.strip()]
                    if author_list:
                        last_author = author_list[-1]
                        # 清理作者名字，提取姓氏
                        if ',' in last_author:
                            surname = last_author.split(',')[0].strip()
                        else:
                            # 假设是 "First Last" 格式
                            parts = last_author.split()
                            surname = parts[-1] if parts else last_author
                        
                        authors_info.append({
                            "full_name": last_author,
                            "surname": surname,
                            "relevance_score": article.get("relevance_score", 0)
                        })
            
            # 按相关性评分排序，返回前5位作者
            authors_info.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
            return [author["surname"] for author in authors_info[:5]]
            
        except Exception as e:
            logger.error(f"提取作者信息出错: {str(e)}")
            return []
    
    def expand_citation_network(self, high_quality_articles):
        """扩展引用网络 - 使用真实的Crossref API和DeepSeek推理模式筛选"""
        citation_urls = []
        all_citation_data = []
        
        try:
            print("\n" + "="*80)
            print("🔗 引用网络扩展阶段")
            print("="*80)
            
            for article in high_quality_articles:
                doi = article.get("doi", "")
                if doi:
                    if self.status_callback:
                        self.status_callback(f"扩展DOI引用网络: {doi}")
                    
                    print(f"📖 正在扩展文章引用网络: {article.get('title', '未知标题')[:50]}...")
                    print(f"   DOI: {doi}")
                    
                    # 获取引用文献
                    references = query_crossref_references(doi, self.status_callback)
                    citations = query_crossref_citations(doi, self.status_callback)
                    
                    all_citation_data.extend(references + citations)
                    
                    print(f"   📚 找到引用文献: {len(references)} 篇")
                    print(f"   📝 找到被引文献: {len(citations)} 篇")
                    
                    # 保存引用网络数据
                    if references or citations:
                        self.save_citation_network(doi, references + citations)
            
            print(f"\n📊 引用网络扩展统计:")
            print(f"   总计发现文献: {len(all_citation_data)} 篇")
            
            # 使用DeepSeek推理模式进行智能筛选
            if all_citation_data:
                print(f"🧠 启动DeepSeek推理模式进行引用文献筛选...")
                filtered_citations = self.intelligent_citation_filtering(all_citation_data, high_quality_articles)
                
                # 收集筛选后的URL
                for citation in filtered_citations:
                    if citation.get('url'):
                        citation_urls.append(citation['url'])
                
                print(f"✅ 筛选完成: {len(all_citation_data)} → {len(filtered_citations)} 篇高质量引用文献")
                print(f"🔗 生成URL: {len(citation_urls)} 个")
            
            if self.status_callback:
                self.status_callback(f"引用网络扩展完成: 筛选出 {len(citation_urls)} 个高质量URL")
            
            return citation_urls
            
        except Exception as e:
            logger.error(f"引用网络扩展出错: {str(e)}")
            return []
    
    def save_citation_network(self, source_doi, citation_data):
        """保存引用网络数据"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_doi = source_doi.replace('/', '_').replace('.', '_')
            
            # 保存到CSV (保存到temp_analysis目录)
            csv_file = os.path.join(self.project_dir, "temp_analysis", f"citation_network_{safe_doi}_{timestamp}.csv")
            os.makedirs(os.path.dirname(csv_file), exist_ok=True)
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['DOI', 'Title', 'Authors', 'Year', 'URL', 'Relation', 'Source_DOI'])
                
                for item in citation_data:
                    writer.writerow([
                        item.get('doi', ''),
                        item.get('title', ''),
                        item.get('authors', ''),
                        item.get('year', ''),
                        item.get('url', ''),
                        item.get('relation', ''),
                        source_doi
                    ])
            
            logger.info(f"引用网络数据已保存: {csv_file}")
            
        except Exception as e:
            logger.error(f"保存引用网络数据出错: {str(e)}")
    
    def check_stop_condition(self):
        """检查停止条件"""
        current_count = len(self.high_quality_articles)
        
        if current_count >= self.target_article_count:
            if self.status_callback:
                self.status_callback(f"已达到目标文章数量 {current_count}/{self.target_article_count}")
            return True
        
        if self.current_iteration >= self.max_iterations:
            if self.status_callback:
                self.status_callback(f"已达到最大迭代次数 {self.current_iteration}/{self.max_iterations}")
            return True
        
        return False
    
    def update_research_strategy(self):
        """更新研究策略"""
        current_count = len(self.high_quality_articles)
        
        if current_count < self.target_article_count * 0.3:
            if self.status_callback:
                self.status_callback("高质量文章较少，调整搜索策略以扩大范围...")
        elif current_count > self.target_article_count * 0.8:
            if self.status_callback:
                self.status_callback("接近目标数量，提高质量筛选标准...")
    
    def save_iteration_result(self, iteration_data):
        """保存迭代结果"""
        try:
            iteration_file = os.path.join(
                self.project_dir, 
                "iterations", 
                f"iteration_{self.current_iteration}.json"
            )
            
            with open(iteration_file, 'w', encoding='utf-8') as f:
                json.dump(iteration_data, f, ensure_ascii=False, indent=2)
            
            # 更新总体工作流数据
            self.workflow_data["iterations"].append(iteration_data)
            self.workflow_data["total_articles_found"] = len(self.high_quality_articles)
            
            logger.info(f"第{self.current_iteration}轮迭代结果已保存")
            
        except Exception as e:
            logger.error(f"保存迭代结果出错: {str(e)}")
    
    def generate_final_report(self):
        """生成最终研究报告"""
        try:
            report_data = {
                "project_summary": {
                    "original_question": self.research_question,
                    "final_question": self.updated_question,
                    "total_iterations": self.current_iteration,
                    "total_high_quality_articles": len(self.high_quality_articles),
                    "target_achieved": len(self.high_quality_articles) >= self.target_article_count
                },
                "workflow_data": self.workflow_data,
                "high_quality_articles": self.high_quality_articles,
                "generated_at": datetime.datetime.now().isoformat()
            }
            
            # 保存JSON报告 (保存到temp_analysis目录)
            report_file = os.path.join(self.project_dir, "temp_analysis", "final_report.json")
            os.makedirs(os.path.dirname(report_file), exist_ok=True)
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            
            # 生成HTML报告
            self.generate_html_report(report_data)
            
            if self.status_callback:
                self.status_callback(f"最终报告已生成: {report_file}")
            
        except Exception as e:
            logger.error(f"生成最终报告出错: {str(e)}")
    
    def generate_html_report(self, report_data):
        """生成HTML格式的最终报告"""
        try:
            html_content = f"""
            <!DOCTYPE html>
            <html lang="zh-CN">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>增强版闭环研究工作流报告</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
                    .header {{ background: #f4f4f4; padding: 20px; border-radius: 5px; }}
                    .section {{ margin: 20px 0; padding: 15px; border-left: 4px solid #007bff; }}
                    .iteration {{ background: #f9f9f9; margin: 10px 0; padding: 10px; border-radius: 3px; }}
                    .article {{ background: #e9ecef; margin: 5px 0; padding: 8px; border-radius: 3px; }}
                    .score {{ font-weight: bold; color: #28a745; }}
                    table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    .evolution {{ background: #fff3cd; padding: 10px; margin: 5px 0; border-radius: 3px; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>增强版闭环科学研究工作流报告</h1>
                    <p><strong>生成时间:</strong> {report_data['generated_at']}</p>
                    <p><strong>原始研究问题:</strong> {report_data['project_summary']['original_question']}</p>
                    <p><strong>最终研究问题:</strong> {report_data['project_summary']['final_question']}</p>
                </div>
                
                <div class="section">
                    <h2>项目概览</h2>
                    <table>
                        <tr><th>指标</th><th>值</th></tr>
                        <tr><td>总迭代次数</td><td>{report_data['project_summary']['total_iterations']}</td></tr>
                        <tr><td>高质量文章数量</td><td>{report_data['project_summary']['total_high_quality_articles']}</td></tr>
                        <tr><td>目标是否达成</td><td>{'是' if report_data['project_summary']['target_achieved'] else '否'}</td></tr>
                    </table>
                </div>
                
                <div class="section">
                    <h2>研究问题演进</h2>
            """
            
            # 添加研究演进
            for evolution in report_data['workflow_data']['research_evolution']:
                html_content += f"""
                <div class="evolution">
                    <h4>第 {evolution['iteration']} 轮迭代</h4>
                    <p><strong>原问题:</strong> {evolution['old_question']}</p>
                    <p><strong>新问题:</strong> {evolution['new_question']}</p>
                    <p><strong>更新理由:</strong> {evolution['reason']}</p>
                    <p><strong>下一步建议:</strong> {evolution['next_steps']}</p>
                </div>
                """
            
            # 添加迭代详情
            html_content += """
                </div>
                
                <div class="section">
                    <h2>迭代过程</h2>
            """
            
            for iteration in report_data['workflow_data']['iterations']:
                html_content += f"""
                <div class="iteration">
                    <h3>第 {iteration['iteration']} 轮迭代</h3>
                    <p><strong>时间:</strong> {iteration['timestamp']}</p>
                    <p><strong>研究问题:</strong> {iteration['research_question']}</p>
                    <p><strong>搜索结果:</strong> {len(iteration.get('search_results', []))} 个</p>
                    <p><strong>分析结果:</strong> {len(iteration.get('analysis_results', []))} 个</p>
                    <p><strong>高质量文章:</strong> {iteration.get('high_quality_count', 0)} 篇</p>
                    <p><strong>引用扩展:</strong> {len(iteration.get('citation_expansion', []))} 个URL</p>
                </div>
                """
            
            # 添加高质量文章列表
            html_content += """
                </div>
                
                <div class="section">
                    <h2>高质量文章列表</h2>
            """
            
            for i, article in enumerate(report_data['high_quality_articles'][:30]):  # 限制显示数量
                score = article.get('relevance_score', 0)
                html_content += f"""
                <div class="article">
                    <h4>{i+1}. {article.get('title', '未知标题')}</h4>
                    <p><strong>作者:</strong> {article.get('authors', '未知')}</p>
                    <p><strong>年份:</strong> {article.get('publication_year', '未知')}</p>
                    <p><strong>DOI:</strong> {article.get('doi', '未知')}</p>
                    <p><strong>相关性评分:</strong> <span class="score">{score}/10</span></p>
                    <p><strong>研究焦点:</strong> {article.get('research_focus', '未知')}</p>
                    <p><strong>主要贡献:</strong> {article.get('major_contributions', '未知')}</p>
                </div>
                """
            
            html_content += """
                </div>
            </body>
            </html>
            """
            
            # 保存HTML报告 (保存到temp_analysis目录)
            html_file = os.path.join(self.project_dir, "temp_analysis", "final_report.html")
            os.makedirs(os.path.dirname(html_file), exist_ok=True)
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"HTML报告已生成: {html_file}")
            
        except Exception as e:
            logger.error(f"生成HTML报告出错: {str(e)}")
    
    def print_closed_loop_sources(self):
        """打印闭环研究线索来源总结"""
        print("\n" + "="*80)
        print("🔄 第一轮分析完毕后，系统通过以下三个主要途径获得下一轮研究线索：")
        print("="*80)
        
        print("📍 途径1: 深度思考分析 → 研究问题更新")
        print("   🧠 对高质量文章进行深度思考分析")
        print("   🔄 基于分析结果更新研究问题")
        print("   👥 提取作者关键词用于搜索策略")
        print("   📋 制定引用网络搜索策略")
        
        if hasattr(self, 'updated_question') and self.updated_question != self.research_question:
            print(f"   ✅ 当前更新的研究问题: {self.updated_question[:100]}...")
        
        if hasattr(self, 'author_keywords') and self.author_keywords:
            print(f"   ✅ 提取的作者关键词: {', '.join(self.author_keywords[:5])}")
        
        print("\n📍 途径2: 引用网络扩展")
        print("   🔗 从高质量文章的DOI查询Crossref API")
        print("   📚 获取'它引用了谁'（references）")
        print("   📝 获取'谁引用了它'（citations）")
        print("   🧠 使用DeepSeek推理模式智能筛选引用文献")
        
        if hasattr(self, 'previous_citation_urls') and self.previous_citation_urls:
            print(f"   ✅ 上一轮筛选出的引用URL数量: {len(self.previous_citation_urls)}")
        
        print("\n📍 途径3: 作者网络搜索")
        print("   👤 基于高质量文章的作者信息")
        print("   🔍 生成作者相关的搜索查询")
        print("   📖 查找同一作者的其他相关研究")
        
        print("\n🎯 下一轮搜索策略:")
        print("   1️⃣ 使用更新后的研究问题进行搜索")
        print("   2️⃣ 添加基于作者关键词的搜索查询")
        print("   3️⃣ 直接分析引用网络扩展的URL")
        print("   4️⃣ 结合多种策略形成综合搜索结果")
        
        print("\n💡 闭环优势:")
        print("   🔄 每轮迭代都基于前一轮的高质量发现")
        print("   🎯 研究问题不断精炼和聚焦")
        print("   🌐 引用网络确保学术脉络的完整性")
        print("   👥 作者网络挖掘权威研究团队")
        
        print("="*80)
    
    def intelligent_citation_filtering(self, all_citation_data, high_quality_articles, target_count=15):
        """
        使用DeepSeek推理模式智能筛选引用文献 - 优化版本
        
        参数:
            all_citation_data: 所有引用数据列表
            high_quality_articles: 高质量文章列表
            target_count: 目标筛选数量（从面板传递）
            
        返回:
            筛选后的引用文献列表
        """
        try:
            print(f"\n🧠 开始DeepSeek推理模式智能筛选")
            print(f"   📊 输入数据统计:")
            print(f"      - 待筛选引用文献: {len(all_citation_data)} 篇")
            print(f"      - 参考高质量文章: {len(high_quality_articles)} 篇")
            print(f"      - 目标筛选数量: {target_count}")
            
            if not all_citation_data:
                print(f"   ❌ 没有待筛选的引用文献")
                return []
            
            # 扩大处理数量限制，充分利用60k token
            max_citations = 200  # 增加到200篇
            if len(all_citation_data) > max_citations:
                print(f"   📏 数据量过大，进行预筛选: {len(all_citation_data)} → {max_citations}")
                
                # 优先选择有DOI的文献
                with_doi = [item for item in all_citation_data if item.get('doi')]
                without_doi = [item for item in all_citation_data if not item.get('doi')]
                
                # 按年份排序，优先选择较新的文献
                with_doi.sort(key=lambda x: self._parse_year(x.get('year', '0')), reverse=True)
                without_doi.sort(key=lambda x: self._parse_year(x.get('year', '0')), reverse=True)
                
                # 选择前150个有DOI的和前50个无DOI的
                selected_citations = with_doi[:150] + without_doi[:50]
                print(f"      - 有DOI文献: {len(with_doi)} → {min(150, len(with_doi))}")
                print(f"      - 无DOI文献: {len(without_doi)} → {min(50, len(without_doi))}")
            else:
                selected_citations = all_citation_data
                print(f"   ✅ 数据量适中，直接处理全部 {len(selected_citations)} 篇")
            
            if not selected_citations:
                print(f"   ❌ 预筛选后没有可用文献")
                return []
            
            # 构建更详细的研究上下文 - 直接合并完整文章内容
            print(f"   📖 构建研究上下文...")
            research_context = []
            for i, article in enumerate(high_quality_articles[:10]):  # 增加到前10篇
                # 直接使用完整的文章数据，避免字段名依赖问题
                context_item = {}
                
                # 复制所有字段，但限制长度以控制token使用
                for key, value in article.items():
                    if isinstance(value, str):
                        # 对字符串字段进行长度限制
                        if key in ['title']:
                            context_item[key] = value[:200]  # 标题稍长一些
                        elif key in ['authors', 'journal']:
                            context_item[key] = value[:100]  # 作者和期刊中等长度
                        elif key in ['research_focus', 'key_methods', 'major_contributions', 'challenges']:
                            context_item[key] = value[:]  # 重要内容字段更长
                        else:
                            context_item[key] = value[:]  # 其他字段默认长度
                    else:
                        # 非字符串字段直接复制
                        context_item[key] = value
                
                research_context.append(context_item)
                title = context_item.get('title', '未知标题')
                score = context_item.get('relevance_score', 0)
                print(f"      [{i+1}] {title[:60]}... (评分: {score})")
            
            # 构建更详细的引用文献信息
            print(f"   📋 构建引用文献信息...")
            citations_summary = []
            for i, citation in enumerate(selected_citations):
                citation_item = {
                    "index": i,
                    "title": citation.get("title", "")[:200],  # 增加标题长度
                    "authors": citation.get("authors", "")[:100],
                    "year": citation.get("year", ""),
                    "doi": citation.get("doi", ""),
                    "relation": citation.get("relation", ""),
                    "url": citation.get("url", "")[:100] if citation.get("url") else ""
                }
                citations_summary.append(citation_item)
            
            print(f"      - 构建完成: {len(citations_summary)} 篇引用文献信息")
            
            # 构建优化的筛选prompt
            filter_prompt = f"""
            你是一位专业的学术研究分析师，专门从事引用网络分析。请基于提供的高质量研究文章上下文，从引用网络中筛选出最相关的文献。

            ## 研究上下文（已确认的高质量文章）:
            {json.dumps(research_context, ensure_ascii=False, indent=2)}

            ## 待筛选的引用文献（共{len(citations_summary)}篇）:
            {json.dumps(citations_summary, ensure_ascii=False, indent=2)}

            ## 筛选任务要求:
            请从上述{len(citations_summary)}篇引用文献中筛选出最相关的{target_count}篇文献。

            ## 筛选标准（按重要性排序）:
            1. **主题相关性**: 与研究上下文中的高质量文章主题高度相关
            2. **学者**: 具有和高质量文章中相同的作者
            3. **时效性**: 优先选择较新的文献（2018年后）
            4. **引用关系**: 考虑引用关系的类型和重要性


            ## 深度推理要求:
            请进行深度推理分析，考虑以下方面：
            - 分析每篇候选文献与研究上下文的关联度
            - 评估文献的学术价值和创新性
            - 考虑文献间的互补性和多样性
            - 权衡时效性与经典性的平衡

            ## 输出格式:
            请返回JSON格式的筛选结果：
            {{
                "selected_indices": [索引列表，共{target_count}个],
                "selection_reasoning": "详细的筛选推理过程和理由",
                "quality_assessment": "对筛选结果质量的评估",
                "coverage_analysis": "筛选结果的覆盖面分析"
            }}

            请确保选择的索引在0到{len(citations_summary)-1}范围内，且总数为{target_count}篇。
            """
            
            print(f"   🤖 调用DeepSeek-Reasoner模型进行智能筛选...")
            print(f"      - 模型: deepseek-reasoner")
            print(f"      - Max tokens: 60000")
            print(f"      - Temperature: 0.1")
            
            client = OpenAI(api_key=self.api_key, base_url="https://api.deepseek.com")
            
            # 只使用reasoner模型，不降级
            response = client.chat.completions.create(
                model="deepseek-reasoner",
                messages=[
                    {"role": "system", "content": "You are an expert research analyst with deep reasoning capabilities, specializing in citation network analysis and academic literature evaluation."},
                    {"role": "user", "content": filter_prompt}
                ],
                temperature=0.1,  # 降低温度以提高一致性
                max_tokens=60000  # 设置为60k
            )
            
            result = response.choices[0].message.content
            print(f"   ✅ DeepSeek-Reasoner响应完成")
            print(f"      - 响应长度: {len(result)} 字符")
            
            # 解析筛选结果
            print(f"   🔍 解析筛选结果...")
            try:
                json_match = re.search(r'(\{[\s\S]*\})', result)
                if json_match:
                    filter_data = json.loads(json_match.group(1))
                    selected_indices = filter_data.get("selected_indices", [])
                    reasoning = filter_data.get("selection_reasoning", "AI深度推理筛选")
                    quality_assessment = filter_data.get("quality_assessment", "")
                    coverage_analysis = filter_data.get("coverage_analysis", "")
                    
                    print(f"   📊 筛选结果解析成功:")
                    print(f"      - 选中索引数量: {len(selected_indices)}")
                    print(f"      - 目标数量: {target_count}")
                    print(f"      - 推理过程: {reasoning[:100]}...")
                    
                    # 根据索引筛选文献
                    filtered_citations = []
                    valid_indices = []
                    for idx in selected_indices:
                        if isinstance(idx, int) and 0 <= idx < len(selected_citations):
                            filtered_citations.append(selected_citations[idx])
                            valid_indices.append(idx)
                        else:
                            print(f"      ⚠️ 无效索引: {idx}")
                    
                    print(f"   ✅ 智能筛选完成:")
                    print(f"      - 有效索引: {len(valid_indices)}")
                    print(f"      - 筛选出文献: {len(filtered_citations)} 篇")
                    print(f"      - 筛选理由: {reasoning[:200]}...")
                    
                    if quality_assessment:
                        print(f"      - 质量评估: {quality_assessment[:150]}...")
                    if coverage_analysis:
                        print(f"      - 覆盖分析: {coverage_analysis[:150]}...")
                    
                    # 显示筛选结果预览
                    print(f"   📋 筛选结果预览:")
                    for i, citation in enumerate(filtered_citations[:5]):
                        print(f"      [{i+1}] {citation.get('title', '未知标题')[:60]}...")
                        print(f"          年份: {citation.get('year', '未知')} | 关系: {citation.get('relation', '未知')}")
                    
                    if len(filtered_citations) > 5:
                        print(f"      ... 还有 {len(filtered_citations) - 5} 篇文献")
                    
                    return filtered_citations
                else:
                    print("   ❌ 无法解析JSON格式，使用备用筛选策略")
                    return self._fallback_filtering(selected_citations, target_count)
                    
            except json.JSONDecodeError as e:
                print(f"   ❌ JSON解析失败: {str(e)}")
                print("   🔄 使用备用筛选策略")
                return self._fallback_filtering(selected_citations, target_count)
                
        except Exception as e:
            print(f"   ❌ 智能引用筛选出错: {str(e)}")
            logger.error(f"智能引用筛选出错: {str(e)}")
            import traceback
            traceback.print_exc()
            # 失败时返回简单筛选结果
            return self._fallback_filtering(all_citation_data, target_count) if all_citation_data else []
    
    def _parse_year(self, year_str):
        """解析年份字符串为整数"""
        try:
            if isinstance(year_str, (int, float)):
                return int(year_str)
            if isinstance(year_str, str):
                # 提取年份数字
                year_match = re.search(r'\d{4}', str(year_str))
                if year_match:
                    return int(year_match.group())
            return 0
        except:
            return 0
    
    def _fallback_filtering(self, citations, target_count):
        """备用筛选策略：基于年份和DOI的简单筛选"""
        print(f"   🔄 执行备用筛选策略")
        
        # 按年份和是否有DOI排序
        def sort_key(citation):
            year = self._parse_year(citation.get('year', '0'))
            has_doi = 1 if citation.get('doi') else 0
            return (has_doi, year)
        
        sorted_citations = sorted(citations, key=sort_key, reverse=True)
        result = sorted_citations[:target_count]
        
        print(f"      - 备用筛选完成: {len(citations)} → {len(result)} 篇")
        return result
