#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库查看器 - 用于查看和操作SQLite数据库
支持查看表结构、查询数据、简单的数据编辑等功能
"""

import sqlite3
import os
import sys
from typing import List, Dict, Any, Optional
import json

class DatabaseViewer:
    def __init__(self, db_path: str):
        """初始化数据库查看器"""
        self.db_path = db_path
        if not os.path.exists(db_path):
            print(f"❌ 数据库文件不存在: {db_path}")
            sys.exit(1)
    
    def connect(self) -> sqlite3.Connection:
        """连接到数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # 使结果可以按列名访问
            return conn
        except sqlite3.Error as e:
            print(f"❌ 连接数据库失败: {e}")
            sys.exit(1)
    
    def get_tables(self) -> List[str]:
        """获取所有表名"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        return tables
    
    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """获取表结构"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = []
        for row in cursor.fetchall():
            columns.append({
                'cid': row[0],
                'name': row[1],
                'type': row[2],
                'notnull': bool(row[3]),
                'default_value': row[4],
                'pk': bool(row[5])
            })
        conn.close()
        return columns
    
    def get_table_data(self, table_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """获取表数据"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit}")
        rows = []
        for row in cursor.fetchall():
            rows.append(dict(row))
        conn.close()
        return rows
    
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """执行自定义查询"""
        conn = self.connect()
        cursor = conn.cursor()
        try:
            cursor.execute(query)
            if query.strip().upper().startswith('SELECT'):
                rows = []
                for row in cursor.fetchall():
                    rows.append(dict(row))
                return rows
            else:
                conn.commit()
                return [{"message": "查询执行成功", "affected_rows": cursor.rowcount}]
        except sqlite3.Error as e:
            return [{"error": str(e)}]
        finally:
            conn.close()
    
    def get_table_count(self, table_name: str) -> int:
        """获取表的记录数"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        conn.close()
        return count

def print_separator(title: str = ""):
    """打印分隔线"""
    if title:
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}")
    else:
        print("-" * 60)

def print_table_schema(columns: List[Dict[str, Any]]):
    """打印表结构"""
    print(f"{'列名':<20} {'类型':<15} {'非空':<8} {'主键':<8} {'默认值'}")
    print("-" * 70)
    for col in columns:
        pk_mark = "✓" if col['pk'] else ""
        notnull_mark = "✓" if col['notnull'] else ""
        default_val = str(col['default_value']) if col['default_value'] is not None else ""
        print(f"{col['name']:<20} {col['type']:<15} {notnull_mark:<8} {pk_mark:<8} {default_val}")

def print_table_data(data: List[Dict[str, Any]], max_width: int = 20):
    """打印表数据"""
    if not data:
        print("📭 没有数据")
        return
    
    # 获取所有列名
    columns = list(data[0].keys())
    
    # 计算每列的最大宽度
    col_widths = {}
    for col in columns:
        col_widths[col] = max(len(str(col)), max_width)
        for row in data:
            col_widths[col] = max(col_widths[col], len(str(row.get(col, ""))))
    
    # 打印表头
    header = " | ".join([col.ljust(col_widths[col]) for col in columns])
    print(header)
    print("-" * len(header))
    
    # 打印数据行
    for row in data:
        row_str = " | ".join([str(row.get(col, "")).ljust(col_widths[col]) for col in columns])
        print(row_str)

def main():
    """主程序"""
    print("🗄️  SQLite数据库查看器")
    print("=" * 60)
    
    # 检查数据库文件
    db_files = []
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.endswith(".db"):
                db_files.append(os.path.join(root, file))
    
    if not db_files:
        print("❌ 当前目录下没有找到.db文件")
        return
    
    # 选择数据库文件
    if len(db_files) == 1:
        db_path = db_files[0]
        print(f"📁 找到数据库文件: {db_path}")
    else:
        print("📁 找到多个数据库文件:")
        for i, db_file in enumerate(db_files, 1):
            print(f"  {i}. {db_file}")
        
        while True:
            try:
                choice = int(input("请选择数据库文件 (输入数字): ")) - 1
                if 0 <= choice < len(db_files):
                    db_path = db_files[choice]
                    break
                else:
                    print("❌ 无效选择，请重新输入")
            except ValueError:
                print("❌ 请输入有效数字")
    
    # 初始化数据库查看器
    viewer = DatabaseViewer(db_path)
    
    while True:
        print_separator("主菜单")
        print("1. 📋 查看所有表")
        print("2. 🔍 查看表结构")
        print("3. 📊 查看表数据")
        print("4. 🔢 查看表记录数")
        print("5. 💻 执行自定义SQL查询")
        print("6. 📈 数据库统计信息")
        print("0. 🚪 退出")
        
        choice = input("\n请选择操作 (输入数字): ").strip()
        
        if choice == "0":
            print("👋 再见!")
            break
        elif choice == "1":
            show_all_tables(viewer)
        elif choice == "2":
            show_table_schema(viewer)
        elif choice == "3":
            show_table_data(viewer)
        elif choice == "4":
            show_table_count(viewer)
        elif choice == "5":
            execute_custom_query(viewer)
        elif choice == "6":
            show_database_stats(viewer)
        else:
            print("❌ 无效选择，请重新输入")

def show_all_tables(viewer: DatabaseViewer):
    """显示所有表"""
    print_separator("数据库表列表")
    tables = viewer.get_tables()
    if tables:
        for i, table in enumerate(tables, 1):
            count = viewer.get_table_count(table)
            print(f"{i}. {table} ({count} 条记录)")
    else:
        print("📭 数据库中没有表")

def show_table_schema(viewer: DatabaseViewer):
    """显示表结构"""
    tables = viewer.get_tables()
    if not tables:
        print("📭 数据库中没有表")
        return
    
    print("📋 选择要查看结构的表:")
    for i, table in enumerate(tables, 1):
        print(f"  {i}. {table}")
    
    try:
        choice = int(input("请选择表 (输入数字): ")) - 1
        if 0 <= choice < len(tables):
            table_name = tables[choice]
            print_separator(f"表结构: {table_name}")
            columns = viewer.get_table_schema(table_name)
            print_table_schema(columns)
        else:
            print("❌ 无效选择")
    except ValueError:
        print("❌ 请输入有效数字")

def show_table_data(viewer: DatabaseViewer):
    """显示表数据"""
    tables = viewer.get_tables()
    if not tables:
        print("📭 数据库中没有表")
        return
    
    print("📋 选择要查看数据的表:")
    for i, table in enumerate(tables, 1):
        count = viewer.get_table_count(table)
        print(f"  {i}. {table} ({count} 条记录)")
    
    try:
        choice = int(input("请选择表 (输入数字): ")) - 1
        if 0 <= choice < len(tables):
            table_name = tables[choice]
            limit = input("显示记录数限制 (默认100，直接回车使用默认值): ").strip()
            limit = int(limit) if limit.isdigit() else 100
            
            print_separator(f"表数据: {table_name} (显示前{limit}条)")
            data = viewer.get_table_data(table_name, limit)
            print_table_data(data)
        else:
            print("❌ 无效选择")
    except ValueError:
        print("❌ 请输入有效数字")

def show_table_count(viewer: DatabaseViewer):
    """显示表记录数"""
    print_separator("表记录数统计")
    tables = viewer.get_tables()
    if tables:
        total_records = 0
        for table in tables:
            count = viewer.get_table_count(table)
            total_records += count
            print(f"{table:<30} {count:>10} 条记录")
        print("-" * 45)
        print(f"{'总计':<30} {total_records:>10} 条记录")
    else:
        print("📭 数据库中没有表")

def execute_custom_query(viewer: DatabaseViewer):
    """执行自定义SQL查询"""
    print_separator("自定义SQL查询")
    print("💡 提示: 支持所有SQLite SQL语句")
    print("💡 示例: SELECT * FROM products WHERE product_name LIKE '%手机%'")
    print("💡 示例: SELECT COUNT(*) FROM products")
    
    query = input("\n请输入SQL查询语句: ").strip()
    if not query:
        print("❌ 查询语句不能为空")
        return
    
    print_separator("查询结果")
    result = viewer.execute_query(query)
    
    if result and "error" in result[0]:
        print(f"❌ 查询错误: {result[0]['error']}")
    elif result and "message" in result[0]:
        print(f"✅ {result[0]['message']}")
        if "affected_rows" in result[0]:
            print(f"📊 影响行数: {result[0]['affected_rows']}")
    else:
        print_table_data(result)

def show_database_stats(viewer: DatabaseViewer):
    """显示数据库统计信息"""
    print_separator("数据库统计信息")
    
    # 数据库文件信息
    db_size = os.path.getsize(viewer.db_path)
    print(f"📁 数据库文件: {viewer.db_path}")
    print(f"📏 文件大小: {db_size:,} 字节 ({db_size/1024:.2f} KB)")
    
    # 表信息
    tables = viewer.get_tables()
    print(f"📋 表数量: {len(tables)}")
    
    if tables:
        print("\n📊 各表详细信息:")
        total_records = 0
        for table in tables:
            count = viewer.get_table_count(table)
            total_records += count
            columns = viewer.get_table_schema(table)
            print(f"  📋 {table}: {count} 条记录, {len(columns)} 个字段")
        
        print(f"\n📈 总记录数: {total_records}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 程序被用户中断，再见!")
    except Exception as e:
        print(f"\n❌ 程序运行出错: {e}")
        import traceback
        traceback.print_exc()
