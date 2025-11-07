import os
import shutil
import filecmp

def sync_folders(source_folder, destination_folder, dry_run):
    """
    同步两个文件夹，使目标文件夹(destination_folder)与源文件夹(source_folder)保持一致。

    :param source_folder: 源文件夹的路径
    :param destination_folder: 目标文件夹的路径 (需要被更新的文件夹)
    :param dry_run: 是否为演练模式。True时，只打印将要执行的操作，不实际修改文件。
    """
    print("--- 开始同步 ---")
    print(f"源文件夹: {source_folder}")
    print(f"目标文件夹: {destination_folder}")
    if dry_run:
        print("模式: 演练模式 (不会修改任何文件)")
    else:
        print("模式: 正式执行模式 (将会修改文件!)")
    print("-" * 20)

    # 在比较之前，确保顶层目标文件夹存在
    print(f"检查目标文件夹是否存在: {destination_folder}")
    if not os.path.isdir(destination_folder):
        print(f"目标文件夹不存在。")
        if not dry_run:
            print(f"正在创建目标文件夹: {destination_folder}")
            os.makedirs(destination_folder, exist_ok=True) # 使用 makedirs 创建文件夹，可以创建多级目录
        else:
            # 在演练模式下，如果目标文件夹不存在，后续比较会失败。
            # 提示并返回。
            print("[演练模式] 目标文件夹不存在，无法进行比较。同步将在此处停止。")
            print("\n--- 同步完成 ---")
            return

    # 1. 创建顶层比较对象
    # hide=[os.curdir, os.pardir] 忽略当前和上级目录的特殊符号
    # ignore=['.DS_Store', 'Thumbs.db'] 可以添加你想要忽略的系统文件名
    comparison = filecmp.dircmp(source_folder, destination_folder, ignore=['.DS_Store', 'Thumbs.db'])

    # 2. 调用递归函数执行同步
    _sync_recursive(comparison, source_folder, destination_folder, dry_run)

    print("\n--- 同步完成 ---")


def _sync_recursive(dcmp, source_root, dest_root, dry_run):
    """递归同步的核心函数"""

    # 3. 新增和更新
    # 3.1 处理源文件夹中独有的文件和目录 (dcmp.left_only)
    for name in dcmp.left_only:
        source_path = os.path.join(dcmp.left, name)
        dest_path = os.path.join(dcmp.right, name)

        if os.path.isdir(source_path):
            print(f"[新增目录] 准备复制: {source_path} -> {dest_path}")
            if not dry_run:
                shutil.copytree(source_path, dest_path)
        else:
            print(f"[新增文件] 准备复制: {source_path} -> {dest_path}")
            if not dry_run:
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copy2(source_path, dest_path)

    # 3.2 处理内容不同的文件 (dcmp.diff_files)
    for name in dcmp.diff_files:
        source_path = os.path.join(dcmp.left, name)
        dest_path = os.path.join(dcmp.right, name)
        print(f"[更新文件] 准备复制: {source_path} -> {dest_path}")
        if not dry_run:
            shutil.copy2(source_path, dest_path)

    # 4. 删除
    # right_only 是目标文件夹中多余的文件或文件夹
    for filename in dcmp.right_only:
        path_to_delete = os.path.join(dcmp.right, filename)
        if os.path.isdir(path_to_delete):
            print(f"[删除目录] 准备删除: {path_to_delete}")
            if not dry_run:
                shutil.rmtree(path_to_delete)
        else:
            print(f"[删除文件] 准备删除: {path_to_delete}")
            if not dry_run:
                os.remove(path_to_delete)

    # 5. 递归进入子文件夹 (对于两边都存在的目录)
    for sub_dir_name, sub_dcmp in dcmp.subdirs.items():
        _sync_recursive(sub_dcmp, source_root, dest_root, dry_run)