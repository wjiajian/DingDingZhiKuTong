# -*- coding: utf-8 -*-
import asyncio
from typing import Optional, Dict

from alibabacloud_dingtalk.oauth2_1_0.client import Client as DingTalkOAuthClient
from alibabacloud_dingtalk.oauth2_1_0 import models as dingtalk_oauth_models
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util.client import Client as UtilClient

def get_dingtalk_access_token(app_key: str, app_secret: str) -> Optional[Dict[str, any]]:
    """
    获取钉钉企业内部应用的 Access Token。

    通过 AppKey 和 AppSecret 调用钉钉开放平台接口，获取访问凭证。

    Args:
        app_key (str): 应用的 AppKey。
        app_secret (str): 应用的 AppSecret。

    Returns:
        如果成功，返回accessToken
        如果失败，则返回 None。
    """
    try:
        # 1. 初始化 OpenAPI Client
        config = open_api_models.Config(protocol='https', region_id='central')
        client = DingTalkOAuthClient(config)

        # 2. 构建请求体
        request = dingtalk_oauth_models.GetAccessTokenRequest(
            app_key=app_key,
            app_secret=app_secret
        )

        # 3. 发送请求并获取响应
        response = client.get_access_token(request)

        # 4. 提取并返回关键信息
        if response.body:
            print("成功获取 Access Token。")
            return response.body.access_token,
        return None

    except Exception as err:
        # 异常处理
        if not UtilClient.empty(err.code) and not UtilClient.empty(err.message):
            print(f"获取 Access Token 失败: code={err.code}, message={err.message}")
        else:
            print(f"获取 Access Token 时发生未知错误: {err}")
        return None