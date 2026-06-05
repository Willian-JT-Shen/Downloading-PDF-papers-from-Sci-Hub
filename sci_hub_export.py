import os
import pandas as pd
import selenium.common.exceptions
from tqdm import tqdm
import bibtexparser
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.ie.service import Service
from selenium.webdriver.common.by import By
import re
import sys


# ==========================================
# 注意事项
# ==========================================
"""
需要把 chrome-win64, chromedriver-win64 文件夹放在该 py 程序的目录以下

需要提前安装的包有：
pip install pandas selenium tqdm bibtexparser
"""

def resource_path(relative_path):
    """
    获取资源的绝对路径。
    无论是源码开发环境，还是 PyInstaller 打包后的单文件环境，都能正确解析。
    """
    try:
        # 当被 PyInstaller 打包后，sys._MEIPASS 会指向解压后的临时目录
        base_path = sys._MEIPASS
    except Exception:
        # 如果是正常的 Python 脚本运行，则获取当前运行目录
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class Article_export():
# ==========================================
# 配置
# ==========================================
    def __init__(self,
                BIB_FILE = "references.bib",  # 更换成本目录下存储参考文献的 bib 文件名
                SAVE_DIR = "papers",  # 本目录下存储文献的地址
                EMAIL = "123456789@gmail.com"  # 填写自己的邮箱即可；Unpaywall 要求提供邮箱
                 ):

        self.BIB_FILE = BIB_FILE
        self.SAVE_DIR = SAVE_DIR
        self.EMAIL = EMAIL
        self.SCI_HUB_URLs = ["https://www.sci-hub.ee/",
                        "https://www.sci-hub.mk/",
                        "https://www.sci-hub.ren/",
                        "https://www.sci-hub.in/",
                        "https://www.sci-hub.vg/",
                        "https://www.sci-hub.al/"]
        os.makedirs(SAVE_DIR, exist_ok=True)  # 创建文件夹


# ==========================================
# 读取 bib 文件
# ==========================================
    def read_bib(self):
        with open(self.BIB_FILE, "r", encoding="utf-8") as bibtex_file:
            bib_database = bibtexparser.load(bibtex_file)

        self.entries = bib_database.entries


# ==========================================
# 主循环
# ==========================================
    def run(self):
        self.read_bib()

        # ========== 1. 只启动一次浏览器，并提前设置好无头模式 ==========
        # 配置 selenium 设置
        ## 修改下述代码
        # s = Service('chromedriver-win64/chromedriver-win64/chromedriver.exe')
        chrome_options = Options()
        # chrome_options.binary_location = 'chrome-win64/chrome-win64/chrome.exe'  # 指向浏览器的位置

        ## 改为以下形式：
        driver_path = resource_path(os.path.join('chromedriver-win64', 'chromedriver-win64', 'chromedriver.exe'))
        browser_path = resource_path(os.path.join('chrome-win64', 'chrome-win64', 'chrome.exe'))
        s = Service(driver_path)
        chrome_options.binary_location = browser_path


        # 所有参数必须在 webdriver.Chrome() 之前添加
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--headless')  # ← 关键：不显示浏览器窗口
        chrome_options.add_argument('--disable-gpu')  # 这行在 Windows 下有时需要，一起加上
        chrome_options.add_argument('--window-size=1920,1080')  # 避免某些布局问题
        driver = webdriver.Chrome(service=s, options=chrome_options)
        # print(driver.title)

        # ========== 2. 预先测试可用的 Sci‑Hub 地址 ==========
        available_sci_hub = None
        for sci_hub_url in self.SCI_HUB_URLs:
            try:
                driver.get(sci_hub_url)  # 随便访问主页，看能不能通
                # 如果能正常访问，就把它当作可用地址
                available_sci_hub = sci_hub_url
                break
            except Exception:
                continue

        if not available_sci_hub:
            print("所有 Sci‑Hub 地址均不可用，程序终止。")
            driver.quit()
            return

        # ========== 3. 正式开始处理论文 ==========
        not_in_sci_hub = []  # 用于存储在 Sci-Hub 检索不到的文章；移到循环外面，避免每次被重置
        for entry in tqdm(self.entries[:]):
            title = entry.get("title", "unknown_title")
            doi = entry.get("doi", None)

            print("\n" + "=" * 60)
            print(f"处理论文: {title}")

            # --------------------------------------
            # 如果没有 DOI，可以尝试 CrossRef 搜索
            # --------------------------------------

            if doi is None:
                query_url = (
                    "https://api.crossref.org/works"
                    f"?query.title={title}"
                    "&rows=1"
                )

                try:
                    r = requests.get(query_url, timeout=20)

                    items = r.json()["message"]["items"]

                    if len(items) > 0:
                        doi = items[0].get("DOI", None)

                except:
                    pass

            if doi is None:
                print("未找到 DOI")
                not_in_sci_hub.append(title)  # 记录为找不到
                continue

            print("DOI:", doi)

            # --------------------------------------
            # 用 Sci-hub 爬取文档 ~
            # --------------------------------------

            # 读取 pdf
            pdf_url = None
            try:
                driver.get(available_sci_hub + doi)
                # 短暂等待页面元素出现（按需可增加 WebDriverWait）
                element = driver.find_element(By.ID, 'article')
                url_pre = element.find_element(By.ID, 'pdf')
                pdf_url = url_pre.get_attribute('src')
            except selenium.common.exceptions.NoSuchElementException:
                # 可能 Sci‑Hub 没有这篇文章
                pass
            except Exception as e:
                print(f"访问 Sci‑Hub 时出错: {e}")

            if not pdf_url:
                not_in_sci_hub.append(title)
                print("Sci-Hub 上没有这篇文章 :(")
                continue

            # 下载 pdf
            try:
                # 文件名清理函数
                def sanitize_filename(name):
                    name = re.sub(r'[\\/*?:"<>|]', '', name)
                    name = name.strip(' .')
                    name = name.replace(':', '：')
                    return name if name else "untitled"

                response = requests.get(pdf_url, stream=True)
                with open(f'./{self.SAVE_DIR}/{sanitize_filename(title)}.pdf', 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print("论文下载完毕！")
            except Exception as e:
                print(f"下载失败: {e}")
                not_in_sci_hub.append(title)

        # ========== 4. 全部完成后清理 ==========
        driver.quit()

        # 保存未找到的文章列表
        if not_in_sci_hub:
            df = pd.DataFrame(not_in_sci_hub, columns=["title"])
            df.to_csv(f'./{self.SAVE_DIR}/Sci-Hub无法检索到的文章目录.csv', index=False)
        else:
            print("所有文章均已成功下载！")

# # ==========================================
# # 调用示例
# # ==========================================
# article_export = Article_export()
# article_export.run()