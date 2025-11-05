# -*- coding: utf-8 -*-

"""
本程序用于遍历钉钉知识库中的所有文件，并将它们的URL导出到一个文本文件中。

工作流程:
1. 调用钉钉开放平台API获取知识库列表。
2. 将获取的知识库列表写入 workspaces_list_new.json 文件。
3. 从返回的知识库列表中根据知识库名称查找根节点的ID。
4. 使用钉钉开放平台的API，从根节点开始，递归地遍历所有子节点。
5. 将遍历过程中获取的所有节点信息写入 nodelist_new.json 文件。
6. 如果节点是文件 (FILE)，则将其URL写入到指定的输出文件中。

使用前请确保:
- 已安装所需的Python库: `alibabacloud_dingtalk`, `alibabacloud_tea_openapi`, `alibabacloud_tea_util`
- 已正确填写下面的配置信息 (ACCESS_TOKEN, OPERATOR_ID, WORKSPACE_NAME)。
"""

import json
from typing import List, Dict, Any

# 导入钉钉开放平台Wiki相关的SDK客户端和模型
from alibabacloud_dingtalk.wiki_2_0.client import Client as dingtalkwiki_2_0Client
from alibabacloud_dingtalk.wiki_2_0 import models as dingtalkwiki__2__0_models
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_tea_util.client import Client as UtilClient

# --- 配置区 ---
# 请根据您的实际情况修改以下配置
ACCESS_TOKEN = "YOUR_ACCESS_TOKEN"       # 访问钉钉API的access_token，需要通过钉钉开发者后台获取
OPERATOR_ID = "YOUR_OPERATOR_ID"             # 钉钉用户的unionId，需要通过钉钉开发者后台获取
WORKSPACE_NAME = "YOUR_WORKSPACE_NAME"                    # 需要遍历的目标知识库的完整名称
OUTPUT_FILE = "file_urls.txt"                           # 定义输出文件的名称，用于存储所有文档的URL
WORKSPACE_LIST_OUTPUT_FILE = "workspaces_list.json" # 存储获取的知识库列表的文件
NODE_LIST_OUTPUT_FILE = "nodelist.json"             # 存储获取的节点列表的文件

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
        print("错误: 未能从API获取到有效的知识库列表。")
    
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

def traverse_nodes(node_id: str, access_token: str, operator_id: str, out_file, all_nodes_list: list):
    """
    递归地遍历所有节点，收集节点信息，并将文件URL写入文件。

    Args:
        node_id (str): 当前要遍历的父节点的ID。
        access_token (str): API访问令牌。
        operator_id (str): 操作人的unionId。
        out_file (file object): 用于写入URL的文件对象。
        all_nodes_list (list): 用于收集所有节点信息的列表。
    """
    nodes = get_node_list(node_id, access_token, operator_id)
    if nodes:
        for node in nodes:
            print(f"  正在处理节点: {node.name} (类型: {node.type})")
            # 将节点信息转换为字典并添加到列表中
            all_nodes_list.append(node.to_map())
            
            if node.type == "FOLDER":
                traverse_nodes(node.node_id, access_token, operator_id, out_file, all_nodes_list)
            elif node.type == "FILE":
                out_file.write(node.url + "\n")

# --- 主程序入口 ---
if __name__ == "__main__":
    # 1. 从API获取知识库数据并找到根节点ID
    root_node_id, workspaces_list = get_workspace_data(WORKSPACE_NAME, ACCESS_TOKEN, OPERATOR_ID)

    if root_node_id:
        print(f"开始遍历知识库: '{WORKSPACE_NAME}' (根节点ID: {root_node_id})")
        
        all_nodes_collected = []
        
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            traverse_nodes(root_node_id, ACCESS_TOKEN, OPERATOR_ID, f, all_nodes_collected)
            
        # 5. 将收集到的所有节点信息写入新文件
        try:
            with open(NODE_LIST_OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(all_nodes_collected, f, ensure_ascii=False, indent=4)
            print(f"\n所有节点信息已成功写入到 '{NODE_LIST_OUTPUT_FILE}'")
        except IOError as e:
            print(f"错误: 无法写入文件 '{NODE_LIST_OUTPUT_FILE}': {e}")

        print(f"\n遍历完成！结果已保存到文件: {OUTPUT_FILE}")
    else:
        print(f"错误: 无法找到名为 '{WORKSPACE_NAME}' 的知识库。请检查名称是否正确 সন")