import os
import json
import shutil

def sync_nas_with_kb_tree(kb_tree_file, source_folder, destination_folder, dry_run=False):
    """
    使用知识库文件树（kb_tree.json）作为权威来源，同步NAS文件夹。

    1. 删除NAS中不存在于知识库树中的文件和文件夹。
    2. 将源文件夹（已下载的新文件）中的内容移动到NAS目标文件夹。

    :param kb_tree_file: kb_tree.json文件的路径。
    :param source_folder: 包含新下载和整理好的文件的源文件夹。
    :param destination_folder: 最终要同步的NAS目标文件夹。
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
        with open(kb_tree_file, 'r', encoding='utf-8') as f:
            kb_tree = json.load(f)
        print("成功加载知识库文件树。")
    except FileNotFoundError:
        print(f"错误: 知识库文件树 '{kb_tree_file}' 未找到。无法继续。")
        return
    except json.JSONDecodeError:
        print(f"错误: 解析知识库文件树 '{kb_tree_file}' 失败。")
        return

    # 规范化kb_tree的键，以匹配本地文件系统
    # 将所有路径分隔符统一为os.sep
    normalized_kb_paths = {os.path.normpath(p) for p in kb_tree.keys()}

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
                relative_path = os.path.normpath(os.path.relpath(file_path, destination_folder))
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
                    # 检查该目录本身是否应该存在（通过检查是否有任何kb路径以它开头）
                    relative_path = os.path.normpath(os.path.relpath(dir_path, destination_folder))
                    
                    # 如果没有任何知识库文件路径以这个目录作为前缀，那么它就是多余的
                    is_needed_dir = any(p.startswith(relative_path + os.sep) for p in normalized_kb_paths)
                    
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


if __name__ == '__main__':
    # --- 示例用法 ---
    # 1. 知识库的完整文件结构
    KB_TREE_JSON = 'kb_tree.json' 

    # 2. 下载了新文件并按目录结构整理好的文件夹
    SOURCE_DIR = 'download_new' 

    # 3. 最终要同步到的NAS文件夹
    DEST_DIR = 'nas_final' 
    
    
    # 假设这是我们的kb_tree.json内容
    sample_kb_tree = {
        "folder1/file1.txt": {"modifiedTime": "...", "url": "..."},
        "folder1/new_file.txt": {"modifiedTime": "...", "url": "..."},
        "file_at_root.txt": {"modifiedTime": "...", "url": "..."},
    }
    with open(KB_TREE_JSON, 'w', encoding='utf-8') as f:
        json.dump(sample_kb_tree, f)

    # 准备模拟环境
    # 创建一个假的NAS目录，包含一个将被删除的文件
    os.makedirs(os.path.join(DEST_DIR, 'folder1'), exist_ok=True)
    os.makedirs(os.path.join(DEST_DIR, 'folder_to_delete'), exist_ok=True)
    with open(os.path.join(DEST_DIR, 'folder1', 'file1.txt'), 'w') as f: f.write('old')
    with open(os.path.join(DEST_DIR, 'folder_to_delete', 'old_file.txt'), 'w') as f: f.write('delete me')
    
    # 创建一个假的源目录，包含新文件
    os.makedirs(os.path.join(SOURCE_DIR, 'folder1'), exist_ok=True)
    with open(os.path.join(SOURCE_DIR, 'folder1', 'new_file.txt'), 'w') as f: f.write('new')
    with open(os.path.join(SOURCE_DIR, 'file_at_root.txt'), 'w') as f: f.write('new root file')

    print("--- 准备模拟环境完成 ---")
    print("NAS目录结构:", list(os.walk(DEST_DIR)))
    print("源目录结构:", list(os.walk(SOURCE_DIR)))
    print("-" * 20)

    # 执行同步（演练模式）
    sync_nas_with_kb_tree(KB_TREE_JSON, SOURCE_DIR, DEST_DIR, dry_run=True)
    
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
