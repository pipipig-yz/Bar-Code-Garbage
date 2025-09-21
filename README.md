# 智能产品识别与垃圾分类管理系统

## 项目简介

这是一个基于Python开发的智能产品识别与垃圾分类管理系统，集成了计算机视觉、人工智能、语音识别和OCR技术。系统能够实时识别产品条形码，通过AI分析进行智能垃圾分类，支持语音交互和自动产品信息识别。

## 功能特色

- 🔍 **实时条形码识别**: 支持多种格式条形码（EAN13、UPC、CODE128等）
- 🤖 **AI智能分类**: 集成DeepSeek大模型进行垃圾分类分析
- 🎤 **语音交互**: 支持语音输入和文字输入双重交互方式
- 📷 **OCR识别**: 自动识别产品名称，提升数据录入效率
- 🗂️ **产品管理**: 完整的产品信息CRUD操作
- 🎨 **图形化界面**: 现代化GUI设计，直观易用

## 系统架构

```
智能产品识别与垃圾分类管理系统
├── 用户端 (barcode_scanner_stable.py)
│   ├── 实时条形码识别
│   ├── AI垃圾分类助手
│   ├── 语音交互功能
│   └── 产品信息展示
└── 商家端 (product_manager.py)
    ├── 产品信息管理
    ├── 垃圾分类设置
    ├── OCR产品识别
    └── 数据库操作
```

## 安装依赖

### 系统要求
- Python 3.7+
- Windows 10/11 或 macOS 或 Linux
- 摄像头设备
- 麦克风设备（语音功能）

### 安装Python库

```bash
# 核心依赖
pip install opencv-python
pip install pyzbar
pip install pillow
pip install tkinter
pip install sqlite3

# AI和API相关
pip install openai
pip install requests
pip install speechrecognition
pip install pyaudio

# 图像处理
pip install numpy
pip install opencv-contrib-python

# 其他工具
pip install base64
pip install threading
pip install datetime
```

### 完整安装命令

```bash
pip install opencv-python pyzbar pillow openai requests speechrecognition pyaudio numpy opencv-contrib-python
```

## 使用说明

### 1. 用户端 - 产品识别与分类

#### 启动程序
```bash
python barcode_scanner_stable.py
```

#### 主要功能

**条形码识别**
- 将产品条形码对准摄像头
- 系统自动识别并显示条形码信息
- 支持多种条形码格式

**AI垃圾分类助手**
- 在聊天框中输入产品名称
- 或点击🎤按钮进行语音输入
- AI助手会分析并给出垃圾分类建议

**产品信息查看**
- 识别成功后自动显示产品详细信息
- 包括产品名称、照片、垃圾分类等
- 支持包装和产品本身的双重分类

#### 操作界面说明

![用户端界面](screenshots/user_interface.png)
*用户端主界面 - 左侧摄像头显示，右侧识别结果和AI助手*

### 2. 商家端 - 产品管理

#### 启动程序
```bash
python product_manager.py
```

#### 主要功能

**创建新产品**
- 点击"Create New Product"按钮
- 使用摄像头拍摄产品照片
- 系统自动识别条形码和产品名称
- 设置垃圾分类信息

**产品信息管理**
- 查看所有产品列表
- 编辑产品信息
- 删除产品记录
- 支持在线编辑功能

#### 操作界面说明

![商家端界面](screenshots/admin_interface.png)
*商家端主界面 - 产品创建和管理功能*

## 详细操作指南

### 用户端操作流程

1. **启动程序**
   ```bash
   python barcode_scanner_stable.py
   ```

2. **条形码识别**
   - 将产品条形码对准摄像头
   - 等待系统自动识别
   - 查看识别结果和产品信息

3. **AI垃圾分类咨询**
   - 在聊天框中输入产品名称
   - 或点击🎤按钮进行语音输入
   - 查看AI给出的垃圾分类建议

4. **查看产品信息**
   - 识别成功后自动显示详细信息
   - 包括包装和产品本身的分类

### 商家端操作流程

1. **启动程序**
   ```bash
   python product_manager.py
   ```

2. **创建新产品**
   - 点击"Create New Product"
   - 拍摄产品照片
   - 系统自动识别条形码和产品名称
   - 设置垃圾分类信息
   - 保存产品信息

3. **管理产品**
   - 点击"View Products List"
   - 查看所有产品
   - 双击产品进行编辑
   - 选择产品进行删除

## 技术特性

### 核心技术栈
- **计算机视觉**: OpenCV + pyzbar
- **人工智能**: DeepSeek API
- **语音识别**: Google Speech API + Sphinx
- **OCR技术**: 百度OCR API
- **数据库**: SQLite
- **GUI**: Tkinter

### 技术亮点
- 多线程处理确保实时性能
- 多模态输入支持（视觉+语音+文字）
- 智能图像预处理优化
- 完善的异常处理机制
- 模块化设计便于扩展

## 配置说明

### API配置

**DeepSeek API**
- 在代码中配置您的DeepSeek API密钥
- 用于AI垃圾分类分析

**百度OCR API**
- 配置百度OCR的API密钥和Secret Key
- 用于产品名称自动识别

**语音识别**
- 支持Google在线识别和Sphinx离线识别
- 自动检测网络状态并切换

### 数据库配置
- 系统自动创建SQLite数据库
- 支持数据备份和恢复
- 表结构自动升级

## 故障排除

### 常见问题

**摄像头无法启动**
- 检查摄像头权限
- 确认摄像头未被其他程序占用
- 尝试重启程序

**条形码识别失败**
- 确保条形码清晰可见
- 调整摄像头角度和距离
- 检查光线条件

**语音识别不工作**
- 检查麦克风权限
- 确认网络连接（Google识别需要网络）
- 测试麦克风功能

**API调用失败**
- 检查网络连接
- 验证API密钥是否正确
- 查看API使用额度

### 错误日志
程序运行时会输出详细的错误信息，请根据错误提示进行排查。

## 项目结构

```
智能产品识别与垃圾分类管理系统/
├── barcode_scanner_stable.py    # 用户端主程序
├── product_manager.py           # 商家端主程序
├── gs1_barcode_query.py         # 条形码查询工具
├── 数据库查看器.py               # 数据库管理工具
├── products.db                  # SQLite数据库
├── photos/                      # 产品照片存储目录
├── 图形化显示/                   # 垃圾分类图标
├── video/                       # 视频文件
├── Product list/                # 产品列表文件
└── README.md                    # 项目说明文档
```

## 更新日志

### v1.0.0 (2024-01-20)
- 初始版本发布
- 实现基础条形码识别功能
- 集成AI垃圾分类助手
- 添加语音交互功能
- 完善产品管理系统

## 贡献指南

欢迎提交Issue和Pull Request来改进这个项目。

## 许可证

本项目采用MIT许可证，详情请查看LICENSE文件。

## 联系方式

如有问题或建议，请通过以下方式联系：
- 提交GitHub Issue
- 发送邮件至项目维护者

---

**注意**: 使用前请确保已正确配置所有API密钥，并遵守相关API的使用条款。
