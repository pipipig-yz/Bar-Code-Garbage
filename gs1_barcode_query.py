import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import requests
import json
import threading
import time

class GS1BarcodeQuery:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("条码查询工具 - 聚合数据API")
        self.root.geometry("800x600")
        self.root.configure(bg='#f0f0f0')
        
        # API相关变量
        self.api_url = "http://api.juheapi.com/jhbar/bar"  # 聚合数据条码查询API
        self.api_key = ""  # 聚合数据API密钥
        self.pkg = "com.barcode.query.tool"  # 应用包名
        self.cityid = "1"  # 城市ID，默认1（上海）
        
        # 创建GUI界面
        self.create_widgets()
        
    def create_widgets(self):
        """创建GUI界面"""
        # 主框架
        main_frame = tk.Frame(self.root, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 标题
        title_label = tk.Label(main_frame, text="条码查询工具", 
                              font=('Arial', 18, 'bold'), bg='#f0f0f0')
        title_label.pack(pady=(0, 20))
        
        # 输入区域
        input_frame = tk.Frame(main_frame, bg='white', relief=tk.RAISED, bd=2)
        input_frame.pack(fill=tk.X, pady=(0, 20))
        
        # 输入框标签
        input_label = tk.Label(input_frame, text="请输入条码号 (8-13位数字):", 
                              font=('Arial', 12, 'bold'), bg='white')
        input_label.pack(pady=10)
        
        # 输入框
        self.input_entry = tk.Entry(input_frame, 
                                   font=('Consolas', 14),
                                   width=50,
                                   relief=tk.SUNKEN,
                                   bd=2)
        self.input_entry.pack(pady=(0, 10), padx=20)
        self.input_entry.bind('<Return>', self.on_enter_pressed)
        
        # 按钮区域
        button_frame = tk.Frame(input_frame, bg='white')
        button_frame.pack(pady=(0, 15))
        
        # 查询按钮
        query_button = tk.Button(button_frame, text="查询", 
                                command=self.query_barcode,
                                font=('Arial', 12, 'bold'),
                                bg='#007acc', fg='white',
                                relief=tk.RAISED, bd=2,
                                padx=30, pady=8)
        query_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # 清空按钮
        clear_button = tk.Button(button_frame, text="清空", 
                                command=self.clear_input,
                                font=('Arial', 12),
                                bg='#666666', fg='white',
                                relief=tk.RAISED, bd=2,
                                padx=30, pady=8)
        clear_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # 设置按钮
        settings_button = tk.Button(button_frame, text="API设置", 
                                   command=self.open_settings,
                                   font=('Arial', 12),
                                   bg='#ff8800', fg='white',
                                   relief=tk.RAISED, bd=2,
                                   padx=30, pady=8)
        settings_button.pack(side=tk.LEFT)
        
        # 结果显示区域
        result_frame = tk.Frame(main_frame, bg='white', relief=tk.RAISED, bd=2)
        result_frame.pack(fill=tk.BOTH, expand=True)
        
        # 结果标题
        result_label = tk.Label(result_frame, text="查询结果:", 
                               font=('Arial', 12, 'bold'), bg='white')
        result_label.pack(pady=10)
        
        # 结果文本框
        self.result_text = scrolledtext.ScrolledText(result_frame, 
                                                    width=80, height=20,
                                                    font=('Consolas', 11),
                                                    bg='#f8f8f8',
                                                    relief=tk.SUNKEN,
                                                    bd=1)
        self.result_text.pack(padx=20, pady=(0, 20), fill=tk.BOTH, expand=True)
        
        # 状态栏
        self.status_label = tk.Label(main_frame, text="就绪", 
                                    font=('Arial', 10), bg='#f0f0f0',
                                    relief=tk.SUNKEN, bd=1)
        self.status_label.pack(fill=tk.X, pady=(10, 0))
        
    def on_enter_pressed(self, event):
        """回车键事件"""
        self.query_barcode()
        
    def clear_input(self):
        """清空输入框"""
        self.input_entry.delete(0, tk.END)
        self.result_text.delete(1.0, tk.END)
        self.status_label.config(text="已清空")
        
    def open_settings(self):
        """打开API设置窗口"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("API设置")
        settings_window.geometry("500x300")
        settings_window.configure(bg='#f0f0f0')
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # 设置窗口内容
        tk.Label(settings_window, text="API设置", 
                font=('Arial', 14, 'bold'), bg='#f0f0f0').pack(pady=20)
        
        # API密钥设置
        tk.Label(settings_window, text="聚合数据API密钥 (appkey):", 
                font=('Arial', 10), bg='#f0f0f0').pack(anchor='w', padx=20)
        api_key_entry = tk.Entry(settings_window, width=60, font=('Consolas', 10), show='*')
        api_key_entry.pack(padx=20, pady=(0, 10))
        api_key_entry.insert(0, self.api_key)
        
        # 城市ID设置
        tk.Label(settings_window, text="城市ID (默认1-上海):", 
                font=('Arial', 10), bg='#f0f0f0').pack(anchor='w', padx=20)
        cityid_entry = tk.Entry(settings_window, width=60, font=('Consolas', 10))
        cityid_entry.pack(padx=20, pady=(0, 10))
        cityid_entry.insert(0, self.cityid)
        
        # 应用包名设置
        tk.Label(settings_window, text="应用包名 (可选):", 
                font=('Arial', 10), bg='#f0f0f0').pack(anchor='w', padx=20)
        pkg_entry = tk.Entry(settings_window, width=60, font=('Consolas', 10))
        pkg_entry.pack(padx=20, pady=(0, 20))
        pkg_entry.insert(0, self.pkg)
        
        # 保存按钮
        def save_settings():
            self.api_key = api_key_entry.get().strip()
            self.cityid = cityid_entry.get().strip() or "1"
            self.pkg = pkg_entry.get().strip() or "com.barcode.query.tool"
            settings_window.destroy()
            self.status_label.config(text="API设置已保存")
            
        tk.Button(settings_window, text="保存", 
                 command=save_settings,
                 font=('Arial', 12, 'bold'),
                 bg='#007acc', fg='white',
                 padx=20, pady=5).pack(pady=10)
        
    def query_barcode(self):
        """查询条形码"""
        barcode = self.input_entry.get().strip()
        
        if not barcode:
            messagebox.showwarning("警告", "请输入条码号")
            return
            
        # 验证条码格式（8-13位数字）
        if not barcode.isdigit() or len(barcode) < 8 or len(barcode) > 13:
            messagebox.showwarning("警告", "条码号必须是8-13位数字")
            return
            
        if not self.api_key:
            messagebox.showwarning("警告", "请先设置API密钥")
            return
            
        # 在新线程中执行查询，避免界面卡顿
        self.status_label.config(text="正在查询...")
        query_thread = threading.Thread(target=self.perform_query, args=(barcode,), daemon=True)
        query_thread.start()
        
    def perform_query(self, barcode):
        """执行查询（在后台线程中）"""
        try:
            # 构建请求参数（根据聚合数据API文档）
            params = {
                'appkey': self.api_key,
                'barcode': barcode,
                'cityid': self.cityid,
                'pkg': self.pkg
            }
            
            # 设置请求头
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'Barcode-Query-Tool/1.0'
            }
            
            # 发送GET请求
            response = requests.get(
                self.api_url,
                params=params,
                headers=headers,
                timeout=30
            )
            
            # 处理响应
            if response.status_code == 200:
                result = response.json()
                self.root.after(0, self.display_result, result, barcode)
            else:
                error_msg = f"API请求失败: {response.status_code} - {response.text}"
                self.root.after(0, self.display_error, error_msg)
                
        except requests.exceptions.Timeout:
            self.root.after(0, self.display_error, "请求超时，请检查网络连接")
        except requests.exceptions.ConnectionError:
            self.root.after(0, self.display_error, "连接失败，请检查API地址")
        except requests.exceptions.RequestException as e:
            self.root.after(0, self.display_error, f"请求错误: {str(e)}")
        except json.JSONDecodeError:
            self.root.after(0, self.display_error, "API返回格式错误")
        except Exception as e:
            self.root.after(0, self.display_error, f"未知错误: {str(e)}")
            
    def display_result(self, result, barcode):
        """显示查询结果"""
        try:
            # 清空结果区域
            self.result_text.delete(1.0, tk.END)
            
            # 显示查询信息
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            self.result_text.insert(tk.END, f"查询时间: {timestamp}\n")
            self.result_text.insert(tk.END, f"查询编码: {barcode}\n")
            self.result_text.insert(tk.END, "=" * 50 + "\n\n")
            
            # 检查API返回的错误码
            if result.get('error_code') == 0:
                # 查询成功，格式化显示商品信息
                self.display_product_info(result.get('result', {}))
                self.status_label.config(text="查询成功")
            else:
                # 显示错误信息
                error_code = result.get('error_code', '未知')
                reason = result.get('reason', '未知错误')
                self.result_text.insert(tk.END, f"查询失败\n")
                self.result_text.insert(tk.END, f"错误码: {error_code}\n")
                self.result_text.insert(tk.END, f"错误信息: {reason}\n\n")
                
                # 显示完整JSON结果
                formatted_result = json.dumps(result, indent=2, ensure_ascii=False)
                self.result_text.insert(tk.END, "完整返回结果:\n")
                self.result_text.insert(tk.END, formatted_result)
                
                self.status_label.config(text="查询失败")
            
        except Exception as e:
            self.display_error(f"显示结果错误: {str(e)}")
    
    def display_product_info(self, result_data):
        """显示商品信息"""
        try:
            summary = result_data.get('summary', {})
            
            # 显示商品基本信息
            self.result_text.insert(tk.END, "商品信息:\n")
            self.result_text.insert(tk.END, f"条码: {summary.get('barcode', 'N/A')}\n")
            self.result_text.insert(tk.END, f"商品名称: {summary.get('name', 'N/A')}\n")
            self.result_text.insert(tk.END, f"价格区间: {summary.get('interval', 'N/A')}\n")
            self.result_text.insert(tk.END, f"实体店数量: {summary.get('shopNum', 'N/A')}\n")
            self.result_text.insert(tk.END, f"网店数量: {summary.get('eshopNum', 'N/A')}\n")
            
            # 显示实体店价格
            shops = result_data.get('shop', [])
            if shops:
                self.result_text.insert(tk.END, "\n实体店价格:\n")
                self.result_text.insert(tk.END, "-" * 30 + "\n")
                for shop in shops:
                    price = shop.get('price', 'N/A')
                    shopname = shop.get('shopname', 'N/A')
                    self.result_text.insert(tk.END, f"{shopname}: ¥{price}\n")
            
            # 显示网店价格
            eshops = result_data.get('eshop', [])
            if eshops:
                self.result_text.insert(tk.END, "\n网店价格:\n")
                self.result_text.insert(tk.END, "-" * 30 + "\n")
                for eshop in eshops:
                    price = eshop.get('price', 'N/A')
                    shopname = eshop.get('shopname', 'N/A')
                    self.result_text.insert(tk.END, f"{shopname}: ¥{price}\n")
            
            # 显示完整JSON结果
            self.result_text.insert(tk.END, "\n完整返回数据:\n")
            self.result_text.insert(tk.END, "=" * 50 + "\n")
            formatted_result = json.dumps(result_data, indent=2, ensure_ascii=False)
            self.result_text.insert(tk.END, formatted_result)
            
        except Exception as e:
            self.result_text.insert(tk.END, f"解析商品信息错误: {str(e)}\n")
            
    def display_error(self, error_msg):
        """显示错误信息"""
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, f"错误: {error_msg}\n")
        self.result_text.insert(tk.END, "\n请检查:\n")
        self.result_text.insert(tk.END, "1. 网络连接是否正常\n")
        self.result_text.insert(tk.END, "2. API密钥是否有效（聚合数据）\n")
        self.result_text.insert(tk.END, "3. 条码号格式是否正确（8-13位数字）\n")
        self.result_text.insert(tk.END, "4. 条码号是否存在（可能为未知条码）\n")
        self.result_text.insert(tk.END, "\n常见错误码说明:\n")
        self.result_text.insert(tk.END, "205201: 错误的条码\n")
        self.result_text.insert(tk.END, "205202: 未知的条码\n")
        self.result_text.insert(tk.END, "205203: 错误的请求参数\n")
        self.result_text.insert(tk.END, "10001: 错误的请求KEY\n")
        self.result_text.insert(tk.END, "10002: 该KEY无请求权限\n")
        
        self.status_label.config(text="查询失败")
        
    def run(self):
        """运行程序"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.root.quit()

if __name__ == "__main__":
    app = GS1BarcodeQuery()
    app.run()
