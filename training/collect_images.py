import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image
from io import BytesIO
import uuid
import argparse

def setup_browser():
    """设置无头浏览器"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    service = Service(ChromeDriverManager().install())
    browser = webdriver.Chrome(service=service, options=chrome_options)
    return browser

def download_image(url, save_path):
    """下载并保存图像"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            # 验证图像是否有效
            try:
                img = Image.open(BytesIO(response.content))
                img.verify()  # 验证图像
                img = Image.open(BytesIO(response.content))  # 重新打开图像
                img.save(save_path)
                return True
            except Exception as e:
                print(f"无效图像: {e}")
                return False
        else:
            print(f"下载失败，状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"下载出错: {e}")
        return False

def search_and_download_images(query, num_images, output_dir):
    """搜索并下载图像"""
    browser = setup_browser()
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 访问搜索引擎
    search_url = f"https://www.bing.com/images/search?q={query}&form=HDRSC2&first=1"
    browser.get(search_url)
    
    # 等待页面加载
    time.sleep(2)
    
    # 滚动页面以加载更多图像
    for _ in range(5):
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
    
    # 查找所有图像元素
    image_elements = browser.find_elements(By.CSS_SELECTOR, ".mimg")
    print(f"找到 {len(image_elements)} 个图像")
    
    # 下载图像
    count = 0
    for img in image_elements:
        if count >= num_images:
            break
            
        try:
            img_url = img.get_attribute("src")
            if img_url and not img_url.startswith("data:"):
                file_name = f"{uuid.uuid4()}.jpg"
                save_path = os.path.join(output_dir, file_name)
                
                if download_image(img_url, save_path):
                    count += 1
                    print(f"已下载 {count}/{num_images} 图像")
        except Exception as e:
            print(f"处理图像时出错: {e}")
    
    browser.quit()
    print(f"总共下载了 {count} 张图像到 {output_dir}")

def main():
    parser = argparse.ArgumentParser(description="从网络收集香烟图像")
    parser.add_argument("--query", type=str, default="cigarette smoking person", help="搜索关键词")
    parser.add_argument("--num", type=int, default=100, help="要下载的图像数量")
    parser.add_argument("--output", type=str, default="datasets/smoking/collected_images", help="输出目录")
    args = parser.parse_args()
    
    print(f"开始收集 '{args.query}' 相关的图像...")
    search_and_download_images(args.query, args.num, args.output)
    print("图像收集完成！")
    print("请注意：这些图像需要手动标注才能用于训练。")
    print("您可以使用工具如 LabelImg (https://github.com/tzutalin/labelImg) 进行标注。")

if __name__ == "__main__":
    main() 