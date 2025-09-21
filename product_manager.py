#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Product Management System
New product creation tool based on barcode scanner
"""

import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import numpy as np
from pyzbar import pyzbar
from PIL import Image, ImageTk
import threading
import time
import os
import sqlite3
from datetime import datetime
import requests
import base64
import json
import sys
import argparse


class ProductManager:
    def __init__(self, prefill_gs1_code=None):
        self.root = tk.Tk()
        self.root.title("Product Management System")
        self.root.geometry("800x600")
        self.root.configure(bg='#f0f0f0')
        
        # Store prefill GS1 code
        self.prefill_gs1_code = prefill_gs1_code
        
        # Database initialization
        self.init_database()
        
        # Create main interface
        self.create_main_interface()
        
    def init_database(self):
        """Initialize database"""
        try:
            self.conn = sqlite3.connect('products.db')
            cursor = self.conn.cursor()
            
            # Create products table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    barcode TEXT UNIQUE,
                    product_name TEXT,
                    image_path TEXT,
                    packaging_waste_type TEXT,
                    product_waste_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Check if new columns need to be added (compatibility with old database)
            cursor.execute("PRAGMA table_info(products)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'packaging_waste_type' not in columns:
                cursor.execute('ALTER TABLE products ADD COLUMN packaging_waste_type TEXT')
                print("Added packaging waste classification column")
            
            if 'product_waste_type' not in columns:
                cursor.execute('ALTER TABLE products ADD COLUMN product_waste_type TEXT')
                print("Added product waste classification column")
            
            if 'packaging_material' not in columns:
                cursor.execute('ALTER TABLE products ADD COLUMN packaging_material TEXT')
                print("Added packaging material column")
            
            if 'plastic_type' not in columns:
                cursor.execute('ALTER TABLE products ADD COLUMN plastic_type TEXT')
                print("Added plastic type column")
            
            self.conn.commit()
            print("Database initialization successful")
            
        except Exception as e:
            print(f"Database initialization failed: {e}")
            messagebox.showerror("Error", f"Database initialization failed: {e}")
    
    def create_main_interface(self):
        """Create main interface"""
        # Title
        title_label = tk.Label(self.root, text="Product Management System", 
                              font=('Arial', 20, 'bold'), 
                              bg='#f0f0f0', fg='#333333')
        title_label.pack(pady=20)
        
        # Main button area
        button_frame = tk.Frame(self.root, bg='#f0f0f0')
        button_frame.pack(expand=True)
        
        # Create new product button
        create_product_btn = tk.Button(button_frame, 
                                      text="Create New Product", 
                                      font=('Arial', 16, 'bold'),
                                      bg='#4CAF50', fg='white',
                                      relief=tk.RAISED, bd=3,
                                      padx=30, pady=15,
                                      command=self.open_create_product_window)
        create_product_btn.pack(pady=20)
        
        # View products list button
        view_products_btn = tk.Button(button_frame, 
                                     text="View Products List", 
                                     font=('Arial', 16, 'bold'),
                                     bg='#2196F3', fg='white',
                                     relief=tk.RAISED, bd=3,
                                     padx=30, pady=15,
                                     command=self.view_products)
        view_products_btn.pack(pady=10)
        
        # Status bar
        self.status_label = tk.Label(self.root, text="Ready", 
                                    font=('Arial', 10), 
                                    bg='#f0f0f0', fg='#666666')
        self.status_label.pack(side=tk.BOTTOM, pady=10)
    
    def open_create_product_window(self):
        """Open create new product window"""
        try:
            # Create new product window
            product_window = CreateProductWindow(self.root, self.conn, self.prefill_gs1_code)
            product_window.run()
        except Exception as e:
            print(f"Failed to open create product window: {e}")
            messagebox.showerror("Error", f"Failed to open create product window: {e}")
    
    def view_products(self):
        """View products list"""
        try:
            # Create products list window
            products_window = ProductsListWindow(self.root, self.conn)
            products_window.run()
        except Exception as e:
            print(f"Failed to open products list: {e}")
            messagebox.showerror("Error", f"Failed to open products list: {e}")
    
    def run(self):
        """Run program"""
        try:
            self.root.protocol("WM_DELETE_WINDOW", self.close_program)
            self.root.mainloop()
        except KeyboardInterrupt:
            self.close_program()
    
    def close_program(self):
        """Close program"""
        try:
            if hasattr(self, 'conn'):
                self.conn.close()
            self.root.quit()
            self.root.destroy()
        except Exception as e:
            print(f"Close program error: {e}")


class CreateProductWindow:
    def __init__(self, parent, conn, prefill_gs1_code=None):
        self.parent = parent
        self.conn = conn
        self.prefill_gs1_code = prefill_gs1_code
        self.window = tk.Toplevel(parent)
        self.window.title("Create New Product")
        
        # Get screen dimensions
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        
        # Set window size to fit screen (leave some margin)
        window_width = int(screen_width * 0.95)
        window_height = int(screen_height * 0.95)
        
        # Center the window
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.window.configure(bg='#f0f0f0')
        
        # Store dimensions for layout calculations
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.window_width = window_width
        self.window_height = window_height
        
        # Product data
        self.barcode = ""
        self.product_name = ""
        self.image_path = ""
        self.captured_image = None
        
        # Waste classification selection
        self.packaging_waste_type = tk.StringVar(value="")
        self.product_waste_type = tk.StringVar(value="")
        
        # Packaging material and plastic type
        self.packaging_material = tk.StringVar(value="")
        self.plastic_type = tk.StringVar(value="")
        
        # Camera related
        self.cap = None
        self.is_running = False
        self.current_frame = None
        
        # Baidu OCR configuration
        self.baidu_ocr_config = {
            'api_key': 'eJAk0i6aKQbGabIk9UPrcxcR',
            'secret_key': 'PTYD5yhAJIsHeWL6SRswQkHRT37kk2AG',
            'access_token': ''
        }
        
        # Automatically get access token
        try:
            self.get_baidu_access_token()
        except Exception as e:
            print(f"Failed to get Baidu OCR access token: {e}")
        
        # Create interface
        self.create_interface()
        
        # Configure layout proportions after window is created
        self.configure_layout_proportions()
        
        # Start camera
        self.start_camera()
    
    def create_interface(self):
        """Create interface"""
        # Title
        title_label = tk.Label(self.window, text="Create New Product", 
                              font=('Arial', 18, 'bold'), 
                              bg='#f0f0f0', fg='#333333')
        title_label.pack(pady=10)
        
        # Main content area
        main_frame = tk.Frame(self.window, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Left camera area
        left_frame = tk.Frame(main_frame, bg='white', relief=tk.RAISED, bd=2)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Camera title
        camera_title = tk.Label(left_frame, text="Camera View", 
                               font=('Arial', 14, 'bold'), bg='white')
        camera_title.pack(pady=10)
        
        # Camera display
        self.camera_label = tk.Label(left_frame, bg='black')
        self.camera_label.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Capture button
        capture_btn = tk.Button(left_frame, text="Capture Photo", 
                               font=('Arial', 12, 'bold'),
                               bg='#FF9800', fg='white',
                               relief=tk.RAISED, bd=2,
                               padx=20, pady=5,
                               command=self.capture_photo)
        capture_btn.pack(pady=10)
        
        # Right information area
        right_frame = tk.Frame(main_frame, bg='white', relief=tk.RAISED, bd=2)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        # Create canvas and scrollbar for right side
        canvas = tk.Canvas(right_frame, bg='white', relief=tk.RAISED, bd=2)
        scrollbar = ttk.Scrollbar(right_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='white')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Information title
        info_title = tk.Label(scrollable_frame, text="Product Information", 
                             font=('Arial', 14, 'bold'), bg='white')
        info_title.pack(pady=10)
        
        # GS1 code area
        barcode_frame = tk.Frame(scrollable_frame, bg='white')
        barcode_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(barcode_frame, text="GS1 Code:", 
                font=('Arial', 12, 'bold'), bg='white').pack(anchor='w')
        
        # 如果有预填的GS1代码，显示它；否则显示"Not Recognized"
        initial_barcode_text = self.prefill_gs1_code if self.prefill_gs1_code else "Not Recognized"
        initial_barcode_color = '#333333' if self.prefill_gs1_code else '#666666'
        
        self.barcode_label = tk.Label(barcode_frame, text=initial_barcode_text, 
                                     font=('Arial', 11), bg='white', 
                                     fg=initial_barcode_color, relief=tk.SUNKEN, bd=1)
        self.barcode_label.pack(fill=tk.X, pady=5)
        
        # 如果有预填的GS1代码，设置barcode变量
        if self.prefill_gs1_code:
            self.barcode = self.prefill_gs1_code
        
        # Product name area
        name_frame = tk.Frame(scrollable_frame, bg='white')
        name_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(name_frame, text="Product Name:", 
                font=('Arial', 12, 'bold'), bg='white').pack(anchor='w')
        
        self.name_entry = tk.Entry(name_frame, font=('Arial', 11), 
                                  relief=tk.SUNKEN, bd=1)
        self.name_entry.pack(fill=tk.X, pady=5)
        
        # OCR recognition button
        ocr_btn = tk.Button(name_frame, text="OCR Recognize Product Name", 
                           font=('Arial', 10),
                           bg='#9C27B0', fg='white',
                           relief=tk.RAISED, bd=1,
                           padx=10, pady=3,
                           command=self.ocr_product_name)
        ocr_btn.pack(pady=5)
        
        # Product photo area
        photo_frame = tk.Frame(scrollable_frame, bg='white')
        photo_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        tk.Label(photo_frame, text="Product Photo:", 
                font=('Arial', 12, 'bold'), bg='white').pack(anchor='w')
        
        # Photo display area
        self.photo_display_frame = tk.Frame(photo_frame, bg='#f8f8f8', relief=tk.SUNKEN, bd=1)
        self.photo_display_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.photo_label = tk.Label(self.photo_display_frame, text="No Photo Taken", 
                                   font=('Arial', 11), bg='#f8f8f8', 
                                   fg='#666666')
        self.photo_label.pack(expand=True)
        
        # Waste classification selection area
        waste_selection_frame = tk.Frame(scrollable_frame, bg='white')
        waste_selection_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(waste_selection_frame, text="Waste Classification:", 
                font=('Arial', 12, 'bold'), bg='white').pack(anchor='w')
        
        # Waste classification selection container
        waste_buttons_frame = tk.Frame(waste_selection_frame, bg='white')
        waste_buttons_frame.pack(fill=tk.X, pady=5)
        
        # Packaging waste classification
        packaging_frame = tk.Frame(waste_buttons_frame, bg='white')
        packaging_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        tk.Label(packaging_frame, text="Packaging", 
                font=('Arial', 10, 'bold'), bg='white').pack(anchor='w')
        
        # 包装垃圾分类按钮网格
        packaging_grid = tk.Frame(packaging_frame, bg='white')
        packaging_grid.pack(fill=tk.X, pady=2)
        
        # 第一行按钮
        row1_frame = tk.Frame(packaging_grid, bg='white')
        row1_frame.pack(fill=tk.X, pady=1)
        
        self.packaging_recyclable_btn = tk.Button(row1_frame, text="Recyclable", 
                                                 font=('Arial', 9), width=8, height=2,
                                                 bg='#E3F2FD', fg='#1976D2',
                                                 relief=tk.RAISED, bd=1,
                                                 command=lambda: self.select_waste_type('packaging', 'Recyclable'))
        self.packaging_recyclable_btn.pack(side=tk.LEFT, padx=1)
        
        self.packaging_harmful_btn = tk.Button(row1_frame, text="Hazardous", 
                                              font=('Arial', 9), width=8, height=2,
                                              bg='#E3F2FD', fg='#1976D2',
                                              relief=tk.RAISED, bd=1,
                                              command=lambda: self.select_waste_type('packaging', 'Hazardous'))
        self.packaging_harmful_btn.pack(side=tk.LEFT, padx=1)
        
        # 第二行按钮
        row2_frame = tk.Frame(packaging_grid, bg='white')
        row2_frame.pack(fill=tk.X, pady=1)
        
        self.packaging_wet_btn = tk.Button(row2_frame, text="Wet Waste", 
                                          font=('Arial', 9), width=8, height=2,
                                          bg='#E3F2FD', fg='#1976D2',
                                          relief=tk.RAISED, bd=1,
                                          command=lambda: self.select_waste_type('packaging', 'Wet Waste'))
        self.packaging_wet_btn.pack(side=tk.LEFT, padx=1)
        
        self.packaging_other_btn = tk.Button(row2_frame, text="Other Waste", 
                                            font=('Arial', 9), width=8, height=2,
                                            bg='#E3F2FD', fg='#1976D2',
                                            relief=tk.RAISED, bd=1,
                                            command=lambda: self.select_waste_type('packaging', 'Other Waste'))
        self.packaging_other_btn.pack(side=tk.LEFT, padx=1)
        
        # Product itself waste classification
        product_frame = tk.Frame(waste_buttons_frame, bg='white')
        product_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        tk.Label(product_frame, text="Product Itself", 
                font=('Arial', 10, 'bold'), bg='white').pack(anchor='w')
        
        # 产品本身垃圾分类按钮网格
        product_grid = tk.Frame(product_frame, bg='white')
        product_grid.pack(fill=tk.X, pady=2)
        
        # 第一行按钮
        row1_frame = tk.Frame(product_grid, bg='white')
        row1_frame.pack(fill=tk.X, pady=1)
        
        self.product_recyclable_btn = tk.Button(row1_frame, text="Recyclable", 
                                               font=('Arial', 9), width=8, height=2,
                                               bg='#E8F5E8', fg='#2E7D32',
                                               relief=tk.RAISED, bd=1,
                                               command=lambda: self.select_waste_type('product', 'Recyclable'))
        self.product_recyclable_btn.pack(side=tk.LEFT, padx=1)
        
        self.product_harmful_btn = tk.Button(row1_frame, text="Hazardous", 
                                            font=('Arial', 9), width=8, height=2,
                                            bg='#E8F5E8', fg='#2E7D32',
                                            relief=tk.RAISED, bd=1,
                                            command=lambda: self.select_waste_type('product', 'Hazardous'))
        self.product_harmful_btn.pack(side=tk.LEFT, padx=1)
        
        # 第二行按钮
        row2_frame = tk.Frame(product_grid, bg='white')
        row2_frame.pack(fill=tk.X, pady=1)
        
        self.product_wet_btn = tk.Button(row2_frame, text="Wet Waste", 
                                        font=('Arial', 9), width=8, height=2,
                                        bg='#E8F5E8', fg='#2E7D32',
                                        relief=tk.RAISED, bd=1,
                                        command=lambda: self.select_waste_type('product', 'Wet Waste'))
        self.product_wet_btn.pack(side=tk.LEFT, padx=1)
        
        self.product_other_btn = tk.Button(row2_frame, text="Other Waste", 
                                          font=('Arial', 9), width=8, height=2,
                                          bg='#E8F5E8', fg='#2E7D32',
                                          relief=tk.RAISED, bd=1,
                                          command=lambda: self.select_waste_type('product', 'Other Waste'))
        self.product_other_btn.pack(side=tk.LEFT, padx=1)
        
        # Packaging material selection area (only shown when recyclable is selected)
        self.material_selection_frame = tk.Frame(waste_selection_frame, bg='white')
        # Initially hidden, shown after selecting recyclable
        
        # Packaging material selection container
        self.material_buttons_frame = tk.Frame(self.material_selection_frame, bg='white')
        self.material_buttons_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(self.material_buttons_frame, text="Packaging Material:", 
                font=('Arial', 10, 'bold'), bg='white').pack(anchor='w')
        
        # 材质选择按钮网格
        material_grid = tk.Frame(self.material_buttons_frame, bg='white')
        material_grid.pack(fill=tk.X, pady=2)
        
        # 第一行按钮
        material_row1_frame = tk.Frame(material_grid, bg='white')
        material_row1_frame.pack(fill=tk.X, pady=1)
        
        self.paper_btn = tk.Button(material_row1_frame, text="Paper", 
                                  font=('Arial', 9), width=8, height=2,
                                  bg='#FFF3E0', fg='#F57C00',
                                  relief=tk.RAISED, bd=1,
                                  command=lambda: self.select_material('Paper'))
        self.paper_btn.pack(side=tk.LEFT, padx=1)
        
        self.plastic_btn = tk.Button(material_row1_frame, text="Plastic", 
                                    font=('Arial', 9), width=8, height=2,
                                    bg='#FFF3E0', fg='#F57C00',
                                    relief=tk.RAISED, bd=1,
                                    command=lambda: self.select_material('Plastic'))
        self.plastic_btn.pack(side=tk.LEFT, padx=1)
        
        # 第二行按钮
        material_row2_frame = tk.Frame(material_grid, bg='white')
        material_row2_frame.pack(fill=tk.X, pady=1)
        
        self.metal_btn = tk.Button(material_row2_frame, text="Metal", 
                                  font=('Arial', 9), width=8, height=2,
                                  bg='#FFF3E0', fg='#F57C00',
                                  relief=tk.RAISED, bd=1,
                                  command=lambda: self.select_material('Metal'))
        self.metal_btn.pack(side=tk.LEFT, padx=1)
        
        self.glass_btn = tk.Button(material_row2_frame, text="Glass", 
                                  font=('Arial', 9), width=8, height=2,
                                  bg='#FFF3E0', fg='#F57C00',
                                  relief=tk.RAISED, bd=1,
                                  command=lambda: self.select_material('Glass'))
        self.glass_btn.pack(side=tk.LEFT, padx=1)
        
        # Plastic type input box (only shown when plastic is selected)
        self.plastic_type_frame = tk.Frame(self.material_selection_frame, bg='white')
        
        tk.Label(self.plastic_type_frame, text="Plastic Type:", 
                font=('Arial', 10, 'bold'), bg='white').pack(anchor='w')
        
        self.plastic_type_entry = tk.Entry(self.plastic_type_frame, font=('Arial', 10), 
                                          relief=tk.SUNKEN, bd=1)
        self.plastic_type_entry.pack(fill=tk.X, pady=5)
        
        # Bottom button area
        button_frame = tk.Frame(self.window, bg='#f0f0f0')
        button_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Save button
        save_btn = tk.Button(button_frame, text="Save Product", 
                            font=('Arial', 12, 'bold'),
                            bg='#4CAF50', fg='white',
                            relief=tk.RAISED, bd=2,
                            padx=20, pady=5,
                            command=self.save_product)
        save_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Cancel button
        cancel_btn = tk.Button(button_frame, text="Cancel", 
                              font=('Arial', 12),
                              bg='#f44336', fg='white',
                              relief=tk.RAISED, bd=2,
                              padx=20, pady=5,
                              command=self.close_window)
        cancel_btn.pack(side=tk.RIGHT)
        
        # Status bar
        self.status_label = tk.Label(self.window, text="Ready", 
                                    font=('Arial', 10), 
                                    bg='#f0f0f0', fg='#666666')
        self.status_label.pack(side=tk.BOTTOM, pady=5)
    
    def configure_layout_proportions(self):
        """Configure layout proportions - camera view takes 40% of window height"""
        try:
            # Wait for window to be fully created
            self.window.update_idletasks()
            
            # Get window dimensions
            window_height = self.window.winfo_height()
            
            # Calculate 40% of window height
            camera_height = int(window_height * 0.4)
            
            print(f"Layout configured: Camera view set to 40% of window height ({camera_height}px)")
            print("Grid weights: Camera=4 (40%), Photo=6 (60%)")
            
        except Exception as e:
            print(f"Layout configuration error: {e}")
    
    def start_camera(self):
        """Start camera"""
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                self.status_label.config(text="Status: Unable to open camera")
                return
            
            # 设置摄像头参数
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            self.is_running = True
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
                    time.sleep(0.1)
                    continue
                
                # 翻转图像（镜像效果）
                frame = cv2.flip(frame, 1)
                
                # 识别条形码
                frame_with_barcodes = self.detect_barcodes(frame)
                
                # 更新显示
                self.update_camera_display(frame_with_barcodes)
                
                time.sleep(0.05)
                
            except Exception as e:
                print(f"摄像头循环错误: {e}")
                time.sleep(0.1)
    
    def detect_barcodes(self, frame):
        """Detect barcodes"""
        try:
            # 转换为灰度图像
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # 图像预处理
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(gray)
            
            # 尝试多种图像处理方式
            images_to_try = [
                gray,
                enhanced,
                cv2.GaussianBlur(enhanced, (3, 3), 0),
                cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
            ]
            
            all_barcodes = []
            for img in images_to_try:
                try:
                    barcodes = pyzbar.decode(img)
                    all_barcodes.extend(barcodes)
                except Exception as e:
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
                    continue
            
            # 在图像上标注检测到的条形码
            for barcode in unique_barcodes:
                try:
                    (x, y, w, h) = barcode.rect
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    
                    barcode_data = barcode.data.decode('utf-8')
                    barcode_type = barcode.type
                    
                    text = f"{barcode_type}: {barcode_data}"
                    cv2.putText(frame, text, (x, y - 10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    
                    # 更新条形码显示
                    if barcode_data != self.barcode:
                        self.barcode = barcode_data
                        self.barcode_label.config(text=barcode_data, fg='#333333')
                        self.status_label.config(text=f"Status: Recognized barcode - {barcode_data}")
                        
                except Exception as e:
                    continue
            
        except Exception as e:
            print(f"条形码检测错误: {e}")
        
        return frame
    
    def update_camera_display(self, frame):
        """Update camera display"""
        try:
            # 检查窗口是否还存在
            if not self.window.winfo_exists():
                return
            
            # 调整图像大小
            height, width = frame.shape[:2]
            max_width = 500
            max_height = 400
            
            if width > max_width or height > max_height:
                scale = min(max_width/width, max_height/height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                frame = cv2.resize(frame, (new_width, new_height))
            
            # 转换颜色格式
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # 转换为PIL图像
            image = Image.fromarray(frame_rgb)
            photo = ImageTk.PhotoImage(image)
            
            # 在主线程中更新显示
            self.window.after(0, self.update_camera_label, photo)
            
            # 保存当前帧用于拍照
            self.current_frame = frame.copy()
            
        except Exception as e:
            print(f"更新摄像头显示错误: {e}")
    
    def update_camera_label(self, photo):
        """Update camera label (called in main thread)"""
        try:
            if self.window.winfo_exists() and hasattr(self, 'camera_label'):
                self.camera_label.config(image=photo)
                self.camera_label.image = photo  # 保持引用
        except Exception as e:
            print(f"更新摄像头标签错误: {e}")
    
    def capture_photo(self):
        """Capture photo"""
        try:
            if self.current_frame is None:
                messagebox.showwarning("Warning", "Please start camera first")
                return
            
            # 保存照片
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"product_photo_{timestamp}.jpg"
            
            # 创建photos目录
            if not os.path.exists("photos"):
                os.makedirs("photos")
            
            self.image_path = os.path.join("photos", filename)
            cv2.imwrite(self.image_path, self.current_frame)
            
            # 保存当前帧用于显示
            self.captured_image = self.current_frame.copy()
            
            # 显示照片
            self.display_captured_photo()
            
            # Update status
            self.status_label.config(text=f"Status: Photo taken, recognizing text...")
            
            # 直接开始OCR识别
            self.ocr_product_name()
            
        except Exception as e:
            print(f"拍照错误: {e}")
            messagebox.showerror("Error", f"Photo capture failed: {e}")
    
    def display_captured_photo(self):
        """Display captured photo"""
        try:
            if self.captured_image is None:
                return
            
            # 调整图像大小以适应显示区域
            height, width = self.captured_image.shape[:2]
            max_width = 300
            max_height = 200
            
            if width > max_width or height > max_height:
                scale = min(max_width/width, max_height/height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                display_image = cv2.resize(self.captured_image, (new_width, new_height))
            else:
                display_image = self.captured_image
            
            # 左右翻转照片
            flipped_image = cv2.flip(display_image, 1)  # 1表示水平翻转
            
            # 转换颜色格式
            display_image_rgb = cv2.cvtColor(flipped_image, cv2.COLOR_BGR2RGB)
            
            # 转换为PIL图像
            image = Image.fromarray(display_image_rgb)
            photo = ImageTk.PhotoImage(image)
            
            # 更新显示
            self.photo_label.config(image=photo, text="")
            self.photo_label.image = photo  # 保持引用
            
            print("产品照片已进行左右翻转显示")
            
        except Exception as e:
            print(f"显示照片错误: {e}")
            self.photo_label.config(text="Photo display failed", fg='#ff0000')
    
    def get_baidu_access_token(self):
        """Get Baidu OCR access token"""
        try:
            # 如果token还有效，直接返回
            if (self.baidu_ocr_config.get('access_token') and 
                self.baidu_ocr_config.get('token_expire_time', 0) > time.time()):
                return self.baidu_ocr_config['access_token']
            
            url = "https://aip.baidubce.com/oauth/2.0/token"
            params = {
                'grant_type': 'client_credentials',
                'client_id': self.baidu_ocr_config['api_key'],
                'client_secret': self.baidu_ocr_config['secret_key']
            }
            
            response = requests.post(url, params=params, timeout=10)
            result = response.json()
            
            if 'access_token' in result:
                self.baidu_ocr_config['access_token'] = result['access_token']
                # 设置过期时间（提前5分钟刷新）
                self.baidu_ocr_config['token_expire_time'] = time.time() + result.get('expires_in', 3600) - 300
                print("Baidu OCR access token obtained successfully")
                return self.baidu_ocr_config['access_token']
            else:
                raise Exception(f"获取访问令牌失败: {result}")
                
        except Exception as e:
            print(f"Error getting Baidu OCR access token: {e}")
            raise e
    
    def ocr_product_name(self):
        """OCR recognize product name"""
        try:
            if not self.image_path or not os.path.exists(self.image_path):
                messagebox.showwarning("Warning", "Please take a photo first")
                return
            
            # 获取访问令牌
            try:
                access_token = self.get_baidu_access_token()
            except Exception as e:
                messagebox.showerror("Error", f"Baidu OCR service unavailable: {e}")
                return
            
            # 读取图片
            img = cv2.imread(self.image_path)
            if img is None:
                messagebox.showerror("Error", "Unable to read image file")
                return
            
            # 预处理图片以提高识别效果
            processed_img = self.preprocess_image_for_ocr_cv2(img)
            
            # 使用百度OCR进行文字识别
            recognized_text = self.recognize_text_with_baidu(processed_img, access_token)
            
            if recognized_text and recognized_text.strip():
                # 更新产品名称输入框
                self.name_entry.delete(0, tk.END)
                self.name_entry.insert(0, recognized_text.strip())
                self.status_label.config(text="Status: OCR recognition completed")
                messagebox.showinfo("Success", f"Recognized text: {recognized_text.strip()}")
            else:
                self.status_label.config(text="Status: No valid text recognized")
                messagebox.showinfo("Info", "No valid text recognized")
                
        except Exception as e:
            print(f"OCR识别错误: {e}")
            messagebox.showerror("Error", f"OCR recognition failed: {e}")
    
    def preprocess_image_for_ocr_cv2(self, img):
        """Preprocess image to improve OCR recognition"""
        try:
            # 左右翻转图片
            flipped_img = cv2.flip(img, 1)  # 1表示水平翻转
            
            # 转换为灰度图
            if len(flipped_img.shape) == 3:
                gray = cv2.cvtColor(flipped_img, cv2.COLOR_BGR2GRAY)
            else:
                gray = flipped_img
            
            # 增强对比度
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(gray)
            
            # 去噪
            denoised = cv2.medianBlur(enhanced, 3)
            
            # 二值化
            _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            print("图片已进行左右翻转处理")
            return binary
            
        except Exception as e:
            print(f"图片预处理错误: {e}")
            return img  # 如果预处理失败，返回原图
    
    def recognize_text_with_baidu(self, img, access_token):
        """Use Baidu OCR to recognize text"""
        try:
            # 将图像转换为base64
            base64_image = self.image_to_base64(img)
            
            # 构建请求URL - 使用accurate_basic接口提高精度
            url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic?access_token={access_token}"
            
            # 构建请求参数
            payload = {
                'image': base64_image,
                'detect_direction': 'false',
                'paragraph': 'true',
                'probability': 'false',
                'multidirectional_recognize': 'false'
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json'
            }
            
            print(f"发送OCR请求，图片大小: {len(base64_image)} chars")
            
            # 发送请求
            response = requests.post(url, headers=headers, data=payload, timeout=30)
            response.raise_for_status()
            
            # 解析响应
            result = response.json()
            
            print(f"OCR识别响应: {result}")
            
            if 'error_code' in result:
                raise Exception(f"OCR识别失败: {result.get('error_msg', '未知错误')}")
            
            # 提取文字内容
            texts = []
            if 'words_result' in result:
                for item in result['words_result']:
                    if 'words' in item:
                        texts.append(item['words'])
            
            # 合并所有文字
            recognized_text = " ".join(texts)
            
            return recognized_text
            
        except Exception as e:
            print(f"百度OCR识别错误: {e}")
            raise e
    
    def image_to_base64(self, image):
        """Convert OpenCV image to base64 encoding"""
        try:
            # 将BGR转换为RGB
            if len(image.shape) == 3:
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            else:
                image_rgb = image
            
            # 编码为JPEG格式
            success, encoded_image = cv2.imencode('.jpg', image_rgb)
            if not success:
                raise Exception("图像编码失败")
            
            # 转换为base64
            base64_image = base64.b64encode(encoded_image).decode('utf-8')
            return base64_image
            
        except Exception as e:
            print(f"图像编码错误: {e}")
            raise e
    
    def select_waste_type(self, category, waste_type):
        """Select waste classification"""
        try:
            if category == 'packaging':
                # 重置包装按钮状态
                self.reset_packaging_buttons()
                # 设置选中的包装类型
                self.packaging_waste_type.set(waste_type)
                # 高亮选中的按钮
                self.highlight_packaging_button(waste_type)
                
                # If recyclable is selected, show material selection area
                if waste_type == 'Recyclable':
                    self.show_material_selection()
                else:
                    self.hide_material_selection()
                    
            elif category == 'product':
                # 重置产品按钮状态
                self.reset_product_buttons()
                # 设置选中的产品类型
                self.product_waste_type.set(waste_type)
                # 高亮选中的按钮
                self.highlight_product_button(waste_type)
            
            print(f"选择了{category}: {waste_type}")
            
        except Exception as e:
            print(f"选择垃圾分类错误: {e}")
    
    def reset_packaging_buttons(self):
        """Reset packaging button states"""
        buttons = [
            self.packaging_recyclable_btn,
            self.packaging_harmful_btn,
            self.packaging_wet_btn,
            self.packaging_other_btn
        ]
        for btn in buttons:
            btn.config(bg='#E3F2FD', fg='#1976D2', relief=tk.RAISED)
    
    def reset_product_buttons(self):
        """Reset product button states"""
        buttons = [
            self.product_recyclable_btn,
            self.product_harmful_btn,
            self.product_wet_btn,
            self.product_other_btn
        ]
        for btn in buttons:
            btn.config(bg='#E8F5E8', fg='#2E7D32', relief=tk.RAISED)
    
    def highlight_packaging_button(self, waste_type):
        """Highlight selected packaging button"""
        button_map = {
            'Recyclable': self.packaging_recyclable_btn,
            'Hazardous': self.packaging_harmful_btn,
            'Wet Waste': self.packaging_wet_btn,
            'Other Waste': self.packaging_other_btn
        }
        if waste_type in button_map:
            button_map[waste_type].config(bg='#1976D2', fg='white', relief=tk.SUNKEN)
    
    def highlight_product_button(self, waste_type):
        """Highlight selected product button"""
        button_map = {
            'Recyclable': self.product_recyclable_btn,
            'Hazardous': self.product_harmful_btn,
            'Wet Waste': self.product_wet_btn,
            'Other Waste': self.product_other_btn
        }
        if waste_type in button_map:
            button_map[waste_type].config(bg='#2E7D32', fg='white', relief=tk.SUNKEN)
    
    def show_material_selection(self):
        """Show material selection area"""
        try:
            self.material_selection_frame.pack(fill=tk.X, pady=10)
            print("显示材质选择区域")
        except Exception as e:
            print(f"显示材质选择区域错误: {e}")
    
    def hide_material_selection(self):
        """Hide material selection area"""
        try:
            self.material_selection_frame.pack_forget()
            # 重置材质选择
            self.reset_material_buttons()
            self.packaging_material.set("")
            self.hide_plastic_type_input()
            print("隐藏材质选择区域")
        except Exception as e:
            print(f"隐藏材质选择区域错误: {e}")
    
    def select_material(self, material):
        """Select packaging material"""
        try:
            # 重置材质按钮状态
            self.reset_material_buttons()
            # 设置选中的材质
            self.packaging_material.set(material)
            # 高亮选中的按钮
            self.highlight_material_button(material)
            
            # If plastic is selected, show plastic type input box
            if material == 'Plastic':
                self.show_plastic_type_input()
            else:
                self.hide_plastic_type_input()
                self.plastic_type.set("")
            
            print(f"选择了包装材质: {material}")
            
        except Exception as e:
            print(f"选择包装材质错误: {e}")
    
    def reset_material_buttons(self):
        """Reset material button states"""
        buttons = [
            self.paper_btn,
            self.plastic_btn,
            self.metal_btn,
            self.glass_btn
        ]
        for btn in buttons:
            btn.config(bg='#FFF3E0', fg='#F57C00', relief=tk.RAISED)
    
    def highlight_material_button(self, material):
        """Highlight selected material button"""
        button_map = {
            'Paper': self.paper_btn,
            'Plastic': self.plastic_btn,
            'Metal': self.metal_btn,
            'Glass': self.glass_btn
        }
        if material in button_map:
            button_map[material].config(bg='#F57C00', fg='white', relief=tk.SUNKEN)
    
    def show_plastic_type_input(self):
        """Show plastic type input box"""
        try:
            self.plastic_type_frame.pack(fill=tk.X, pady=5)
            print("显示塑料种类输入框")
        except Exception as e:
            print(f"显示塑料种类输入框错误: {e}")
    
    def hide_plastic_type_input(self):
        """Hide plastic type input box"""
        try:
            self.plastic_type_frame.pack_forget()
            self.plastic_type_entry.delete(0, tk.END)
            print("隐藏塑料种类输入框")
        except Exception as e:
            print(f"隐藏塑料种类输入框错误: {e}")
    
    def save_product(self):
        """Save product"""
        try:
            # 验证必填字段
            if not self.barcode:
                messagebox.showwarning("Warning", "Please recognize barcode first")
                return
            
            product_name = self.name_entry.get().strip()
            if not product_name:
                messagebox.showwarning("Warning", "Please enter product name")
                return
            
            # 获取垃圾分类信息
            packaging_waste_type = self.packaging_waste_type.get()
            product_waste_type = self.product_waste_type.get()
            
            # Get packaging material and plastic type information
            packaging_material = self.packaging_material.get()
            plastic_type = self.plastic_type_entry.get().strip() if packaging_material == 'Plastic' else ""
            
            # If packaging is not recyclable, clear material and plastic type
            if packaging_waste_type != 'Recyclable':
                packaging_material = ""
                plastic_type = ""
            
            # 保存到数据库
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO products (gs1_code, product_name, product_image, packaging_waste_type, product_waste_type, packaging_material, plastic_type)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (self.barcode, product_name, self.image_path, packaging_waste_type, product_waste_type, packaging_material, plastic_type))
            
            self.conn.commit()
            
            # Display save success message with waste classification information
            success_msg = "Product saved successfully!"
            if packaging_waste_type:
                success_msg += f"\nPackaging Classification: {packaging_waste_type}"
                if packaging_material:
                    success_msg += f"\nPackaging Material: {packaging_material}"
                    if plastic_type:
                        success_msg += f"\nPlastic Type: {plastic_type}"
            if product_waste_type:
                success_msg += f"\nProduct Classification: {product_waste_type}"
            
            messagebox.showinfo("Success", success_msg)
            self.close_window()
            
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "This barcode already exists")
        except Exception as e:
            print(f"保存产品错误: {e}")
            messagebox.showerror("Error", f"Failed to save product: {e}")
    
    def close_window(self):
        """Close window"""
        try:
            self.is_running = False
            if self.cap:
                self.cap.release()
            self.window.destroy()
        except Exception as e:
            print(f"Close window error: {e}")
    
    def run(self):
        """Run window"""
        self.window.protocol("WM_DELETE_WINDOW", self.close_window)
        self.window.mainloop()


class ProductsListWindow:
    def __init__(self, parent, conn):
        self.parent = parent
        self.conn = conn
        self.window = tk.Toplevel(parent)
        self.window.title("Products List")
        self.window.geometry("1000x500")
        self.window.configure(bg='#f0f0f0')
        
        # Edit related variables
        self.editing_item = None
        self.editing_column = None
        self.edit_widget = None
        
        self.create_interface()
        self.load_products()
    
    def create_interface(self):
        """Create interface"""
        # Title (flexible layout)
        title_label = tk.Label(self.window, text="Products List", 
                              font=('Arial', 14, 'bold'), 
                              bg='#f0f0f0', fg='#333333')
        title_label.pack(pady=(10, 5))
        
        # Products list
        self.tree = ttk.Treeview(self.window, columns=('gs1_code', 'name', 'packaging_waste', 'packaging_material', 'plastic_type', 'product_waste', 'created_at'), show='headings')
        self.tree.heading('gs1_code', text='Barcode')
        self.tree.heading('name', text='Product Name')
        self.tree.heading('packaging_waste', text='Packaging Classification')
        self.tree.heading('packaging_material', text='Packaging Material')
        self.tree.heading('plastic_type', text='Plastic Type')
        self.tree.heading('product_waste', text='Product Classification')
        self.tree.heading('created_at', text='Created At')
        
        # 设置列宽（灵活布局，根据内容自适应）
        self.tree.column('gs1_code', width=120, minwidth=100)
        self.tree.column('name', width=150, minwidth=120)
        self.tree.column('packaging_waste', width=90, minwidth=80)
        self.tree.column('packaging_material', width=90, minwidth=80)
        self.tree.column('plastic_type', width=100, minwidth=80)
        self.tree.column('product_waste', width=90, minwidth=80)
        self.tree.column('created_at', width=130, minwidth=100)
        
        # 绑定选择事件
        self.tree.bind('<<TreeviewSelect>>', self.on_item_select)
        self.tree.bind('<Double-1>', self.on_item_double_click)
        self.tree.bind('<Button-1>', self.on_item_click)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(self.window, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # 主列表区域（灵活布局，占据主要空间）
        list_frame = tk.Frame(self.window, bg='#f0f0f0')
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 5))
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 底部操作区域（灵活布局）
        bottom_frame = tk.Frame(self.window, bg='#f0f0f0')
        bottom_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # 操作按钮（水平排列，灵活设计）
        button_frame = tk.Frame(bottom_frame, bg='#f0f0f0')
        button_frame.pack(side=tk.LEFT, pady=8)
        
        self.edit_btn = tk.Button(button_frame, text="Edit Product", 
                                 font=('Arial', 10),
                                 bg='#2196F3', fg='white',
                                 relief=tk.RAISED, bd=1,
                                 padx=12, pady=6,
                                 command=self.edit_selected_product,
                                 state=tk.DISABLED)
        self.edit_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        self.delete_btn = tk.Button(button_frame, text="Delete Product", 
                                   font=('Arial', 10),
                                   bg='#f44336', fg='white',
                                   relief=tk.RAISED, bd=1,
                                   padx=12, pady=6,
                                   command=self.delete_selected_product,
                                   state=tk.DISABLED)
        self.delete_btn.pack(side=tk.LEFT, padx=(0, 15))
        
        # Status information
        self.status_label = tk.Label(bottom_frame, text="Please select product", 
                                    font=('Arial', 9), 
                                    bg='#f0f0f0', fg='#666666')
        self.status_label.pack(side=tk.RIGHT, pady=8)
        
        # Close button
        close_btn = tk.Button(bottom_frame, text="Close", 
                             font=('Arial', 10),
                             bg='#f44336', fg='white',
                             relief=tk.RAISED, bd=1,
                             padx=15, pady=6,
                             command=self.close_window)
        close_btn.pack(side=tk.RIGHT, padx=(8, 0))
    
    def load_products(self):
        """Load products list"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT gs1_code, product_name, packaging_waste_type, packaging_material, plastic_type, product_waste_type, created_at FROM products ORDER BY created_at DESC')
            products = cursor.fetchall()
            
            for product in products:
                # Handle empty values, display as "Unclassified" or empty string
                processed_product = list(product)
                if not processed_product[2]:  # packaging_waste_type
                    processed_product[2] = "Unclassified"
                if not processed_product[3]:  # packaging_material
                    processed_product[3] = ""
                if not processed_product[4]:  # plastic_type
                    processed_product[4] = ""
                if not processed_product[5]:  # product_waste_type
                    processed_product[5] = "Unclassified"
                self.tree.insert('', 'end', values=processed_product)
                
        except Exception as e:
            print(f"加载产品列表错误: {e}")
            messagebox.showerror("Error", f"Failed to load products list: {e}")
    
    def on_item_select(self, event):
        """Handle product selection event"""
        try:
            selected_items = self.tree.selection()
            if selected_items:
                self.edit_btn.config(state=tk.NORMAL)
                self.delete_btn.config(state=tk.NORMAL)
                self.status_label.config(text=f"Selected {len(selected_items)} products")
            else:
                self.edit_btn.config(state=tk.DISABLED)
                self.delete_btn.config(state=tk.DISABLED)
                self.status_label.config(text="Please select product")
        except Exception as e:
            print(f"选择事件处理错误: {e}")
    
    def on_item_double_click(self, event):
        """Handle double-click event, edit product directly"""
        try:
            selected_items = self.tree.selection()
            if selected_items:
                self.edit_selected_product()
        except Exception as e:
            print(f"双击事件处理错误: {e}")
    
    def on_item_click(self, event):
        """Handle click event, start in-table editing"""
        try:
            # 如果正在编辑，先保存
            if self.editing_item:
                self.save_edit()
            
            # 获取点击的列
            item = self.tree.identify_row(event.y)
            column = self.tree.identify_column(event.x)
            
            if not item or not column:
                return
            
            # 获取列名
            column_index = int(column.replace('#', '')) - 1
            column_names = ['gs1_code', 'name', 'packaging_waste', 'packaging_material', 'plastic_type', 'product_waste', 'created_at']
            
            if column_index >= len(column_names):
                return
            
            column_name = column_names[column_index]
            
            # Barcode and creation time are not editable
            if column_name in ['gs1_code', 'created_at']:
                return
            
            # 启动编辑
            self.start_edit(item, column_name, event.x, event.y)
            
        except Exception as e:
            print(f"单击事件处理错误: {e}")
    
    def start_edit(self, item, column_name, x, y):
        """Start editing cell"""
        try:
            # 获取当前值
            values = self.tree.item(item, 'values')
            column_index = ['gs1_code', 'name', 'packaging_waste', 'packaging_material', 'plastic_type', 'product_waste', 'created_at'].index(column_name)
            current_value = values[column_index] if column_index < len(values) else ""
            
            # 获取单元格位置
            bbox = self.tree.bbox(item, column_name)
            if not bbox:
                return
            
            # 创建编辑控件
            if column_name in ['packaging_waste', 'packaging_material', 'product_waste']:
                # 下拉选择框
                self.edit_widget = ttk.Combobox(self.tree, state="readonly")
                
                if column_name == 'packaging_waste' or column_name == 'product_waste':
                    options = ["", "Recyclable", "Hazardous", "Wet Waste", "Other Waste"]
                elif column_name == 'packaging_material':
                    options = ["", "Paper", "Plastic", "Metal", "Glass"]
                
                self.edit_widget['values'] = options
                self.edit_widget.set(current_value)
            else:
                # 输入框
                self.edit_widget = tk.Entry(self.tree)
                self.edit_widget.insert(0, current_value)
            
            # 设置位置和大小
            self.edit_widget.place(x=bbox[0], y=bbox[1], width=bbox[2], height=bbox[3])
            self.edit_widget.focus()
            self.edit_widget.select_range(0, tk.END)
            
            # 绑定事件
            self.edit_widget.bind('<Return>', lambda e: self.save_edit())
            self.edit_widget.bind('<Escape>', lambda e: self.cancel_edit())
            self.edit_widget.bind('<FocusOut>', lambda e: self.save_edit())
            
            # 记录编辑状态
            self.editing_item = item
            self.editing_column = column_name
            
        except Exception as e:
            print(f"开始编辑错误: {e}")
    
    def save_edit(self):
        """Save edit"""
        try:
            if not self.editing_item or not self.edit_widget:
                return
            
            # 获取新值
            new_value = self.edit_widget.get()
            
            # 获取产品数据
            values = list(self.tree.item(self.editing_item, 'values'))
            column_index = ['gs1_code', 'name', 'packaging_waste', 'packaging_material', 'plastic_type', 'product_waste', 'created_at'].index(self.editing_column)
            
            # 更新显示
            values[column_index] = new_value
            self.tree.item(self.editing_item, values=values)
            
            # 更新数据库
            barcode = values[0]  # 条形码作为主键
            
            cursor = self.conn.cursor()
            if self.editing_column == 'name':
                cursor.execute("UPDATE products SET product_name = ? WHERE gs1_code = ?", (new_value, barcode))
            elif self.editing_column == 'packaging_waste':
                cursor.execute("UPDATE products SET packaging_waste_type = ? WHERE gs1_code = ?", (new_value, barcode))
            elif self.editing_column == 'packaging_material':
                cursor.execute("UPDATE products SET packaging_material = ? WHERE gs1_code = ?", (new_value, barcode))
            elif self.editing_column == 'plastic_type':
                cursor.execute("UPDATE products SET plastic_type = ? WHERE gs1_code = ?", (new_value, barcode))
            elif self.editing_column == 'product_waste':
                cursor.execute("UPDATE products SET product_waste_type = ? WHERE gs1_code = ?", (new_value, barcode))
            
            self.conn.commit()
            
            # 清理编辑状态
            self.cancel_edit()
            
        except Exception as e:
            print(f"保存编辑错误: {e}")
            self.cancel_edit()
    
    def cancel_edit(self):
        """Cancel edit"""
        try:
            if self.edit_widget:
                self.edit_widget.destroy()
                self.edit_widget = None
            
            self.editing_item = None
            self.editing_column = None
            
        except Exception as e:
            print(f"取消编辑错误: {e}")
    
    def edit_selected_product(self):
        """Edit selected product (in-table editing)"""
        try:
            selected_items = self.tree.selection()
            if not selected_items:
                messagebox.showwarning("Warning", "Please select a product to edit first")
                return
            
            if len(selected_items) > 1:
                messagebox.showwarning("Warning", "Please select only one product to edit")
                return
            
            # 获取选中产品的数据
            item = selected_items[0]
            values = self.tree.item(item, 'values')
            
            # Prompt user to click the column to edit
            messagebox.showinfo("Info", "Please click the column you want to edit\n\nEditable columns:\n- Product Name (input box)\n- Packaging Classification (dropdown)\n- Packaging Material (dropdown)\n- Plastic Type (input box)\n- Product Classification (dropdown)")
            
        except Exception as e:
            print(f"编辑产品错误: {e}")
            messagebox.showerror("Error", f"Failed to edit product: {e}")
    
    def delete_selected_product(self):
        """Delete selected product"""
        try:
            selected_items = self.tree.selection()
            if not selected_items:
                messagebox.showwarning("Warning", "Please select a product to delete first")
                return
            
            # Confirm deletion
            if len(selected_items) == 1:
                item = selected_items[0]
                values = self.tree.item(item, 'values')
                product_name = values[1]  # Product name
                confirm_msg = f"Are you sure you want to delete product '{product_name}'?"
            else:
                confirm_msg = f"Are you sure you want to delete the selected {len(selected_items)} products?"
            
            if messagebox.askyesno("Confirm Deletion", confirm_msg):
                # Execute deletion
                cursor = self.conn.cursor()
                for item in selected_items:
                    values = self.tree.item(item, 'values')
                    barcode = values[0]  # Barcode
                    cursor.execute("DELETE FROM products WHERE gs1_code = ?", (barcode,))
                
                self.conn.commit()
                
                # Refresh list
                self.refresh_product_list()
                
                messagebox.showinfo("Success", f"Deleted {len(selected_items)} products")
                
        except Exception as e:
            print(f"删除产品错误: {e}")
            messagebox.showerror("Error", f"Failed to delete product: {e}")
    
    def refresh_product_list(self):
        """Refresh products list"""
        try:
            # Clear existing data
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Reload data
            self.load_products()
            
        except Exception as e:
            print(f"刷新产品列表错误: {e}")
    
    def close_window(self):
        """Close window"""
        self.window.destroy()
    
    def run(self):
        """Run window"""
        self.window.mainloop()


class EditProductWindow:
    def __init__(self, parent, conn, product_values, refresh_callback):
        self.parent = parent
        self.conn = conn
        self.refresh_callback = refresh_callback
        self.window = tk.Toplevel(parent)
        self.window.title("Edit Product")
        self.window.geometry("600x500")
        self.window.configure(bg='#f0f0f0')
        self.window.grab_set()  # 模态窗口
        
        # Product data
        self.barcode = product_values[0]
        self.product_name = product_values[1]
        self.packaging_waste_type = product_values[2] if product_values[2] != "Unclassified" else ""
        self.packaging_material = product_values[3] if product_values[3] else ""
        self.plastic_type = product_values[4] if product_values[4] else ""
        self.product_waste_type = product_values[5] if product_values[5] != "Unclassified" else ""
        
        # 创建界面
        self.create_interface()
    
    def create_interface(self):
        """Create edit interface"""
        # Title
        title_label = tk.Label(self.window, text="Edit Product", 
                              font=('Arial', 16, 'bold'), 
                              bg='#f0f0f0', fg='#333333')
        title_label.pack(pady=15)
        
        # 主内容区域
        main_frame = tk.Frame(self.window, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Barcode (read-only)
        barcode_frame = tk.Frame(main_frame, bg='#f0f0f0')
        barcode_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(barcode_frame, text="Barcode:", 
                font=('Arial', 12, 'bold'), bg='#f0f0f0').pack(anchor='w')
        
        barcode_entry = tk.Entry(barcode_frame, font=('Arial', 11), 
                                relief=tk.SUNKEN, bd=1, state='readonly')
        barcode_entry.pack(fill=tk.X, pady=5)
        barcode_entry.insert(0, self.barcode)
        
        # Product name
        name_frame = tk.Frame(main_frame, bg='#f0f0f0')
        name_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(name_frame, text="Product Name:", 
                font=('Arial', 12, 'bold'), bg='#f0f0f0').pack(anchor='w')
        
        self.name_entry = tk.Entry(name_frame, font=('Arial', 11), 
                                  relief=tk.SUNKEN, bd=1)
        self.name_entry.pack(fill=tk.X, pady=5)
        self.name_entry.insert(0, self.product_name)
        
        # Packaging waste classification
        packaging_frame = tk.Frame(main_frame, bg='#f0f0f0')
        packaging_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(packaging_frame, text="Packaging Waste Classification:", 
                font=('Arial', 12, 'bold'), bg='#f0f0f0').pack(anchor='w')
        
        self.packaging_waste_var = tk.StringVar(value=self.packaging_waste_type)
        packaging_options = ["", "Recyclable", "Hazardous", "Wet Waste", "Other Waste"]
        packaging_combo = ttk.Combobox(packaging_frame, textvariable=self.packaging_waste_var, 
                                      values=packaging_options, state="readonly", font=('Arial', 11))
        packaging_combo.pack(fill=tk.X, pady=5)
        packaging_combo.bind('<<ComboboxSelected>>', self.on_packaging_waste_change)
        
        # Packaging material selection
        self.material_frame = tk.Frame(main_frame, bg='#f0f0f0')
        
        tk.Label(self.material_frame, text="Packaging Material:", 
                font=('Arial', 12, 'bold'), bg='#f0f0f0').pack(anchor='w')
        
        self.packaging_material_var = tk.StringVar(value=self.packaging_material)
        material_options = ["", "Paper", "Plastic", "Metal", "Glass"]
        self.material_combo = ttk.Combobox(self.material_frame, textvariable=self.packaging_material_var, 
                                          values=material_options, state="readonly", font=('Arial', 11))
        self.material_combo.pack(fill=tk.X, pady=5)
        self.material_combo.bind('<<ComboboxSelected>>', self.on_material_change)
        
        # Plastic type input
        self.plastic_frame = tk.Frame(main_frame, bg='#f0f0f0')
        
        tk.Label(self.plastic_frame, text="Plastic Type:", 
                font=('Arial', 12, 'bold'), bg='#f0f0f0').pack(anchor='w')
        
        self.plastic_type_entry = tk.Entry(self.plastic_frame, font=('Arial', 11), 
                                          relief=tk.SUNKEN, bd=1)
        self.plastic_type_entry.pack(fill=tk.X, pady=5)
        self.plastic_type_entry.insert(0, self.plastic_type)
        
        # Product itself waste classification
        product_frame = tk.Frame(main_frame, bg='#f0f0f0')
        product_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(product_frame, text="Product Itself Waste Classification:", 
                font=('Arial', 12, 'bold'), bg='#f0f0f0').pack(anchor='w')
        
        self.product_waste_var = tk.StringVar(value=self.product_waste_type)
        product_options = ["", "Recyclable", "Hazardous", "Wet Waste", "Other Waste"]
        product_combo = ttk.Combobox(product_frame, textvariable=self.product_waste_var, 
                                    values=product_options, state="readonly", font=('Arial', 11))
        product_combo.pack(fill=tk.X, pady=5)
        
        # Button area
        button_frame = tk.Frame(self.window, bg='#f0f0f0')
        button_frame.pack(fill=tk.X, padx=20, pady=15)
        
        # Save button
        save_btn = tk.Button(button_frame, text="Save Changes", 
                            font=('Arial', 12, 'bold'),
                            bg='#4CAF50', fg='white',
                            relief=tk.RAISED, bd=2,
                            padx=20, pady=5,
                            command=self.save_changes)
        save_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Cancel button
        cancel_btn = tk.Button(button_frame, text="Cancel", 
                              font=('Arial', 12),
                              bg='#f44336', fg='white',
                              relief=tk.RAISED, bd=2,
                              padx=20, pady=5,
                              command=self.close_window)
        cancel_btn.pack(side=tk.RIGHT)
        
        # 初始化显示状态
        self.on_packaging_waste_change(None)
        self.on_material_change(None)
    
    def on_packaging_waste_change(self, event):
        """Handle packaging waste classification change"""
        waste_type = self.packaging_waste_var.get()
        if waste_type == "Recyclable":
            self.material_frame.pack(fill=tk.X, pady=5)
        else:
            self.material_frame.pack_forget()
            self.plastic_frame.pack_forget()
            self.packaging_material_var.set("")
            self.plastic_type_entry.delete(0, tk.END)
    
    def on_material_change(self, event):
        """Handle packaging material change"""
        material = self.packaging_material_var.get()
        if material == "Plastic":
            self.plastic_frame.pack(fill=tk.X, pady=5)
        else:
            self.plastic_frame.pack_forget()
            self.plastic_type_entry.delete(0, tk.END)
    
    def save_changes(self):
        """Save changes"""
        try:
            # 获取修改后的数据
            product_name = self.name_entry.get().strip()
            packaging_waste_type = self.packaging_waste_var.get()
            packaging_material = self.packaging_material_var.get()
            plastic_type = self.plastic_type_entry.get().strip()
            product_waste_type = self.product_waste_var.get()
            
            # Validate required fields
            if not product_name:
                messagebox.showwarning("Warning", "Please enter product name")
                return
            
            # If packaging is not recyclable, clear material and plastic type
            if packaging_waste_type != 'Recyclable':
                packaging_material = ""
                plastic_type = ""
            elif packaging_material != 'Plastic':
                plastic_type = ""
            
            # 更新数据库
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE products 
                SET product_name = ?, packaging_waste_type = ?, packaging_material = ?, 
                    plastic_type = ?, product_waste_type = ?, updated_at = CURRENT_TIMESTAMP
                WHERE gs1_code = ?
            ''', (product_name, packaging_waste_type, packaging_material, 
                  plastic_type, product_waste_type, self.barcode))
            
            self.conn.commit()
            
            # Display save success message
            success_msg = "Product updated successfully!"
            if packaging_waste_type:
                success_msg += f"\nPackaging Classification: {packaging_waste_type}"
                if packaging_material:
                    success_msg += f"\nPackaging Material: {packaging_material}"
                    if plastic_type:
                        success_msg += f"\nPlastic Type: {plastic_type}"
            if product_waste_type:
                success_msg += f"\nProduct Classification: {product_waste_type}"
            
            messagebox.showinfo("Success", success_msg)
            
            # Refresh products list
            self.refresh_callback()
            
            # Close window
            self.close_window()
            
        except Exception as e:
            print(f"Save changes error: {e}")
            messagebox.showerror("Error", f"Failed to save changes: {e}")
    
    def close_window(self):
        """关闭窗口"""
        self.window.destroy()
    
    def run(self):
        """运行窗口"""
        self.window.protocol("WM_DELETE_WINDOW", self.close_window)
        self.window.mainloop()


if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Product Management System')
    parser.add_argument('--gs1-code', type=str, help='Pre-fill GS1 code for new product')
    args = parser.parse_args()
    
    # 创建应用实例，传递预填的GS1代码
    app = ProductManager(prefill_gs1_code=args.gs1_code)
    
    # 如果有预填的GS1代码，直接打开创建产品窗口
    if args.gs1_code:
        app.open_create_product_window()
    
    app.run()
