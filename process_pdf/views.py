import os
import tempfile
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

# 导入PDF处理函数
from .pdf_chunk_milvus import process_pdf

@csrf_exempt
def upload_pdf(request):
    """
    处理PDF上传并进行向量化存储
    
    请求参数:
    - pid: 项目ID或文档ID，用于在Milvus中标识该文档
    - pdf: PDF文件
    
    返回:
    - status: 处理状态 (success/error)
    - pid: 项目ID
    - chunks: 分块数量
    - error: 错误信息(如果有)
    """
    if request.method != "POST":
        return JsonResponse({"error": "只允许POST方法"}, status=405)

    pid = request.POST.get("pid")
    pdf_file = request.FILES.get("pdf")

    if not pid or not pdf_file:
        return JsonResponse({"error": "缺少pid或pdf文件"}, status=400)

    # DEBUG: 打印接收到的文件信息
    print(f"[DEBUG]接收到的文件:{pdf_file.name}，大小={pdf_file.size}")

    # 创建临时文件保存上传的PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        for chunk in pdf_file.chunks():
            tmp.write(chunk)
        tmp_path = tmp.name
    
    # DEBUG: 打印保存路径信息
    print(f"[DEBUG]保存路径:{tmp_path}，是否存在:{os.path.exists(tmp_path)}")

    try:
        # 调用PDF处理函数
        result = process_pdf(tmp_path, int(pid))
        # 处理完成后删除临时文件
        os.remove(tmp_path)
        return JsonResponse({"status": "success", **result})
    except Exception as e:
        # 发生错误时也要删除临时文件
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return JsonResponse({"error": str(e)}, status=500)
