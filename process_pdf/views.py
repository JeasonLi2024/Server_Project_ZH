import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.files.storage import default_storage

# 导入PDF处理函数
from .pdf_chunk_milvus import process_pdf
# 导入相关模型和函数
from project.models import File, Requirement, get_requirement_file_path, generate_unique_filename

@csrf_exempt
def upload_pdf(request):
    """
    处理PDF上传并进行向量化存储
    
    请求参数:
    - pid: 项目需求ID，用于在Milvus中标识该文档
    - pdf: PDF文件
    
    返回:
    - status: 处理状态 (success/error)
    - pid: 项目需求ID
    - chunks: 分块数量
    - file_id: 保存的文件ID
    - error: 错误信息(如果有)
    """
    if request.method != "POST":
        return JsonResponse({"error": "只允许POST方法"}, status=405)

    pid = request.POST.get("pid")
    pdf_file = request.FILES.get("pdf")

    if not pid or not pdf_file:
        return JsonResponse({"error": "缺少pid或pdf文件"}, status=400)

    try:
        # 验证需求是否存在
        requirement = Requirement.objects.get(id=int(pid))
    except (ValueError, Requirement.DoesNotExist):
        return JsonResponse({"error": "无效的需求ID"}, status=400)

    # DEBUG: 打印接收到的文件信息
    print(f"[DEBUG]接收到的文件:{pdf_file.name}，大小={pdf_file.size}")

    try:
        # 生成唯一文件名和保存路径
        file_path = get_requirement_file_path(pid, pdf_file.name)
        
        # 保存文件到指定目录
        saved_path = default_storage.save(file_path, pdf_file)
        full_file_path = os.path.join(settings.MEDIA_ROOT, saved_path)
        
        # DEBUG: 打印保存路径信息
        print(f"[DEBUG]保存路径:{full_file_path}，是否存在:{os.path.exists(full_file_path)}")
        
        # 创建File模型记录
        file_obj = File.objects.create(
            name=pdf_file.name,
            path=f"/需求文档/{requirement.title}/{pdf_file.name}",  # 虚拟路径
            real_path=saved_path,  # 实际存储路径
            parent_path=f"/需求文档/{requirement.title}",  # 父级虚拟路径
            is_folder=False,
            is_cloud_link=False,
            size=pdf_file.size
        )
        
        # 将文件关联到需求
        requirement.files.add(file_obj)
        
        # 调用PDF处理函数
        result = process_pdf(full_file_path, int(pid))
        
        # 添加文件ID到返回结果
        result["file_id"] = file_obj.id
        
        return JsonResponse({"status": "success", **result})
        
    except Exception as e:
        # 发生错误时删除已保存的文件
        try:
            if 'saved_path' in locals():
                default_storage.delete(saved_path)
            if 'file_obj' in locals():
                file_obj.delete()
        except:
            pass
        
        return JsonResponse({"error": str(e)}, status=500)
