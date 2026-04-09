#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高质量文章分析工具
从已完成的分析日志中筛选高质量文章，进行深度思考分析并生成报告

使用方法：
1. 修改下方的配置参数
2. 在VSCode中直接运行此脚本
"""

import os
import json
import csv
import re
import datetime
from openai import OpenAI
import pandas as pd

# ================================
# 配置参数 - 请在这里修改您的设置
# ================================

# 日志文件夹路径
LOGS_FOLDER_PATH = r"C:\Users\YumingSu\3\logs"

# 相关性评分阈值（8或9分）
RELEVANCE_THRESHOLD = 8

# DeepSeek API配置
API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

# 深度思考模型的多种分析prompt
RESEARCH_FLOW_PROMPT = """分析以下学术文献集合数据，提供一份全面详尽的研究脉络分析报告。请依次执行以下步骤，每个步骤至少给出5点内容，每一个体积的文献要提供doi或者链接跳转：

第一步：文献概述分析
- 首先分析所有文献的基本信息，包括发表年份分布、主要期刊分布、主要研究机构和研究团队
- 识别最频繁出现的关键词和主题
- 统计不同评分段的文献分布情况
- 分析文献的地理分布和国际合作模式
- 评估文献集合的整体质量和代表性

第二步：时间演化分析
- 绘制研究主题随时间的发展路径图
- 识别研究领域中的关键突破点和范式转换
- 分析最新研究趋势和预测未来可能的发展方向
- 追踪高影响因子研究的出现时间点
- 分析研究热点的周期性变化和持续性

第三步：学术谱系分析
- 识别主要研究团队、学派及其相互关系
- 识别该研究领域的创始性工作和开创性研究
- 分析早期概念框架和理论基础的建立
- 描述关键技术突破和方法论创新
- 评估早期研究的局限性和历史背景
- 分析早期研究对后续发展的奠基作用

第四步：方法论演进分析
- 追踪主要研究方法的演变历程
- 识别新技术和新方法的引入时间点及其影响
- 评估当前主流方法的优势、局限性和适用场景
- 分析方法学争议和技术路线选择
- 预测可能改变研究范式的新兴方法

第五步：知识地图构建
- 构建核心概念及其关系网络
- 划分研究领域的主要分支和识别交叉研究点
- 区分存在争议的领域和已达成共识的领域
- 分析知识创新的路径和传播机制
- 识别理论空白和潜在的突破点

第六步：研究挑战与机会分析
- 总结当前未解决的关键问题
- 分析技术或理论瓶颈所在
- 提出潜在的研究机会和创新点
- 评估产业化前景和应用价值
- 识别跨学科融合的可能性

第七步：影响因子与质量评估
- 分析高相关性文献（8分以上）的共同特征
- 评估不同研究方法的成果质量
- 分析期刊影响因子与研究质量的关系
- 识别被低估的潜在高价值研究
- 预测可能产生重大影响的研究方向

第八步：定量统计与证据支持
- 提供可靠的定量统计数据支持以上分析
- 包括研究方法分布、主题分布、引用模式等
- 使用具体的文献引用作为证据支持观点
- 分析数据的可信度和潜在偏差
- 提供统计图表和可视化分析

最后，请总结这一研究领域的整体发展状态，并预测未来3-5年可能的发展方向和突破点。你的分析需要客观、全面、有深度，并充分利用给定的数据。输出html格式(不要包含图片格式)供我观看。

分析的文献集合JSON数据，"relevance_score"大于8分的要特别关注：
{JSON_DATA}"""

TIMELINE_ANALYSIS_PROMPT = """基于以下学术文献数据，创建一份详尽的时间线分析报告，重点关注研究领域随时间的演变。请按照如下结构组织你的分析，每个结构至少给出5点内容：

1. 起源与基础 (Pioneer Phase)
- 识别该研究领域的创始性工作和开创性研究
- 分析早期概念框架和理论基础的建立
- 描述关键技术突破和方法论创新
- 评估早期研究的局限性和历史背景
- 分析早期研究对后续发展的奠基作用

2. 关键时期与转折点分析
- 识别并详细分析研究领域中的重大转折点
- 对每个转折点，分析促成变革的技术、理论或社会因素
- 评估转折点对后续研究方向的影响程度
- 分析转折点的标志性事件和关键人物
- 评估转折点的深远影响和持续效应

3. 时间分段分析（按年代或技术代际）
- 将研究发展分为清晰的时期，每个时期的主要特征
- 每个时期的代表性成果、主导团队和核心方法
- 时期之间的比较，展示研究重点的迁移
- 分析各时期的技术成熟度和应用水平
- 评估时期划分的合理性和内在逻辑

4. 方法与技术演进时间线
- 呈现主要研究方法、技术和工具的出现时间线
- 分析技术进步如何解锁新的研究可能性
- 评估不同方法在各时期的流行度变化
- 追踪技术标准化和规范化的过程
- 预测技术发展的未来轨迹

5. 理论框架的发展与竞争
- 追踪主要理论范式的形成、演变和可能的衰落
- 分析不同理论学派之间的关系和交互
- 识别理论争议点及其随时间的解决或持续
- 评估理论创新的动力和阻力
- 分析理论统一和分化的趋势

6. 研究重点的演变轨迹
- 分析研究焦点随时间的迁移模式
- 识别推动研究重点变化的内外因素
- 评估研究重点变化的合理性和必然性
- 分析新兴研究方向的出现机制
- 预测未来研究重点的可能转向

7. 影响力传播与扩散分析
- 识别各时期最具影响力的研究、研究者和机构
- 分析影响力的传播路径和放大机制
- 评估影响力的持久性和跨领域扩散
- 分析影响力衰减和复兴的周期性
- 识别潜在的未来影响力中心

8. 趋势预测和未来展望
- 基于历史发展模式，预测未来3-5年的研究方向
- 分析可能出现的新技术、新方法及其潜在影响
- 提出尚未解决的关键问题及其解决路径
- 评估外部环境变化对研究发展的影响
- 建议研究策略和资源配置的优化方向

请确保分析立足于数据，客观评价发展脉络，并为每个主要观点提供具体文献支持。给我提供html格式作为输出。

分析的文献集合JSON数据，"relevance_score"大于8分的要特别关注：
{JSON_DATA}"""

METHODOLOGY_ANALYSIS_PROMPT = """基于以下学术文献数据，请进行一次深入的方法学分析，重点评估研究领域中使用的方法、技术和工具的演变、效力和局限性。请按照如下结构组织你的分析，每个结构至少给出5点内容：

1. 方法学概述
- 全面梳理研究领域中使用的主要方法、技术和分析框架
- 对各类方法进行分类（如实验方法、计算方法、理论方法等）
- 提供关于方法使用频率、流行度和演变趋势的总体统计
- 分析方法学标准化和规范化的程度
- 评估方法学多样性对研究质量的影响

2. 核心方法的深入分析
- 详细分析3-5种最关键的研究方法，包括：
    * 方法的技术原理和理论基础
    * 适用场景和应用领域
    * 方法的优势、局限性和潜在偏差
    * 方法的演变过程和关键改进
    * 方法的可重复性和可靠性评估

3. 方法论争议与挑战
- 识别研究领域中存在的方法学争议
- 分析不同方法产生不同或矛盾结果的案例
- 评估方法验证、重复性和可靠性方面的挑战
- 分析方法选择偏好的主观性和客观性
- 讨论方法学标准统一的必要性和可行性

4. 技术依赖性分析
- 评估研究进展对特定技术、设备或软件的依赖程度
- 分析技术限制如何塑造研究问题的提出和解决
- 讨论技术进步如何推动方法创新和研究突破
- 评估技术壁垒对研究公平性的影响
- 分析技术开源化对方法普及的作用

5. 跨学科方法整合
- 识别从其他学科借鉴、改编的方法和技术
- 分析跨学科方法的整合过程、挑战和成功案例
- 评估跨学科方法对研究领域拓展的贡献
- 分析方法融合中的理论冲突和协调机制
- 预测跨学科方法整合的未来趋势

6. 实践与应用视角
- 分析方法从实验室到实际应用的转化过程
- 评估方法在实际应用中的性能、可靠性和经济性
- 讨论实践需求如何反向驱动方法学创新
- 分析方法标准化对产业化的重要性
- 评估方法学研究的社会价值和经济效益

7. 方法学质量评估
- 建立方法学质量评估的标准和指标
- 分析高质量方法学研究的共同特征
- 评估方法学创新的原创性和影响力
- 识别方法学研究中的常见缺陷和改进空间
- 分析方法学同行评议的标准和效果

8. 未来方法学展望
- 预测可能改变研究领域的新兴方法和技术
- 提出现有方法的潜在改进方向
- 建议解决当前方法学局限的路径和策略
- 分析人工智能和大数据对方法学的革命性影响
- 讨论方法学教育和培训的改革方向

请确保分析立足于数据，客观评价各方法的优劣，避免未经证实的主观判断。对各主要结论，请提供具体的文献支持。注重方法之间的比较与对照，以及方法与研究问题、结果质量之间的关系。给我提供html格式作为输出。

分析的文献集合JSON数据，"relevance_score"大于8分的要特别关注：
{JSON_DATA}"""

# 分析类型选择
ANALYSIS_TYPE = "research_flow"  # 可选: "research_flow", "timeline", "methodology"

# ================================
# 核心功能实现
# ================================

class HighQualityAnalyzer:
    def __init__(self, logs_path, threshold, api_key):
        self.logs_path = logs_path
        self.threshold = threshold
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        
        # 创建带绝对时间戳的输出文件夹
        self.timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = os.path.join(logs_path, f"analysis_results_{self.timestamp}")
        os.makedirs(self.output_dir, exist_ok=True)
        
        print(f"🔍 高质量文章分析工具启动")
        print(f"📁 日志路径: {logs_path}")
        print(f"🎯 相关性阈值: {threshold}分")
        print(f"📊 输出目录: {self.output_dir}")
        print("="*60)
    
    def get_analysis_prompt(self, analysis_type):
        """根据分析类型返回对应的prompt"""
        prompts = {
            "research_flow": RESEARCH_FLOW_PROMPT,
            "timeline": TIMELINE_ANALYSIS_PROMPT,
            "methodology": METHODOLOGY_ANALYSIS_PROMPT,
            "custom": RESEARCH_FLOW_PROMPT  # 自定义模板默认使用研究脉络分析的prompt
        }
        return prompts.get(analysis_type, RESEARCH_FLOW_PROMPT)
    
    def parse_log_file(self, log_file_path):
        """解析单个日志文件，提取分析结果"""
        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 查找DeepSeek AI的分析回答部分
            ai_response_start = content.find("DeepSeek AI的分析回答:")
            if ai_response_start == -1:
                return None
            
            ai_response = content[ai_response_start:].split("日志结束")[0]
            
            # 提取JSON部分
            json_match = re.search(r'(\{[\s\S]*?\})', ai_response)
            if json_match:
                try:
                    analysis_data = json.loads(json_match.group(1))
                    return analysis_data
                except json.JSONDecodeError:
                    return None
            
            return None
            
        except Exception as e:
            print(f"❌ 解析日志文件失败: {log_file_path} - {str(e)}")
            return None
    
    def load_and_filter_articles(self):
        """加载并筛选高质量文章"""
        print("📖 开始解析日志文件...")
        
        high_quality_articles = []
        total_files = 0
        parsed_files = 0
        
        # 遍历日志文件夹中的所有txt文件
        for filename in os.listdir(self.logs_path):
            if filename.endswith('.txt') and filename != 'log_index.csv':
                total_files += 1
                log_file_path = os.path.join(self.logs_path, filename)
                
                analysis_data = self.parse_log_file(log_file_path)
                if analysis_data:
                    parsed_files += 1
                    
                    # 检查相关性评分
                    relevance_score = analysis_data.get('relevance_score', 0)
                    try:
                        score = float(relevance_score)
                        if score >= self.threshold:
                            analysis_data['log_filename'] = filename
                            high_quality_articles.append(analysis_data)
                            print(f"✅ 发现高质量文章: {analysis_data.get('title', '未知标题')[:50]}... (评分: {score})")
                    except (ValueError, TypeError):
                        continue
        
        print(f"\n📊 统计结果:")
        print(f"   总日志文件: {total_files}")
        print(f"   成功解析: {parsed_files}")
        print(f"   高质量文章: {len(high_quality_articles)}")
        print("="*60)
        
        return high_quality_articles
    
    def perform_deep_analysis(self, high_quality_articles, analysis_type="research_flow"):
        """使用DeepSeek进行深度思考分析"""
        if not high_quality_articles:
            print("❌ 没有找到符合条件的高质量文章")
            return None
        
        analysis_names = {
            "research_flow": "研究脉络分析",
            "timeline": "时间线分析",
            "methodology": "方法学分析",
            "custom": "自定义"
        }
        
        print(f"🧠 开始{analysis_names.get(analysis_type, '深度')}分析 ({len(high_quality_articles)} 篇文章)...")
        
        # 准备文章摘要数据
        articles_summary = []
        for i, article in enumerate(high_quality_articles, 1):
            summary = {
                "序号": i,
                "标题": article.get("title", "未知"),
                "作者": article.get("authors", "未知"),
                "年份": article.get("publication_year", "未知"),
                "期刊": article.get("journal", "未知"),
                "DOI": article.get("doi", ""),
                "研究焦点": article.get("research_focus", ""),
                "关键方法": article.get("key_methods", ""),
                "主要贡献": article.get("major_contributions", ""),
                "相关性评分": article.get("relevance_score", 0),
                "技术方法": article.get("technical_methods", ""),
                "创新点": article.get("innovation_points", ""),
                "局限性": article.get("limitations", ""),
                "未来方向": article.get("future_directions", "")
            }
            articles_summary.append(summary)
        
        # 构建深度分析prompt
        articles_json = json.dumps(articles_summary, ensure_ascii=False, indent=2)
        analysis_prompt = self.get_analysis_prompt(analysis_type)
        final_prompt = analysis_prompt.replace("{JSON_DATA}", articles_json)
        
        try:
            # 使用DeepSeek推理模型进行深度分析
            print("🤔 调用DeepSeek推理模型...")
            try:
                response = self.client.chat.completions.create(
                    model="deepseek-reasoner",
                    messages=[
                        {"role": "system", "content": f"You are an expert research analyst with deep thinking capabilities for scientific literature {analysis_type} analysis."},
                        {"role": "user", "content": final_prompt}
                    ],
                    temperature=0.1,
                    max_tokens=32000
                )
            except Exception:
                # 如果推理模式不可用，使用标准模式
                print("⚠️ 推理模式不可用，使用标准模式...")
                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": f"You are an expert research analyst for {analysis_type} analysis."},
                        {"role": "user", "content": final_prompt}
                    ],
                    temperature=0.2,
                    max_tokens=32000
                )
            
            analysis_result = response.choices[0].message.content
            print("✅ 深度分析完成")
            return analysis_result
            
        except Exception as e:
            print(f"❌ 深度分析失败: {str(e)}")
            return None
    
    def generate_reports(self, high_quality_articles, deep_analysis, analysis_type="research_flow"):
        """生成分析报告"""
        analysis_names = {
            "research_flow": "research_flow",
            "timeline": "timeline",
            "methodology": "methodology",
            "custom": "custom"
        }
        
        analysis_suffix = analysis_names.get(analysis_type, "analysis")
        
        # 1. 保存高质量文章列表 (JSON)
        articles_file = os.path.join(self.output_dir, f"high_quality_articles_{self.timestamp}.json")
        with open(articles_file, 'w', encoding='utf-8') as f:
            json.dump(high_quality_articles, f, ensure_ascii=False, indent=2)
        print(f"📄 高质量文章列表已保存: {articles_file}")
        
        # 2. 保存高质量文章列表 (CSV)
        csv_file = os.path.join(self.output_dir, f"high_quality_articles_{self.timestamp}.csv")
        if high_quality_articles:
            df = pd.DataFrame(high_quality_articles)
            df.to_csv(csv_file, index=False, encoding='utf-8-sig')
            print(f"📊 CSV报告已保存: {csv_file}")
        
        # 3. 保存深度分析结果
        if deep_analysis:
            analysis_file = os.path.join(self.output_dir, f"{analysis_suffix}_analysis_{self.timestamp}.html")
            with open(analysis_file, 'w', encoding='utf-8') as f:
                # 如果分析结果已经是HTML格式，直接保存
                if deep_analysis.strip().startswith('<!DOCTYPE html>') or deep_analysis.strip().startswith('<html'):
                    f.write(deep_analysis)
                else:
                    # 否则包装成HTML格式
                    html_wrapper = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{analysis_names.get(analysis_type, '深度分析')}报告</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 20px; line-height: 1.6; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; }}
        pre {{ white-space: pre-wrap; font-family: inherit; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{analysis_names.get(analysis_type, '深度分析')}报告</h1>
            <p>生成时间: {datetime.datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
            <p>分析文章数量: {len(high_quality_articles)}</p>
        </div>
        <div class="content">
            <pre>{deep_analysis}</pre>
        </div>
    </div>
</body>
</html>"""
                    f.write(html_wrapper)
            print(f"🧠 {analysis_names.get(analysis_type, '深度分析')}报告已保存: {analysis_file}")
        
        # 4. 生成综合统计报告
        stats_file = os.path.join(self.output_dir, f"analysis_summary_{self.timestamp}.txt")
        with open(stats_file, 'w', encoding='utf-8') as f:
            f.write(f"高质量文章分析统计报告\n")
            f.write(f"生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"分析类型: {analysis_names.get(analysis_type, '综合分析')}\n")
            f.write(f"分析文章数量: {len(high_quality_articles)}\n")
            f.write(f"相关性阈值: {self.threshold}分\n")
            f.write("="*80 + "\n\n")
            
            if high_quality_articles:
                scores = [float(a.get('relevance_score', 0)) for a in high_quality_articles]
                years = [str(a.get('publication_year', '未知')) for a in high_quality_articles]
                journals = [str(a.get('journal', '未知')) for a in high_quality_articles]
                
                f.write(f"相关性评分统计:\n")
                f.write(f"  平均分: {round(sum(scores) / len(scores), 2)}\n")
                f.write(f"  最高分: {max(scores)}\n")
                f.write(f"  最低分: {min(scores)}\n")
                f.write(f"  9分以上: {len([s for s in scores if s >= 9])}\n\n")
                
                year_count = {}
                for year in years:
                    year_count[year] = year_count.get(year, 0) + 1
                f.write(f"年份分布:\n")
                for year, count in sorted(year_count.items()):
                    f.write(f"  {year}: {count}篇\n")
                f.write("\n")
                
                journal_count = {}
                for journal in journals:
                    journal_count[journal] = journal_count.get(journal, 0) + 1
                f.write(f"期刊分布（前10）:\n")
                for journal, count in sorted(journal_count.items(), key=lambda x: x[1], reverse=True)[:10]:
                    f.write(f"  {journal}: {count}篇\n")
        
        print(f"📈 统计报告已保存: {stats_file}")
        
        return {
            "articles_json": articles_file,
            "articles_csv": csv_file,
            "deep_analysis": analysis_file if deep_analysis else None,
            "summary": stats_file
        }
    
    def run(self, analysis_type="research_flow"):
        """运行完整的分析流程"""
        analysis_names = {
            "research_flow": "研究脉络分析",
            "timeline": "时间线分析",
            "methodology": "方法学分析",
            "custom": "自定义"
        }
        
        print(f"🚀 开始{analysis_names.get(analysis_type, '深度')}流程...\n")
        
        # 1. 加载并筛选高质量文章
        high_quality_articles = self.load_and_filter_articles()
        
        if not high_quality_articles:
            print("❌ 没有找到符合条件的高质量文章，请检查日志路径和阈值设置")
            return
        
        # 2. 进行深度思考分析
        deep_analysis = self.perform_deep_analysis(high_quality_articles, analysis_type)
        
        # 3. 生成报告
        print("\n📋 生成分析报告...")
        report_files = self.generate_reports(high_quality_articles, deep_analysis, analysis_type)
        
        # 4. 显示结果摘要
        print("\n" + "="*60)
        print("🎉 分析完成！生成的文件:")
        for file_type, file_path in report_files.items():
            if file_path:
                print(f"   📁 {file_type}: {os.path.basename(file_path)}")
        
        print(f"\n📊 分析摘要:")
        print(f"   🎯 筛选出 {len(high_quality_articles)} 篇高质量文章")
        if high_quality_articles:
            scores = [float(a.get('relevance_score', 0)) for a in high_quality_articles]
            print(f"   📈 平均相关性评分: {round(sum(scores) / len(scores), 1)}")
            print(f"   🏆 最高评分: {max(scores)}")
        print(f"   📁 输出目录: {self.output_dir}")
        
        return report_files

# ================================
# 主程序入口
# ================================

def main():
    """主程序入口"""
    print("🔬 高质量文章分析工具")
    print("="*60)
    
    # 检查配置
    if not os.path.exists(LOGS_FOLDER_PATH):
        print(f"❌ 错误: 日志文件夹不存在: {LOGS_FOLDER_PATH}")
        print("请检查并修改脚本顶部的 LOGS_FOLDER_PATH 配置")
        return
    
    if not API_KEY or API_KEY == "your_api_key_here":
        print("❌ 错误: 请配置有效的 DeepSeek API Key")
        print("请检查并修改脚本顶部的 API_KEY 配置")
        return
    
    # 创建分析器并运行
    analyzer = HighQualityAnalyzer(
        logs_path=LOGS_FOLDER_PATH,
        threshold=RELEVANCE_THRESHOLD,
        api_key=API_KEY
    )
    
    try:
        # 可以通过修改ANALYSIS_TYPE来选择不同的分析类型
        analyzer.run(ANALYSIS_TYPE)
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断了分析过程")
    except Exception as e:
        print(f"\n❌ 分析过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
