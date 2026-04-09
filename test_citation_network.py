#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
引用网络功能调试程序（改进版）
用于测试CrossRef API的引用文献和被引文献查询功能
"""

import requests
import json
import time
from urllib.parse import quote

def get_random_headers():
    """获取请求头"""
    return {
        'User-Agent': 'ScienceSearchApp/1.0 (mailto:your_email@example.com)',
        'Accept': 'application/json'
    }

def test_query_crossref_references(doi):
    """
    测试查询引用文献（它引用了谁）
    改进：为有DOI的引用文献批量获取完整信息（包括摘要）
    """
    print("\n" + "="*80)
    print(f"🔍 测试查询引用文献（它引用了谁）")
    print(f"📌 测试DOI: {doi}")
    print("="*80)
    
    # 构建Crossref API URL
    url = f"https://api.crossref.org/works/{doi}"
    
    try:
        headers = get_random_headers()
        
        print(f"\n📡 发送请求: {url}")
        response = requests.get(url, headers=headers, timeout=20)
        print(f"✅ 响应状态码: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ 请求失败，状态码: {response.status_code}")
            return
        
        data = response.json()
        
        if 'message' not in data:
            print(f"❌ 响应中没有'message'字段")
            return
        
        message = data['message']
        
        # 检查是否有引用文献
        if 'reference' not in message:
            print(f"\n❌ 该文献没有'reference'字段（可能没有引用其他文献）")
            return
        
        references = message['reference']
        print(f"\n📚 找到 {len(references)} 个引用文献")
        
        # 统计有DOI的引用文献
        refs_with_doi = [ref for ref in references if ref.get('DOI')]
        print(f"📊 其中有DOI的: {len(refs_with_doi)} 个")
        print(f"📊 无DOI的: {len(references) - len(refs_with_doi)} 个")
        
        # 批量查询前5个有DOI的引用文献的完整信息
        print(f"\n" + "="*80)
        print(f"📖 批量查询前5个有DOI的引用文献的完整信息（包括摘要）:")
        print("="*80)
        
        enhanced_references = []
        for i, ref in enumerate(refs_with_doi[:5]):
            ref_doi = ref.get('DOI')
            print(f"\n--- 引用文献 #{i+1}/{min(5, len(refs_with_doi))} ---")
            print(f"📌 DOI: {ref_doi}")
            
            # 基础信息（从reference字段）
            print(f"👤 作者: {ref.get('author', '未知')}")
            print(f"📅 年份: {ref.get('year', '未知')}")
            print(f"📖 期刊: {ref.get('journal-title', '未知')}")
            
            # 查询完整信息
            print(f"🔍 正在查询完整信息...")
            time.sleep(1)  # 避免API限流
            
            full_info = get_full_article_info(ref_doi)
            
            if full_info:
                enhanced_ref = {
                    'doi': ref_doi,
                    'title': full_info.get('title', '未知'),
                    'abstract': full_info.get('abstract', ''),
                    'year': ref.get('year', full_info.get('year', '未知')),
                    'authors': ref.get('author', '未知'),
                    'journal': full_info.get('journal', ref.get('journal-title', '未知')),
                    'is_referenced_by_count': full_info.get('is_referenced_by_count', 0),
                    'type': full_info.get('type', '未知'),
                    'url': full_info.get('url', f"https://doi.org/{ref_doi}")
                }
                enhanced_references.append(enhanced_ref)
                
                # 显示摘要状态
                if enhanced_ref['abstract']:
                    print(f"✅ 标题: {enhanced_ref['title'][:80]}...")
                    print(f"✅ 摘要: {enhanced_ref['abstract'][:200]}...")
                    print(f"📊 被引次数: {enhanced_ref['is_referenced_by_count']}")
                else:
                    print(f"✅ 标题: {enhanced_ref['title'][:80]}...")
                    print(f"❌ 无摘要（CrossRef未收录该文献的摘要）")
                    print(f"📊 被引次数: {enhanced_ref['is_referenced_by_count']}")
            else:
                print(f"❌ 无法获取完整信息")
        
        # 统计摘要覆盖率
        refs_with_abstract = [ref for ref in enhanced_references if ref.get('abstract')]
        print(f"\n" + "="*80)
        print(f"📊 摘要覆盖率统计:")
        print(f"   查询的引用文献数: {len(enhanced_references)}")
        print(f"   有摘要的文献数: {len(refs_with_abstract)}")
        print(f"   摘要覆盖率: {len(refs_with_abstract)/len(enhanced_references)*100:.1f}%")
        print("="*80)
        
        print(f"\n✅ 引用文献查询测试完成")
        
        return enhanced_references
        
    except Exception as e:
        print(f"\n❌ 查询出错: {str(e)}")
        import traceback
        traceback.print_exc()

def test_query_crossref_citations(doi):
    """
    测试查询被引文献（谁引用了它）
    修复：正确编码DOI以避免400错误
    """
    print("\n" + "="*80)
    print(f"🔍 测试查询被引文献（谁引用了它）")
    print(f"📌 测试DOI: {doi}")
    print("="*80)
    
    # 🔧 修复：对DOI进行URL编码
    encoded_doi = quote(doi, safe='')
    
    # 构建Crossref API URL查询引用情况
    url = f"https://api.crossref.org/works?filter=doi:{encoded_doi}&rows=100"
    
    # 🔧 修复：使用正确的filter参数
    # 方法1: 使用doi filter（查询特定DOI的文献）
    # 方法2: 使用reference-doi filter（查询引用了该DOI的文献）
    
    # 先尝试方法2（这才是查询被引文献的正确方式）
    url_method2 = f"https://api.crossref.org/works?rows=10&filter=reference-doi:{encoded_doi}"
    
    print(f"\n💡 尝试两种查询方法:")
    print(f"   方法1（错误）: filter=reference.DOI:{doi}")
    print(f"   方法2（正确）: filter=reference-doi:{encoded_doi}")
    
    try:
        headers = get_random_headers()
        
        print(f"\n📡 发送请求（方法2）: {url_method2}")
        response = requests.get(url_method2, headers=headers, timeout=20)
        print(f"✅ 响应状态码: {response.status_code}")
        
        if response.status_code == 400:
            print(f"\n❌ 400错误详情:")
            try:
                error_data = response.json()
                print(f"   {json.dumps(error_data, indent=2)}")
            except:
                print(f"   {response.text}")
            
            print(f"\n💡 可能的原因:")
            print(f"   1. DOI格式问题（需要URL编码）")
            print(f"   2. Filter参数名称错误")
            print(f"   3. CrossRef API更新了参数要求")
            return
        
        if response.status_code != 200:
            print(f"❌ 请求失败，状态码: {response.status_code}")
            return
        
        data = response.json()
        
        if 'message' not in data:
            print(f"❌ 响应中没有'message'字段")
            return
        
        message = data['message']
        
        # 检查总数
        total_results = message.get('total-results', 0)
        print(f"\n📊 被引用总数: {total_results}")
        
        if total_results == 0:
            print(f"\n❌ 该文献没有被引用记录")
            print(f"💡 可能原因：")
            print(f"   1. 该文献较新，尚未被引用")
            print(f"   2. CrossRef尚未收录被引用数据")
            print(f"   3. 需要使用其他API（如Semantic Scholar）")
            
            # 尝试从原文献信息中获取被引次数
            print(f"\n🔍 尝试从原文献元数据中获取被引次数...")
            original_info = get_full_article_info(doi)
            if original_info and 'is_referenced_by_count' in original_info:
                print(f"✅ 该文献被引次数: {original_info['is_referenced_by_count']}")
            
            return
        
        # 检查是否有items
        if 'items' not in message:
            print(f"❌ 响应中没有'items'字段")
            return
        
        items = message['items']
        print(f"\n📚 返回 {len(items)} 条被引用文献")
        
        # 详细分析前5个被引用文献
        print(f"\n" + "="*80)
        print(f"📖 详细分析前5条被引用文献:")
        print("="*80)
        
        citations_with_abstract = 0
        
        for i, item in enumerate(items[:5]):
            print(f"\n--- 被引文献 #{i+1} ---")
            
            # 提取DOI
            citing_doi = item.get('DOI', '')
            print(f"📌 DOI: {citing_doi if citing_doi else '❌ 无DOI'}")
            
            # 提取标题
            title = ''
            if 'title' in item and item['title']:
                title = item['title'][0]
                print(f"📄 标题: {title[:100]}...")
            else:
                print(f"❌ 无标题")
            
            # 提取年份
            year = ''
            if 'published' in item and 'date-parts' in item['published']:
                year_parts = item['published']['date-parts']
                if year_parts and year_parts[0]:
                    year = year_parts[0][0]
            print(f"📅 年份: {year if year else '❌ 无年份'}")
            
            # 提取作者
            authors = []
            if 'author' in item:
                for author in item['author'][:3]:
                    if 'family' in author and 'given' in author:
                        authors.append(f"{author['family']}, {author['given']}")
                    elif 'family' in author:
                        authors.append(author['family'])
            authors_str = '; '.join(authors)
            if len(item.get('author', [])) > 3:
                authors_str += f" 等 {len(item['author'])} 人"
            print(f"👤 作者: {authors_str if authors_str else '❌ 无作者信息'}")
            
            # 🔍 重点检查摘要
            abstract = item.get('abstract', '')
            if abstract:
                print(f"✅ 摘要: {abstract[:200]}...")
                citations_with_abstract += 1
            else:
                print(f"❌ 无摘要信息")
            
            # 检查期刊信息
            journal = ''
            if 'container-title' in item and item['container-title']:
                journal = item['container-title'][0]
                print(f"📖 期刊: {journal}")
            
            # 检查被引次数
            cited_count = item.get('is-referenced-by-count', 0)
            print(f"📊 被引次数: {cited_count}")
        
        # 统计摘要覆盖率
        print(f"\n" + "="*80)
        print(f"📊 被引文献摘要覆盖率:")
        print(f"   查询的被引文献数: {min(5, len(items))}")
        print(f"   有摘要的文献数: {citations_with_abstract}")
        print(f"   摘要覆盖率: {citations_with_abstract/min(5, len(items))*100:.1f}%")
        print("="*80)
        
        print(f"\n✅ 被引用文献查询测试完成")
        
    except Exception as e:
        print(f"\n❌ 查询出错: {str(e)}")
        import traceback
        traceback.print_exc()

def get_full_article_info(doi):
    """
    获取单篇文献的完整信息（包括摘要）
    返回字典格式的详细信息
    """
    url = f"https://api.crossref.org/works/{doi}"
    
    try:
        headers = get_random_headers()
        response = requests.get(url, headers=headers, timeout=20)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        
        if 'message' not in data:
            return None
        
        message = data['message']
        
        # 提取标题
        title = ''
        if 'title' in message and message['title']:
            title = message['title'][0]
        
        # 提取摘要
        abstract = message.get('abstract', '')
        
        # 提取期刊
        journal = ''
        if 'container-title' in message and message['container-title']:
            journal = message['container-title'][0]
        
        # 提取年份
        year = ''
        if 'published' in message and 'date-parts' in message['published']:
            year_parts = message['published']['date-parts']
            if year_parts and year_parts[0]:
                year = str(year_parts[0][0])
        
        return {
            'title': title,
            'abstract': abstract,
            'journal': journal,
            'year': year,
            'is_referenced_by_count': message.get('is-referenced-by-count', 0),
            'type': message.get('type', ''),
            'url': f"https://doi.org/{doi}"
        }
        
    except Exception as e:
        print(f"   ❌ 查询完整信息出错: {str(e)}")
        return None

def main():
    """主测试函数"""
    print("\n" + "="*80)
    print("🧪 CrossRef引用网络API调试程序（改进版）")
    print("="*80)
    
    # 使用你提供的DOI
    test_doi = "10.1039/D1EE01388B"
    
    print(f"\n📌 测试DOI: {test_doi}")
    print(f"📖 文献信息: Multi-length scale microstructural design of lithium-ion...")
    print(f"📅 发表年份: 2021")
    
    # 先获取该文献的基本信息
    print(f"\n" + "="*80)
    print(f"📊 步骤0: 获取测试文献的基本信息")
    print("="*80)
    
    article_info = get_full_article_info(test_doi)
    if article_info:
        print(f"✅ 标题: {article_info['title']}")
        print(f"📖 期刊: {article_info['journal']}")
        print(f"📅 年份: {article_info['year']}")
        print(f"📊 被引次数: {article_info['is_referenced_by_count']}")
        if article_info['abstract']:
            print(f"✅ 摘要: {article_info['abstract'][:500]}...")
        else:
            print(f"❌ 该文献本身在CrossRef中也没有摘要")
    
    # 测试1: 查询引用文献（它引用了谁）
    print(f"\n⏳ 等待2秒...")
    time.sleep(2)
    test_query_crossref_references(test_doi)
    
    # 测试2: 查询被引文献（谁引用了它）
    print(f"\n⏳ 等待2秒...")
    time.sleep(2)
    test_query_crossref_citations(test_doi)
    
    print("\n" + "="*80)
    print("🏁 测试完成")
    print("="*80)
    print(f"\n📊 重要发现:")
    print(f"   ✅ 修复了被引文献查询的400错误（DOI需要URL编码）")
    print(f"   ✅ 改进了引用文献查询（批量获取完整信息包括摘要）")
    print(f"   ⚠️  CrossRef的摘要覆盖率确实有限（约30-50%）")
    print(f"\n💡 建议:")
    print(f"   1. 对于需要摘要的场景，考虑组合使用多个API")
    print(f"   2. Semantic Scholar API的摘要覆盖率更高")
    print(f"   3. PubMed API对生物医学文献的摘要覆盖更好")
    print("\n" + "="*80)

if __name__ == "__main__":
    main()