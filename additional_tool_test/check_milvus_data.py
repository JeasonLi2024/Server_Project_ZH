#!/usr/bin/env python3
"""
Milvus向量数据库查看工具
用于检查enterprise_vectors集合中的数据
"""

from pymilvus import connections, Collection, utility
import json

# ========== 配置 ==========
MILVUS_HOST = "10.129.22.101"
MILVUS_PORT = "19530"
COLLECTION_NAME = "enterprise_vectors"

def connect_to_milvus():
    """连接到Milvus数据库"""
    try:
        connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
        print(f"✅ 成功连接到Milvus: {MILVUS_HOST}:{MILVUS_PORT}")
        return True
    except Exception as e:
        print(f"❌ 连接Milvus失败: {e}")
        return False

def check_collection_exists():
    """检查集合是否存在"""
    try:
        exists = utility.has_collection(COLLECTION_NAME)
        if exists:
            print(f"✅ 集合 '{COLLECTION_NAME}' 存在")
            return True
        else:
            print(f"❌ 集合 '{COLLECTION_NAME}' 不存在")
            return False
    except Exception as e:
        print(f"❌ 检查集合失败: {e}")
        return False

def get_collection_info():
    """获取集合基本信息"""
    try:
        collection = Collection(COLLECTION_NAME)
        
        # 加载集合到内存
        collection.load()
        
        # 获取集合统计信息
        print(f"\n📊 集合统计信息:")
        print(f"   集合名称: {COLLECTION_NAME}")
        print(f"   数据条数: {collection.num_entities}")
        
        # 获取集合schema信息
        schema = collection.schema
        print(f"\n📋 集合结构:")
        for field in schema.fields:
            print(f"   字段: {field.name} | 类型: {field.dtype}")
            if hasattr(field, 'description') and field.description:
                print(f"     描述: {field.description}")
        
        return collection
    except Exception as e:
        print(f"❌ 获取集合信息失败: {e}")
        return None

def query_data_by_pid(collection, pid=None, limit=10):
    """根据PID查询数据"""
    try:
        if pid is not None:
            # 查询特定PID的数据
            expr = f"Pid == {pid}"
            print(f"\n🔍 查询PID={pid}的数据:")
        else:
            # 查询所有数据（限制数量）
            expr = "Pid >= 0"
            print(f"\n🔍 查询所有数据（前{limit}条）:")
        
        results = collection.query(
            expr=expr,
            output_fields=["Pid", "ChunkNumber", "Text", "AddData1", "AddData2"],
            limit=limit,
            consistency_level="Eventually"
        )
        
        if not results:
            print("   📭 没有找到数据")
            return
        
        print(f"   📦 找到 {len(results)} 条记录:")
        for i, result in enumerate(results):
            print(f"\n   记录 {i+1}:")
            print(f"     PID: {result.get('Pid', 'N/A')}")
            print(f"     块编号: {result.get('ChunkNumber', 'N/A')}")
            
            # 解析文本内容
            text = result.get('Text', '')
            if text:
                try:
                    # 如果是JSON格式，尝试解析
                    if text.startswith('"') and text.endswith('"'):
                        text_content = json.loads(text)
                    else:
                        text_content = text
                    
                    # 显示文本内容（截取前100字符）
                    display_text = str(text_content)[:100]
                    if len(str(text_content)) > 100:
                        display_text += "..."
                    print(f"     文本内容: {display_text}")
                except:
                    print(f"     文本内容: {text[:100]}...")
            else:
                print(f"     文本内容: 无")
        
    except Exception as e:
        print(f"❌ 查询数据失败: {e}")

def get_all_pids(collection):
    """获取所有不同的PID"""
    try:
        # 查询所有PID
        results = collection.query(
            expr="Pid >= 0",
            output_fields=["Pid"],
            limit=1000,  # 限制查询数量
            consistency_level="Eventually"
        )
        
        if not results:
            print("📭 没有找到任何数据")
            return []
        
        # 获取唯一的PID列表
        pids = list(set([result['Pid'] for result in results]))
        pids.sort()
        
        print(f"\n📋 找到的PID列表: {pids}")
        print(f"   总共有 {len(pids)} 个不同的PID")
        
        # 统计每个PID的记录数
        pid_counts = {}
        for result in results:
            pid = result['Pid']
            pid_counts[pid] = pid_counts.get(pid, 0) + 1
        
        print(f"\n📊 每个PID的记录数:")
        for pid in sorted(pid_counts.keys()):
            print(f"   PID {pid}: {pid_counts[pid]} 条记录")
        
        return pids
    except Exception as e:
        print(f"❌ 获取PID列表失败: {e}")
        return []

def main():
    """主函数"""
    print("🚀 Milvus向量数据库查看工具")
    print("=" * 50)
    
    # 1. 连接数据库
    if not connect_to_milvus():
        return
    
    # 2. 检查集合是否存在
    if not check_collection_exists():
        return
    
    # 3. 获取集合信息
    collection = get_collection_info()
    if not collection:
        return
    
    # 4. 获取所有PID
    pids = get_all_pids(collection)
    
    # 5. 交互式查询
    while True:
        print("\n" + "=" * 50)
        print("🔍 查询选项:")
        print("1. 查看所有数据（前10条）")
        print("2. 根据PID查询数据")
        print("3. 重新获取PID列表")
        print("4. 退出")
        
        choice = input("\n请选择操作 (1-4): ").strip()
        
        if choice == '1':
            query_data_by_pid(collection, pid=None, limit=10)
        elif choice == '2':
            if not pids:
                print("❌ 没有可用的PID")
                continue
            print(f"可用的PID: {pids}")
            try:
                pid_input = input("请输入要查询的PID: ").strip()
                pid = int(pid_input)
                query_data_by_pid(collection, pid=pid, limit=50)
            except ValueError:
                print("❌ 请输入有效的数字")
        elif choice == '3':
            pids = get_all_pids(collection)
        elif choice == '4':
            print("👋 再见！")
            break
        else:
            print("❌ 无效选择，请重试")

if __name__ == "__main__":
    main()