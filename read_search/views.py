# read_search/views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from .read_search import search_in_milvus, get_mysql_data
from .services import search_service, cache_service
from .milvus_manager import milvus_manager
import logging

logger = logging.getLogger(__name__) 


@csrf_exempt
@require_http_methods(["POST"])
def search_api(request):
    """学生标签匹配初筛API - 根据学生ID获取匹配的项目需求并进行向量搜索"""

    try:
        body = json.loads(request.body.decode("utf-8"))
        query = body.get("query")
        sid = body.get("sid")

        if not query or not sid:
            return JsonResponse({"error": "Missing query or sid"}, status=400)

        try:
            sid_int = int(sid)
        except ValueError:
            return JsonResponse({"error": "sid must be a valid integer"}, status=400)

        # 1. 使用SearchService获取学生匹配的项目需求ID列表
        requirement_ids = search_service.get_requirement_ids_for_student(sid_int)
        logger.info(f"学生{sid_int}匹配到{len(requirement_ids)}个项目需求")

        if not requirement_ids:
            return JsonResponse({
                "results": [],
                "message": "该学生暂无匹配的项目需求"
            }, json_dumps_params={"ensure_ascii": False})

        # 2. 使用向量搜索进行查询
        results = search_in_milvus(query, requirement_ids, top_k=5)

        return JsonResponse({
            "results": results
        }, json_dumps_params={"ensure_ascii": False})

    except Exception as e:
        logger.error(f"搜索API错误: {e}")
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def search_api_v2(request):
    """优化后的搜索API，统一使用POST方法"""
    try:
        data = json.loads(request.body)
        query = data.get('query', '')
        pid = data.get('Pid', '')
        
        if not query or not pid:
            return JsonResponse({'error': '缺少必要参数 query 或 Pid'}, status=400)
        
        try:
            pid_int = int(pid)
        except ValueError:
            return JsonResponse({'error': 'Pid 必须是有效的整数'}, status=400)
        
        # 使用向量搜索进行查询
        requirement_ids = [str(pid_int)]
        results = search_in_milvus(query, requirement_ids, top_k=5)
        
        # 转换为search_api_v2期望的格式
        output = []
        for result in results:
            output.append({
                "id": pid_int,
                "id_chunk": result.get("id_chunk", 0),
                "content": result.get("content", "")
            })
        results = output
        
        return JsonResponse({
            "results": results
        }, json_dumps_params={"ensure_ascii": False})
        
    except Exception as e:
        logger.error(f"搜索API错误: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def clear_cache_api(request):
    """清除缓存的API"""
    try:
        data = json.loads(request.body)
        cache_type = data.get('cache_type', 'all')  # 'student', 'milvus', 'all'
        student_id = data.get('student_id')
        
        success_messages = []
        
        if cache_type in ['student', 'all'] and student_id:
            # 清除学生相关缓存（已禁用缓存）
            if search_service.clear_student_cache(student_id):
                success_messages.append(f"学生{student_id}缓存（已禁用，无需清除）")
        
        if cache_type in ['milvus', 'all']:
            # 清除Milvus搜索缓存
            from django.core.cache import cache
            cache.clear()
            success_messages.append("Milvus搜索缓存")
        
        if not success_messages:
            return JsonResponse({
                'status': 'warning',
                'message': '没有指定有效的缓存清除操作'
            })
        
        return JsonResponse({
            'status': 'success',
            'message': f'已清除: {", ".join(success_messages)}',
            'cache_type': cache_type
        })
        
    except Exception as e:
        logger.error(f"清除缓存API错误: {e}")
        return JsonResponse({'error': str(e)}, status=500)