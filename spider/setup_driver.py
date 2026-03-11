import os
import sys
import subprocess
import requests
import zipfile
import shutil

def get_chrome_version():
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon")
        version, _ = winreg.QueryValueEx(key, "version")
        return version
    except:
        try:
            result = subprocess.run(
                ['reg', 'query', 'HKEY_CURRENT_USER\\Software\\Google\\Chrome\\BLBeacon', '/v', 'version'],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                version = result.stdout.split()[-1]
                return version
        except:
            pass
    return None

def download_chromedriver():
    print("正在检测 Chrome 浏览器版本...")
    chrome_version = get_chrome_version()
    
    if chrome_version:
        print(f"检测到 Chrome 版本: {chrome_version}")
        major_version = chrome_version.split('.')[0]
    else:
        print("无法自动检测 Chrome 版本，使用默认版本")
        major_version = "120"
    
    driver_dir = os.path.join(os.path.dirname(__file__), 'drivers')
    os.makedirs(driver_dir, exist_ok=True)
    
    driver_path = os.path.join(driver_dir, 'chromedriver.exe')
    
    if os.path.exists(driver_path):
        print(f"ChromeDriver 已存在: {driver_path}")
        return driver_path
    
    print(f"\n正在下载 ChromeDriver (版本 {major_version})...")
    print("这可能需要几分钟，请耐心等待...\n")
    
    try:
        if int(major_version) >= 115:
            versions_url = "https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json"
            print(f"正在获取可用版本列表...")
            response = requests.get(versions_url)
            data = response.json()
            
            matching_version = None
            for version_info in reversed(data['versions']):
                if version_info['version'].startswith(f"{major_version}."):
                    matching_version = version_info
                    break
            
            if not matching_version:
                matching_version = data['versions'][-1]
            
            version_num = matching_version['version']
            print(f"找到匹配版本: {version_num}")
            
            for download in matching_version.get('downloads', {}).get('chromedriver', []):
                if download['platform'] == 'win64':
                    url = download['url']
                    break
            else:
                raise Exception("未找到 Windows 64位版本")
        else:
            url = f"https://chromedriver.storage.googleapis.com/LATEST_RELEASE_{major_version}"
            response = requests.get(url)
            version = response.text.strip()
            url = f"https://chromedriver.storage.googleapis.com/{version}/chromedriver_win32.zip"
        
        print(f"下载地址: {url}")
        response = requests.get(url, stream=True)
        
        if response.status_code != 200:
            print(f"下载失败，状态码: {response.status_code}")
            return manual_download_guide()
        
        zip_path = os.path.join(driver_dir, 'chromedriver.zip')
        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print("正在解压...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(driver_dir)
        
        for root, dirs, files in os.walk(driver_dir):
            for file in files:
                if file == 'chromedriver.exe':
                    src = os.path.join(root, file)
                    if src != driver_path:
                        shutil.move(src, driver_path)
        
        os.remove(zip_path)
        
        for item in os.listdir(driver_dir):
            item_path = os.path.join(driver_dir, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
        
        print(f"\n✅ ChromeDriver 安装成功！")
        print(f"路径: {driver_path}\n")
        return driver_path
        
    except Exception as e:
        print(f"\n❌ 自动下载失败: {e}")
        return manual_download_guide()

def manual_download_guide():
    print("\n" + "="*60)
    print("请手动下载 ChromeDriver：")
    print("="*60)
    print("\n步骤：")
    print("1. 打开 Chrome 浏览器，输入: chrome://settings/help")
    print("2. 查看你的 Chrome 版本号")
    print("3. 访问: https://googlechromelabs.github.io/chrome-for-testing/")
    print("4. 下载对应版本的 ChromeDriver (Windows 64-bit)")
    print("5. 解压后将 chromedriver.exe 放到:")
    driver_dir = os.path.join(os.path.dirname(__file__), 'drivers')
    print(f"   {driver_dir}")
    print("\n或者将 chromedriver.exe 添加到系统 PATH 环境变量中")
    print("="*60 + "\n")
    return None

if __name__ == '__main__':
    print("ChromeDriver 安装工具")
    print("="*60 + "\n")
    download_chromedriver()
    print("\n按任意键退出...")
    input()
