# 项目截图指南

## 需要截图的界面

### 1. 用户端界面截图
**文件位置**: `screenshots/user_interface.png`

**截图内容**:
- 左侧：摄像头实时显示区域，显示条形码识别框
- 右侧上方：识别结果显示区域，显示检测到的条形码
- 右侧中间：AI垃圾分类助手聊天界面
- 右侧下方：产品信息图形化显示区域

**截图步骤**:
1. 运行 `python barcode_scanner_stable.py`
2. 将产品条形码对准摄像头
3. 等待系统识别条形码
4. 在AI助手中输入产品名称
5. 截图保存为 `screenshots/user_interface.png`

### 2. 商家端界面截图
**文件位置**: `screenshots/admin_interface.png`

**截图内容**:
- 主界面：显示"Create New Product"和"View Products List"按钮
- 产品创建界面：左侧摄像头，右侧产品信息输入区域
- 产品列表界面：显示所有产品的表格视图

**截图步骤**:
1. 运行 `python product_manager.py`
2. 点击"Create New Product"进入创建界面
3. 截图保存为 `screenshots/admin_interface.png`

### 3. 功能演示截图

#### 条形码识别演示
**文件位置**: `screenshots/barcode_recognition.png`
- 显示摄像头识别条形码的过程
- 条形码周围有绿色识别框
- 显示识别出的条形码信息

#### AI垃圾分类演示
**文件位置**: `screenshots/ai_classification.png`
- 显示AI助手的聊天界面
- 用户输入产品名称
- AI返回垃圾分类建议

#### 产品信息展示
**文件位置**: `screenshots/product_info.png`
- 显示完整的产品信息界面
- 包括产品名称、照片、垃圾分类图标
- 包装和产品本身的双重分类显示

## 截图要求

1. **分辨率**: 建议使用1920x1080或更高分辨率
2. **格式**: PNG格式，保持清晰度
3. **内容**: 确保界面元素完整显示
4. **隐私**: 避免截取包含个人信息的条形码

## 创建截图目录

```bash
mkdir screenshots
```

## 截图命名规范

- `user_interface.png` - 用户端主界面
- `admin_interface.png` - 商家端主界面
- `barcode_recognition.png` - 条形码识别演示
- `ai_classification.png` - AI分类演示
- `product_info.png` - 产品信息展示
- `voice_interaction.png` - 语音交互演示
- `product_management.png` - 产品管理界面

## 更新README

截图完成后，请更新README.md文件中的图片路径，确保所有截图都能正确显示。
