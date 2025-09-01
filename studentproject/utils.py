import os
from django.conf import settings
from django.core.files.storage import default_storage
from project.models import File


def ensure_virtual_folder_exists(project, folder_name):
    """确保虚拟文件夹存在，如果不存在则创建"""
    # 统一使用File模型来处理虚拟文件夹
    return ensure_file_folder_exists(folder_name)


def ensure_file_folder_exists(folder_path):
    """确保File模型的虚拟文件夹存在"""

    if folder_path == '/' or not folder_path:
        return

    # 规范化路径
    folder_path = folder_path.strip('/')
    if not folder_path:
        return

    # 分解路径
    path_parts = folder_path.split('/')
    current_path = '/'

    for part in path_parts:
        if not part:
            continue

        parent_path = current_path
        current_path = os.path.join(current_path, part).replace('\\', '/')

        # 检查文件夹是否存在
        if not File.objects.filter(path=current_path, is_folder=True).exists():
            File.objects.create(
                name=part,
                path=current_path,
                parent_path=parent_path,
                is_folder=True,
                is_cloud_link=False,
                size=0
            )


def handle_cloud_links(cloud_links_data, deliverable):
    """处理网盘链接数据"""
    from .models import CloudLink

    if cloud_links_data:
        # 清除现有的网盘链接
        deliverable.cloud_links.all().delete()

        # 创建新的网盘链接
        for link_data in cloud_links_data:
            CloudLink.objects.create(
                deliverable=deliverable,
                platform=link_data.get('platform', ''),
                url=link_data.get('url', ''),
                access_code=link_data.get('access_code', ''),
                description=link_data.get('description', '')
            )


def get_file_upload_path(instance, filename):
    """生成文件上传路径"""
    if hasattr(instance, 'deliverable') and instance.deliverable:
        project_id = instance.deliverable.project.id
        return f'projects/{project_id}/deliverables/{filename}'
    elif hasattr(instance, 'project'):
        project_id = instance.project.id
        return f'projects/{project_id}/{filename}'
    return f'uploads/{filename}'


def validate_file_size(file, max_size_mb=50):
    """验证文件大小"""
    if file.size > max_size_mb * 1024 * 1024:
        raise ValueError(f'文件大小不能超过 {max_size_mb}MB')
    return True


def validate_file_type(file, allowed_types=None):
    """验证文件类型"""
    if allowed_types is None:
        allowed_types = ['.pdf', '.doc', '.docx', '.txt', '.zip', '.rar']

    file_ext = os.path.splitext(file.name)[1].lower()
    if file_ext not in allowed_types:
        raise ValueError(f'不支持的文件类型: {file_ext}')
    return True