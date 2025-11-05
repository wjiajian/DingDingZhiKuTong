# DingDingZhiKuTong

连接到钉钉知识库，获取知识库下所有文件URL，为将其同步或下载到NAS提供支持。

## 功能

*   获取钉钉知识库列表。
*   遍历指定知识库下的所有文件夹和文件。
*   提取所有文件的URL并保存到文本文件中。
*   将获取的知识库列表和节点信息保存为JSON文件，方便二次开发。

## 如何使用

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

### 3. 配置并运行主程序

1.  打开 `get_KB_FILE_URL.py` 文件。
2.  在“配置区”部分，填入以下信息：
    *   `ACCESS_TOKEN`: 步骤2中获取到的 `accessToken`。
    *   `OPERATOR_ID`: 您的 `unionId`。
    *   `WORKSPACE_NAME`: 您要遍历的钉钉知识库的完整名称。
3.  运行 `get_KB_FILE_URL.py` 脚本：

    ```bash
    python get_KB_FILE_URL.py
    ```
4.  程序运行完毕后，您将在项目根目录下找到 `file_urls.txt` 文件，其中包含了所有文件的URL。

## 文件说明

*   `getToken.py`: 用于获取钉钉API的 `access_token`。
*   `get_KB_FILE_URL.py`: 主程序，用于遍历知识库并提取文件URL。
*   `file_urls.txt`: (程序生成) 存储所有文件URL的文本文件。
*   `workspaces_list.json`: (程序生成) 存储获取到的知识库列表的JSON文件。
*   `nodelist.json`: (程序生成) 存储获取到的所有节点信息的JSON文件。
*   `README.md`: 本文档。