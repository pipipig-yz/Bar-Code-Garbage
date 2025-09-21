#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能产品识别与垃圾分类管理系统 - 依赖安装脚本
自动安装所需的Python库
"""

import subprocess
import sys
import os

def install_package(package):
    """安装单个包"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ 成功安装: {package}")
        return True
    except subprocess.CalledProcessError:
        print(f"❌ 安装失败: {package}")
        return False

def check_package(package):
    """检查包是否已安装"""
    try:
        __import__(package)
        return True
    except ImportError:
        return False

def main():
    """主安装函数"""
    print("🚀 智能产品识别与垃圾分类管理系统 - 依赖安装")
    print("=" * 60)
    
    # 需要安装的包列表
    packages = [
        "opencv-python>=4.5.0",
        "pyzbar>=0.1.8", 
        "pillow>=8.0.0",
        "numpy>=1.19.0",
        "openai>=1.0.0",
        "requests>=2.25.0",
        "speechrecognition>=3.8.0",
        "pyaudio>=0.2.11",
        "opencv-contrib-python>=4.5.0"
    ]
    
    # 检查内置模块
    builtin_modules = ["sqlite3", "tkinter", "base64", "threading", "datetime", "json", "os", "sys", "time", "argparse", "subprocess"]
    
    print("📋 检查内置模块...")
    for module in builtin_modules:
        if check_package(module):
            print(f"✅ {module} (内置模块)")
        else:
            print(f"❌ {module} (内置模块，但未找到)")
    
    print("\n📦 安装外部依赖包...")
    success_count = 0
    total_count = len(packages)
    
    for package in packages:
        package_name = package.split(">=")[0].split("==")[0]
        if check_package(package_name):
            print(f"✅ {package} (已安装)")
            success_count += 1
        else:
            print(f"📥 正在安装: {package}")
            if install_package(package):
                success_count += 1
    
    print("\n" + "=" * 60)
    print(f"📊 安装完成: {success_count}/{total_count} 个包安装成功")
    
    if success_count == total_count:
        print("🎉 所有依赖安装成功！可以运行程序了。")
        print("\n🚀 启动程序:")
        print("  用户端: python barcode_scanner_stable.py")
        print("  商家端: python product_manager.py")
    else:
        print("⚠️  部分依赖安装失败，请手动安装失败的包。")
        print("💡 可以尝试使用以下命令手动安装:")
        for package in packages:
            print(f"  pip install {package}")
    
    print("\n📝 注意事项:")
    print("1. 确保Python版本 >= 3.7")
    print("2. 确保网络连接正常")
    print("3. 某些包可能需要管理员权限")
    print("4. 如果安装失败，请检查网络连接或使用国内镜像源")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 安装被用户中断")
    except Exception as e:
        print(f"\n❌ 安装过程中出现错误: {e}")
        print("💡 请尝试手动安装依赖包")
