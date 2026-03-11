import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
                             QLineEdit, QLabel, QMessageBox, QDialog, QFormLayout,
                             QTextEdit, QSpinBox, QTabWidget, QStackedWidget, QGroupBox,
                             QGridLayout, QSizePolicy, QProgressDialog, QDialogButtonBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.font_manager as fm
import pandas as pd
import seaborn as sns
import numpy as np
from wordcloud import WordCloud
import jieba
from database import WeiboDatabase
from weibo_spider import WeiboSpider

# 配置中文字体
def setup_chinese_font():
    """配置matplotlib中文字体"""
    font_paths = [
        'C:\\Windows\\Fonts\\msyh.ttc',      # 微软雅黑
        'C:\\Windows\\Fonts\\msyhbd.ttc',    # 微软雅黑粗体
        'C:\\Windows\\Fonts\\simhei.ttf',    # 黑体
        'C:\\Windows\\Fonts\\simsun.ttc',    # 宋体
        'C:\\Windows\\Fonts\\simkai.ttf',    # 楷体
    ]
    
    font_found = None
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                font_prop = fm.FontProperties(fname=font_path)
                font_name = font_prop.get_name()
                if font_name:
                    font_found = font_name
                    break
            except:
                continue
    
    if font_found:
        plt.rcParams['font.sans-serif'] = [font_found]
        plt.rcParams['font.family'] = 'sans-serif'
    else:
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'SimSun', 'KaiTi']
    
    plt.rcParams['axes.unicode_minus'] = False
    
    return font_paths[0] if os.path.exists(font_paths[0]) else (
           font_paths[2] if os.path.exists(font_paths[2]) else None)

CHINESE_FONT_PATH = setup_chinese_font()
sns.set_style("whitegrid")
sns.set_palette("husl")

class SpiderThread(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    
    def __init__(self, keyword, start_page, end_page, min_delay=60, max_delay=180):
        super().__init__()
        self.keyword = keyword
        self.start_page = start_page
        self.end_page = end_page
        self.min_delay = min_delay
        self.max_delay = max_delay
    
    def run(self):
        try:
            spider = WeiboSpider()
            posts = spider.crawl_by_keyword(self.keyword, self.start_page, self.end_page, 
                                           self.min_delay, self.max_delay)
            spider.close()
            self.finished.emit(posts)
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            self.error.emit(f"{str(e)}\n\n{error_detail}")

class CrawlDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("爬取设置")
        self.setMinimumWidth(400)
        layout = QFormLayout()
        
        self.keyword_edit = QLineEdit()
        self.keyword_edit.setPlaceholderText("例如: 咖啡")
        
        self.start_page_spin = QSpinBox()
        self.start_page_spin.setMinimum(1)
        self.start_page_spin.setMaximum(9999)
        self.start_page_spin.setValue(1)
        
        self.end_page_spin = QSpinBox()
        self.end_page_spin.setMinimum(1)
        self.end_page_spin.setMaximum(9999)
        self.end_page_spin.setValue(5)
        
        self.min_delay_spin = QSpinBox()
        self.min_delay_spin.setMinimum(10)
        self.min_delay_spin.setMaximum(600)
        self.min_delay_spin.setValue(60)
        self.min_delay_spin.setSuffix(" 秒")
        
        self.max_delay_spin = QSpinBox()
        self.max_delay_spin.setMinimum(10)
        self.max_delay_spin.setMaximum(600)
        self.max_delay_spin.setValue(180)
        self.max_delay_spin.setSuffix(" 秒")
        
        layout.addRow("搜索关键词:", self.keyword_edit)
        layout.addRow("起始页:", self.start_page_spin)
        layout.addRow("结束页:", self.end_page_spin)
        layout.addRow("最小间隔:", self.min_delay_spin)
        layout.addRow("最大间隔:", self.max_delay_spin)
        
        info_label = QLabel("提示: 每页约包含10-20条微博\n页数越多，爬取时间越长\n建议间隔60-180秒，避免被检测")
        info_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addRow(info_label)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        
        self.setLayout(layout)
    
    def get_params(self):
        return {
            'keyword': self.keyword_edit.text(),
            'start_page': self.start_page_spin.value(),
            'end_page': self.end_page_spin.value(),
            'min_delay': self.min_delay_spin.value(),
            'max_delay': self.max_delay_spin.value()
        }

class FilterWordsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("屏蔽词设置")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self.setup_ui()
        self.load_words()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        info_label = QLabel("每行输入一个屏蔽词，这些词将不会出现在词云和词频统计中：")
        info_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(info_label)
        
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("例如：\n咖啡\n喝咖啡\n展开\n...")
        layout.addWidget(self.text_edit)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def load_words(self):
        """加载当前屏蔽词"""
        import config
        custom_words = set()
        if os.path.exists(config.STOP_WORDS_FILE):
            try:
                with open(config.STOP_WORDS_FILE, 'r', encoding='utf-8') as f:
                    import json
                    custom_words = set(json.load(f))
            except:
                pass
        
        # 获取默认屏蔽词
        default_words = config.load_stop_words()
        # 只显示用户自定义的屏蔽词（排除默认的）
        default_stop_words = {
            '转发', '微博', 'http', 'https', 'com', 'www', 'weibo', 'sinaimg', 'cn', 't', 'co',
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
            '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
            '自己', '这', '那', '可以', '能', '会', '要', '什么', '怎么', '为什么', '这个', '那个',
            '这样', '那样', '还是', '展开', '全文', '收起', '查看', '更多', '详情',
            '点击', '链接', '图片', '视频', '话题', '超话', '热搜'
        }
        user_words = custom_words - default_stop_words
        self.text_edit.setText('\n'.join(sorted(user_words)))
    
    def get_words(self):
        """获取用户输入的屏蔽词"""
        text = self.text_edit.toPlainText()
        words = [w.strip() for w in text.split('\n') if w.strip()]
        return set(words)

class EditDialog(QDialog):
    def __init__(self, post_data=None, parent=None):
        super().__init__(parent)
        self.post_data = post_data
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("编辑微博")
        self.setMinimumWidth(500)
        layout = QFormLayout()
        
        self.user_name_edit = QLineEdit()
        self.content_edit = QTextEdit()
        self.likes_spin = QSpinBox()
        self.likes_spin.setMaximum(99999999)
        self.comments_spin = QSpinBox()
        self.comments_spin.setMaximum(99999999)
        self.reposts_spin = QSpinBox()
        self.reposts_spin.setMaximum(99999999)
        self.post_time_edit = QLineEdit()
        self.url_edit = QLineEdit()
        
        if self.post_data:
            self.user_name_edit.setText(self.post_data[1])
            self.content_edit.setText(self.post_data[2])
            self.likes_spin.setValue(self.post_data[3])
            self.comments_spin.setValue(self.post_data[4])
            self.reposts_spin.setValue(self.post_data[5])
            self.post_time_edit.setText(self.post_data[6])
            self.url_edit.setText(self.post_data[8])
        
        layout.addRow("用户名:", self.user_name_edit)
        layout.addRow("内容:", self.content_edit)
        layout.addRow("点赞数:", self.likes_spin)
        layout.addRow("评论数:", self.comments_spin)
        layout.addRow("转发数:", self.reposts_spin)
        layout.addRow("发布时间:", self.post_time_edit)
        layout.addRow("链接:", self.url_edit)
        
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        cancel_btn = QPushButton("取消")
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        
        layout.addRow(btn_layout)
        self.setLayout(layout)
    
    def get_data(self):
        return {
            'user_name': self.user_name_edit.text(),
            'content': self.content_edit.toPlainText(),
            'likes': self.likes_spin.value(),
            'comments': self.comments_spin.value(),
            'reposts': self.reposts_spin.value(),
            'post_time': self.post_time_edit.text(),
            'url': self.url_edit.text()
        }

class ChartWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.figure = Figure(figsize=(16, 8), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        # 加载屏蔽词
        import config
        self.stop_words = config.load_stop_words()
    
    def plot_data(self, data):
        self.figure.clear()
        
        # 每次绘图前重新设置中文字体
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'SimSun', 'KaiTi', 'Arial Unicode MS']
        plt.rcParams['axes.unicode_minus'] = False
        
        if not data or len(data) == 0:
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, '暂无数据', ha='center', va='center', fontsize=20)
            ax.axis('off')
            self.canvas.draw()
            return
        
        df = pd.DataFrame(data, columns=['ID', '用户名', '内容', '点赞', '评论', '转发', 
                                         '发布时间', '爬取时间', '链接'])
        
        df['用户名'] = df['用户名'].astype(str).str.strip()
        df['内容'] = df['内容'].astype(str).str.strip()
        df = df[df['用户名'] != '']
        df = df[df['用户名'] != 'nan']
        df = df[df['内容'] != '']
        df = df[df['内容'] != 'nan']
        
        if len(df) == 0:
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, '数据为空', ha='center', va='center', fontsize=20)
            ax.axis('off')
            self.canvas.draw()
            return
        
        # 使用GridSpec创建自定义布局：左侧大词云，右侧2个小图表
        from matplotlib.gridspec import GridSpec
        gs = GridSpec(2, 3, figure=self.figure, width_ratios=[2, 1, 1], height_ratios=[1, 1], 
                     hspace=0.3, wspace=0.3)
        
        # 1. 大词云图（占据左侧2列2行）
        ax_wordcloud = self.figure.add_subplot(gs[:, 0])
        try:
            valid_contents = [str(x).strip() for x in df['内容'] if x and str(x).strip() and str(x).strip() != 'nan']
            all_text = ' '.join(valid_contents)
            words = jieba.cut(all_text)
            
            # 使用自定义屏蔽词（从config加载）
            stop_words = self.stop_words.copy()
            
            # 统计词频，找出可能是搜索关键词的高频词
            from collections import Counter
            word_freq = Counter()
            for w in words:
                w = w.strip()
                if len(w) > 1 and w not in stop_words and not w.isspace() and not w.isdigit():
                    # 过滤掉符号和特殊字符
                    if not any(char in w for char in '，。！？、；：""''（）【】《》<>[]{}()'):
                        word_freq[w] += 1
            
            # 找出TOP5高频词，可能是搜索关键词，需要过滤
            top_keywords = [w for w, _ in word_freq.most_common(5)]
            
            # 如果某个词出现频率过高（超过总词数的30%），很可能是搜索关键词
            total_count = sum(word_freq.values())
            filtered_word_freq = {}
            for w, count in word_freq.items():
                # 过滤条件：
                # 1. 不在停用词列表中
                # 2. 不是单字词
                # 3. 不是数字
                # 4. 不包含符号
                # 5. 不是搜索关键词（频率过高或在前5名）
                if (w not in stop_words and 
                    len(w) > 1 and 
                    not w.isdigit() and
                    not any(char in w for char in '，。！？、；：""''（）【】《》<>[]{}()') and
                    count / total_count < 0.3):  # 频率不超过30%
                    filtered_word_freq[w] = count
            
            # 如果过滤后词太少，放宽条件（只过滤TOP1）
            if len(filtered_word_freq) < 20 and len(top_keywords) > 0:
                top1 = top_keywords[0]
                filtered_word_freq = {w: count for w, count in word_freq.items() 
                                     if w != top1 and w not in stop_words and len(w) > 1 
                                     and not w.isdigit() and not any(char in w for char in '，。！？、；：""''（）【】《》<>[]{}()')}
            
            # 如果过滤后词太少，使用原始词频（只过滤TOP1）
            if len(filtered_word_freq) < 20:
                # 重新生成，只过滤TOP1高频词
                if len(word_freq) > 0:
                    top1 = word_freq.most_common(1)[0][0]
                    filtered_word_freq = {w: count for w, count in word_freq.items() 
                                         if w != top1 and w not in stop_words and len(w) > 1 
                                         and not w.isdigit() and not any(char in w for char in '，。！？、；：""''（）【】《》<>[]{}()')}
            
            if len(filtered_word_freq) > 10:
                
                # 尝试多个字体路径
                font_paths = [
                    'C:\\Windows\\Fonts\\msyh.ttc',
                    'C:\\Windows\\Fonts\\simhei.ttf',
                    'C:\\Windows\\Fonts\\simsun.ttc',
                    'C:\\Windows\\Fonts\\simkai.ttf'
                ]
                font_path = None
                for fp in font_paths:
                    if os.path.exists(fp):
                        font_path = fp
                        break
                
                try:
                    # 尝试创建圆形mask，如果失败则使用无mask版本
                    mask_image = None
                    try:
                        from PIL import Image
                        # 创建圆形mask
                        mask_size = 800
                        mask = np.zeros((mask_size, mask_size), dtype=np.uint8)
                        center = mask_size // 2
                        radius = mask_size // 2 - 20
                        
                        y, x = np.ogrid[:mask_size, :mask_size]
                        mask_circle = (x - center) ** 2 + (y - center) ** 2 <= radius ** 2
                        mask[mask_circle] = 255
                        
                        # 转换为PIL Image
                        mask_image = Image.fromarray(mask)
                    except Exception as mask_error:
                        # mask创建失败，使用无mask版本
                        mask_image = None
                    
                    # 创建词云参数 - 透明背景，每个词只出现一次
                    wordcloud_params = {
                        'width': 1200,
                        'height': 800,
                        'background_color': None,  # 透明背景
                        'mode': 'RGBA',  # 使用RGBA模式支持透明
                        'font_path': font_path,
                        'colormap': 'viridis',
                        'max_words': min(200, len(filtered_word_freq)),  # 最多显示200个词或所有词
                        'relative_scaling': 0.8,  # 增加相对缩放，让大小差异更明显
                        'min_font_size': 15,  # 最小字体
                        'max_font_size': 180,  # 最大字体（排名第一的词）
                        'prefer_horizontal': 0.6,
                        'collocations': False,
                        'margin': 5,
                        'contour_width': 0,
                        'random_state': 42
                    }
                    
                    # 如果mask创建成功，添加mask参数
                    if mask_image is not None:
                        wordcloud_params['mask'] = mask_image
                    
                    # 直接使用词频字典生成词云，每个词只出现一次
                    wordcloud = WordCloud(**wordcloud_params).generate_from_frequencies(filtered_word_freq)
                    
                    # 确保词云生成成功
                    if wordcloud is not None:
                        # 如果是RGBA模式，需要处理透明背景
                        if wordcloud_params.get('mode') == 'RGBA':
                            ax_wordcloud.imshow(wordcloud, interpolation='bilinear', aspect='auto')
                        else:
                            ax_wordcloud.imshow(wordcloud, interpolation='bilinear', aspect='auto')
                        ax_wordcloud.set_title('关键词云图', fontsize=16, fontweight='bold', pad=15)
                        ax_wordcloud.axis('off')
                        # 设置背景为白色（因为词云背景是透明的）
                        ax_wordcloud.set_facecolor('white')
                        # 设置figure背景也为白色
                        self.figure.patch.set_facecolor('white')
                    else:
                        raise Exception("词云对象为空")
                except Exception as e:
                    # 打印错误信息以便调试
                    print(f"词云生成错误: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    # 尝试使用更简单的参数重新生成
                    try:
                        simple_wordcloud = WordCloud(
                            width=1200, height=800,
                            background_color=None,  # 透明背景
                            mode='RGBA',
                            font_path=font_path,
                            colormap='viridis',
                            max_words=min(100, len(filtered_word_freq)),
                            relative_scaling=0.8,
                            min_font_size=15,
                            max_font_size=150
                        ).generate_from_frequencies(filtered_word_freq)
                        ax_wordcloud.imshow(simple_wordcloud, interpolation='bilinear', aspect='auto')
                        ax_wordcloud.set_title('关键词云图', fontsize=16, fontweight='bold', pad=15)
                        ax_wordcloud.axis('off')
                        ax_wordcloud.set_facecolor('white')
                        self.figure.patch.set_facecolor('white')
                    except Exception as e2:
                        ax_wordcloud.text(0.5, 0.5, f'词云生成失败\n{str(e2)[:100]}', ha='center', va='center', 
                                        fontsize=12)
                        ax_wordcloud.set_title('关键词云图', fontsize=16, fontweight='bold', pad=15)
                        ax_wordcloud.set_facecolor('white')
                        ax_wordcloud.axis('off')
            else:
                ax_wordcloud.text(0.5, 0.5, '数据不足，无法生成词云', ha='center', va='center', 
                                fontsize=14)
                ax_wordcloud.set_title('关键词云图', fontsize=16, fontweight='bold', pad=15)
                ax_wordcloud.set_facecolor('white')
                ax_wordcloud.axis('off')
        except Exception as e:
            ax_wordcloud.text(0.5, 0.5, f'词云生成异常\n{str(e)[:50]}', ha='center', va='center', 
                            fontsize=12)
            ax_wordcloud.set_title('关键词云图', fontsize=16, fontweight='bold', pad=15)
            ax_wordcloud.set_facecolor('white')
            ax_wordcloud.axis('off')
        
        # 2. TOP20高频词条形图（右上）
        ax_freq = self.figure.add_subplot(gs[0, 1:])
        try:
            from collections import Counter
            valid_contents = [str(x).strip() for x in df['内容'] if x and str(x).strip() and str(x).strip() != 'nan']
            all_text = ' '.join(valid_contents)
            words = jieba.cut(all_text)
            
            # 使用自定义屏蔽词
            stop_words = self.stop_words.copy()
            
            # 统计词频
            word_freq_temp = Counter()
            for w in words:
                w = w.strip()
                if (len(w) > 1 and w not in stop_words and not w.isspace() and not w.isdigit() and
                    not any(char in w for char in '，。！？、；：""''（）【】《》<>[]{}()')):
                    word_freq_temp[w] += 1
            
            # 过滤掉可能是搜索关键词的高频词
            total_count = sum(word_freq_temp.values())
            filtered_word_freq = {}
            for w, count in word_freq_temp.items():
                if count / total_count < 0.3:  # 频率不超过30%
                    filtered_word_freq[w] = count
            
            # 如果过滤后词太少，只过滤TOP1
            if len(filtered_word_freq) < 20 and len(word_freq_temp) > 0:
                top1 = word_freq_temp.most_common(1)[0][0]
                filtered_word_freq = {w: count for w, count in word_freq_temp.items() if w != top1}
            
            top_words = sorted(filtered_word_freq.items(), key=lambda x: x[1], reverse=True)[:20]
            
            if len(top_words) > 0:
                words_list = [w[0] for w in top_words]
                freq_list = [w[1] for w in top_words]
                
                # 使用渐变色
                colors = sns.color_palette("viridis", len(words_list))
                bars = ax_freq.barh(range(len(words_list)), freq_list, color=colors)
                ax_freq.set_yticks(range(len(words_list)))
                ax_freq.set_yticklabels(words_list, fontsize=10)
                ax_freq.set_xlabel('出现频次', fontsize=11, fontweight='bold')
                ax_freq.set_title('TOP20 高频词', fontsize=12, fontweight='bold', pad=10)
                
                # 在条形图上显示数值
                for i, (bar, freq) in enumerate(zip(bars, freq_list)):
                    ax_freq.text(freq, i, f' {freq}', va='center', fontsize=9, fontweight='bold')
                
                ax_freq.grid(axis='x', alpha=0.3, linestyle='--')
                ax_freq.tick_params(labelsize=9)
                # 反转Y轴，使最高频词在顶部
                ax_freq.invert_yaxis()
            else:
                ax_freq.text(0.5, 0.5, '数据不足', ha='center', va='center', fontsize=11)
                ax_freq.set_title('TOP20 高频词', fontsize=12, fontweight='bold', pad=10)
                ax_freq.axis('off')
        except Exception as e:
            ax_freq.text(0.5, 0.5, '词频统计失败', ha='center', va='center', fontsize=11)
            ax_freq.set_title('TOP20 高频词', fontsize=12, fontweight='bold', pad=10)
            ax_freq.axis('off')
        
        # 3. 内容长度分布直方图（占据右下两个位置）
        ax_length = self.figure.add_subplot(gs[1, 1:])
        try:
            df['内容长度'] = df['内容'].astype(str).str.len()
            lengths = df['内容长度'].values
            
            if len(lengths) > 0:
                # 计算统计信息
                mean_len = lengths.mean()
                median_len = np.median(lengths)
                
                # 绘制直方图
                n, bins, patches = ax_length.hist(lengths, bins=30, color='#4ECDC4', 
                                                  edgecolor='black', alpha=0.7, linewidth=1.2)
                
                # 添加平均值和中位数线
                ax_length.axvline(mean_len, color='#FF6B6B', linestyle='--', linewidth=2, 
                                 label=f'平均值: {int(mean_len)}')
                ax_length.axvline(median_len, color='#45B7D1', linestyle='--', linewidth=2, 
                                 label=f'中位数: {int(median_len)}')
                
                ax_length.set_xlabel('内容长度（字符数）', fontsize=10, fontweight='bold')
                ax_length.set_ylabel('频次', fontsize=10, fontweight='bold')
                ax_length.set_title('内容长度分布', fontsize=12, fontweight='bold', pad=10)
                ax_length.legend(fontsize=8, loc='upper right')
                ax_length.grid(axis='y', alpha=0.3, linestyle='--')
                ax_length.tick_params(labelsize=9)
            else:
                ax_length.text(0.5, 0.5, '数据不足', ha='center', va='center', fontsize=11)
                ax_length.set_title('内容长度分布', fontsize=12, fontweight='bold', pad=10)
                ax_length.axis('off')
        except Exception as e:
            ax_length.text(0.5, 0.5, '长度分析失败', ha='center', va='center', fontsize=11)
            ax_length.set_title('内容长度分布', fontsize=12, fontweight='bold', pad=10)
            ax_length.axis('off')
        
        self.figure.tight_layout(pad=2.0)
        self.canvas.draw()

class WeiboApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = WeiboDatabase()
        self.setup_ui()
        # 延迟加载数据，优化启动速度
        # self.load_data()  # 注释掉，改为按需加载
        self.apply_styles()
        # 初始化数据加载标志
        self.data_loaded = False
    
    def setup_ui(self):
        self.setWindowTitle("微博爬虫管理系统")
        self.setGeometry(100, 100, 1400, 800)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout()
        main_widget.setLayout(main_layout)
        
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel)
        
        self.stacked_widget = QStackedWidget()
        
        home_page = self.create_home_page()
        query_page = self.create_query_page()
        add_page = self.create_add_page()
        manage_page = self.create_manage_page()
        chart_page = self.create_chart_page()
        
        self.stacked_widget.addWidget(home_page)
        self.stacked_widget.addWidget(query_page)
        self.stacked_widget.addWidget(add_page)
        self.stacked_widget.addWidget(manage_page)
        self.stacked_widget.addWidget(chart_page)
        
        main_layout.addWidget(self.stacked_widget, 4)
    
    def create_left_panel(self):
        panel = QWidget()
        panel.setFixedWidth(220)
        layout = QVBoxLayout()
        panel.setLayout(layout)
        
        title = QLabel("功能菜单")
        title.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        layout.addSpacing(20)
        
        home_btn = self.create_menu_button("🏠 首页", 0)
        query_btn = self.create_menu_button("🔍 数据查询", 1)
        add_btn = self.create_menu_button("➕ 数据新增", 2)
        manage_btn = self.create_menu_button("📝 数据管理", 3)
        chart_btn = self.create_menu_button("📊 数据可视化", 4)
        
        layout.addWidget(home_btn)
        layout.addWidget(query_btn)
        layout.addWidget(add_btn)
        layout.addWidget(manage_btn)
        layout.addWidget(chart_btn)
        
        layout.addStretch()
        
        crawl_btn = QPushButton("🕷️ 开始爬取")
        crawl_btn.setMinimumHeight(50)
        crawl_btn.clicked.connect(self.start_crawl)
        layout.addWidget(crawl_btn)
        
        return panel
    
    def create_menu_button(self, text, page_index):
        btn = QPushButton(text)
        btn.setMinimumHeight(50)
        btn.setCheckable(True)
        btn.clicked.connect(lambda: self.switch_page(page_index))
        if page_index == 0:
            btn.setChecked(True)
        return btn
    
    def switch_page(self, index):
        self.stacked_widget.setCurrentIndex(index)
        # 按需加载数据，优化性能
        if index == 1:  # 数据查询页面
            if not hasattr(self, 'query_data_loaded') or not self.query_data_loaded:
                self.load_data_paginated(1, page_type='query')
        elif index == 3:  # 数据管理页面
            if not hasattr(self, 'manage_data_loaded') or not self.manage_data_loaded:
                self.load_data_paginated(1, page_type='manage')
        elif index == 4:  # 数据可视化页面
            self.update_chart()
    
    def create_home_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        page.setLayout(layout)
        
        title = QLabel("微博爬虫管理系统")
        title.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(28)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        layout.addSpacing(30)
        
        grid = QGridLayout()
        
        query_box = self.create_feature_box("🔍 数据查询", "查看和搜索所有爬取的微博数据", 1)
        add_box = self.create_feature_box("➕ 数据新增", "手动添加新的微博数据记录", 2)
        manage_box = self.create_feature_box("📝 数据管理", "编辑和删除现有的微博数据", 3)
        chart_box = self.create_feature_box("📊 数据可视化", "查看数据统计图表和分析", 4)
        
        grid.addWidget(query_box, 0, 0)
        grid.addWidget(add_box, 0, 1)
        grid.addWidget(manage_box, 1, 0)
        grid.addWidget(chart_box, 1, 1)
        
        layout.addLayout(grid)
        layout.addStretch()
        
        stats = self.create_stats_panel()
        layout.addWidget(stats)
        
        return page
    
    def create_feature_box(self, title, desc, page_index):
        box = QGroupBox()
        box.setMinimumHeight(150)
        layout = QVBoxLayout()
        box.setLayout(layout)
        
        title_label = QLabel(title)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        desc_label = QLabel(desc)
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        btn = QPushButton("进入")
        btn.clicked.connect(lambda: self.switch_page(page_index))
        layout.addWidget(btn)
        
        return box
    
    def create_stats_panel(self):
        panel = QGroupBox("数据统计")
        layout = QHBoxLayout()
        panel.setLayout(layout)
        
        stats = self.db.get_statistics()
        
        self.total_label = QLabel(f"总数据量: {stats[0] if stats[0] else 0}")
        self.likes_label = QLabel(f"总点赞: {stats[1] if stats[1] else 0}")
        self.comments_label = QLabel(f"总评论: {stats[2] if stats[2] else 0}")
        self.reposts_label = QLabel(f"总转发: {stats[3] if stats[3] else 0}")
        
        for label in [self.total_label, self.likes_label, self.comments_label, self.reposts_label]:
            label.setAlignment(Qt.AlignCenter)
            label_font = QFont()
            label_font.setPointSize(12)
            label.setFont(label_font)
            layout.addWidget(label)
        
        return panel
    
    def create_query_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        page.setLayout(layout)
        
        title = QLabel("数据查询")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入关键词搜索用户名或内容...")
        self.search_input.setMinimumHeight(35)
        search_btn = QPushButton("🔍 搜索")
        search_btn.setMinimumHeight(35)
        search_btn.clicked.connect(self.search_data)
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.setMinimumHeight(35)
        refresh_btn.clicked.connect(lambda: self.load_data_paginated(1))
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(search_btn)
        search_layout.addWidget(refresh_btn)
        layout.addLayout(search_layout)
        
        # 分页控件
        page_layout = QHBoxLayout()
        self.query_page_spin = QSpinBox()
        self.query_page_spin.setMinimum(1)
        self.query_page_spin.setMaximum(999999)
        self.query_page_spin.setValue(1)
        self.query_page_spin.setMinimumWidth(80)
        self.query_page_label = QLabel("第 1 页")
        prev_btn = QPushButton("◀ 上一页")
        prev_btn.setMinimumHeight(30)
        prev_btn.clicked.connect(lambda: self.load_prev_page('query'))
        next_btn = QPushButton("下一页 ▶")
        next_btn.setMinimumHeight(30)
        next_btn.clicked.connect(lambda: self.load_next_page('query'))
        page_layout.addWidget(QLabel("页码:"))
        page_layout.addWidget(self.query_page_spin)
        page_layout.addWidget(self.query_page_label)
        page_layout.addWidget(prev_btn)
        page_layout.addWidget(next_btn)
        page_layout.addStretch()
        layout.addLayout(page_layout)
        
        self.query_table = QTableWidget()
        self.query_table.setColumnCount(9)
        self.query_table.setHorizontalHeaderLabels(['ID', '用户名', '内容', '点赞', '评论', 
                                              '转发', '发布时间', '爬取时间', '链接'])
        self.query_table.setColumnWidth(2, 350)
        self.query_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.query_table)
        
        return page
    
    def create_add_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        page.setLayout(layout)
        
        title = QLabel("数据新增")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        form_layout = QFormLayout()
        
        self.add_user_name = QLineEdit()
        self.add_content = QTextEdit()
        self.add_content.setMaximumHeight(150)
        self.add_likes = QSpinBox()
        self.add_likes.setMaximum(99999999)
        self.add_comments = QSpinBox()
        self.add_comments.setMaximum(99999999)
        self.add_reposts = QSpinBox()
        self.add_reposts.setMaximum(99999999)
        self.add_post_time = QLineEdit()
        self.add_post_time.setPlaceholderText("例: 2026-03-04 12:00:00")
        self.add_url = QLineEdit()
        
        form_layout.addRow("用户名:", self.add_user_name)
        form_layout.addRow("内容:", self.add_content)
        form_layout.addRow("点赞数:", self.add_likes)
        form_layout.addRow("评论数:", self.add_comments)
        form_layout.addRow("转发数:", self.add_reposts)
        form_layout.addRow("发布时间:", self.add_post_time)
        form_layout.addRow("链接:", self.add_url)
        
        layout.addLayout(form_layout)
        
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("💾 保存")
        save_btn.setMinimumHeight(40)
        save_btn.clicked.connect(self.save_new_post)
        clear_btn = QPushButton("🗑️ 清空")
        clear_btn.setMinimumHeight(40)
        clear_btn.clicked.connect(self.clear_add_form)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(clear_btn)
        layout.addLayout(btn_layout)
        
        layout.addStretch()
        
        return page
    
    def create_manage_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        page.setLayout(layout)
        
        title = QLabel("数据管理")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # 分页控件
        page_layout = QHBoxLayout()
        self.manage_page_spin = QSpinBox()
        self.manage_page_spin.setMinimum(1)
        self.manage_page_spin.setMaximum(999999)
        self.manage_page_spin.setValue(1)
        self.manage_page_spin.setMinimumWidth(80)
        self.manage_page_label = QLabel("第 1 页")
        prev_btn = QPushButton("◀ 上一页")
        prev_btn.setMinimumHeight(30)
        prev_btn.clicked.connect(lambda: self.load_prev_page('manage'))
        next_btn = QPushButton("下一页 ▶")
        next_btn.setMinimumHeight(30)
        next_btn.clicked.connect(lambda: self.load_next_page('manage'))
        page_layout.addWidget(QLabel("页码:"))
        page_layout.addWidget(self.manage_page_spin)
        page_layout.addWidget(self.manage_page_label)
        page_layout.addWidget(prev_btn)
        page_layout.addWidget(next_btn)
        page_layout.addStretch()
        layout.addLayout(page_layout)
        
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(['ID', '用户名', '内容', '点赞', '评论', 
                                              '转发', '发布时间', '爬取时间', '链接'])
        self.table.setColumnWidth(2, 350)
        layout.addWidget(self.table)
        
        btn_layout = QHBoxLayout()
        edit_btn = QPushButton("✏️ 编辑")
        edit_btn.setMinimumHeight(40)
        delete_btn = QPushButton("🗑️ 删除")
        delete_btn.setMinimumHeight(40)
        delete_all_btn = QPushButton("🗑️ 一键清空")
        delete_all_btn.setMinimumHeight(40)
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.setMinimumHeight(40)
        edit_btn.clicked.connect(self.edit_post)
        delete_btn.clicked.connect(self.delete_post)
        delete_all_btn.clicked.connect(self.delete_all_posts)
        refresh_btn.clicked.connect(lambda: self.load_data_paginated(1))
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(delete_btn)
        btn_layout.addWidget(delete_all_btn)
        btn_layout.addWidget(refresh_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        return page
    
    def create_chart_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        page.setLayout(layout)
        
        # 标题和按钮行
        title_layout = QHBoxLayout()
        title = QLabel("数据可视化")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title_layout.addWidget(title)
        title_layout.addStretch()
        
        # 屏蔽词设置按钮
        filter_words_btn = QPushButton("⚙️ 屏蔽词设置")
        filter_words_btn.setMinimumHeight(35)
        filter_words_btn.clicked.connect(self.show_filter_words_dialog)
        title_layout.addWidget(filter_words_btn)
        
        # 刷新图表按钮
        refresh_chart_btn = QPushButton("🔄 刷新图表")
        refresh_chart_btn.setMinimumHeight(35)
        refresh_chart_btn.clicked.connect(self.update_chart)
        title_layout.addWidget(refresh_chart_btn)
        
        layout.addLayout(title_layout)
        
        self.chart_widget = ChartWidget()
        layout.addWidget(self.chart_widget)
        
        return page
    
    def show_filter_words_dialog(self):
        """显示屏蔽词设置对话框"""
        dialog = FilterWordsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            words = dialog.get_words()
            import config
            # 获取默认屏蔽词
            default_stop_words = {
                '转发', '微博', 'http', 'https', 'com', 'www', 'weibo', 'sinaimg', 'cn', 't', 'co',
                '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
                '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
                '自己', '这', '那', '可以', '能', '会', '要', '什么', '怎么', '为什么', '这个', '那个',
                '这样', '那样', '还是', '展开', '全文', '收起', '查看', '更多', '详情',
                '点击', '链接', '图片', '视频', '话题', '超话', '热搜'
            }
            # 合并默认和用户自定义的屏蔽词
            all_words = default_stop_words | words
            if config.save_stop_words(list(all_words)):
                # 重新加载屏蔽词
                self.chart_widget.stop_words = config.load_stop_words()
                QMessageBox.information(self, "成功", "屏蔽词设置已保存！\n请点击'刷新图表'按钮更新图表。")
            else:
                QMessageBox.warning(self, "错误", "保存屏蔽词失败！")
    
    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:checked {
                background-color: #2196F3;
            }
            QGroupBox {
                border: 2px solid #ddd;
                border-radius: 10px;
                margin-top: 10px;
                padding: 15px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLineEdit, QTextEdit, QSpinBox {
                border: 2px solid #ddd;
                border-radius: 5px;
                padding: 5px;
                background-color: white;
            }
            QLineEdit:focus, QTextEdit:focus, QSpinBox:focus {
                border: 2px solid #4CAF50;
            }
            QTableWidget {
                border: 1px solid #ddd;
                background-color: white;
                gridline-color: #e0e0e0;
            }
            QHeaderView::section {
                background-color: #4CAF50;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
    
    def update_chart(self):
        """更新图表（只加载数据用于可视化，不加载到表格）"""
        # 对于图表，我们只需要数据，不需要全部加载到内存
        # 但为了词云和词频统计，还是需要所有数据
        # 可以考虑优化为只加载内容字段，但为了简单起见，暂时加载全部
        posts = self.db.get_all_posts()
        self.chart_widget.plot_data(posts)
    
    def load_data(self):
        """加载所有数据（用于管理页面等需要完整数据的场景）"""
        posts = self.db.get_all_posts()
        self.display_data(posts, self.table)
        if hasattr(self, 'query_table'):
            self.display_data(posts, self.query_table)
        self.update_stats()
    
    def load_data_paginated(self, page=1, page_size=100, page_type='query'):
        """分页加载数据，优化性能"""
        posts = self.db.get_posts_paginated(page, page_size)
        total_count = self.db.get_total_count()
        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
        
        # 显示数据
        if page_type == 'query' and hasattr(self, 'query_table'):
            self.display_data(posts, self.query_table)
            # 更新分页信息
            if hasattr(self, 'query_page_label'):
                self.query_page_label.setText(f"第 {page} 页 / 共 {total_pages} 页 (总计 {total_count} 条)")
            if hasattr(self, 'query_page_spin'):
                self.query_page_spin.setValue(page)
                self.query_page_spin.setMaximum(max(total_pages, 1))
        elif page_type == 'manage' and hasattr(self, 'table'):
            self.display_data(posts, self.table)
            # 更新分页信息
            if hasattr(self, 'manage_page_label'):
                self.manage_page_label.setText(f"第 {page} 页 / 共 {total_pages} 页 (总计 {total_count} 条)")
            if hasattr(self, 'manage_page_spin'):
                self.manage_page_spin.setValue(page)
                self.manage_page_spin.setMaximum(max(total_pages, 1))
        
        # 标记数据已加载
        if page_type == 'query':
            self.query_data_loaded = True
        elif page_type == 'manage':
            self.manage_data_loaded = True
    
    def load_prev_page(self, page_type='query'):
        """加载上一页"""
        if page_type == 'query' and hasattr(self, 'query_page_spin'):
            current_page = self.query_page_spin.value()
            if current_page > 1:
                self.load_data_paginated(current_page - 1, page_type='query')
        elif page_type == 'manage' and hasattr(self, 'manage_page_spin'):
            current_page = self.manage_page_spin.value()
            if current_page > 1:
                self.load_data_paginated(current_page - 1, page_type='manage')
    
    def load_next_page(self, page_type='query'):
        """加载下一页"""
        if page_type == 'query' and hasattr(self, 'query_page_spin'):
            current_page = self.query_page_spin.value()
            total_count = self.db.get_total_count()
            total_pages = (total_count + 99) // 100 if total_count > 0 else 1
            if current_page < total_pages:
                self.load_data_paginated(current_page + 1, page_type='query')
        elif page_type == 'manage' and hasattr(self, 'manage_page_spin'):
            current_page = self.manage_page_spin.value()
            total_count = self.db.get_total_count()
            total_pages = (total_count + 99) // 100 if total_count > 0 else 1
            if current_page < total_pages:
                self.load_data_paginated(current_page + 1, page_type='manage')
    
    def search_data(self):
        keyword = self.search_input.text()
        if keyword:
            posts = self.db.search_posts(keyword)
            self.display_data(posts, self.query_table)
        else:
            posts = self.db.get_all_posts()
            self.display_data(posts, self.query_table)
    
    def display_data(self, posts, table):
        table.setRowCount(len(posts))
        for i, post in enumerate(posts):
            for j, value in enumerate(post):
                item = QTableWidgetItem(str(value))
                if j == 2:
                    item.setToolTip(str(value))
                table.setItem(i, j, item)
    
    def save_new_post(self):
        user_name = self.add_user_name.text()
        content = self.add_content.toPlainText()
        
        if not user_name or not content:
            QMessageBox.warning(self, "提示", "用户名和内容不能为空！")
            return
        
        likes = self.add_likes.value()
        comments = self.add_comments.value()
        reposts = self.add_reposts.value()
        post_time = self.add_post_time.text() or "2026-03-04 12:00:00"
        url = self.add_url.text()
        
        self.db.insert_post(user_name, content, likes, comments, reposts, post_time, url)
        QMessageBox.information(self, "成功", "数据新增成功！")
        self.clear_add_form()
        self.update_stats()
    
    def clear_add_form(self):
        self.add_user_name.clear()
        self.add_content.clear()
        self.add_likes.setValue(0)
        self.add_comments.setValue(0)
        self.add_reposts.setValue(0)
        self.add_post_time.clear()
        self.add_url.clear()
    
    def update_stats(self):
        stats = self.db.get_statistics()
        if hasattr(self, 'total_label'):
            self.total_label.setText(f"总数据量: {stats[0] if stats[0] else 0}")
            self.likes_label.setText(f"总点赞: {stats[1] if stats[1] else 0}")
            self.comments_label.setText(f"总评论: {stats[2] if stats[2] else 0}")
            self.reposts_label.setText(f"总转发: {stats[3] if stats[3] else 0}")
    
    def edit_post(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请选择要编辑的行")
            return
        
        post_data = [self.table.item(row, i).text() for i in range(9)]
        dialog = EditDialog(post_data, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            post_id = int(post_data[0])
            self.db.update_post(post_id, data['user_name'], data['content'],
                              data['likes'], data['comments'], data['reposts'],
                              data['post_time'], data['url'])
            self.load_data()
            QMessageBox.information(self, "成功", "修改成功！")
    
    def delete_post(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请选择要删除的行")
            return
        
        reply = QMessageBox.question(self, "确认", "确定要删除这条记录吗？",
                                    QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            post_id = int(self.table.item(row, 0).text())
            self.db.delete_post(post_id)
            self.load_data()
            QMessageBox.information(self, "成功", "删除成功！")
    
    def delete_all_posts(self):
        stats = self.db.get_statistics()
        total_count = stats[0] if stats[0] else 0
        
        if total_count == 0:
            QMessageBox.warning(self, "提示", "数据库中没有数据！")
            return
        
        reply = QMessageBox.question(self, "确认", 
                                    f"确定要删除全部 {total_count} 条记录吗？\n\n此操作不可恢复！",
                                    QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.db.delete_all_posts()
            self.load_data()
            QMessageBox.information(self, "成功", f"已清空所有数据！")
    
    def start_crawl(self):
        dialog = CrawlDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            params = dialog.get_params()
            keyword = params['keyword']
            start_page = params['start_page']
            end_page = params['end_page']
            min_delay = params['min_delay']
            max_delay = params['max_delay']
            
            if not keyword:
                QMessageBox.warning(self, "提示", "请输入搜索关键词！")
                return
            
            if start_page > end_page:
                QMessageBox.warning(self, "提示", "起始页不能大于结束页！")
                return
            
            if min_delay > max_delay:
                QMessageBox.warning(self, "提示", "最小间隔不能大于最大间隔！")
                return
            
            reply = QMessageBox.question(self, "确认", 
                                        f"将爬取关键词 '{keyword}' 的第 {start_page}-{end_page} 页\n\n"
                                        f"这可能需要几分钟时间，确认开始？\n\n"
                                        f"提示：如果出现扫码登录界面，\n"
                                        f"请使用手机微博扫码，程序会自动等待2分钟。",
                                        QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                self.spider_thread = SpiderThread(keyword, start_page, end_page, min_delay, max_delay)
                self.spider_thread.finished.connect(self.on_crawl_finished)
                self.spider_thread.error.connect(self.on_crawl_error)
                self.spider_thread.start()
                
                self.progress = QProgressDialog(f"正在爬取 '{keyword}' 相关微博数据...\n请耐心等待...", 
                                               None, 0, 0, self)
                self.progress.setWindowTitle("爬取中")
                self.progress.setWindowModality(Qt.WindowModal)
                self.progress.setMinimumDuration(0)
                self.progress.setCancelButton(None)
                self.progress.show()
    
    def on_crawl_finished(self, posts):
        if hasattr(self, 'progress'):
            self.progress.close()
        self.load_data()
        QMessageBox.information(self, "成功", f"爬取完成！\n\n共获取 {len(posts)} 条数据")
    
    def on_crawl_error(self, error_msg):
        if hasattr(self, 'progress'):
            self.progress.close()
        QMessageBox.critical(self, "错误", f"爬取失败：\n\n{error_msg}")
    
    def closeEvent(self, event):
        self.db.close()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = WeiboApp()
    window.show()
    sys.exit(app.exec_())
