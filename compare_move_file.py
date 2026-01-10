import os
import json
import shutil

# ============================================================
# 受保护项目配置
# ============================================================
# 在此列表中添加需要保护的文件或文件夹路径（相对于目标文件夹的相对路径）
# 这些项目将不会被删除
# 支持精确匹配和目录递归保护（保护目录时，其下所有内容也受保护）
# ============================================================
PROTECTED_ITEMS = [
    # 示例：
    # "产品中心/内部资料",
    # "机密文档/重要文件.docx",
    # "开发部/临时文件",
]
# ============================================================


def _is_protected(relative_path, protected_items):
    """
    检查路径是否在保护列表中。
    支持精确匹配和目录前缀匹配（保护目录时，其下所有内容也受保护）。

    :param relative_path: 相对于目标文件夹的相对路径（使用正斜杠）
    :param protected_items: 受保护的项目列表（相对路径列表）
    :return: True 表示受保护，False 表示不受保护
    """
    normalized_path = os.path.normpath(relative_path).replace(os.sep, "/")

    for item in protected_items:
        normalized_item = os.path.normpath(item).replace(os.sep, "/")
        # 精确匹配
        if normalized_path == normalized_item:
            return True
        # 检查是否是受保护目录下的文件/子目录
        if normalized_path.startswith(normalized_item + "/"):
            return True

    return False


def sync_nas_with_kb_tree(
    kb_tree_file, source_folder, destination_folder, protected_items=None, dry_run=False
):
    """
    使用知识库文件树（kb_tree.json）作为权威来源，同步NAS文件夹。

    1. 删除NAS中不存在于知识库树中的文件和文件夹（排除受保护项目）。
    2. 将源文件夹（已下载的新文件）中的内容移动到NAS目标文件夹。

    :param kb_tree_file: kb_tree.json文件的路径。
    :param source_folder: 包含新下载和整理好的文件的源文件夹。
    :param destination_folder: 最终要同步的NAS目标文件夹。
    :param protected_items: 受保护的项目列表（相对路径列表）。如果为 None，则使用全局 PROTECTED_ITEMS。
    :param dry_run: 是否为演练模式。True时只打印操作，不实际执行。
    """
    print("--- 开始同步 ---")
    print(f"知识库树: {kb_tree_file}")
    print(f"源文件夹 (新文件): {source_folder}")
    print(f"目标文件夹 (NAS): {destination_folder}")
    mode = "演练模式" if dry_run else "正式执行"
    print(f"模式: {mode}")
    print("-" * 20)

    # 1. 加载知识库文件树
    try:
        with open(kb_tree_file, "r", encoding="utf-8") as f:
            kb_tree = json.load(f)
        print("成功加载知识库文件树。")
    except FileNotFoundError:
        print(f"错误: 知识库文件树 '{kb_tree_file}' 未找到。无法继续。")
        return
    except json.JSONDecodeError:
        print(f"错误: 解析知识库文件树 '{kb_tree_file}' 失败。")
        return

    # 规范化kb_tree的键，统一使用正斜杠作为路径分隔符（跨平台兼容）
    normalized_kb_paths = {
        os.path.normpath(p).replace(os.sep, "/") for p in kb_tree.keys()
    }

    # 确定受保护项目列表
    if protected_items is None:
        protected_items = PROTECTED_ITEMS

    if protected_items:
        print(f"已启用保护机制，共 {len(protected_items)} 项受保护。")
    else:
        print("未配置受保护项目。")

    # --- 2. 清理阶段 ---
    print("\n--- 阶段 1: 清理目标文件夹 ---")
    if not os.path.isdir(destination_folder):
        print(f"目标文件夹 {destination_folder} 不存在，无需清理。")
    else:
        # 从下到上遍历，先处理文件，再处理目录
        for root, dirs, files in os.walk(destination_folder, topdown=False):
            # 清理文件
            for name in files:
                file_path = os.path.join(root, name)
                # 规范化路径并统一使用正斜杠
                relative_path = os.path.normpath(
                    os.path.relpath(file_path, destination_folder)
                ).replace(os.sep, "/")

                # 检查是否受保护
                if _is_protected(relative_path, protected_items):
                    print(f"[受保护跳过] {relative_path}")
                    continue

                if relative_path not in normalized_kb_paths:
                    print(f"[删除文件] {relative_path}")
                    if not dry_run:
                        try:
                            os.remove(file_path)
                        except OSError as e:
                            print(f"  错误: 删除文件失败: {e}")

            # 清理目录
            for name in dirs:
                dir_path = os.path.join(root, name)
                # 检查目录是否为空
                if not os.listdir(dir_path):
                    # 规范化路径并统一使用正斜杠
                    relative_path = os.path.normpath(
                        os.path.relpath(dir_path, destination_folder)
                    ).replace(os.sep, "/")

                    # 检查是否受保护
                    if _is_protected(relative_path, protected_items):
                        print(f"[受保护跳过目录] {relative_path}")
                        continue

                    # 如果没有任何知识库文件路径以这个目录作为前缀，那么它就是多余的
                    is_needed_dir = any(
                        p.startswith(relative_path + "/") for p in normalized_kb_paths
                    )

                    if not is_needed_dir:
                        print(f"[删除空目录] {relative_path}")
                        if not dry_run:
                            try:
                                os.rmdir(dir_path)
                            except OSError as e:
                                print(f"  错误: 删除目录失败: {e}")
    print("清理阶段完成。")

    # --- 3. 移动/复制阶段 ---
    print("\n--- 阶段 2: 移动新文件 ---")
    if not os.path.isdir(source_folder):
        print(f"源文件夹 {source_folder} 不存在，没有新文件需要移动。")
    else:
        for root, _, files in os.walk(source_folder):
            for name in files:
                source_path = os.path.join(root, name)
                relative_path = os.path.relpath(source_path, source_folder)
                destination_path = os.path.join(destination_folder, relative_path)

                print(f"[移动文件] {relative_path}")

                if not dry_run:
                    try:
                        # 确保目标目录存在
                        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
                        # 移动文件，shutil.move会覆盖现有文件
                        shutil.move(source_path, destination_path)
                    except (OSError, shutil.Error) as e:
                        print(f"  错误: 移动文件失败: {e}")
        print("移动新文件阶段完成。")

    print("\n--- 同步完成 ---")


if __name__ == "__main__":
    # --- 示例用法 ---
    # 1. 知识库的完整文件结构
    KB_TREE_JSON = "kb_tree.json"

    # 2. 下载了新文件并按目录结构整理好的文件夹
    SOURCE_DIR = "download_new"

    # 3. 最终要同步到的NAS文件夹
    DEST_DIR = "nas_final"

    # 4. （可选）受保护项目配置 - 在文件顶部的 PROTECTED_ITEMS 中配置
    #    或在此处传入自定义列表：
    #    custom_protected = ["产品中心/内部资料", "机密文档"]

    # 执行同步（演练模式）
    # 使用全局 PROTECTED_ITEMS 配置
    sync_nas_with_kb_tree(KB_TREE_JSON, SOURCE_DIR, DEST_DIR, dry_run=True)

    # 或使用自定义保护列表（覆盖全局配置）
    # sync_nas_with_kb_tree(KB_TREE_JSON, SOURCE_DIR, DEST_DIR,
    #                       protected_items=custom_protected, dry_run=True)

    print("\n--- 演练模式后，检查文件是否变动 (应该没有) ---")
    print("NAS目录结构:", list(os.walk(DEST_DIR)))
    print("源目录结构:", list(os.walk(SOURCE_DIR)))
    print("-" * 20)

    # 执行同步（正式模式）
    sync_nas_with_kb_tree(KB_TREE_JSON, SOURCE_DIR, DEST_DIR, dry_run=False)

    print("\n--- 正式执行后，检查文件是否变动 ---")
    print("NAS目录结构:", list(os.walk(DEST_DIR)))
    print("源目录结构 (应该空了):", list(os.walk(SOURCE_DIR)))
    print("-" * 20)

    # 清理模拟文件
    shutil.rmtree(DEST_DIR)
    shutil.rmtree(SOURCE_DIR)
    os.remove(KB_TREE_JSON)
