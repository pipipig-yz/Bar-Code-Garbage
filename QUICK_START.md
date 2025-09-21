# 快速开始指南

## 1. 安装依赖

### 方法一：使用安装脚本（推荐）
```bash
python install_dependencies.py
```

### 方法二：手动安装
```bash
pip install -r requirements.txt
```

### 方法三：逐个安装
```bash
pip install opencv-python pyzbar pillow numpy openai requests speechrecognition pyaudio opencv-contrib-python
```

## 2. 启动程序

### 用户端 - 产品识别与分类
```bash
python barcode_scanner_stable.py
```

### 商家端 - 产品管理
```bash
python product_manager.py
```

## 3. 基本使用

### 用户端操作
1. 将产品条形码对准摄像头
2. 系统自动识别条形码
3. 在AI助手中输入产品名称或使用语音
4. 查看垃圾分类建议

### 商家端操作
1. 点击"Create New Product"创建新产品
2. 拍摄产品照片
3. 系统自动识别条形码和产品名称
4. 设置垃圾分类信息
5. 保存产品信息

## 4. 配置API

### DeepSeek API（AI分类）
在代码中配置您的API密钥

### 百度OCR API（产品名称识别）
在代码中配置API密钥和Secret Key

## 5. 故障排除

### 常见问题
- **摄像头无法启动**: 检查权限和占用情况
- **条形码识别失败**: 调整角度和光线
- **语音识别不工作**: 检查麦克风权限
- **API调用失败**: 检查网络和密钥

### 获取帮助
- 查看完整README.md文档
- 检查错误日志输出
- 确认所有依赖已正确安装
