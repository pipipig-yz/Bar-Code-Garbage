import cv2
import numpy as np
from pyzbar import pyzbar
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
import sqlite3
from openai import OpenAI
import speech_recognition as sr
import pyaudio
import socket
import json

class BarcodeScannerStable:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Product Barcode Scanner (Stable Version)")
        self.root.geometry("1400x900")
        self.root.configure(bg='#f0f0f0')
        
        # 摄像头相关变量
        self.cap = None
        self.is_running = False
        self.current_frame = None
        
        # 已识别的条形码集合（用于去重）
        self.detected_barcodes = set()
        
        # 编码上传相关变量
        self.barcode_checkboxes = {}  # 存储每个编码的checkbox
        self.selected_barcodes = set()  # 存储选中的编码
        
        # 上一个识别出的GS1编码（用于备用搜索）
        self.last_gs1_code = None
        
        # 数据库相关变量
        self.db_path = 'products.db'
        self.init_database()
        
        # 错误计数
        self.error_count = 0
        self.max_errors = 5
        
        # DeepSeek OpenAI客户端配置
        self.openai_client = OpenAI(
            api_key="sk-c33383af3d7c47488b9b55000b659d50", 
            base_url="https://api.deepseek.com"
        )
        
        # 语音识别配置
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self.is_listening = False
        self.init_voice_recognition()
        
        # 已询问过的GS1代码集合，避免重复弹窗
        self.asked_gs1_codes = set()
        
        # 加载垃圾分类图片
        self.load_waste_classification_images()
        
        # 创建GUI界面
        self.create_widgets()
        
        # 启动摄像头
        self.start_camera()
    
    def load_waste_classification_images(self):
        """加载垃圾分类图片"""
        try:
            from PIL import Image, ImageTk
            import os
            
            # 图片路径
            image_dir = "图形化显示"
            self.waste_images = {}
            
            # 定义图片映射
            image_mapping = {
                'recycle': '可回收.jpg',
                'landfill': '其他垃圾.jpg', 
                'compost': '湿垃圾.jpg',
                'hazardous': '有害垃圾 - 副本 (3).jpg'
            }
            
            # 加载图片
            for waste_type, filename in image_mapping.items():
                image_path = os.path.join(image_dir, filename)
                if os.path.exists(image_path):
                    try:
                        img = Image.open(image_path)
                        # 调整图片大小为80x80像素
                        img = img.resize((80, 80), Image.Resampling.LANCZOS)
                        photo = ImageTk.PhotoImage(img)
                        self.waste_images[waste_type] = photo
                        print(f"成功加载图片: {filename}")
                    except Exception as e:
                        print(f"加载图片失败 {filename}: {e}")
                        self.waste_images[waste_type] = None
                else:
                    print(f"图片文件不存在: {image_path}")
                    self.waste_images[waste_type] = None
                    
        except Exception as e:
            print(f"加载垃圾分类图片错误: {e}")
            self.waste_images = {}
    
    def init_voice_recognition(self):
        """初始化语音识别"""
        try:
            print("正在初始化语音识别...")
            
            # 初始化麦克风
            self.microphone = sr.Microphone()
            
            # 测试麦克风访问
            with self.microphone as source:
                print("麦克风初始化成功!")
            
            print("语音识别初始化完成（使用Google和Sphinx）")
            return True
                
        except Exception as e:
            print(f"语音识别初始化失败: {e}")
            self.microphone = None
            return False
    
    def create_product_info_display(self, parent):
        """创建图形化的产品信息显示界面"""
        # 主容器
        self.product_info_container = tk.Frame(parent, bg='white')
        self.product_info_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 1. 产品名称区域
        self.product_name_frame = tk.Frame(self.product_info_container, bg='white')
        self.product_name_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.product_name_label = tk.Label(self.product_name_frame, text="Product Name: Not Set", 
                                         font=('Arial', 16, 'bold'), bg='white', fg='#333333')
        self.product_name_label.pack(anchor=tk.W)
        
        # 2. 产品照片区域
        self.product_image_frame = tk.Frame(self.product_info_container, bg='white')
        self.product_image_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.product_image_label = tk.Label(self.product_image_frame, text="No Image", 
                                          font=('Arial', 12), bg='#f8f8f8', 
                                          relief=tk.SUNKEN, bd=1, width=25, height=8)
        self.product_image_label.pack(anchor=tk.W)
        
        # 3. 垃圾分类区域
        waste_classification_frame = tk.Frame(self.product_info_container, bg='white')
        waste_classification_frame.pack(fill=tk.BOTH, expand=True)
        
        # 垃圾分类标题
        waste_title = tk.Label(waste_classification_frame, text="Waste Classification", 
                              font=('Arial', 16, 'bold'), bg='white', fg='#333333')
        waste_title.pack(anchor=tk.W, pady=(0, 10))
        
        # 左右分栏容器
        waste_content_frame = tk.Frame(waste_classification_frame, bg='white')
        waste_content_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧：包装垃圾分类
        self.packaging_frame = tk.Frame(waste_content_frame, bg='#f0f8ff', relief=tk.RAISED, bd=1)
        self.packaging_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # 包装分类标题
        packaging_title = tk.Label(self.packaging_frame, text="Package", 
                                  font=('Arial', 14, 'bold'), bg='#f0f8ff', fg='#333333')
        packaging_title.pack(pady=5)
        
        # 包装分类状态
        self.packaging_status_label = tk.Label(self.packaging_frame, text="Recycle", 
                                              font=('Arial', 12, 'bold'), bg='#f0f8ff', fg='#059669')
        self.packaging_status_label.pack(pady=2)
        
        # 包装分类图标
        self.packaging_icon_label = tk.Label(self.packaging_frame, text="📦", 
                                            font=('Arial', 32), bg='#f0f8ff')
        self.packaging_icon_label.pack(pady=5)
        
        # 包装材料信息
        self.packaging_material_label = tk.Label(self.packaging_frame, text="Material: Not Set", 
                                                font=('Arial', 12, 'bold'), bg='#f0f8ff', fg='#333333')
        self.packaging_material_label.pack(pady=3)
        
        # 塑料类型信息
        self.plastic_type_label = tk.Label(self.packaging_frame, text="Plastic Type: Not Set", 
                                          font=('Arial', 12, 'bold'), bg='#f0f8ff', fg='#333333')
        self.plastic_type_label.pack(pady=3)
        
        # 右侧：产品本身垃圾分类
        self.product_waste_frame = tk.Frame(waste_content_frame, bg='#fff8f0', relief=tk.RAISED, bd=1)
        self.product_waste_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # 产品分类标题
        product_waste_title = tk.Label(self.product_waste_frame, text="Product", 
                                      font=('Arial', 14, 'bold'), bg='#fff8f0', fg='#333333')
        product_waste_title.pack(pady=5)
        
        # 产品分类状态
        self.product_waste_status_label = tk.Label(self.product_waste_frame, text="Recycle", 
                                                  font=('Arial', 12, 'bold'), bg='#fff8f0', fg='#059669')
        self.product_waste_status_label.pack(pady=2)
        
        # 产品分类图标
        self.product_waste_icon_label = tk.Label(self.product_waste_frame, text="🛍️", 
                                                font=('Arial', 32), bg='#fff8f0')
        self.product_waste_icon_label.pack(pady=5)
        
        # 产品分类信息
        self.product_waste_info_label = tk.Label(self.product_waste_frame, text="Classification: Not Set", 
                                                font=('Arial', 12, 'bold'), bg='#fff8f0', fg='#333333')
        self.product_waste_info_label.pack(pady=3)
    
    def update_product_info_display(self, product_data):
        """更新图形化产品信息显示"""
        try:
            product_name, product_image, packaging_waste_type, product_waste_type, packaging_material, plastic_type, created_at = product_data
            
            # 1. 更新产品名称
            if product_name:
                self.product_name_label.config(text=f"Product Name: {product_name}")
            else:
                self.product_name_label.config(text="Product Name: Not Set")
            
            # 2. 更新产品照片
            if product_image:
                try:
                    # 尝试加载并显示产品照片
                    from PIL import Image, ImageTk
                    img = Image.open(product_image)
                    # 设置图片高度为4cm，宽度自动调整
                    # 假设屏幕DPI为96，1英寸=2.54cm，所以1cm≈37.8像素
                    cm_to_pixels = 37.8
                    target_height_cm = 4
                    target_height_pixels = int(target_height_cm * cm_to_pixels)
                    
                    # 计算保持宽高比的宽度
                    original_width, original_height = img.size
                    aspect_ratio = original_width / original_height
                    target_width_pixels = int(target_height_pixels * aspect_ratio)
                    
                    img = img.resize((target_width_pixels, target_height_pixels), Image.Resampling.LANCZOS)
                    
                    photo = ImageTk.PhotoImage(img)
                    self.product_image_label.config(image=photo, text="")
                    self.product_image_label.image = photo  # 保持引用
                except Exception as e:
                    print(f"加载产品照片错误: {e}")
                    self.product_image_label.config(image="", text="Image Load Error")
            else:
                self.product_image_label.config(image="", text="No Image")
            
            # 3. 更新包装垃圾分类
            if packaging_waste_type:
                self.packaging_status_label.config(text=packaging_waste_type)
                # 根据分类类型设置颜色和图片
                waste_type_lower = packaging_waste_type.lower()
                if "recyclable" in waste_type_lower or "recycle" in waste_type_lower or "可回收" in packaging_waste_type:
                    self.packaging_status_label.config(fg='#059669')  # 绿色
                    self.update_waste_icon(self.packaging_icon_label, 'recycle')
                elif "other waste" in waste_type_lower or "landfill" in waste_type_lower or "其他垃圾" in packaging_waste_type:
                    self.packaging_status_label.config(fg='#DC2626')  # 红色
                    self.update_waste_icon(self.packaging_icon_label, 'landfill')
                elif "wet waste" in waste_type_lower or "compost" in waste_type_lower or "湿垃圾" in packaging_waste_type:
                    self.packaging_status_label.config(fg='#EA580C')  # 橙色
                    self.update_waste_icon(self.packaging_icon_label, 'compost')
                elif "hazardous" in waste_type_lower or "有害垃圾" in packaging_waste_type:
                    self.packaging_status_label.config(fg='#DC2626')  # 红色
                    self.update_waste_icon(self.packaging_icon_label, 'hazardous')
                else:
                    self.packaging_status_label.config(fg='#6B7280')  # 灰色
                    self.packaging_icon_label.config(image="", text="❓")
            else:
                self.packaging_status_label.config(text="Not Set", fg='#6B7280')
                self.packaging_icon_label.config(image="", text="❓")
            
            # 更新包装材料信息
            if packaging_material:
                self.packaging_material_label.config(text=f"Material: {packaging_material}")
                if plastic_type and packaging_material == 'Plastic':
                    self.plastic_type_label.config(text=f"Plastic Type: {plastic_type}")
                else:
                    self.plastic_type_label.config(text="Plastic Type: N/A")
            else:
                self.packaging_material_label.config(text="Material: Not Set")
                self.plastic_type_label.config(text="Plastic Type: Not Set")
            
            # 4. 更新产品本身垃圾分类
            if product_waste_type:
                self.product_waste_status_label.config(text=product_waste_type)
                # 根据分类类型设置颜色和图片
                waste_type_lower = product_waste_type.lower()
                if "recyclable" in waste_type_lower or "recycle" in waste_type_lower or "可回收" in product_waste_type:
                    self.product_waste_status_label.config(fg='#059669')  # 绿色
                    self.update_waste_icon(self.product_waste_icon_label, 'recycle')
                elif "other waste" in waste_type_lower or "landfill" in waste_type_lower or "其他垃圾" in product_waste_type:
                    self.product_waste_status_label.config(fg='#DC2626')  # 红色
                    self.update_waste_icon(self.product_waste_icon_label, 'landfill')
                elif "wet waste" in waste_type_lower or "compost" in waste_type_lower or "湿垃圾" in product_waste_type:
                    self.product_waste_status_label.config(fg='#EA580C')  # 橙色
                    self.update_waste_icon(self.product_waste_icon_label, 'compost')
                elif "hazardous" in waste_type_lower or "有害垃圾" in product_waste_type:
                    self.product_waste_status_label.config(fg='#DC2626')  # 红色
                    self.update_waste_icon(self.product_waste_icon_label, 'hazardous')
                else:
                    self.product_waste_status_label.config(fg='#6B7280')  # 灰色
                    self.product_waste_icon_label.config(image="", text="❓")
                
                self.product_waste_info_label.config(text=f"Classification: {product_waste_type}")
            else:
                self.product_waste_status_label.config(text="Not Set", fg='#6B7280')
                self.product_waste_icon_label.config(image="", text="❓")
                self.product_waste_info_label.config(text="Classification: Not Set")
                
        except Exception as e:
            print(f"更新产品信息显示错误: {e}")
    
    def update_waste_icon(self, icon_label, waste_type):
        """更新垃圾分类图标"""
        try:
            print(f"更新垃圾分类图标: {waste_type}")
            if hasattr(self, 'waste_images') and waste_type in self.waste_images:
                if self.waste_images[waste_type] is not None:
                    print(f"显示图片: {waste_type}")
                    icon_label.config(image=self.waste_images[waste_type], text="")
                    icon_label.image = self.waste_images[waste_type]  # 保持引用
                else:
                    print(f"图片为空，使用emoji备选: {waste_type}")
                    # 如果图片加载失败，使用emoji作为备选
                    fallback_icons = {
                        'recycle': '♻️',
                        'landfill': '🗑️',
                        'compost': '🌱',
                        'hazardous': '⚠️'
                    }
                    icon_label.config(image="", text=fallback_icons.get(waste_type, '❓'))
            else:
                print(f"没有找到图片，使用emoji备选: {waste_type}")
                # 如果没有图片，使用emoji作为备选
                fallback_icons = {
                    'recycle': '♻️',
                    'landfill': '🗑️',
                    'compost': '🌱',
                    'hazardous': '⚠️'
                }
                icon_label.config(image="", text=fallback_icons.get(waste_type, '❓'))
        except Exception as e:
            print(f"更新垃圾分类图标错误: {e}")
            icon_label.config(image="", text="❓")
    
    def clear_product_info_display(self):
        """清空产品信息显示"""
        try:
            self.product_name_label.config(text="Product Name: Not Set")
            self.product_image_label.config(image="", text="No Image")
            
            self.packaging_status_label.config(text="Not Set", fg='#6B7280')
            self.packaging_icon_label.config(image="", text="❓")
            self.packaging_material_label.config(text="Material: Not Set")
            self.plastic_type_label.config(text="Plastic Type: Not Set")
            
            self.product_waste_status_label.config(text="Not Set", fg='#6B7280')
            self.product_waste_icon_label.config(image="", text="❓")
            self.product_waste_info_label.config(text="Classification: Not Set")
        except Exception as e:
            print(f"清空产品信息显示错误: {e}")
    
    def init_database(self):
        """初始化数据库连接"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            cursor = self.conn.cursor()
            
            # 检查表是否存在，如果不存在则创建
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    gs1_code TEXT UNIQUE,
                    product_name TEXT,
                    product_image TEXT,
                    packaging_waste_type TEXT,
                    product_waste_type TEXT,
                    packaging_material TEXT,
                    plastic_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            self.conn.commit()
            print("数据库初始化成功")
            
        except Exception as e:
            print(f"数据库初始化失败: {e}")
            self.conn = None
        
    def create_widgets(self):
        """创建GUI界面"""
        # 主框架
        main_frame = tk.Frame(self.root, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左侧摄像头显示区域 (减小20%)
        left_frame = tk.Frame(main_frame, bg='white', relief=tk.RAISED, bd=2)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        # 设置左侧框架的权重为0.8 (减小20%)
        main_frame.columnconfigure(0, weight=8)
        main_frame.columnconfigure(1, weight=12)
        
        # 摄像头标题
        camera_label = tk.Label(left_frame, text="Camera Recognition View (Stable Version)", 
                               font=('Arial', 14, 'bold'), bg='white')
        camera_label.pack(pady=10)
        
        # 摄像头显示标签
        self.camera_label = tk.Label(left_frame, bg='black')
        self.camera_label.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # 右侧区域 - 分为上下两部分
        right_frame = tk.Frame(main_frame, bg='white', relief=tk.RAISED, bd=2)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # ========== 右侧上方：识别结果和代码选择 ==========
        top_right_frame = tk.Frame(right_frame, bg='white', relief=tk.RAISED, bd=1)
        top_right_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(5, 2))
        
        # 识别结果标题
        recognition_title = tk.Label(top_right_frame, text="Recognition Results", 
                                   font=('Arial', 14, 'bold'), bg='white')
        recognition_title.pack(pady=5)
        
        # 识别结果显示区域 (缩小到5行)
        self.recognition_text = scrolledtext.ScrolledText(top_right_frame, 
                                                         width=40, height=5,
                                                         font=('Consolas', 10),
                                                         bg='#f8f8f8',
                                                         relief=tk.SUNKEN,
                                                         bd=1)
        self.recognition_text.pack(padx=5, pady=5, fill=tk.X)
        
        # 代码选择区域
        code_selection_frame = tk.Frame(top_right_frame, bg='white')
        code_selection_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 代码选择标题
        code_selection_label = tk.Label(code_selection_frame, text="Select Code to Search:", 
                                       font=('Arial', 10, 'bold'), bg='white')
        code_selection_label.pack(anchor='w')
        
        # 代码选择下拉框
        self.selected_code_var = tk.StringVar()
        self.code_combobox = ttk.Combobox(code_selection_frame, 
                                         textvariable=self.selected_code_var,
                                         font=('Consolas', 10),
                                         state='readonly',
                                         width=30)
        self.code_combobox.pack(side=tk.LEFT, padx=(0, 5), pady=2)
        
        # 搜索按钮
        search_button = tk.Button(code_selection_frame, text="Search", 
                                 command=self.search_product_in_database,
                                 font=('Arial', 10, 'bold'),
                                 bg='#007acc', fg='white',
                                 relief=tk.RAISED, bd=2,
                                 padx=15, pady=3)
        search_button.pack(side=tk.LEFT, padx=5, pady=2)
        
        # ========== DeepSeek Waste Classification Assistant ==========
        chat_frame = tk.Frame(top_right_frame, bg='white', relief=tk.RAISED, bd=1)
        chat_frame.pack(fill=tk.X, padx=5, pady=(10, 5))
        
        # 聊天标题
        chat_title = tk.Label(chat_frame, text="DeepSeek Waste Classification Assistant", 
                             font=('Arial', 12, 'bold'), bg='white', fg='#333333')
        chat_title.pack(pady=5)
        
        # 聊天显示区域
        self.chat_display = scrolledtext.ScrolledText(chat_frame, 
                                                     width=40, height=6,
                                                     font=('Arial', 9),
                                                     bg='#f8f8f8',
                                                     relief=tk.SUNKEN,
                                                     bd=1,
                                                     state=tk.DISABLED)
        self.chat_display.pack(padx=5, pady=5, fill=tk.X)
        
        # 配置文本标签颜色
        self.chat_display.tag_configure("user", foreground="#0066cc")
        self.chat_display.tag_configure("assistant", foreground="#006600")
        self.chat_display.tag_configure("system", foreground="#cc6600")
        
        # 输入框和发送按钮
        input_frame = tk.Frame(chat_frame, bg='white')
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.chat_input = tk.Entry(input_frame, font=('Arial', 10), width=25)
        self.chat_input.pack(side=tk.LEFT, padx=(0, 5), pady=2)
        self.chat_input.bind('<Return>', lambda e: self.send_chat_message())
        
        # 语音识别按钮
        self.voice_button = tk.Button(input_frame, text="🎤", 
                                     command=self.start_voice_recognition,
                                     font=('Arial', 12),
                                     bg='#ff6b6b', fg='white',
                                     relief=tk.RAISED, bd=2,
                                     padx=8, pady=2)
        self.voice_button.pack(side=tk.LEFT, padx=(0, 5), pady=2)
        
        send_button = tk.Button(input_frame, text="Send", 
                               command=self.send_chat_message,
                               font=('Arial', 10, 'bold'),
                               bg='#28a745', fg='white',
                               relief=tk.RAISED, bd=2,
                               padx=10, pady=2)
        send_button.pack(side=tk.LEFT, pady=2)
        
        # 测试按钮
        test_button = tk.Button(input_frame, text="Test", 
                               command=self.test_microphone,
                               font=('Arial', 10),
                               bg='#6c757d', fg='white',
                               relief=tk.RAISED, bd=2,
                               padx=8, pady=2)
        test_button.pack(side=tk.LEFT, padx=(5, 0), pady=2)
        
        # ========== 右侧下方：产品信息显示 ==========
        bottom_right_frame = tk.Frame(right_frame, bg='white', relief=tk.RAISED, bd=1)
        bottom_right_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(2, 5))
        
        # 产品信息标题
        product_info_title = tk.Label(bottom_right_frame, text="Product Information", 
                                     font=('Arial', 14, 'bold'), bg='white')
        product_info_title.pack(pady=5)
        
        # 产品信息显示区域 - 重新设计为图形化界面
        self.create_product_info_display(bottom_right_frame)
        
        # 底部控制按钮区域
        control_frame = tk.Frame(self.root, bg='#f0f0f0')
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 状态标签
        self.status_label = tk.Label(control_frame, text="Status: Starting camera...", 
                                    font=('Arial', 10), bg='#f0f0f0')
        self.status_label.pack(side=tk.LEFT)
        
        # 关闭按钮
        close_button = tk.Button(control_frame, text="Close Program", 
                                command=self.close_program,
                                font=('Arial', 12, 'bold'),
                                bg='#ff4444', fg='white',
                                relief=tk.RAISED, bd=2,
                                padx=20, pady=5)
        close_button.pack(side=tk.RIGHT)
        
        # 清空按钮
        clear_button = tk.Button(control_frame, text="Clear Results", 
                                command=self.clear_results,
                                font=('Arial', 12),
                                bg='#4444ff', fg='white',
                                relief=tk.RAISED, bd=2,
                                padx=20, pady=5)
        clear_button.pack(side=tk.RIGHT, padx=(0, 10))
        
        # 重启摄像头按钮
        restart_button = tk.Button(control_frame, text="Restart Camera", 
                                  command=self.restart_camera,
                                  font=('Arial', 12),
                                  bg='#00aa00', fg='white',
                                  relief=tk.RAISED, bd=2,
                                  padx=20, pady=5)
        restart_button.pack(side=tk.RIGHT, padx=(0, 10))
        
    def start_camera(self):
        """Start camera"""
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                self.status_label.config(text="Status: Unable to open camera")
                return
            
            # 设置摄像头分辨率（降低分辨率提高稳定性）
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            # 设置缓冲区大小
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            self.is_running = True
            self.error_count = 0
            self.status_label.config(text="Status: Camera started, recognizing barcodes...")
            
            # 启动摄像头线程
            self.camera_thread = threading.Thread(target=self.camera_loop, daemon=True)
            self.camera_thread.start()
            
        except Exception as e:
            self.status_label.config(text=f"Status: Camera startup failed - {str(e)}")
    
    def camera_loop(self):
        """Camera loop processing"""
        while self.is_running:
            try:
                ret, frame = self.cap.read()
                if not ret:
                    self.error_count += 1
                    if self.error_count > self.max_errors:
                        self.root.after(0, self.update_status, "Status: Camera read failed, please restart camera")
                        break
                    time.sleep(0.1)
                    continue
                
                # 重置错误计数
                self.error_count = 0
                
                # 翻转图像（镜像效果）
                frame = cv2.flip(frame, 1)
                
                # 识别条形码
                frame_with_barcodes = self.detect_barcodes(frame)
                
                # 更新显示
                self.update_camera_display(frame_with_barcodes)
                
                time.sleep(0.05)  # 降低帧率，提高稳定性
                
            except Exception as e:
                print(f"摄像头循环错误: {e}")
                self.error_count += 1
                if self.error_count > self.max_errors:
                    self.root.after(0, self.update_status, f"Status: Camera error - {str(e)}")
                    break
                time.sleep(0.1)
    
    def detect_barcodes(self, frame):
        """Detect barcodes and annotate"""
        try:
            # 转换为灰度图像
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # 图像预处理 - 增强对比度
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(gray)
            
            # 尝试多种图像处理方式
            images_to_try = [
                gray,           # 原始灰度图
                enhanced,       # 增强对比度
                cv2.GaussianBlur(enhanced, (3, 3), 0),  # 去噪
                cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],  # 二值化
            ]
            
            all_barcodes = []
            for img in images_to_try:
                try:
                    # 使用pyzbar检测条形码
                    barcodes = pyzbar.decode(img)
                    all_barcodes.extend(barcodes)
                except Exception as e:
                    print(f"pyzbar解码错误: {e}")
                    continue
            
            # 去重
            unique_barcodes = []
            seen_data = set()
            for barcode in all_barcodes:
                try:
                    barcode_data = barcode.data.decode('utf-8')
                    if barcode_data not in seen_data:
                        unique_barcodes.append(barcode)
                        seen_data.add(barcode_data)
                except Exception as e:
                    print(f"条形码数据解码错误: {e}")
                    continue
            
            # 在图像上标注检测到的条形码
            for barcode in unique_barcodes:
                try:
                    # 获取条形码的边界框坐标
                    (x, y, w, h) = barcode.rect
                    
                    # 绘制矩形框
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    
                    # 获取条形码数据
                    barcode_data = barcode.data.decode('utf-8')
                    barcode_type = barcode.type
                    
                    # 在条形码上方显示数据
                    text = f"{barcode_type}: {barcode_data}"
                    cv2.putText(frame, text, (x, y - 10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    
                    # 如果这是新的条形码，添加到输出
                    if barcode_data not in self.detected_barcodes:
                        self.detected_barcodes.add(barcode_data)
                        self.add_barcode_to_output(barcode_data, barcode_type)
                        
                except Exception as e:
                    print(f"条形码标注错误: {e}")
                    continue
            
            # 更新状态显示
            if len(unique_barcodes) > 0:
                self.root.after(0, self.update_status, f"Status: Detected {len(unique_barcodes)} barcodes")
            else:
                self.root.after(0, self.update_status, "Status: Recognizing barcodes...")
            
        except Exception as e:
            print(f"条形码检测错误: {e}")
            self.root.after(0, self.update_status, f"Status: Detection error - {str(e)}")
        
        return frame
    
    def add_barcode_to_output(self, barcode_data, barcode_type):
        """Add barcode to output area and auto-search if GS1 code"""
        try:
            timestamp = time.strftime("%H:%M:%S")
            output_text = f"[{timestamp}] {barcode_type}: {barcode_data}\n"
            
            # 在主线程中更新GUI
            self.root.after(0, self.update_recognition_text, output_text)
            self.root.after(0, self.update_code_combobox, barcode_data)
            
            # 如果是GS1代码，自动搜索
            if barcode_type in ['EAN13', 'EAN8', 'UPC_A', 'UPC_E', 'CODE128', 'CODE39']:
                self.root.after(100, self.auto_search_barcode, barcode_data)
                
        except Exception as e:
            print(f"添加输出错误: {e}")
    
    
    def update_recognition_text(self, text):
        """Update recognition text (called in main thread)"""
        try:
            self.recognition_text.insert(tk.END, text)
            self.recognition_text.see(tk.END)  # 滚动到底部
        except Exception as e:
            print(f"更新识别文本错误: {e}")
    
    def update_code_combobox(self, barcode_data):
        """Update code combobox with new barcode"""
        try:
            current_values = list(self.code_combobox['values'])
            if barcode_data not in current_values:
                current_values.append(barcode_data)
                self.code_combobox['values'] = current_values
                # 自动选择最新的代码
                self.code_combobox.set(barcode_data)
        except Exception as e:
            print(f"更新下拉框错误: {e}")
    
    def auto_search_barcode(self, barcode_data):
        """自动搜索条形码"""
        try:
            # 设置选中的代码
            self.selected_code_var.set(barcode_data)
            
            # 执行搜索
            found = self.search_product_in_database()
            
            # 如果当前编码未找到且存在上一个GS1编码，尝试搜索上一个编码
            if not found and self.last_gs1_code and self.last_gs1_code != barcode_data:
                print(f"当前编码 {barcode_data} 未找到，尝试上一个编码: {self.last_gs1_code}")
                self.selected_code_var.set(self.last_gs1_code)
                found = self.search_product_in_database()
                if found:
                    self.update_status(f"Status: 使用上一个编码找到产品: {self.last_gs1_code}")
                else:
                    self.update_status(f"Status: 当前编码和上一个编码都未找到产品信息")
            else:
                if found:
                    self.update_status(f"Status: 找到产品信息 - {barcode_data}")
                else:
                    self.update_status(f"Status: 未找到产品信息 - {barcode_data}")
            
            # 更新上一个GS1编码
            self.last_gs1_code = barcode_data
            
        except Exception as e:
            print(f"自动搜索错误: {e}")
            self.update_status(f"Status: Auto-search failed - {str(e)}")
    
    def search_product_in_database(self):
        """在数据库中搜索选中的GS1代码"""
        try:
            selected_code = self.selected_code_var.get()
            if not selected_code:
                messagebox.showwarning("警告", "请先选择一个代码进行搜索")
                return False
            
            if not self.conn:
                messagebox.showerror("错误", "数据库连接失败")
                return False
            
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT product_name, product_image, packaging_waste_type, 
                       product_waste_type, packaging_material, plastic_type, created_at
                FROM products 
                WHERE gs1_code = ?
            """, (selected_code,))
            
            result = cursor.fetchone()
            
            if result:
                product_name, product_image, packaging_waste_type, product_waste_type, packaging_material, plastic_type, created_at = result
                
                # 使用新的图形化显示更新产品信息
                self.update_product_info_display(result)
                
                return True
                
            else:
                # 未找到产品 - 清空显示
                self.clear_product_info_display()
                
                # 询问是否要添加新产品
                self.ask_to_add_new_product(selected_code)
                
                return False
                
        except Exception as e:
            print(f"搜索产品错误: {e}")
            messagebox.showerror("错误", f"搜索失败: {str(e)}")
            return False
    
    def ask_to_add_new_product(self, gs1_code):
        """询问是否要添加新产品"""
        try:
            # 检查是否已经询问过这个GS1代码
            if gs1_code in self.asked_gs1_codes:
                # 已经询问过，不再弹窗，只在聊天框中显示信息
                self.add_chat_message("System", f"GS1代码 '{gs1_code}' 未找到，之前已询问过是否添加。")
                return
            
            # 将GS1代码添加到已询问集合中
            self.asked_gs1_codes.add(gs1_code)
            
            # 显示询问对话框
            result = messagebox.askyesno(
                "未找到产品", 
                f"GS1代码 '{gs1_code}' 在数据库中未找到。\n\n是否要添加这个新产品？",
                icon='question'
            )
            
            if result:
                # 用户选择添加新产品，打开产品管理器
                self.open_product_manager_with_code(gs1_code)
            else:
                # 用户选择不添加，显示提示信息
                self.add_chat_message("System", f"GS1代码 '{gs1_code}' 未找到，用户选择不添加新产品。")
                
        except Exception as e:
            print(f"询问添加新产品错误: {e}")
            self.add_chat_message("System", f"Error asking to add new product: {str(e)}")
    
    def open_product_manager_with_code(self, gs1_code):
        """打开产品管理器并预填GS1代码"""
        try:
            # 导入产品管理器
            import subprocess
            import sys
            import os
            
            # 获取产品管理器脚本路径
            product_manager_path = os.path.join(os.path.dirname(__file__), "product_manager.py")
            
            if os.path.exists(product_manager_path):
                # 启动产品管理器，并传递GS1代码作为参数
                subprocess.Popen([
                    sys.executable, 
                    product_manager_path, 
                    "--gs1-code", 
                    gs1_code
                ])
                
                self.add_chat_message("System", f"已打开产品管理器，GS1代码 '{gs1_code}' 已预填。")
                self.update_status(f"Status: 已打开产品管理器添加新产品 - {gs1_code}")
                
            else:
                messagebox.showerror("错误", "找不到产品管理器文件 (product_manager.py)")
                self.add_chat_message("System", "Error: Product manager file not found.")
                
        except Exception as e:
            print(f"打开产品管理器错误: {e}")
            messagebox.showerror("错误", f"无法打开产品管理器: {str(e)}")
            self.add_chat_message("System", f"Error opening product manager: {str(e)}")
    
    def update_status(self, status_text):
        """Update status display (called in main thread)"""
        try:
            self.status_label.config(text=status_text)
        except Exception as e:
            print(f"更新状态错误: {e}")
    
    def send_chat_message(self):
        """发送聊天消息到DeepSeek"""
        try:
            message = self.chat_input.get().strip()
            if not message:
                return
            
            # 清空输入框
            self.chat_input.delete(0, tk.END)
            
            # 显示用户消息
            self.add_chat_message("User", message)
            
            # 在后台线程中调用DeepSeek API
            threading.Thread(target=self.get_deepseek_response, args=(message,), daemon=True).start()
            
        except Exception as e:
            print(f"发送聊天消息错误: {e}")
            self.add_chat_message("System", f"Failed to send message: {str(e)}")
    
    def get_deepseek_response(self, user_message):
        """获取DeepSeek回复"""
        try:
            # 构建垃圾分类相关的系统提示
            system_prompt = """You are a professional waste classification assistant. Please determine which waste category the product provided by the user should belong to.

Waste Classification Standards:
1. Recyclable Waste: Paper, plastic, metal, glass, textiles and other reusable materials
2. Wet Waste (Organic Waste): Food scraps, fruit peels, vegetable leaves and other easily decomposable organic waste
3. Hazardous Waste: Batteries, medicines, paint, fluorescent tubes and other environmentally harmful waste
4. Other Waste (Dry Waste): Other waste except the above three categories

Please answer concisely and clearly in the following format:
Product Name: [Product Name]
Waste Classification: [Waste Category]
Explanation: [Brief explanation of the reason]

If the product name is not clear enough, please ask for more details.

IMPORTANT: Please respond in English only."""
            
            response = self.openai_client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                stream=False
            )
            
            ai_response = response.choices[0].message.content
            
            # 在主线程中更新聊天显示
            self.root.after(0, self.add_chat_message, "DeepSeek Assistant", ai_response)
            
            # 解析回复并更新垃圾分类显示
            self.root.after(0, self.parse_and_update_waste_classification, ai_response)
            
        except Exception as e:
            print(f"获取DeepSeek回复错误: {e}")
            error_msg = f"Failed to get response: {str(e)}"
            self.root.after(0, self.add_chat_message, "System", error_msg)
    
    def add_chat_message(self, sender, message):
        """添加聊天消息到显示区域"""
        try:
            self.chat_display.config(state=tk.NORMAL)
            
            # 添加时间戳
            timestamp = time.strftime("%H:%M:%S")
            
            # 根据发送者设置不同的颜色和格式
            if sender == "User":
                self.chat_display.insert(tk.END, f"[{timestamp}] {sender}: {message}\n", "user")
            elif sender == "DeepSeek Assistant":
                self.chat_display.insert(tk.END, f"[{timestamp}] {sender}:\n{message}\n\n", "assistant")
            else:
                self.chat_display.insert(tk.END, f"[{timestamp}] {sender}: {message}\n", "system")
            
            # 滚动到底部
            self.chat_display.see(tk.END)
            self.chat_display.config(state=tk.DISABLED)
            
        except Exception as e:
            print(f"添加聊天消息错误: {e}")
    
    def parse_and_update_waste_classification(self, ai_response):
        """解析DeepSeek回复并更新垃圾分类显示"""
        try:
            # 解析回复中的垃圾分类信息
            waste_type = self.extract_waste_type_from_response(ai_response)
            
            # 解析回复中的产品名称
            product_name = self.extract_product_name_from_response(ai_response)
            
            if waste_type:
                # 更新产品垃圾分类显示
                self.update_product_waste_display_from_chat(waste_type)
                print(f"Updated waste classification to: {waste_type}")
                
                # 如果解析到产品名称，也更新产品名称显示
                if product_name:
                    self.update_product_name_from_chat(product_name)
                    print(f"Updated product name to: {product_name}")
            else:
                print("Could not extract waste type from response")
                
        except Exception as e:
            print(f"解析垃圾分类回复错误: {e}")
    
    def extract_waste_type_from_response(self, response):
        """从DeepSeek回复中提取垃圾分类类型"""
        try:
            response_lower = response.lower()
            
            # 定义垃圾分类关键词映射
            waste_type_mapping = {
                'recyclable': ['recyclable', 'recycle', 'recycling'],
                'hazardous': ['hazardous', 'dangerous', 'toxic'],
                'wet': ['wet waste', 'organic', 'compost', 'food waste'],
                'other': ['other waste', 'dry waste', 'general waste', 'residual']
            }
            
            # 查找匹配的垃圾分类
            for waste_type, keywords in waste_type_mapping.items():
                for keyword in keywords:
                    if keyword in response_lower:
                        return waste_type
            
            return None
            
        except Exception as e:
            print(f"提取垃圾分类类型错误: {e}")
            return None
    
    def extract_product_name_from_response(self, response):
        """从DeepSeek回复中提取产品名称"""
        try:
            lines = response.split('\n')
            for line in lines:
                line = line.strip()
                # 查找 "Product Name:" 开头的行
                if line.lower().startswith('product name:'):
                    product_name = line.split(':', 1)[1].strip()
                    if product_name and product_name != '[Product Name]':
                        return product_name
                # 查找 "产品名称:" 开头的行（中文支持）
                elif line.startswith('产品名称:'):
                    product_name = line.split(':', 1)[1].strip()
                    if product_name and product_name != '[产品名称]':
                        return product_name
            
            # 如果没有找到标准格式，尝试从第一行提取
            first_line = lines[0].strip() if lines else ""
            if first_line and not first_line.lower().startswith(('waste', 'classification', 'explanation')):
                return first_line
            
            return None
            
        except Exception as e:
            print(f"提取产品名称错误: {e}")
            return None
    
    def update_product_name_from_chat(self, product_name):
        """根据聊天结果更新产品名称显示"""
        try:
            # 更新产品名称显示
            self.product_name_label.config(text=f"Product Name: {product_name}")
            print(f"Updated product name display to: {product_name}")
            
        except Exception as e:
            print(f"更新产品名称显示错误: {e}")
    
    def update_product_waste_display_from_chat(self, waste_type):
        """根据聊天结果更新产品垃圾分类显示"""
        try:
            # 映射垃圾分类类型到显示文本
            waste_type_display = {
                'recyclable': 'Recyclable',
                'hazardous': 'Hazardous',
                'wet': 'Wet Waste',
                'other': 'Other Waste'
            }
            
            display_text = waste_type_display.get(waste_type, 'Unknown')
            
            # 更新产品垃圾分类状态
            self.product_waste_status_label.config(text=display_text)
            
            # 根据分类类型设置颜色和图片
            if waste_type == 'recyclable':
                self.product_waste_status_label.config(fg='#059669')  # 绿色
                self.update_waste_icon(self.product_waste_icon_label, 'recycle')
            elif waste_type == 'hazardous':
                self.product_waste_status_label.config(fg='#DC2626')  # 红色
                self.update_waste_icon(self.product_waste_icon_label, 'hazardous')
            elif waste_type == 'wet':
                self.product_waste_status_label.config(fg='#EA580C')  # 橙色
                self.update_waste_icon(self.product_waste_icon_label, 'compost')
            elif waste_type == 'other':
                self.product_waste_status_label.config(fg='#DC2626')  # 红色
                self.update_waste_icon(self.product_waste_icon_label, 'landfill')
            else:
                self.product_waste_status_label.config(fg='#6B7280')  # 灰色
                self.product_waste_icon_label.config(image="", text="❓")
            
            # 更新产品分类信息
            self.product_waste_info_label.config(text=f"Classification: {display_text}")
            
        except Exception as e:
            print(f"更新产品垃圾分类显示错误: {e}")
    
    def start_voice_recognition(self):
        """开始语音识别"""
        try:
            if self.is_listening:
                return  # 如果正在录音，忽略重复点击
            
            # 检查麦克风是否可用
            if self.microphone is None:
                self.add_chat_message("System", "Microphone not available. Please check microphone permissions.")
                return
            
            self.is_listening = True
            
            # 更新按钮状态
            self.voice_button.config(text="⏹️", bg='#dc3545', state='disabled')
            self.add_chat_message("System", "Recording... Please speak now.")
            
            # 在后台线程中进行语音识别
            threading.Thread(target=self.voice_recognition_worker, daemon=True).start()
            
        except Exception as e:
            print(f"开始语音识别错误: {e}")
            self.add_chat_message("System", f"Failed to start voice recognition: {str(e)}")
            self.reset_voice_button()
    
    def reset_voice_button(self):
        """重置语音按钮状态"""
        try:
            self.is_listening = False
            self.voice_button.config(text="🎤", bg='#ff6b6b', state='normal')
        except Exception as e:
            print(f"重置语音按钮错误: {e}")
    
    def check_internet_connection(self):
        """检查网络连接"""
        try:
            # 尝试连接Google DNS服务器
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except OSError:
            return False
    
    def check_google_speech_service(self):
        """检查Google语音识别服务连接"""
        try:
            # 尝试连接Google语音识别服务
            socket.create_connection(("speech.googleapis.com", 443), timeout=5)
            return True
        except OSError:
            return False
    
    def voice_recognition_worker(self):
        """语音识别工作线程"""
        try:
            # 检查麦克风是否可用
            if self.microphone is None:
                self.root.after(0, self.add_chat_message, "System", "Microphone not available.")
                return
            
            # 检查网络连接
            has_internet = self.check_internet_connection()
            google_available = self.check_google_speech_service()
            
            if not has_internet:
                self.root.after(0, self.add_chat_message, "System", "No internet connection. Using local recognition only.")
            elif not google_available:
                self.root.after(0, self.add_chat_message, "System", "Google speech service unavailable. Using local recognition.")
            
            print("开始调整麦克风环境噪音...")
            # 创建新的麦克风实例避免上下文管理器冲突
            work_microphone = sr.Microphone()
            
            # 调整麦克风环境噪音
            with work_microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            print("环境噪音调整完成")
            
            print("开始监听语音输入...")
            # 监听语音输入
            with work_microphone as source:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
            print("语音输入监听完成")
            
            # 识别语音 - 尝试多种识别引擎
            text = None
            
            # 首先尝试Google在线识别
            if google_available:
                try:
                    text = self.recognizer.recognize_google(audio, language='en-US')
                    print(f"Google recognition result: {text}")
                except sr.RequestError as e:
                    print(f"Google recognition failed: {e}")
                    # 如果Google失败，尝试Sphinx离线识别
                    try:
                        text = self.recognizer.recognize_sphinx(audio)
                        print(f"Sphinx recognition result: {text}")
                    except sr.UnknownValueError:
                        print("Sphinx could not understand audio")
                    except Exception as e:
                        print(f"Sphinx recognition error: {e}")
                except sr.UnknownValueError:
                    print("Google could not understand audio")
            else:
                # 如果Google不可用，直接尝试Sphinx
                try:
                    text = self.recognizer.recognize_sphinx(audio)
                    print(f"Sphinx recognition result: {text}")
                except sr.UnknownValueError:
                    print("Sphinx could not understand audio")
                except Exception as e:
                    print(f"Sphinx recognition error: {e}")
            
            # 如果识别成功，处理结果
            if text:
                # 显示使用的识别引擎
                if google_available and "Google" in str(text):
                    engine_info = " (Google Online)"
                else:
                    engine_info = " (Sphinx Offline)"
                
                self.root.after(0, self.process_voice_input, text)
                self.root.after(0, self.add_chat_message, "System", f"Recognition successful{engine_info}")
            else:
                self.root.after(0, self.add_chat_message, "System", "Voice recognition failed. Please type your message manually in the input box.")
            
        except sr.WaitTimeoutError:
            self.root.after(0, self.add_chat_message, "System", "No speech detected. Please try again.")
        except Exception as e:
            print(f"语音识别工作线程错误: {e}")
            self.root.after(0, self.add_chat_message, "System", f"Voice recognition error: {str(e)}")
        finally:
            # 重置按钮状态
            self.root.after(0, self.reset_voice_button)
    
    def process_voice_input(self, text):
        """处理语音输入"""
        try:
            # 将识别的文本填入输入框，但不自动发送
            self.chat_input.delete(0, tk.END)
            self.chat_input.insert(0, text)
            
            # 显示识别结果，让用户确认
            self.add_chat_message("System", f"Recognized: '{text}'. Please review and click Send if correct.")
            
        except Exception as e:
            print(f"处理语音输入错误: {e}")
            self.add_chat_message("System", f"Failed to process voice input: {str(e)}")
    
    
    def test_microphone(self):
        """测试麦克风功能"""
        try:
            if self.microphone is None:
                self.add_chat_message("System", "Microphone not initialized. Please restart the program.")
                return
            
            self.add_chat_message("System", "Testing microphone... Please speak for 3 seconds.")
            
            # 在后台线程中测试麦克风
            threading.Thread(target=self.test_microphone_worker, daemon=True).start()
            
        except Exception as e:
            print(f"测试麦克风错误: {e}")
            self.add_chat_message("System", f"Microphone test failed: {str(e)}")
    
    def test_microphone_worker(self):
        """测试麦克风工作线程"""
        try:
            print("开始测试麦克风...")
            
            # 创建新的麦克风实例避免上下文管理器冲突
            test_microphone = sr.Microphone()
            
            # 调整环境噪音
            with test_microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            
            # 简单录音测试
            with test_microphone as source:
                audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=3)
            
            # 尝试识别
            text = None
            
            # 首先尝试Google
            try:
                text = self.recognizer.recognize_google(audio, language='en-US')
                self.root.after(0, self.add_chat_message, "System", f"Google test successful! Recognized: '{text}'")
            except sr.RequestError as e:
                self.root.after(0, self.add_chat_message, "System", f"Network error: {str(e)}")
                # 如果Google失败，尝试Sphinx
                try:
                    text = self.recognizer.recognize_sphinx(audio)
                    self.root.after(0, self.add_chat_message, "System", f"Sphinx test successful! Recognized: '{text}'")
                except sr.UnknownValueError:
                    self.root.after(0, self.add_chat_message, "System", "Could not understand audio, but microphone works.")
                except Exception as e:
                    self.root.after(0, self.add_chat_message, "System", f"Sphinx error: {str(e)}")
            except sr.UnknownValueError:
                self.root.after(0, self.add_chat_message, "System", "Could not understand audio, but microphone works.")
            
        except sr.WaitTimeoutError:
            self.root.after(0, self.add_chat_message, "System", "No audio detected. Microphone may not be working.")
        except Exception as e:
            print(f"麦克风测试错误: {e}")
            self.root.after(0, self.add_chat_message, "System", f"Microphone test error: {str(e)}")
    
    def update_camera_display(self, frame):
        """Update camera display"""
        try:
            # 调整图像大小以适应显示区域 (减小20%)
            height, width = frame.shape[:2]
            max_width = 480  # 从600减小到480 (减小20%)
            max_height = 450
            
            if width > max_width or height > max_height:
                scale = min(max_width/width, max_height/height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                frame = cv2.resize(frame, (new_width, new_height))
            
            # 转换颜色格式（BGR -> RGB）
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # 转换为PIL图像
            image = Image.fromarray(frame_rgb)
            photo = ImageTk.PhotoImage(image)
            
            # 在主线程中更新显示
            self.root.after(0, self.update_camera_label, photo)
        except Exception as e:
            print(f"更新摄像头显示错误: {e}")
    
    def update_camera_label(self, photo):
        """Update camera label (called in main thread)"""
        try:
            self.camera_label.config(image=photo)
            self.camera_label.image = photo  # 保持引用
        except Exception as e:
            print(f"更新摄像头标签错误: {e}")
    
    def clear_results(self):
        """Clear recognition results"""
        try:
            self.detected_barcodes.clear()
            self.selected_barcodes.clear()
            self.recognition_text.delete(1.0, tk.END)
            
            # 清空图形化产品信息显示
            self.clear_product_info_display()
            
            # 清空下拉框
            self.code_combobox['values'] = []
            self.selected_code_var.set('')
            
            # 清空上一个GS1编码
            self.last_gs1_code = None
            
            # 清空已询问的GS1代码集合，允许重新询问
            self.asked_gs1_codes.clear()
            
            # 清空聊天记录
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.delete(1.0, tk.END)
            self.chat_display.config(state=tk.DISABLED)
            
            # 清空所有checkbox（如果还有的话）
            for barcode_data, checkbox_info in self.barcode_checkboxes.items():
                checkbox_info['frame'].destroy()
            self.barcode_checkboxes.clear()
            
            self.status_label.config(text="Status: Results cleared")
        except Exception as e:
            print(f"清空结果错误: {e}")
    
    
    def restart_camera(self):
        """Restart camera"""
        try:
            self.is_running = False
            if self.cap:
                self.cap.release()
            time.sleep(0.5)
            self.start_camera()
        except Exception as e:
            print(f"重启摄像头错误: {e}")
    
    def close_program(self):
        """Close program"""
        try:
            self.is_running = False
            if self.cap:
                self.cap.release()
            if self.conn:
                self.conn.close()
            cv2.destroyAllWindows()
            self.root.quit()
            self.root.destroy()
        except Exception as e:
            print(f"关闭程序错误: {e}")
    
    def run(self):
        """Run program"""
        try:
            self.root.protocol("WM_DELETE_WINDOW", self.close_program)
            self.root.mainloop()
        except KeyboardInterrupt:
            self.close_program()

if __name__ == "__main__":
    app = BarcodeScannerStable()
    app.run()
