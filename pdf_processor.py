#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDF处理工具 - 将PDF文件夹中的所有PDF转换为TXT
用于内容分析栏的PDF文件夹输入功能

作者: Yuming Su
日期: 2025-08-28
"""

import os
import logging
from typing import List, Dict, Optional
import fitz  # PyMuPDF
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PDFProcessor:
    """PDF处理器 - 递归查找PDF并转换为TXT"""
    
    def __init__(self):
        self.supported_extensions = ['.pdf']
        self.processed_files = []
        self.failed_files = []
    
    def find_all_pdfs(self, folder_path: str) -> List[str]:
        """递归查找文件夹中的所有PDF文件"""
        pdf_files = []
        
        try:
            folder_path = Path(folder_path)
            if not folder_path.exists() or not folder_path.is_dir():
                logger.error(f"文件夹不存在或不是目录: {folder_path}")
                return pdf_files
            
            # 递归查找所有PDF文件
            for pdf_file in folder_path.rglob("*.pdf"):
                if pdf_file.is_file():
                    pdf_files.append(str(pdf_file))
                    logger.debug(f"找到PDF文件: {pdf_file}")
            
            logger.info(f"在 {folder_path} 中找到 {len(pdf_files)} 个PDF文件")
            return pdf_files
            
        except Exception as e:
            logger.error(f"查找PDF文件时出错: {str(e)}")
            return pdf_files
    
    def extract_text_from_pdf(self, pdf_path: str) -> Optional[str]:
        """从PDF文件中提取文本"""
        try:
            doc = fitz.open(pdf_path)
            text_content = ""
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()
                text_content += text + "\n"
            
            doc.close()
            
            # 清理文本
            text_content = text_content.strip()
            if not text_content:
                logger.warning(f"PDF文件 {pdf_path} 中没有提取到文本内容")
                return None
            
            return text_content
            
        except Exception as e:
            logger.error(f"提取PDF文本失败 {pdf_path}: {str(e)}")
            return None
    
    def convert_pdf_to_txt(self, pdf_path: str, output_dir: str) -> Optional[str]:
        """将单个PDF转换为TXT文件"""
        try:
            # 提取文本
            text_content = self.extract_text_from_pdf(pdf_path)
            if not text_content:
                return None
            
            # 生成输出文件名
            pdf_name = Path(pdf_path).stem
            txt_filename = f"{pdf_name}.txt"
            txt_path = os.path.join(output_dir, txt_filename)
            
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            # 保存TXT文件
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(f"# 原始PDF文件: {pdf_path}\n")
                f.write(f"# 转换时间: {os.path.getctime(pdf_path)}\n")
                f.write("# " + "="*50 + "\n\n")
                f.write(text_content)
            
            logger.info(f"成功转换: {pdf_path} -> {txt_path}")
            return txt_path
            
        except Exception as e:
            logger.error(f"转换PDF到TXT失败 {pdf_path}: {str(e)}")
            return None
    
    def process_pdf_folder(self, folder_path: str, output_dir: str) -> Dict[str, any]:
        """处理PDF文件夹，将所有PDF转换为TXT"""
        results = {
            'total_pdfs': 0,
            'successful_conversions': 0,
            'failed_conversions': 0,
            'txt_files': [],
            'failed_files': [],
            'output_dir': output_dir
        }
        
        try:
            # 查找所有PDF文件
            pdf_files = self.find_all_pdfs(folder_path)
            results['total_pdfs'] = len(pdf_files)
            
            if not pdf_files:
                logger.warning(f"在 {folder_path} 中没有找到PDF文件")
                return results
            
            logger.info(f"开始处理 {len(pdf_files)} 个PDF文件...")
            
            # 逐个转换PDF
            for i, pdf_path in enumerate(pdf_files, 1):
                logger.info(f"处理进度: {i}/{len(pdf_files)} - {os.path.basename(pdf_path)}")
                
                txt_path = self.convert_pdf_to_txt(pdf_path, output_dir)
                
                if txt_path:
                    results['successful_conversions'] += 1
                    results['txt_files'].append(txt_path)
                    self.processed_files.append(pdf_path)
                else:
                    results['failed_conversions'] += 1
                    results['failed_files'].append(pdf_path)
                    self.failed_files.append(pdf_path)
            
            logger.info(f"PDF处理完成: 成功 {results['successful_conversions']}, 失败 {results['failed_conversions']}")
            return results
            
        except Exception as e:
            logger.error(f"处理PDF文件夹时出错: {str(e)}")
            results['error'] = str(e)
            return results
    
    def create_combined_txt(self, txt_files: List[str], output_path: str) -> bool:
        """将多个TXT文件合并为一个大文件供LLM分析"""
        try:
            with open(output_path, 'w', encoding='utf-8') as combined_file:
                combined_file.write("# 合并的PDF文本内容\n")
                combined_file.write(f"# 包含 {len(txt_files)} 个PDF文件的内容\n")
                combined_file.write("# " + "="*80 + "\n\n")
                
                for i, txt_file in enumerate(txt_files, 1):
                    try:
                        with open(txt_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        combined_file.write(f"\n\n{'='*80}\n")
                        combined_file.write(f"文档 {i}: {os.path.basename(txt_file)}\n")
                        combined_file.write(f"{'='*80}\n\n")
                        combined_file.write(content)
                        
                    except Exception as e:
                        logger.error(f"读取TXT文件失败 {txt_file}: {str(e)}")
                        combined_file.write(f"\n[错误: 无法读取文件 {txt_file}]\n")
            
            logger.info(f"成功创建合并文件: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"创建合并文件失败: {str(e)}")
            return False
    
    def get_processing_summary(self) -> str:
        """获取处理摘要"""
        summary = f"PDF处理摘要:\n"
        summary += f"- 成功处理: {len(self.processed_files)} 个文件\n"
        summary += f"- 处理失败: {len(self.failed_files)} 个文件\n"
        
        if self.failed_files:
            summary += f"\n失败的文件:\n"
            for failed_file in self.failed_files[:5]:  # 只显示前5个
                summary += f"  - {os.path.basename(failed_file)}\n"
            if len(self.failed_files) > 5:
                summary += f"  - ... 还有 {len(self.failed_files) - 5} 个失败文件\n"
        
        return summary


def main():
    """测试函数"""
    processor = PDFProcessor()
    
    # 测试文件夹路径
    test_folder = input("请输入包含PDF的文件夹路径: ").strip()
    if not test_folder:
        print("未输入文件夹路径")
        return
    
    # 输出目录
    output_dir = os.path.join(test_folder, "converted_txt")
    
    # 处理PDF文件夹
    results = processor.process_pdf_folder(test_folder, output_dir)
    
    # 打印结果
    print(f"\n处理结果:")
    print(f"总计PDF文件: {results['total_pdfs']}")
    print(f"成功转换: {results['successful_conversions']}")
    print(f"转换失败: {results['failed_conversions']}")
    
    if results['txt_files']:
        print(f"\n生成的TXT文件:")
        for txt_file in results['txt_files'][:5]:
            print(f"  - {txt_file}")
        if len(results['txt_files']) > 5:
            print(f"  - ... 还有 {len(results['txt_files']) - 5} 个文件")
        
        # 创建合并文件
        combined_path = os.path.join(output_dir, "combined_all_pdfs.txt")
        if processor.create_combined_txt(results['txt_files'], combined_path):
            print(f"\n合并文件已创建: {combined_path}")


if __name__ == "__main__":
    main()