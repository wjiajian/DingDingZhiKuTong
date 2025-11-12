# -*- coding: utf-8 -*-

"""
本程序用于遍历钉钉知识库中的所有文件，并将它们的URL导出到一个文本文件中。

工作流程:
1. 调用钉钉开放平台API获取知识库列表。
2. 将获取的知识库列表写入 json 文件。
3. 从返回的知识库列表中根据知识库名称查找根节点的ID。
4. 使用钉钉开放平台的API，从根节点开始，递归地遍历所有子节点。
5. 将遍历过程中获取的所有节点信息写入 json 文件。
6. 如果节点是文件 (FILE)，则将其URL写入到指定的输出文件中。

使用前请确保:
- 已安装所需的Python库: `alibabacloud_dingtalk`, `alibabacloud_tea_openapi`, `alibabacloud_tea_util`
"""
import os
import json
import datetime
from typing import List, Dict, Any

# 导入钉钉开放平台Wiki相关的SDK客户端和模型
from alibabacloud_dingtalk.wiki_2_0.client import Client as dingtalkwiki_2_0Client
from alibabacloud_dingtalk.wiki_2_0 import models as dingtalkwiki__2__0_models
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_tea_util.client import Client as UtilClient

# --- 配置区 ---
# 请根据您的实际情况修改以下配置
ACCESS_TOKEN = ""                                         # 访问钉钉API的access_token
OPERATOR_ID = ""                                          # 钉钉用户的unionId，需要通过钉钉开发者后台获取
WORKSPACE_NAME = ""                                       # 需要遍历的目标知识库的完整名称
OUTPUT_FILE = ""                                          # 定义输出文件的名称，用于存储所有文档的URL
WORKSPACE_LIST_OUTPUT_FILE = ""                           # 存储获取的知识库列表的文件
KB_TREE_OUTPUT_FILE = ""                                  # 存储知识库完整文件树的JSON文件
NAS_ROOT_PATH = ""                                        # 要对比的本地NAS文件夹根路径
# WORKSPACE_NAME = "知识库导入NAS测试库"                    # 需要遍历的目标知识库的完整名称
# OUTPUT_FILE = ".\url.json"                              # 定义输出文件的名称，用于存储所有文档的URL
# WORKSPACE_LIST_OUTPUT_FILE = ".\workspaces_list.json"   # 存储获取的知识库列表的文件
# KB_TREE_OUTPUT_FILE = ".\kb_tree.json"
# NAS_ROOT_PATH = ".\path"

# 钉钉文件后缀到标准Office后缀的映射
EXTENSION_MAPPING = {
    '.adoc': '.docx',
    '.axls': '.xlsx',
    '.aslide': '.pptx',
}

def get_workspaces(access_token: str, operator_id: str):
    """
    调用钉钉API，获取知识库列表。
    """
    client = create_client()
    list_workspaces_headers = dingtalkwiki__2__0_models.ListWorkspacesHeaders()
    list_workspaces_headers.x_acs_dingtalk_access_token = access_token
    list_workspaces_request = dingtalkwiki__2__0_models.ListWorkspacesRequest(
        max_results=30,
        order_by='VIEW_TIME_DESC',
        with_permission_role=False,
        operator_id=operator_id
    )
    try:
        response = client.list_workspaces_with_options(list_workspaces_request, list_workspaces_headers, util_models.RuntimeOptions())
        return response
    except Exception as err:
        if not UtilClient.empty(err.code) and not UtilClient.empty(err.message):
            print(f"API请求失败: {err.message}")
            return None

def get_workspace_data(workspace_name: str, access_token: str, operator_id: str) -> (str, List[Dict[str, Any]]):
    """
    调用API获取知识库列表，写入文件，并返回指定知识库的根节点ID和知识库列表。

    Args:
        workspace_name (str): 知识库的名称。
        access_token (str): API访问令牌。
        operator_id (str): 操作人的unionId。

    Returns:
        tuple: (root_node_id, workspaces_list)
    """
    print("正在从API获取知识库列表...")
    response = get_workspaces(access_token, operator_id)
    if response and response.body and response.body.workspaces:
        workspaces = response.body.to_map().get("workspaces", [])
        
        # 将获取的知识库列表写入新文件
        try:
            with open(WORKSPACE_LIST_OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(workspaces, f, ensure_ascii=False, indent=4)
            print(f"知识库列表已成功写入到 '{WORKSPACE_LIST_OUTPUT_FILE}'")
        except IOError as e:
            print(f"错误: 无法写入文件 '{WORKSPACE_LIST_OUTPUT_FILE}': {e}")

        for workspace in workspaces:
            if workspace.get("name") == workspace_name:
                print(f"成功找到知识库 '{workspace_name}'")
                return workspace.get("rootNodeId"), workspaces
    else:
        print("错误: 未能从API获取到有效的知识库列表。" )
    
    return None, None


def create_client() -> dingtalkwiki_2_0Client:
    """
    创建并初始化一个钉钉Wiki API的客户端实例。

    Returns:
        dingtalkwiki_2_0Client: 配置好的API客户端实例。
    """
    config = open_api_models.Config()
    config.protocol = 'https'
    config.region_id = 'central'
    return dingtalkwiki_2_0Client(config)

def get_node_list(node_id: str, access_token: str, operator_id: str) -> List:
    """
    调用钉钉API，获取指定节点下的子节点列表。

    Args:
        node_id (str): 父节点的ID。
        access_token (str): API访问令牌。
        operator_id (str): 操作人的unionId。

    Returns:
        List: 包含子节点对象的列表。如果发生错误或没有子节点，则返回空列表。
    """
    client = create_client()
    list_nodes_headers = dingtalkwiki__2__0_models.ListNodesHeaders()
    list_nodes_headers.x_acs_dingtalk_access_token = access_token
    
    list_nodes_request = dingtalkwiki__2__0_models.ListNodesRequest(
        parent_node_id=node_id,
        max_results=100, # 增加每次获取的数量
        operator_id=operator_id
    )
    
    all_nodes = []
    next_token = None
    
    while True:
        list_nodes_request.next_token = next_token
        try:
            response = client.list_nodes_with_options(list_nodes_request, list_nodes_headers, util_models.RuntimeOptions())
            if response.body and response.body.nodes:
                all_nodes.extend(response.body.nodes)
            next_token = response.body.next_token
            if not next_token:
                break
        except Exception as err:
            if not UtilClient.empty(err.code) and not UtilClient.empty(err.message):
                print(f"API请求失败: {err.message}")
            break
            
    return all_nodes

def traverse_kb_nodes(node_id: str, access_token: str, operator_id: str, parent_path: str, file_tree: dict):
    """
    递归地遍历所有知识库节点，构建文件树。

    Args:
        node_id (str): 当前要遍历的父节点的ID。
        access_token (str): API访问令牌。
        operator_id (str): 操作人的unionId。
        parent_path (str): 父节点的路径。
        file_tree (dict): 用于存储文件树的字典。
    """
    nodes = get_node_list(node_id, access_token, operator_id)
    if nodes:
        for node in nodes:
            # 替换路径中可能存在的无效字符
            safe_node_name = node.name.replace('/', '_').replace('\\', '_')
            current_path = f"{parent_path}/{safe_node_name}" if parent_path else safe_node_name
            print(f"  正在处理知识库节点: {current_path} (类型: {node.type})")
            
            if node.type == "FOLDER":
                traverse_kb_nodes(node.node_id, access_token, operator_id, current_path, file_tree)
            elif node.type == "FILE":
                # --- 新增：处理文件后缀名 ---
                name, ext = os.path.splitext(current_path)
                if ext in EXTENSION_MAPPING:
                    new_ext = EXTENSION_MAPPING[ext]
                    final_path = name + new_ext
                    print(f"    后缀名转换: '{ext}' -> '{new_ext}'")
                else:
                    final_path = current_path
                # --- 结束 ---

                file_tree[final_path] = {
                    "modifiedTime": node.modified_time,
                    "url": node.url
                }

def get_nas_file_tree(nas_root_path):
    """
    生成NAS文件夹的文件树结构.
    """
    print(f"\n正在扫描本地NAS文件夹: {nas_root_path}")
    file_tree = {}
    if not os.path.isdir(nas_root_path):
        print(f"警告: 本地NAS路径 '{nas_root_path}' 不存在或不是一个目录。将视为空文件夹。" )
        return file_tree

    for root, _, files in os.walk(nas_root_path):
        for file in files:
            file_path = os.path.join(root, file)
            # 使用os.path.normpath来规范化路径分隔符
            relative_path = os.path.normpath(os.path.relpath(file_path, nas_root_path))
            # 将Windows路径分隔符'\'统一替换为'/'
            relative_path = relative_path.replace('\\', '/')
            
            modified_time = os.path.getmtime(file_path)
            # 将时间戳转换为UTC时间的ISO 8601格式字符串，并附加'Z'
            modified_time_iso = datetime.datetime.utcfromtimestamp(modified_time).isoformat(timespec='seconds') + 'Z'
            
            file_tree[relative_path] = {
                "modifiedTime": modified_time_iso,
                "path": file_path
            }
    print("本地NAS文件夹扫描完成。" )
    return file_tree

def compare_trees_and_get_urls(kb_tree, nas_tree):
    """
    比较知识库和NAS的文件树，返回需要下载的URL列表.
    """
    print("\n正在比较知识库与本地NAS文件...")
    urls_to_download = []

    for kb_path, kb_info in kb_tree.items():
        # 检查文件是否在NAS中不存在
        if kb_path not in nas_tree:
            print(f"[新增] 文件 '{kb_path}' 在本地不存在，准备下载。" )
            urls_to_download.append(kb_info['url'])
        else:
            # 文件已存在，比较修改时间
            try:
                # 解析不含毫秒和'Z'的ISO 8601时间字符串
                nas_time_str = nas_tree[kb_path]['modifiedTime'].split('.')[0].replace('Z', '')
                kb_time_str = kb_info['modifiedTime'].split('.')[0].replace('Z', '')
                
                nas_time = datetime.datetime.fromisoformat(nas_time_str)
                kb_time = datetime.datetime.fromisoformat(kb_time_str)

                if kb_time > nas_time:
                    print(f"[更新] 文件 '{kb_path}' 在知识库中已更新，准备下载。 (知识库: {kb_time} > 本地: {nas_time})")
                    urls_to_download.append(kb_info['url'])
            except (ValueError, KeyError) as e:
                print(f"警告: 处理文件 '{kb_path}' 的时间戳时出错: {e}。将默认下载该文件。" )
                urls_to_download.append(kb_info['url'])

    print("文件比较完成。" )
    return urls_to_download


def getdata(name, output, workspace_list, kb_tree_file, nas_path):
    global WORKSPACE_NAME, OUTPUT_FILE, WORKSPACE_LIST_OUTPUT_FILE, KB_TREE_OUTPUT_FILE, NAS_ROOT_PATH
    WORKSPACE_NAME = name
    OUTPUT_FILE = output
    WORKSPACE_LIST_OUTPUT_FILE = workspace_list
    KB_TREE_OUTPUT_FILE = kb_tree_file
    NAS_ROOT_PATH = nas_path


def main(name, output, workspace_list, kb_tree_file, nas_path, token):
    # 初始化参数
    getdata(name, output, workspace_list, kb_tree_file, nas_path)
    global ACCESS_TOKEN
    ACCESS_TOKEN = token

    # 1. 从API获取知识库数据并找到根节点ID
    root_node_id, _ = get_workspace_data(WORKSPACE_NAME, ACCESS_TOKEN, OPERATOR_ID)

    if root_node_id:
        # 2. 获取知识库文件树
        print(f"\n开始遍历知识库: '{WORKSPACE_NAME}' (根节点ID: {root_node_id})")
        kb_tree = {}
        traverse_kb_nodes(root_node_id, ACCESS_TOKEN, OPERATOR_ID, "", kb_tree)
        print("知识库遍历完成。" )

        # 3. 将完整的知识库文件树写入JSON文件，供compare_move_file.py使用
        try:
            with open(KB_TREE_OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(kb_tree, f, ensure_ascii=False, indent=4)
            print(f"完整的知识库文件树已成功写入到 '{KB_TREE_OUTPUT_FILE}'")
        except IOError as e:
            print(f"错误: 无法写入知识库文件树 '{KB_TREE_OUTPUT_FILE}': {e}")


        # 4. 获取NAS文件树
        nas_tree = get_nas_file_tree(NAS_ROOT_PATH)

        # 5. 比较文件树并获取需要下载的URL
        urls_to_download = compare_trees_and_get_urls(kb_tree, nas_tree)
            
        # 6. 将需要下载的URL写入文件
        if urls_to_download:
            print(f"\n--- 发现 {len(urls_to_download)} 个文件需要下载 ---")
            try:
                with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                    for url in urls_to_download:
                        f.write(url + "\n")
                print(f"需要下载的URL列表已成功写入到 '{OUTPUT_FILE}'")
            except IOError as e:
                print(f"错误: 无法写入URL列表文件 '{OUTPUT_FILE}': {e}")
        else:
            print("\n--- 所有文件都是最新的，无需下载。 ---")

        print("\n任务完成！" )
    else:
        print(f"错误: 无法找到名为 '{WORKSPACE_NAME}' 的知识库。请检查名称是否正确。" )

if __name__ == "__main__":
    # 这是一个示例，实际使用时请通过外部调用并传入参数
    # main("知识库名称", "path/to/urls.txt", "path/to/workspaces.json", "path/to/kb_tree.json", "path/to/nas", "your_token")
    pass
