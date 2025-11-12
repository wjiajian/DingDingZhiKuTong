# DingDingZhiKuTong

本工具用于将钉钉知识库与本地NAS（或任何文件夹）进行精确、增量的单向同步。

## 核心功能

*   **智能比较**：通过API获取知识库的完整目录结构，并与本地文件夹进行比较，识别出新增、修改过的文件。
*   **增量下载**：只生成需要下载的新增或已更新文件的URL列表，最大化效率。
*   **精确同步**：确保最终的本地文件夹内容与钉钉知识库的线上状态完全一致，自动删除本地多余的文件和目录。
*   **自动转换后缀**：自动将钉钉的专有后缀（如 `.adoc`, `.axls`）映射为标准的Office后缀（`.docx`, `.xlsx`），确保本地文件可用性。

## 环境准备与凭证

### 1. 环境准备

确保您的环境中已经安装了 Python。然后，安装所需的依赖库：

```bash
pip install alibabacloud_dingtalk alibabacloud_tea_openapi alibabacloud_tea_util
```

### 2. 获取访问凭证

首先，您需要获取访问钉钉API所需的凭证。

#### 获取 `app_key` 和 `app_secret`

1.  登录[钉钉开放平台](https://open.dingtalk.com/)。
2.  创建或选择一个应用，进入应用详情页。
3.  在“应用凭证”区域，您可以找到 `AppKey` 和 `AppSecret`。

#### 获取 `access_token`

1.  打开 `getToken.py` 文件。
2.  将您获取到的 `app_key` 和 `app_secret` 填入到 `get_access_token_request` 中。
3.  运行 `getToken.py` 脚本：

    ```bash
    python getToken.py
    ```
4.  在控制台输出中，您将看到包含 `accessToken` 的信息。请复制 `accessToken` 的值。

#### 获取 `operator_id`

`operator_id` 是操作者的 `unionId`。您可以通过调用[根据手机号获取用户信息](https://open.dingtalk.com/document/org-dev-guide/query-user-details-by-phone-number)接口，或者在钉钉后台的用户管理中获取。

## 文件说明

*   `getToken.py`: 用于获取钉钉API的 `access_token`。
*   `get_KB_FILE_URL.py`: 用于比较线上知识库和本地NAS，并生成 `kb_tree.json` 和 `urls_to_download.txt`。
*   `compare_move_file.py`: 使用 `kb_tree.json` 作为蓝图，将下载好的新文件同步到最终的NAS目录，并清理多余文件。
*   `kb_tree.json`: (程序生成) 包含了知识库中所有文件的完整目录结构、修改时间和URL。
*   `urls_to_download.txt`: (程序生成) 本次需要下载的新文件或更新文件的URL列表。
*   `workspaces_list.json`: (程序生成) 您的钉钉账号下所有知识库的列表，供参考。

## 知识库与NAS同步流程

这是一个三步走的工作流。

### 步骤 1: 生成下载列表和知识库蓝图

运行 `get_KB_FILE_URL.py` 脚本。

-   **配置**: 在脚本顶部的配置区填入以下信息：
    -   `ACCESS_TOKEN`: 步骤2中获取到的 `accessToken`。
    -   `OPERATOR_ID`: 您的 `unionId`。
    -   `WORKSPACE_NAME`: 您要遍历的钉钉知识库的完整名称。
    -   `NAS_ROOT_PATH`: 您最终NAS目标文件夹的路径。
    -   `KB_TREE_OUTPUT_FILE`: `kb_tree.json` 的输出路径。
    -   `OUTPUT_FILE`: `urls_to_download.txt` 的输出路径。
-   **执行**:
    ```bash
    python get_KB_FILE_URL.py
    ```
-   **结果**:
    -   生成 `kb_tree.json` (完整的知识库蓝图)。
    -   生成 `urls_to_download.txt` (本次需下载的URL列表)。

### 步骤 2: 下载并整理文件 (手动)

1.  使用您自己的下载工具处理 `urls_to_download.txt` 文件，将所有文件下载下来。
2.  将下载的文件整理到一个临时的“源文件夹” (例如: `download_new`) 中，并确保其内部的目录结构与知识库中的结构完全一致。

### 步骤 3: 清理并同步到NAS

运行 `compare_move_file.py` 脚本。

-   **配置**: 在脚本的 `if __name__ == '__main__':` 部分，修改以下变量：
    -   `KB_TREE_JSON`: `kb_tree.json` 的路径。
    -   `SOURCE_DIR`: 您在步骤2中创建的“源文件夹”的路径。
    -   `DEST_DIR`: 您最终的“NAS目标文件夹”的路径。
-   **执行**:
    ```bash
    python compare_move_file.py
    ```
-   **过程**:
    1.  **清理阶段**: 脚本会读取 `kb_tree.json`，然后检查“NAS目标文件夹”。如果发现NAS中的任何文件或空目录在 `kb_tree.json` 中不存在，就会将其删除。
    2.  **移动阶段**: 脚本会遍历“源文件夹”，将里面的所有新文件和更新文件移动到“NAS目标文件夹”的正确位置。
-   **结果**:
    -   一个与钉钉知识库文件结构和内容完全同步的NAS文件夹。
    -   “源文件夹”内的文件被移动后，该文件夹会变空。

这个流程确保了每次同步都是安全和精确的，避免了误删未改动的文件。