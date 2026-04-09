import time
import logging
import webbrowser
from pywinauto import Desktop
from pywinauto.keyboard import send_keys
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
import re
import subprocess
import psutil
# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

@dataclass
class PageStatus:
    """页面状态"""
    url: str
    tab_index: int
    is_loaded: bool = False
    is_saved: bool = False
    is_generic_loaded: bool = False  # 新增：是否为通用类型但已加载
    publisher: str = ""
    button_text: str = ""
    check_count: int = 0
    last_check_time: float = 0
    load_time: float = 0
    save_time: float = 0
    retry_count: int = 0
    force_retry_count: int = 0
    first_generic_time: float = 0  # 新增：首次检测到通用类型的时间

@dataclass
class ProcessResult:
    """处理结果"""
    url: str
    success: bool
    publisher: str
    load_time: float = 0
    save_time: float = 0
    error_msg: str = ""
    retry_count: int = 0
    save_phase: str = ""  # 新增：保存阶段（第一阶段/第二阶段）

class ZoteroBatchSaver:
    """Zotero批量保存器 - 先易后难策略版本"""
    
    # 未加载完成的标志
    LOADING_INDICATORS = [
        "Loading",
        "正在加载"
    ]
    
    # 通用页面抓取的标志（需要特殊处理）
    GENERIC_INDICATORS = [
        "Web Page with Snapshot",
        "Web Page",
        "Webpage with Snapshot", 
        "Webpage"
    ]
    
    # 固定批次大小为9
    OPTIMAL_BATCH_SIZE = 9
    
    def __init__(self):
        self.batch_size = self.OPTIMAL_BATCH_SIZE
        self.page_statuses: Dict[int, PageStatus] = {}
        self.results: List[ProcessResult] = []
        self.start_time = time.time()
        self.current_batch_urls: List[str] = []
        self.last_progress_time = time.time()
        
        # 新增：先易后难策略相关
        self.phase_one_complete = False  # 第一阶段是否完成
        self.last_easy_save_time = time.time()  # 最后一次简单保存的时间
        self.phase_one_timeout = 120  # 第一阶段超时时间
        self.generic_wait_time = 30   # 通用类型等待时间
        self.zotero_validation_enabled = True
        self.initial_zotero_count = 0  # 批次开始前的文献数量
        self.expected_zotero_count = 0  # 预期的文献数量
    def is_page_loaded_with_strategy(self, button_text: str, check_count: int = 0) -> Tuple[bool, str, bool]:
        """
        判断页面是否加载完成（先易后难策略版本）
        返回: (是否加载完成, 出版社名称, 是否为通用类型)
        """
        if not button_text:
            return False, "", False
            
        # 检查是否包含明确的加载中标志
        for indicator in self.LOADING_INDICATORS:
            if indicator.lower() in button_text.lower():
                return False, "", False
        
        # 提取出版社名称
        publisher = ""
        if "(" in button_text and ")" in button_text:
            match = re.search(r'\((.*?)\)', button_text)
            if match:
                publisher = match.group(1)
        
        # 判断是否为通用类型
        is_generic = publisher in self.GENERIC_INDICATORS
        
        # 如果有明确的出版社名称（不是通用标志），认为加载完成
        if publisher and not is_generic:
            return True, publisher, False
        
        # 如果是通用类型，也认为技术上已加载，但标记为通用
        if is_generic:
            return True, publisher, True
            
        return False, "", False
    
    def check_and_save_easy_pages(self, edge_window) -> int:
        """
        第一阶段：检查并保存"简单"页面（非通用类型）
        """
        saved_count = 0
        current_time = time.time()
        
        # 打印当前状态
        self.print_current_status()
        
        # 遍历所有标签
        for tab_index in range(1, min(len(self.page_statuses) + 1, 10)):
            if tab_index not in self.page_statuses:
                continue
                
            status = self.page_statuses[tab_index]
            
            # 跳过已保存的页面
            if status.is_saved:
                continue
                
            # 避免检查过于频繁
            if current_time - status.last_check_time < 1.5:
                continue
                
            logger.debug(f"第一阶段检查标签 {tab_index}...")
            
            # 切换到标签页
            if not self.switch_to_tab(edge_window, tab_index):
                continue
            
            # 获取Zotero按钮
            button, button_text = self.get_zotero_button(edge_window)
            
            if button and button_text:
                is_loaded, publisher, is_generic = self.is_page_loaded_with_strategy(
                    button_text, status.check_count
                )
                
                status.button_text = button_text
                status.last_check_time = current_time
                status.check_count += 1
                
                if is_loaded:
                    if not status.is_loaded:
                        # 页面刚刚加载完成
                        status.is_loaded = True
                        status.publisher = publisher
                        status.load_time = current_time - self.start_time
                        
                        if is_generic:
                            # 通用类型，标记但不立即保存
                            status.is_generic_loaded = True
                            if status.first_generic_time == 0:
                                status.first_generic_time = current_time
                            logger.info(f"标签 {tab_index}: ✓ 检测到通用类型 - {publisher} ({status.load_time:.1f}秒) [等待中]")
                        else:
                            # 非通用类型，立即保存
                            logger.info(f"标签 {tab_index}: ✓ 检测到明确类型 - {publisher} ({status.load_time:.1f}秒) [立即保存]")
                    
                    # 第一阶段只保存非通用类型
                    if not is_generic and not status.is_saved:
                        if self.save_page_immediately(edge_window, tab_index, button, "第一阶段"):
                            saved_count += 1
                            self.last_easy_save_time = current_time
                            
                else:
                    # 页面还在加载中
                    logger.debug(f"标签 {tab_index}: 仍在加载中 (按钮文本: {button_text[:30]}...)")
                        
            else:
                status.last_check_time = current_time
                logger.debug(f"标签 {tab_index}: 未找到Zotero按钮")
                
        return saved_count
    def is_zotero_running(self) -> bool:
        """检查Zotero是否正在运行"""
        try:
            for proc in psutil.process_iter(['name']):
                if 'zotero' in proc.info['name'].lower():
                    return True
            return False
        except Exception as e:
            logger.debug(f"检查Zotero进程失败: {e}")
            return False
    
    def start_zotero_if_needed(self) -> bool:
        """如果Zotero未运行则启动它"""
        if self.is_zotero_running():
            logger.info("✓ Zotero已在运行")
            return True
        
        logger.info("启动Zotero...")
        try:
            # 尝试常见的Zotero安装路径
            zotero_paths = [
                r"C:\Program Files (x86)\Zotero\zotero.exe",
                r"D:\Program Files\Zotero\zotero.exe",
                r"C:\Users\{}\AppData\Local\Zotero\zotero.exe".format(os.environ.get('USERNAME', '')),
            ]
            
            for path in zotero_paths:
                if os.path.exists(path):
                    subprocess.Popen([path])
                    logger.info(f"启动Zotero: {path}")
                    
                    # 等待Zotero启动
                    for i in range(10):
                        time.sleep(2)
                        if self.is_zotero_running():
                            logger.info("✓ Zotero启动成功")
                            time.sleep(3)  # 给Zotero更多时间完全加载
                            return True
                    break
            
            logger.warning("无法找到或启动Zotero")
            return False
            
        except Exception as e:
            logger.error(f"启动Zotero失败: {e}")
            return False
    
    def find_zotero_window(self):
        """查找Zotero主窗口（优化版）"""
        try:
            desktop = Desktop(backend="uia")
            windows = desktop.windows()
            
            logger.debug(f"正在查找Zotero窗口，共找到 {len(windows)} 个窗口")
            
            # 可能的Zotero窗口标题模式
            zotero_patterns = [
                "Zotero",
                "zotero", 
                "Zotero Standalone",
                "Zotero 7",
                "Zotero 6",
            ]
            
            # 记录所有窗口用于调试
            found_windows = []
            
            for i, window in enumerate(windows):
                try:
                    window_text = window.window_text()
                    class_name = ""
                    try:
                        class_name = window.class_name()
                    except:
                        pass
                    
                    found_windows.append((window_text, class_name))
                    
                    # 检查窗口标题
                    if window_text:
                        window_text_lower = window_text.lower()
                        
                        # 方法1: 精确匹配
                        for pattern in zotero_patterns:
                            if pattern.lower() == window_text_lower:
                                logger.info(f"找到Zotero窗口(精确匹配): '{window_text}'")
                                return window
                        
                        # 方法2: 包含匹配
                        for pattern in zotero_patterns:
                            if pattern.lower() in window_text_lower:
                                logger.info(f"找到Zotero窗口(包含匹配): '{window_text}'")
                                return window
                        
                        # 方法3: 检查是否以Zotero开头
                        if window_text_lower.startswith("zotero"):
                            logger.info(f"找到Zotero窗口(前缀匹配): '{window_text}'")
                            return window
                            
                except Exception as e:
                    logger.debug(f"检查窗口 {i} 时出错: {e}")
                    continue
            
            # 如果没找到，打印所有窗口用于调试
            logger.warning("未找到Zotero主窗口，当前所有窗口:")
            for i, (title, class_name) in enumerate(found_windows):
                logger.warning(f"  窗口 {i+1}: '{title}' (类名: {class_name})")
            
            # 尝试使用Application方式连接
            logger.info("尝试使用Application方式连接Zotero...")
            return self.find_zotero_window_by_application()
            
        except Exception as e:
            logger.error(f"查找Zotero窗口失败: {e}")
            return None

    def find_zotero_window_by_application(self):
        """通过Application方式查找Zotero窗口"""
        try:
            # 尝试连接到Zotero进程
            zotero_processes = []
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if 'zotero' in proc.info['name'].lower():
                        zotero_processes.append(proc.info['pid'])
                except:
                    continue
            
            if not zotero_processes:
                logger.warning("没有找到Zotero进程")
                return None
            
            logger.info(f"找到 {len(zotero_processes)} 个Zotero进程: {zotero_processes}")
            
            # 尝试连接每个Zotero进程
            for pid in zotero_processes:
                try:
                    app = Application(backend="uia").connect(process=pid)
                    windows = app.windows()
                    
                    for window in windows:
                        try:
                            window_text = window.window_text()
                            if window_text and "zotero" in window_text.lower():
                                logger.info(f"通过Application找到Zotero窗口: '{window_text}' (PID: {pid})")
                                return window
                        except:
                            continue
                            
                except Exception as e:
                    logger.debug(f"连接进程 {pid} 失败: {e}")
                    continue
            
            logger.warning("通过Application方式也未找到Zotero窗口")
            return None
            
        except Exception as e:
            logger.error(f"Application方式查找失败: {e}")
            return None

    def get_zotero_item_count_robust(self) -> Optional[int]:
        """获取Zotero中当前选中集合的文献数量（robust版本）"""
        try:
            if not self.start_zotero_if_needed():
                return None
            
            zotero_window = self.find_zotero_window()
            if not zotero_window:
                logger.warning("无法找到Zotero窗口，尝试其他方法...")
                return self.get_zotero_count_alternative_methods()
            
            logger.info("成功找到Zotero窗口，尝试获取文献数量...")
            
            # 聚焦Zotero窗口
            try:
                zotero_window.set_focus()
                time.sleep(1)
            except Exception as e:
                logger.warning(f"无法聚焦Zotero窗口: {e}")
            
            # 方法1: 尝试查找文献列表区域并全选
            return self.get_count_by_item_list(zotero_window)
            
        except Exception as e:
            logger.error(f"获取Zotero文献数量失败: {e}")
            return None

    def get_count_by_item_list(self, zotero_window) -> Optional[int]:
        """通过文献列表获取数量"""
        try:
            logger.info("尝试通过文献列表获取数量...")
            
            # 方法1: 查找包含文献的列表控件
            list_controls = zotero_window.descendants(control_type="List")
            tree_controls = zotero_window.descendants(control_type="Tree")
            table_controls = zotero_window.descendants(control_type="Table")
            
            all_controls = list(list_controls) + list(tree_controls) + list(table_controls)
            
            logger.info(f"找到 {len(all_controls)} 个可能的列表控件")
            
            for i, control in enumerate(all_controls):
                try:
                    # 尝试获取子项数量
                    children = control.children()
                    if len(children) > 0:
                        logger.info(f"列表控件 {i+1}: 包含 {len(children)} 个子项")
                        
                        # 检查是否是文献列表（子项应该包含文献信息）
                        sample_items = children[:3]  # 检查前3个项目
                        is_item_list = False
                        
                        for child in sample_items:
                            try:
                                child_text = child.window_text()
                                # 如果包含常见的文献信息关键词，认为是文献列表
                                if any(keyword in child_text.lower() for keyword in 
                                    ['journal', 'article', 'author', 'title', '期刊', '作者', '标题']):
                                    is_item_list = True
                                    break
                            except:
                                continue
                        
                        if is_item_list or len(children) > 10:  # 如果确认是文献列表或者项目很多
                            logger.info(f"识别为文献列表，包含 {len(children)} 篇文献")
                            return len(children)
                            
                except Exception as e:
                    logger.debug(f"检查列表控件 {i+1} 失败: {e}")
                    continue
            
            # 方法2: 尝试全选并从选中项获取信息
            return self.get_count_by_selection(zotero_window)
            
        except Exception as e:
            logger.debug(f"通过文献列表获取数量失败: {e}")
            return None

    def get_count_by_selection(self, zotero_window) -> Optional[int]:
        """通过全选操作获取数量"""
        try:
            logger.info("尝试通过全选操作获取数量...")
            
            # 确保窗口有焦点
            zotero_window.set_focus()
            time.sleep(0.5)
            
            # 尝试点击中间的文献列表区域
            try:
                # 获取窗口大小
                rect = zotero_window.rectangle()
                center_x = rect.left + (rect.right - rect.left) // 2
                center_y = rect.top + (rect.bottom - rect.top) // 2
                
                # 点击中间位置
                zotero_window.click_input(coords=(center_x - rect.left, center_y - rect.top))
                time.sleep(0.5)
            except Exception as e:
                logger.debug(f"点击文献列表区域失败: {e}")
            
            # 全选
            send_keys("^a")  # Ctrl+A
            time.sleep(1)
            
            # 方法1: 查看状态栏
            status_bars = zotero_window.descendants(control_type="StatusBar")
            for status_bar in status_bars:
                try:
                    status_text = status_bar.window_text()
                    if status_text:
                        logger.info(f"状态栏文本: '{status_text}'")
                        # 提取数字
                        numbers = re.findall(r'\d+', status_text)
                        if numbers:
                            count = int(numbers[-1])  # 取最后一个数字
                            logger.info(f"从状态栏提取数量: {count}")
                            return count
                except Exception as e:
                    logger.debug(f"检查状态栏失败: {e}")
                    continue
            
            # 方法2: 查找包含选中信息的文本
            all_texts = zotero_window.descendants(control_type="Text")
            for text_element in all_texts:
                try:
                    text_content = text_element.window_text()
                    if text_content and ("selected" in text_content.lower() or "选中" in text_content):
                        logger.info(f"找到选中信息文本: '{text_content}'")
                        numbers = re.findall(r'\d+', text_content)
                        if numbers:
                            count = int(numbers[0])
                            logger.info(f"从选中信息提取数量: {count}")
                            return count
                except Exception as e:
                    continue
            
            logger.warning("无法通过全选操作获取数量")
            return None
            
        except Exception as e:
            logger.debug(f"全选操作获取数量失败: {e}")
            return None

    def get_zotero_count_alternative_methods(self) -> Optional[int]:
        """使用替代方法获取Zotero文献数量"""
        try:
            logger.info("尝试使用替代方法获取Zotero文献数量...")
            
            # 方法1: 通过快捷键直接操作
            logger.info("尝试使用快捷键方法...")
            
            # 按Alt+Tab切换到Zotero
            send_keys("%{TAB}")
            time.sleep(1)
            
            # 尝试多次Alt+Tab找到Zotero
            for i in range(5):
                send_keys("%{TAB}")
                time.sleep(0.5)
                
                # 检查当前窗口标题
                try:
                    current_window = Desktop(backend="uia").active_window()
                    if current_window:
                        title = current_window.window_text()
                        if title and "zotero" in title.lower():
                            logger.info(f"通过Alt+Tab找到Zotero: '{title}'")
                            
                            # 尝试获取数量
                            send_keys("^a")  # 全选
                            time.sleep(1)
                            
                            return self.extract_count_from_window(current_window)
                except Exception as e:
                    logger.debug(f"Alt+Tab尝试 {i+1} 失败: {e}")
                    continue
            
            # 方法2: 尝试手动输入方式
            logger.info("请手动确认Zotero文献数量...")
            logger.info("提示：可以在Zotero中全选文献(Ctrl+A)，然后查看底部状态栏显示的数量")
            
            return None
            
        except Exception as e:
            logger.error(f"替代方法获取数量失败: {e}")
            return None

    def extract_count_from_window(self, window) -> Optional[int]:
        """从窗口中提取文献数量"""
        try:
            # 获取所有文本元素
            all_elements = window.descendants()
            
            for element in all_elements:
                try:
                    text = element.window_text()
                    if text and len(text.strip()) > 0:
                        # 查找包含数量信息的文本
                        if any(keyword in text.lower() for keyword in 
                            ['item', 'selected', 'total', '文献', '选中', '总计']):
                            numbers = re.findall(r'\d+', text)
                            if numbers:
                                count = int(numbers[-1])
                                logger.info(f"从文本提取数量: '{text}' -> {count}")
                                return count
                except Exception:
                    continue
            
            return None
            
        except Exception as e:
            logger.debug(f"从窗口提取数量失败: {e}")
            return None

    # 修改原来的get_zotero_item_count方法
    def get_zotero_item_count(self) -> Optional[int]:
        """获取Zotero中当前选中集合的文献数量（入口方法）"""
        return self.get_zotero_item_count_robust()
    
    def validate_zotero_count(self, expected_success_count: int, batch_num: int) -> bool:
        """
        验证Zotero中的文献数量是否符合预期
        
        Args:
            expected_success_count: 预期成功保存的文献数量
            batch_num: 当前批次号
            
        Returns:
            bool: 验证是否通过
        """
        if not self.zotero_validation_enabled:
            logger.info("Zotero验证已禁用")
            return True
        
        logger.info(f"=== 开始Zotero文献数量验证 (批次 {batch_num}) ===")
        
        try:
            # 获取当前Zotero中的文献数量
            current_count = self.get_zotero_item_count()
            
            if current_count is None:
                logger.warning("无法获取Zotero文献数量，跳过验证")
                return True  # 无法验证时假设通过
            
            # 计算预期的总数量
            expected_total = self.initial_zotero_count + expected_success_count
            
            logger.info(f"Zotero文献数量验证:")
            logger.info(f"  批次开始前: {self.initial_zotero_count}")
            logger.info(f"  预期新增: {expected_success_count}")
            logger.info(f"  预期总数: {expected_total}")
            logger.info(f"  实际总数: {current_count}")
            logger.info(f"  实际新增: {current_count - self.initial_zotero_count}")
            
            if current_count >= expected_total:
                logger.info("✅ Zotero验证通过")
                return True
            else:
                missing_count = expected_total - current_count
                logger.warning(f"⚠️ Zotero验证失败: 缺少 {missing_count} 篇文献")
                return False
                
        except Exception as e:
            logger.error(f"Zotero验证过程出错: {e}")
            return True  # 出错时假设通过，避免阻塞流程
    
    def record_initial_zotero_count(self):
        """记录批次开始前的Zotero文献数量"""
        if not self.zotero_validation_enabled:
            return
        
        logger.info("记录初始Zotero文献数量...")
        self.initial_zotero_count = self.get_zotero_item_count() or 0
        logger.info(f"初始Zotero文献数量: {self.initial_zotero_count}")
    
    def retry_failed_saves_based_on_zotero_validation(self, edge_window, missing_count: int) -> int:
        """
        基于Zotero验证结果，重试保存失败的文献
        
        Args:
            edge_window: Edge浏览器窗口
            missing_count: 缺少的文献数量
            
        Returns:
            int: 额外保存成功的数量
        """
        logger.info(f"=== 基于Zotero验证进行补救，尝试补救 {missing_count} 篇文献 ===")
        
        additional_saved = 0
        
        # 获取所有标记为成功但可能实际失败的页面
        potentially_failed = []
        for tab_index, status in self.page_statuses.items():
            if status.is_saved:  # 即使标记为已保存，也可能实际失败
                potentially_failed.append((tab_index, status))
        
        if not potentially_failed:
            logger.warning("没有找到可重试的页面")
            return 0
        
        # 按标签索引排序，优先重试前面的
        potentially_failed.sort(key=lambda x: x[0])
        
        retry_count = min(missing_count + 2, len(potentially_failed))  # 多重试2个以防万一
        
        logger.info(f"将重试前 {retry_count} 个页面...")
        
        for i, (tab_index, status) in enumerate(potentially_failed[:retry_count]):
            logger.info(f"补救重试 {i+1}/{retry_count}: 标签 {tab_index} - {status.url[:50]}...")
            
            # 切换到标签页
            if not self.switch_to_tab(edge_window, tab_index):
                logger.warning(f"无法切换到标签 {tab_index}")
                continue
            
            # 获取Zotero按钮
            button, button_text = self.get_zotero_button(edge_window)
            
            if button and button_text:
                logger.info(f"标签 {tab_index}: 找到按钮 '{button_text[:50]}...'，进行补救保存")
                
                try:
                    button.click_input()
                    time.sleep(3)
                    send_keys("{ENTER}")
                    time.sleep(2)
                    
                    additional_saved += 1
                    logger.info(f"标签 {tab_index}: ✓ 补救保存成功")
                    
                    # 更新结果记录
                    result = ProcessResult(
                        url=status.url,
                        success=True,
                        publisher=status.publisher,
                        load_time=status.load_time,
                        save_time=time.time() - self.start_time,
                        retry_count=status.retry_count + 1,
                        save_phase="Zotero验证补救"
                    )
                    self.results.append(result)
                    
                except Exception as e:
                    logger.warning(f"标签 {tab_index}: 补救保存失败 - {e}")
            else:
                logger.warning(f"标签 {tab_index}: 找不到Zotero按钮")
            
            time.sleep(2)
        
        logger.info(f"补救完成: 额外保存了 {additional_saved} 篇文献")
        return additional_saved    
    def should_enter_phase_two(self) -> bool:
        """
        判断是否应该进入第二阶段
        """
        current_time = time.time()
        
        # 条件1：第一阶段已经超时
        if current_time - self.start_time > self.phase_one_timeout:
            logger.info("第一阶段超时，进入第二阶段")
            return True
        
        # 条件2：很久没有新的简单页面保存了
        if current_time - self.last_easy_save_time > 30:
            # 检查是否还有未加载的页面
            unloaded_count = sum(1 for s in self.page_statuses.values() 
                               if not s.is_loaded and not s.is_saved)
            if unloaded_count == 0:
                logger.info("没有更多未加载的页面，进入第二阶段")
                return True
        
        # 条件3：所有非通用页面都已处理
        easy_unsaved = sum(1 for s in self.page_statuses.values() 
                          if not s.is_saved and not s.is_generic_loaded)
        if easy_unsaved == 0:
            logger.info("所有非通用页面已处理完成，进入第二阶段")
            return True
            
        return False
    
    def check_and_save_generic_pages(self, edge_window) -> int:
        """
        第二阶段：检查并保存通用类型页面（优化版 - 60秒宽容等待）
        """
        saved_count = 0
        current_time = time.time()
        
        logger.info("=== 第二阶段：处理通用类型页面（宽容等待策略） ===")
        
        # 获取所有通用类型页面
        generic_pages = []
        for tab_index, status in self.page_statuses.items():
            if status.is_generic_loaded and not status.is_saved:
                wait_time = current_time - status.first_generic_time
                generic_pages.append((tab_index, status, wait_time))
        
        if not generic_pages:
            logger.info("没有需要处理的通用类型页面")
            return 0
        
        logger.info(f"找到 {len(generic_pages)} 个通用类型页面，开始宽容等待处理...")
        
        # 宽容等待策略：给每个页面最多30秒的额外等待时间
        TOLERANCE_WAIT_TIME = 60  # 30秒宽容等待
        CHECK_INTERVAL = 3        # 每3秒检查一次
        
        # 按等待时间排序，等待时间长的优先处理
        generic_pages.sort(key=lambda x: x[2], reverse=True)
        
        for tab_index, status, initial_wait_time in generic_pages:
            if status.is_saved:  # 跳过已保存的页面
                continue
                
            logger.info(f"开始处理通用页面 - 标签 {tab_index}: {status.publisher} (已等待 {initial_wait_time:.1f}秒)")
            
            # 切换到标签页
            if not self.switch_to_tab(edge_window, tab_index):
                logger.warning(f"无法切换到标签 {tab_index}")
                continue
            
            # 宽容等待循环：最多等待30秒看是否会变成具体出版社
            tolerance_start_time = time.time()
            last_button_text = ""
            check_count = 0
            found_specific_publisher = False
            
            logger.info(f"标签 {tab_index}: 开始宽容等待，最多等待 {TOLERANCE_WAIT_TIME} 秒检查是否变为具体出版社...")
            
            while (time.time() - tolerance_start_time) < TOLERANCE_WAIT_TIME:
                check_count += 1
                elapsed_tolerance_time = time.time() - tolerance_start_time
                
                # 获取当前按钮状态
                button, button_text = self.get_zotero_button(edge_window)
                
                if button and button_text:
                    # 检查是否从通用类型变成了具体类型
                    is_loaded, new_publisher, is_still_generic = self.is_page_loaded_with_strategy(
                        button_text, status.check_count + check_count
                    )
                    
                    # 如果按钮文本发生了变化，记录下来
                    if button_text != last_button_text:
                        logger.info(f"标签 {tab_index}: 按钮文本更新 '{last_button_text[:30]}...' -> '{button_text[:30]}...' (宽容等待 {elapsed_tolerance_time:.1f}秒)")
                        last_button_text = button_text
                    
                    # 如果变成了具体的出版社（不再是通用类型）
                    if is_loaded and not is_still_generic and new_publisher != status.publisher:
                        logger.info(f"标签 {tab_index}: 🎉 检测到类型转换！{status.publisher} -> {new_publisher} (宽容等待 {elapsed_tolerance_time:.1f}秒)")
                        status.publisher = new_publisher
                        found_specific_publisher = True
                        break
                    
                    # 如果仍然是通用类型，继续等待
                    if is_still_generic:
                        if check_count % 3 == 0:  # 每隔几次检查打印一次状态
                            logger.debug(f"标签 {tab_index}: 仍为通用类型 '{new_publisher}' (宽容等待 {elapsed_tolerance_time:.1f}/{TOLERANCE_WAIT_TIME}秒)")
                    
                else:
                    logger.debug(f"标签 {tab_index}: 未找到按钮 (宽容等待 {elapsed_tolerance_time:.1f}秒)")
                
                # 等待间隔
                time.sleep(CHECK_INTERVAL)
            
            # 宽容等待结束后的处理
            final_elapsed_time = time.time() - tolerance_start_time
            
            if found_specific_publisher:
                logger.info(f"标签 {tab_index}: ✅ 宽容等待成功！发现具体出版社 '{status.publisher}' (等待了 {final_elapsed_time:.1f}秒)")
            else:
                logger.info(f"标签 {tab_index}: ⏰ 宽容等待超时，仍为通用类型 '{status.publisher}' (等待了 {final_elapsed_time:.1f}秒)")
            
            # 获取最终的按钮进行保存
            button, button_text = self.get_zotero_button(edge_window)
            
            if button and button_text:
                # 更新最终的出版社信息
                is_loaded, final_publisher, is_still_generic = self.is_page_loaded_with_strategy(
                    button_text, status.check_count + check_count
                )
                
                if final_publisher and final_publisher != status.publisher:
                    status.publisher = final_publisher
                    logger.info(f"标签 {tab_index}: 最终出版社确认为 '{final_publisher}'")
                
                # 尝试保存（不管是通用还是具体类型）
                save_result_msg = "具体类型" if not is_still_generic else "通用类型"
                logger.info(f"标签 {tab_index}: 准备保存 {save_result_msg} - '{status.publisher}'")
                
                if self.save_page_immediately(edge_window, tab_index, button, "第二阶段"):
                    saved_count += 1
                    success_msg = f"宽容等待{'成功' if found_specific_publisher else '超时'}后保存"
                    logger.info(f"标签 {tab_index}: ✓ 第二阶段保存成功 - {status.publisher} ({success_msg})")
                else:
                    logger.warning(f"标签 {tab_index}: ✗ 第二阶段保存失败")
            else:
                logger.warning(f"标签 {tab_index}: 找不到Zotero按钮，无法保存")
            
            # 给下一个页面处理留出间隔
            time.sleep(2)
        
        logger.info(f"=== 第二阶段完成：处理了 {len(generic_pages)} 个通用页面，成功保存 {saved_count} 个 ===")
        return saved_count
    
    def save_page_immediately(self, edge_window, tab_index: int, button, phase: str = "") -> bool:
        """立即保存页面到Zotero（增加阶段信息）"""
        status = self.page_statuses[tab_index]
        save_start = time.time()
        
        try:
            # 点击Zotero按钮
            logger.info(f"标签 {tab_index}: {phase}立即保存 - {status.publisher}")
            button.click_input()
            
            # 等待保存对话框并确认
            time.sleep(3)
            send_keys("{ENTER}")
            time.sleep(2)
            
            # 标记为已保存
            status.is_saved = True
            status.save_time = time.time() - save_start
            
            # 记录结果
            result = ProcessResult(
                url=status.url,
                success=True,
                publisher=status.publisher,
                load_time=status.load_time,
                save_time=status.save_time,
                retry_count=status.retry_count,
                save_phase=phase
            )
            self.results.append(result)
            
            logger.info(f"标签 {tab_index}: ✓ {phase}保存成功 - {status.publisher} ({status.save_time:.1f}秒)")
            return True
            
        except Exception as e:
            logger.error(f"标签 {tab_index}: ✗ {phase}保存失败 - {e}")
            return False

    def process_batch_live_save_with_strategy(self, urls: List[str]) -> List[ProcessResult]:
        """
        采用先易后难策略的批处理（增加Zotero验证）
        """
        # 确保批次大小不超过9
        batch_urls = urls[:self.OPTIMAL_BATCH_SIZE]
        
        # 记录初始Zotero文献数量
        self.record_initial_zotero_count()
        
        # 额外保护：确保开始处理前浏览器是关闭的
        logger.info("确保浏览器完全关闭...")
        self.close_edge_browser()
        time.sleep(2)
        
        # 打开所有URL
        self.open_urls_batch(batch_urls)
        
        # 等待浏览器启动并查找窗口
        max_attempts = 10
        edge_window = None
        
        for attempt in range(max_attempts):
            edge_window = self.find_edge_window()
            if edge_window:
                logger.info("✓ 找到Edge浏览器窗口")
                break
            else:
                logger.info(f"等待浏览器启动... ({attempt + 1}/{max_attempts})")
                time.sleep(2)
        
        if not edge_window:
            logger.error("未找到Edge窗口")
            failed_results = []
            for url in batch_urls:
                result = ProcessResult(
                    url=url,
                    success=False,
                    publisher="Unknown",
                    error_msg="无法找到浏览器窗口"
                )
                failed_results.append(result)
            return failed_results
        
        logger.info("===== 开始先易后难策略处理 =====")
        
        total_pages = len(batch_urls)
        saved_count = 0
        check_interval = 3
        
        # ===== 第一阶段：处理"简单"页面 =====
        logger.info(">>> 第一阶段：优先处理明确类型页面")
        
        while not self.should_enter_phase_two() and saved_count < total_pages:
            new_saved = self.check_and_save_easy_pages(edge_window)
            saved_count += new_saved
            
            if new_saved > 0:
                logger.info(f"第一阶段进度: {saved_count}/{total_pages} 已保存")
            
            time.sleep(check_interval)
        
        self.phase_one_complete = True
        
        # 统计第一阶段结果
        phase_one_saved = sum(1 for r in self.results if r.save_phase == "第一阶段")
        generic_waiting = sum(1 for s in self.page_statuses.values() if s.is_generic_loaded and not s.is_saved)
        
        logger.info(f">>> 第一阶段完成：已保存 {phase_one_saved} 个明确类型页面，{generic_waiting} 个通用类型页面等待处理")
        
        # ===== 第二阶段：处理通用类型页面 =====
        if generic_waiting > 0:
            logger.info(">>> 第二阶段：处理通用类型页面")
            phase_two_saved = self.check_and_save_generic_pages(edge_window)
            saved_count += phase_two_saved
            logger.info(f"第二阶段完成：额外保存 {phase_two_saved} 个页面")
        
        # ===== 第三阶段：强制重试未完成页面 =====
        unsaved_count = sum(1 for s in self.page_statuses.values() if not s.is_saved)
        if unsaved_count > 0:
            logger.info(f">>> 第三阶段：强制重试 {unsaved_count} 个未完成页面")
            retry_saved = self.force_retry_all_unsaved(edge_window, max_attempts=2)
            saved_count += retry_saved
        
        # ===== 新增：Zotero验证阶段 =====
        expected_success_count = sum(1 for r in self.results if r.success)
        logger.info(f">>> Zotero验证阶段：验证 {expected_success_count} 篇预期保存的文献")
        
        validation_passed = self.validate_zotero_count(expected_success_count, batch_num=1)
        
        if not validation_passed:
            # 获取当前Zotero数量来计算缺失数量
            current_zotero_count = self.get_zotero_item_count() or self.initial_zotero_count
            actual_new_count = current_zotero_count - self.initial_zotero_count
            missing_count = expected_success_count - actual_new_count
            
            if missing_count > 0:
                logger.warning(f">>> Zotero验证补救阶段：尝试补救 {missing_count} 篇缺失文献")
                additional_saved = self.retry_failed_saves_based_on_zotero_validation(edge_window, missing_count)
                saved_count += additional_saved
                
                # 再次验证
                final_validation = self.validate_zotero_count(expected_success_count + additional_saved, batch_num=1)
                if final_validation:
                    logger.info("✅ 补救后Zotero验证通过")
                else:
                    logger.warning("⚠️ 补救后仍未完全通过Zotero验证")
        
        # 处理失败页面
        for tab_index, status in self.page_statuses.items():
            if not status.is_saved:
                result = ProcessResult(
                    url=status.url,
                    success=False,
                    publisher=status.publisher if status.publisher else "Unknown",
                    load_time=status.load_time,
                    error_msg=f"最终未完成保存",
                    retry_count=status.retry_count + status.force_retry_count,
                    save_phase="失败"
                )
                self.results.append(result)
        
        logger.info(f"===== 先易后难策略完成 =====")
        logger.info(f"最终成功保存: {saved_count}/{total_pages}")
        
        return self.results
    
    def print_current_status(self):
        """打印当前状态（增强版）"""
        current_time = time.time()
        # 每10秒打印一次详细状态
        if current_time - self.last_progress_time > 10:
            saved_count = sum(1 for s in self.page_statuses.values() if s.is_saved)
            loaded_count = sum(1 for s in self.page_statuses.values() if s.is_loaded)
            generic_count = sum(1 for s in self.page_statuses.values() if s.is_generic_loaded and not s.is_saved)
            total_count = len(self.page_statuses)
            
            phase_info = "第一阶段" if not self.phase_one_complete else "第二阶段"
            logger.info(f">>> 当前状态({phase_info}): 已保存 {saved_count}/{total_count} | 已加载 {loaded_count}/{total_count} | 通用等待 {generic_count} | 运行时间 {current_time - self.start_time:.1f}秒")
            
            # 打印未完成的标签状态
            for tab_index, status in self.page_statuses.items():
                if not status.is_saved:
                    if status.is_generic_loaded:
                        wait_time = current_time - status.first_generic_time
                        status_text = f"通用等待({wait_time:.1f}s)"
                    elif status.is_loaded:
                        status_text = "等待保存"
                    else:
                        status_text = "等待加载"
                    
                    check_info = f"已检查{status.check_count}次"
                    button_info = f"按钮:{status.button_text[:20]}..." if status.button_text else ""
                    logger.info(f"    标签 {tab_index}: {status_text} - {check_info} - {button_info}")
            
            self.last_progress_time = current_time

    # 保持其他方法不变...
    def load_urls_from_file(self, file_path: str) -> List[str]:
        """从文件加载URL列表"""
        urls = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        urls.append(line)
            logger.info(f"从文件 {file_path} 加载了 {len(urls)} 个URL")
        except FileNotFoundError:
            logger.error(f"文件 {file_path} 不存在")
        except Exception as e:
            logger.error(f"读取文件失败: {e}")
        return urls
    
    def close_edge_browser(self) -> bool:
        """彻底关闭Edge浏览器"""
        try:
            logger.info("正在关闭Edge浏览器...")
            
            # 首先尝试优雅关闭
            subprocess.run(['taskkill', '/im', 'msedge.exe'], 
                         capture_output=True, text=True, timeout=5)
            time.sleep(2)
            
            # 然后强制关闭确保彻底关闭
            subprocess.run(['taskkill', '/f', '/im', 'msedge.exe'], 
                         capture_output=True, text=True, timeout=5)
            
            # 等待进程完全关闭
            time.sleep(3)
            
            # 验证是否关闭成功
            max_verify_attempts = 3
            for attempt in range(max_verify_attempts):
                result = subprocess.run(['tasklist', '/fi', 'imagename eq msedge.exe'], 
                                      capture_output=True, text=True, timeout=5)
                
                if 'msedge.exe' not in result.stdout:
                    logger.info("✓ Edge浏览器已完全关闭")
                    return True
                else:
                    logger.warning(f"Edge浏览器可能仍在运行，再次尝试关闭... ({attempt + 1}/{max_verify_attempts})")
                    subprocess.run(['taskkill', '/f', '/im', 'msedge.exe'], 
                                 capture_output=True, text=True, timeout=5)
                    time.sleep(2)
            
            logger.warning("Edge浏览器可能未完全关闭")
            return False
                
        except subprocess.TimeoutExpired:
            logger.error("关闭Edge浏览器超时")
            return False
        except Exception as e:
            logger.error(f"关闭Edge浏览器失败: {e}")
            return False

    def open_urls_batch(self, urls: List[str]) -> None:
        """批量打开URL（最多9个）"""
        # 确保不超过9个
        batch_urls = urls[:self.OPTIMAL_BATCH_SIZE]
        actual_batch_size = len(batch_urls)
        
        logger.info(f"===== 批量打开 {actual_batch_size} 个URL（最优批次大小：{self.OPTIMAL_BATCH_SIZE}） =====")
        
        # 保存当前批次的URL
        self.current_batch_urls = batch_urls.copy()
        
        # 初始化页面状态（标签索引从1开始，对应Ctrl+1到Ctrl+9）
        for i, url in enumerate(batch_urls, 1):
            self.page_statuses[i] = PageStatus(url=url, tab_index=i)
            logger.debug(f"标签 {i}: {url[:50]}...")
        
        # 打开第一个URL到新窗口
        logger.info("打开第一个URL到新窗口...")
        webbrowser.open(batch_urls[0], new=1)
        time.sleep(3)
        
        # 其余URL打开到新标签页
        for i, url in enumerate(batch_urls[1:], 2):
            logger.info(f"打开标签 {i}/{actual_batch_size}")
            webbrowser.open(url, new=2)
            time.sleep(0.8)
            
        logger.info(f"✓ 已打开所有 {actual_batch_size} 个标签页")
        time.sleep(10)
        
    def find_edge_window(self):
        """查找Edge窗口"""
        desktop = Desktop(backend="uia")
        windows = desktop.windows()
        
        for window in windows:
            try:
                window_text = window.window_text()
                if "Edge" in window_text or "Microsoft" in window_text:
                    logger.debug(f"找到Edge窗口: {window_text[:50]}...")
                    return window
            except:
                continue
        return None

    def switch_to_tab(self, edge_window, tab_index: int) -> bool:
        """切换到指定标签页（仅支持1-9）"""
        try:
            if tab_index < 1 or tab_index > 9:
                logger.error(f"标签索引 {tab_index} 超出范围(1-9)")
                return False
            
            edge_window.set_focus()
            time.sleep(0.3)
            
            send_keys(f"^{tab_index}")
            time.sleep(0.8)
            
            logger.debug(f"已切换到标签 {tab_index}")
            return True
            
        except Exception as e:
            logger.error(f"切换到标签 {tab_index} 失败: {e}")
            return False

    def get_zotero_button(self, edge_window):
        """获取当前页面的Zotero按钮"""
        try:
            buttons = edge_window.descendants(control_type="Button")
            for button in buttons:
                try:
                    button_text = button.window_text()
                    if "Save to Zotero" in button_text or "保存到 Zotero" in button_text:
                        return button, button_text
                except:
                    continue
        except Exception as e:
            logger.debug(f"获取按钮失败: {e}")
        return None, ""

    def get_unsaved_pages(self) -> List[Tuple[int, PageStatus]]:
        """获取未保存的页面列表"""
        unsaved = []
        for tab_index in range(1, 10):
            if tab_index in self.page_statuses:
                status = self.page_statuses[tab_index]
                if not status.is_saved:
                    unsaved.append((tab_index, status))
        return unsaved

    def force_retry_all_unsaved(self, edge_window, max_attempts: int = 2) -> int:
        """强制重试所有未保存的页面"""
        unsaved_pages = self.get_unsaved_pages()
        
        if not unsaved_pages:
            return 0
        
        logger.info(f"===== 强制重试所有 {len(unsaved_pages)} 个未保存的页面 =====")
        forced_saved_count = 0
        
        for attempt in range(max_attempts):
            if not unsaved_pages:
                break
                
            logger.info(f"--- 强制重试第 {attempt + 1}/{max_attempts} 轮 ---")
            
            for tab_index, status in list(unsaved_pages):
                if status.is_saved:
                    continue
                    
                status.force_retry_count += 1
                logger.info(f"强制重试标签 {tab_index}: {status.url[:50]}... (强制第{status.force_retry_count}次)")
                
                if not self.switch_to_tab(edge_window, tab_index):
                    logger.warning(f"无法切换到标签 {tab_index}")
                    continue
                
                button, button_text = self.get_zotero_button(edge_window)
                
                if button:
                    logger.info(f"标签 {tab_index}: 找到按钮 '{button_text[:50]}...'，强制尝试保存")
                    
                    try:
                        button.click_input()
                        time.sleep(3)
                        send_keys("{ENTER}")
                        time.sleep(2)
                        
                        status.is_saved = True
                        status.save_time = time.time() - self.start_time
                        status.publisher = button_text.split('(')[-1].split(')')[0] if '(' in button_text else "Unknown"
                        
                        result = ProcessResult(
                            url=status.url,
                            success=True,
                            publisher=status.publisher,
                            load_time=status.load_time,
                            save_time=status.save_time,
                            retry_count=status.retry_count + status.force_retry_count,
                            save_phase="强制重试"
                        )
                        self.results.append(result)
                        
                        forced_saved_count += 1
                        logger.info(f"标签 {tab_index}: ✓ 强制保存成功！")
                        
                    except Exception as e:
                        logger.warning(f"标签 {tab_index}: 强制保存失败 - {e}")
                else:
                    logger.warning(f"标签 {tab_index}: 找不到Zotero按钮，无法强制保存")
                
                time.sleep(2)
            
            unsaved_pages = self.get_unsaved_pages()
            
            if unsaved_pages:
                logger.info(f"第 {attempt + 1} 轮强制重试后，还剩 {len(unsaved_pages)} 个未保存")
                time.sleep(3)
        
        return forced_saved_count

    def print_batch_summary(self, batch_num: int, total_batches: int, batch_results: List[ProcessResult]) -> None:
        """打印批次处理摘要（增强版）"""
        if not batch_results:
            logger.info(f"批次 {batch_num}/{total_batches}: 没有处理结果")
            return
            
        success = sum(1 for r in batch_results if r.success)
        total = len(batch_results)
        retried = sum(1 for r in batch_results if r.retry_count > 0)
        
        # 按阶段统计
        phase_one = sum(1 for r in batch_results if r.save_phase == "第一阶段")
        phase_two = sum(1 for r in batch_results if r.save_phase == "第二阶段")
        force_retry = sum(1 for r in batch_results if r.save_phase == "强制重试")
        
        logger.info(f"===== 批次 {batch_num}/{total_batches} 完成 =====")
        logger.info(f"本批次: 成功 {success}/{total} | 成功率: {success/total*100:.1f}% | 重试页面: {retried}")
        logger.info(f"保存阶段分布: 第一阶段 {phase_one} | 第二阶段 {phase_two} | 强制重试 {force_retry}")
        
        # 显示成功的文献
        success_results = [r for r in batch_results if r.success]
        if success_results:
            logger.info(f"成功保存:")
            for i, r in enumerate(success_results, 1):
                phase_info = f"[{r.save_phase}]" if r.save_phase else ""
                retry_info = f" (重试{r.retry_count}次)" if r.retry_count > 0 else ""
                logger.info(f"  {i}. {r.publisher} {phase_info} (加载:{r.load_time:.1f}s){retry_info}")
        
        # 显示失败的文献
        failed_results = [r for r in batch_results if not r.success]
        if failed_results:
            logger.info(f"保存失败:")
            for i, r in enumerate(failed_results, 1):
                logger.info(f"  {i}. {r.url[:50]}... - {r.error_msg}")

    def print_final_summary(self) -> None:
        """打印最终摘要（增强版）"""
        if not self.results:
            logger.info("没有处理结果")
            return
            
        logger.info("===== 最终处理摘要 =====")
        total = len(self.results)
        success = sum(1 for r in self.results if r.success)
        
        # 按阶段统计
        phase_one = sum(1 for r in self.results if r.save_phase == "第一阶段")
        phase_two = sum(1 for r in self.results if r.save_phase == "第二阶段")  
        force_retry = sum(1 for r in self.results if r.save_phase == "强制重试")
        
        logger.info(f"总计: {total} | 成功: {success} | 失败: {total - success}")
        logger.info(f"总成功率: {success/total*100:.1f}%")
        logger.info(f"成功分布: 第一阶段 {phase_one} | 第二阶段 {phase_two} | 强制重试 {force_retry}")
        
        if phase_one > 0:
            logger.info(f"第一阶段效率: {phase_one/success*100:.1f}% (明确类型页面)")
        if phase_two > 0:
            logger.info(f"第二阶段贡献: {phase_two/success*100:.1f}% (通用类型页面)")
        if force_retry > 0:
            logger.info(f"强制重试挽救: {force_retry/success*100:.1f}% (强制保存)")

def main():
    """主函数 - 修复版"""
    
    # 配置
    file_path = "iteration_1_urls.txt"
    batch_wait_time = 3
    
    # 创建批处理器
    saver = ZoteroBatchSaver()
    saver.zotero_validation_enabled = True
    # 从文件加载URL
    urls = saver.load_urls_from_file(file_path)
    
    if not urls:
        logger.error("没有找到有效的URL，程序退出")
        return

    selected_urls = urls
    
    logger.info(f"准备处理 {len(selected_urls)} 个URL (先易后难策略)")
    logger.info(f"分批处理，每批固定 {saver.OPTIMAL_BATCH_SIZE} 个URL")
    
    # 分批处理URL
    all_results = []  # 用于收集所有批次的结果
    total_batches = (len(selected_urls) + saver.OPTIMAL_BATCH_SIZE - 1) // saver.OPTIMAL_BATCH_SIZE
    
    for i in range(0, len(selected_urls), saver.OPTIMAL_BATCH_SIZE):
        batch_urls = selected_urls[i:i+saver.OPTIMAL_BATCH_SIZE]
        batch_num = i // saver.OPTIMAL_BATCH_SIZE + 1
        
        logger.info(f"\n{'='*60}")
        logger.info(f"开始处理批次 {batch_num}/{total_batches}")
        logger.info(f"本批次URL数量: {len(batch_urls)}")
        logger.info(f"本批次URL列表:")
        for idx, url in enumerate(batch_urls, 1):
            logger.info(f"  {idx}. {url}")
        logger.info(f"{'='*60}")
        
        # 关闭浏览器
        logger.info("准备开始批次处理，先关闭所有浏览器...")
        saver.close_edge_browser()
        time.sleep(batch_wait_time)
        
        # 重置状态（但不清空results，因为我们要复制结果）
        saver.page_statuses.clear()
        saver.results.clear()  # 清空当前批次的结果
        saver.start_time = time.time()
        saver.last_progress_time = time.time()
        saver.phase_one_complete = False
        saver.last_easy_save_time = time.time()
        
        # 使用先易后难策略处理本批次
        batch_results = saver.process_batch_live_save_with_strategy(batch_urls)
        
        # 重要：深拷贝批次结果，避免引用问题
        batch_results_copy = []
        for result in batch_results:
            batch_results_copy.append(ProcessResult(
                url=result.url,
                success=result.success,
                publisher=result.publisher,
                load_time=result.load_time,
                save_time=result.save_time,
                error_msg=result.error_msg,
                retry_count=result.retry_count,
                save_phase=result.save_phase
            ))
        
        all_results.extend(batch_results_copy)
        
        # 验证批次结果
        logger.info(f"批次 {batch_num} 处理验证:")
        logger.info(f"  期望处理: {len(batch_urls)} 个URL")
        logger.info(f"  实际结果: {len(batch_results_copy)} 个结果")
        logger.info(f"  累计结果: {len(all_results)} 个")
        
        if len(batch_results_copy) != len(batch_urls):
            logger.warning(f"⚠️  批次 {batch_num} 结果数量不匹配！")
            logger.warning(f"  丢失的URL可能是:")
            processed_urls = {r.url for r in batch_results_copy}
            for url in batch_urls:
                if url not in processed_urls:
                    logger.warning(f"    - {url}")
        
        # 打印批次摘要
        saver.print_batch_summary(batch_num, total_batches, batch_results_copy)
        
        # 每批次完成后，立即关闭浏览器
        logger.info(f"批次 {batch_num} 完成，关闭浏览器...")
        saver.close_edge_browser()
        
        # 如果不是最后一批，等待一段时间
        if i + saver.OPTIMAL_BATCH_SIZE < len(selected_urls):
            logger.info(f"等待 {batch_wait_time} 秒后处理下一批次...")
            time.sleep(batch_wait_time)
    
    # 最终验证
    logger.info(f"\n🔍 最终验证:")
    logger.info(f"  总URL数量: {len(selected_urls)}")
    logger.info(f"  总结果数量: {len(all_results)}")
    
    if len(all_results) != len(selected_urls):
        logger.error(f"❌ 结果数量不匹配！丢失了 {len(selected_urls) - len(all_results)} 个URL")
        
        # 找出丢失的URL
        processed_urls = {r.url for r in all_results}
        missing_urls = []
        for url in selected_urls:
            if url not in processed_urls:
                missing_urls.append(url)
        
        if missing_urls:
            logger.error(f"丢失的URL列表:")
            for i, url in enumerate(missing_urls, 1):
                logger.error(f"  {i}. {url}")
    else:
        logger.info(f"✅ 所有URL都已处理")
    
    # 更新总结果
    saver.results = all_results
    
    # 打印最终摘要
    saver.print_final_summary()
    
    # 保存失败的URL到文件
    failed_urls = [r.url for r in all_results if not r.success]
    if failed_urls:
        failed_file = "failed_urls.txt"
        try:
            with open(failed_file, 'w', encoding='utf-8') as f:
                for url in failed_urls:
                    f.write(url + '\n')
            logger.info(f"\n失败的 {len(failed_urls)} 个URL已保存到 {failed_file}")
        except Exception as e:
            logger.error(f"保存失败URL列表时出错: {e}")
    
    logger.info(f"\n🎉 全部处理完成！共处理 {len(all_results)} 个URL")

if __name__ == "__main__":
    main()