import time
import random
import urllib.parse
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from fake_useragent import UserAgent
from database import WeiboDatabase
import config

try:
    from webdriver_manager.chrome import ChromeDriverManager
    HAS_WEBDRIVER_MANAGER = True
except:
    HAS_WEBDRIVER_MANAGER = False

class WeiboSpider:
    def __init__(self):
        self.driver = None
        self.db = WeiboDatabase()
        self.setup_driver()
    
    def setup_driver(self):
        chrome_options = Options()
        ua = UserAgent()
        chrome_options.add_argument(f'user-agent={ua.random}')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        local_driver_path = os.path.join(os.path.dirname(__file__), 'drivers', 'chromedriver.exe')
        
        print("正在启动 Chrome 浏览器...")
        
        try:
            if os.path.exists(local_driver_path):
                print(f"使用本地 ChromeDriver: {local_driver_path}")
                service = Service(local_driver_path)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            elif HAS_WEBDRIVER_MANAGER:
                print("使用 webdriver-manager 自动下载 ChromeDriver...")
                driver_path = ChromeDriverManager().install()
                print(f"ChromeDriver 路径: {driver_path}")
                service = Service(driver_path)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                print("尝试使用系统 PATH 中的 ChromeDriver...")
                self.driver = webdriver.Chrome(options=chrome_options)
            
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
            })
            print("Chrome 浏览器启动成功！")
            
        except Exception as e:
            error_msg = (
                f"❌ 无法启动 Chrome 浏览器\n\n"
                f"错误信息: {str(e)}\n\n"
                f"解决方案：\n"
                f"1. 运行 setup_driver.py 自动安装 ChromeDriver\n"
                f"2. 或手动下载 ChromeDriver:\n"
                f"   - 访问: https://googlechromelabs.github.io/chrome-for-testing/\n"
                f"   - 下载与你的 Chrome 版本匹配的 ChromeDriver\n"
                f"   - 解压后放到: {local_driver_path}\n\n"
                f"3. 确保已安装 Chrome 浏览器"
            )
            raise Exception(error_msg)
    
    def human_like_delay(self, min_time=1, max_time=3):
        time.sleep(random.uniform(min_time, max_time))
    
    def smooth_scroll(self, scroll_count=5):
        for i in range(scroll_count):
            scroll_height = random.randint(300, 800)
            self.driver.execute_script(f"window.scrollBy(0, {scroll_height});")
            self.human_like_delay(1, 2)
    
    def check_login_needed(self):
        """检测是否需要登录"""
        try:
            login_keywords = ['登录', '扫码', 'login', '二维码']
            page_text = self.driver.page_source.lower()
            
            for keyword in login_keywords:
                if keyword.lower() in page_text:
                    return True
            
            if self.driver.find_elements(By.CSS_SELECTOR, "div[class*='login']"):
                return True
            if self.driver.find_elements(By.CSS_SELECTOR, "div[class*='qrcode']"):
                return True
                
        except:
            pass
        return False
    
    def wait_for_login(self, timeout=120):
        """等待用户登录"""
        print("\n" + "="*60)
        print("⚠️  检测到需要登录微博")
        print("="*60)
        print("\n请按以下步骤操作：")
        print("1. 在浏览器窗口中使用手机微博APP扫描二维码")
        print("2. 在手机上确认登录")
        print(f"3. 等待自动继续（最多等待 {timeout} 秒）")
        print("\n正在等待登录...")
        print("="*60 + "\n")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not self.check_login_needed():
                print("\n✅ 登录成功！继续爬取...")
                time.sleep(3)
                return True
            
            remaining = int(timeout - (time.time() - start_time))
            if remaining % 10 == 0:
                print(f"等待中... 剩余 {remaining} 秒")
            
            time.sleep(2)
        
        print("\n⚠️  登录超时，将尝试继续...")
        return False
    
    def crawl_by_keyword(self, keyword, start_page=1, end_page=5, min_delay=60, max_delay=180):
        posts = []
        try:
            encoded_keyword = urllib.parse.quote(keyword)
            
            login_checked = False
            
            for page in range(start_page, end_page + 1):
                url = f"https://s.weibo.com/weibo?q={encoded_keyword}&page={page}"
                print(f"正在爬取第 {page} 页: {url}")
                
                self.driver.get(url)
                self.human_like_delay(3, 5)
                
                if not login_checked:
                    if self.check_login_needed():
                        self.wait_for_login(120)
                    login_checked = True
                
                self.smooth_scroll(3)
                
                try:
                    print("正在查找微博内容...")
                    
                    items = self.driver.find_elements(By.CSS_SELECTOR, "div.card-wrap")
                    
                    if not items:
                        print("⚠️ 未找到任何微博内容！")
                        print("正在保存调试信息...")
                        
                        debug_dir = os.path.join(os.path.dirname(__file__), 'debug')
                        os.makedirs(debug_dir, exist_ok=True)
                        
                        screenshot_path = os.path.join(debug_dir, f'debug_page{page}.png')
                        self.driver.save_screenshot(screenshot_path)
                        print(f"截图已保存: {screenshot_path}")
                        
                        html_path = os.path.join(debug_dir, f'debug_page{page}.html')
                        with open(html_path, 'w', encoding='utf-8') as f:
                            f.write(self.driver.page_source)
                        print(f"页面HTML已保存: {html_path}")
                        
                        continue
                    
                    print(f"找到 {len(items)} 个微博卡片")
                    
                    for idx, item in enumerate(items):
                        try:
                            user_name = "未知用户"
                            try:
                                content_elem = item.find_element(By.CSS_SELECTOR, "p.txt[node-type='feed_list_content']")
                                user_name = content_elem.get_attribute("nick-name") or "未知用户"
                            except:
                                pass
                            
                            content = ""
                            try:
                                # 优先尝试获取完整内容（node-type="feed_list_content_full"）
                                # 这是展开后的完整文本，默认隐藏
                                try:
                                    content_elem = item.find_element(By.CSS_SELECTOR, "p.txt[node-type='feed_list_content_full']")
                                    content = content_elem.text
                                except:
                                    # 如果没有完整内容，获取显示部分（node-type="feed_list_content"）
                                    content_elem = item.find_element(By.CSS_SELECTOR, "p.txt[node-type='feed_list_content']")
                                    content = content_elem.text
                            except:
                                pass
                            
                            if not content:
                                print(f"  第{idx+1}条: 未找到内容，跳过")
                                continue
                            
                            # 互动数据提取
                            likes = 0
                            comments = 0
                            reposts = 0
                            
                            try:
                                # 查找整个互动区域
                                action_area = item.find_element(By.CSS_SELECTOR, "div.card-act")
                                action_links = action_area.find_elements(By.TAG_NAME, "a")
                                
                                for link in action_links:
                                    link_text = link.text.strip()
                                    action_type = link.get_attribute('action-type')
                                    
                                    # 点赞
                                    if action_type == 'feed_list_like' or 'like' in link.get_attribute('class'):
                                        try:
                                            count_elem = link.find_element(By.CSS_SELECTOR, "span.woo-like-count")
                                            likes = self.parse_number(count_elem.text)
                                        except:
                                            likes = self.parse_number(link_text)
                                    
                                    # 评论
                                    elif action_type == 'feed_list_comment':
                                        comments = self.parse_number(link_text)
                                    
                                    # 转发
                                    elif action_type == 'feed_list_forward':
                                        reposts = self.parse_number(link_text)
                            except Exception as e:
                                self.logger.warning(f"提取互动数据失败: {str(e)}")
                                pass
                            
                            post_time = ""
                            try:
                                time_elem = item.find_element(By.CSS_SELECTOR, "div.from a")
                                post_time = time_elem.text
                            except:
                                post_time = time.strftime('%Y-%m-%d %H:%M:%S')
                            
                            post_url = url
                            
                            post_data = {
                                'user_name': user_name,
                                'content': content[:500],
                                'likes': likes,
                                'comments': comments,
                                'reposts': reposts,
                                'post_time': post_time,
                                'url': post_url
                            }
                            posts.append(post_data)
                            
                            self.db.insert_post(user_name, content[:500], likes, comments, 
                                              reposts, post_time, post_url)
                            
                            print(f"✅ [{idx+1}/{len(items)}] {user_name[:10]}: {content[:30]}... (赞:{likes} 评:{comments} 转:{reposts})")
                            
                        except Exception as e:
                            print(f"  解析第{idx+1}条微博出错: {e}")
                            continue
                    
                    self.human_like_delay(2, 4)
                    
                    # 换页延迟，避免被反爬虫检测
                    if page < end_page:
                        delay = random.randint(min_delay, max_delay)
                        print(f"⏰ 准备切换到下一页，等待 {delay} 秒（{delay//60}分{delay%60}秒）...")
                        time.sleep(delay)
                    
                except Exception as e:
                    print(f"爬取第{page}页出错: {e}")
                    # 即使出错也要延迟再继续
                    if page < end_page:
                        delay = random.randint(min_delay, max_delay)
                        print(f"⏰ 出错后等待 {delay} 秒再继续...")
                        time.sleep(delay)
                    continue
            
            return posts
            
        except Exception as e:
            print(f"爬取出错: {e}")
            import traceback
            traceback.print_exc()
            return posts
    
    def parse_number(self, text):
        if not text:
            return 0
        text = text.strip()
        
        import re
        numbers = re.findall(r'\d+\.?\d*', text)
        if not numbers:
            return 0
        
        number_str = numbers[-1]
        
        if '万' in text:
            return int(float(number_str) * 10000)
        elif 'w' in text.lower():
            return int(float(number_str) * 10000)
        
        try:
            return int(float(number_str))
        except:
            return 0
    
    def close(self):
        if self.driver:
            self.driver.quit()
        self.db.close()
