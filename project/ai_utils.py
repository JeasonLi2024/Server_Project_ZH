import os
import logging
import requests
import uuid
from django.conf import settings
from volcenginesdkarkruntime import Ark
from common_utils import build_media_url

logger = logging.getLogger(__name__)

# 风格提示词映射
STYLE_PROMPTS = {
    'default': '现代商务或科技极简风格，画面清晰，构图平衡，适合项目展示',
    'tech': '赛博朋克风格，霓虹灯光，未来城市，高科技感，深色背景，酷炫',
    'illustration': '扁平化矢量插画，色彩明亮，简约线条，创意几何图形，适合UI设计',
    'ink': '中国水墨画风格，写意，留白，山水意境，传统美学，大气',
    '3d': 'C4D渲染风格，3D立体模型，柔和光照，材质细腻，现代感，抽象艺术'
}

def generate_poster_images(title, brief, tags, style='default'):
    """
    调用 Doubao-Seedream-4.5 生成海报图片 (使用 volcenginesdkarkruntime)
    
    Args:
        title (str): 需求标题
        brief (str): 需求简介
        tags (str/list): 标签
        style (str): 风格代码
        
    Returns:
        list: 生成的图片URL列表
    """
    # 从环境变量获取 API Key
    api_key = os.environ.get('ARK_API_KEY')
    
    # 兼容性保留：如果没有环境变量，尝试从 settings 获取
    if not api_key:
        api_key = getattr(settings, 'ARK_API_KEY', None)
        
    if not api_key:
        logger.error("未配置 ARK_API_KEY")
        raise Exception("未配置 AI 服务密钥 (ARK_API_KEY)")

    # 初始化客户端
    # base_url 必须配置为 https://ark.cn-beijing.volces.com/api/v3
    client = Ark(
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        api_key=api_key
    )
    
    # 构建 Prompt
    style_desc = STYLE_PROMPTS.get(style, STYLE_PROMPTS['default'])
    tags_str = tags if isinstance(tags, str) else ' '.join(tags)
    
    prompt = (
        f"设计一组（4张）专业的项目需求横板海报封面，提供不同的设计方案供选择。\n"
        f"【项目标题】：{title}\n"
        f"【项目简介】：{brief}\n"
        f"【相关标签】：{tags_str}\n"
        f"【画面要求】：\n"
        f"1. 风格：{style_desc}。\n"
        f"2. 内容：抽象化表达项目主题，避免过多的文字，突出该项目需求的核心概念。\n"
        f"3. 构图：中心构图或左右构图，留有适当留白，视觉冲击力强。\n"
        f"4. 质量：高分辨率，细节丰富，无模糊噪点。"
    )
    
    try:
        # 调用图片生成 API
        # Model ID 优先从环境变量获取，默认为 doubao-seedream-4-5-251128
        model_id = os.environ.get('ARK_MODEL_ENDPOINT', "doubao-seedream-4-5-251128")
        
        logger.info(f"Generating poster with model: {model_id}")
        
        completion = client.images.generate(
            model=model_id,
            prompt=prompt,
            size="2K",  # 官方推荐 2K 或 4K
            response_format="url",
            watermark=False,
            # 使用 extra_body 传递额外参数以支持组图生成 (需模型支持)
            extra_body={
                "sequential_image_generation": "auto",
                "sequential_image_generation_options": {
                    "max_images": 4 
                }
            }
        )
        
        images = []
        if completion.data:
            for item in completion.data:
                if item.url:
                    images.append(item.url)
        
        if not images:
             logger.warning(f"API返回成功但无图片数据")
             
        return images

    except Exception as e:
        logger.error(f"海报生成服务异常: {e}")
        # 抛出更友好的错误信息
        raise Exception(f"海报生成服务异常: {str(e)}")


def save_temp_images(image_urls, request=None):
    """
    保存临时图片到本地 media/cover/tmp 目录
    
    Args:
        image_urls (list): 图片URL列表
        request (HttpRequest): 请求对象，用于构建绝对URL
        
    Returns:
        list: 本地图片URL列表
    """
    if not image_urls:
        return []
        
    # 确保临时目录存在
    temp_rel_dir = os.path.join('cover', 'tmp')
    temp_dir = os.path.join(settings.MEDIA_ROOT, temp_rel_dir)
    os.makedirs(temp_dir, exist_ok=True)
    
    batch_id = uuid.uuid4().hex
    local_urls = []
    
    for idx, url in enumerate(image_urls):
        try:
            # 下载图片
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                # 保存到临时文件
                file_name = f"{batch_id}_{idx}.png"
                file_path = os.path.join(temp_dir, file_name)
                
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                
                # 构建本地URL
                # 使用正斜杠构建相对路径，确保URL格式正确
                relative_path = f"cover/tmp/{file_name}"
                # 使用 common_utils 中的 build_media_url 构建完整 URL
                local_url = build_media_url(relative_path, request)
                local_urls.append(local_url)
            else:
                logger.error(f"Failed to download image from {url}, status: {response.status_code}")
        except Exception as e:
            logger.error(f"Exception downloading image from {url}: {e}")
            
    return local_urls
