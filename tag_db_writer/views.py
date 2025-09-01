# from django.http import JsonResponse
# from django.views.decorators.csrf import csrf_exempt
# from django.views.decorators.http import require_http_methods
# from .db_writer import insert_general_match
# import json

# @csrf_exempt
# @require_http_methods(["POST"])
# def general_match_view(request):
    # try:
    #     data = json.loads(request.body)
    #     match_type = data.get('match_type')
    #     data_list = data.get('data_list')
        
    #     if not match_type or not data_list:
    #         return JsonResponse({
    #             'success': False,
    #             'message': '缺少必要参数: match_type 或 data_list'
    #         }, status=400)
        
    #     insert_general_match(match_type, data_list)
        
    #     return JsonResponse({
    #         'success': True,
    #         'message': f'成功处理 {len(data_list)} 条数据'
    #     })
        
    # except ValueError as e:
    #     return JsonResponse({
    #         'success': False,
    #         'message': str(e)
    #     }, status=400)
    # except Exception as e:
    #     return JsonResponse({
    #         'success': False,
    #         'message': f'处理失败: {str(e)}'
    #     }, status=500)
    # try:
    #     # 解析请求体 JSON
    #     body_unicode = request.body.decode("utf-8")
    #     data = json.loads(body_unicode)

    #     # 基本参数校验
    #     if "match_type" not in data or "data" not in data:
    #         return JsonResponse({"error": "缺少 match_type 或 data 字段"}, status=400)

    #     if not isinstance(data["data"], list):
    #         return JsonResponse({"error": "data 字段必须是列表"}, status=400)

    #     # 调用主逻辑函数
    #     insert_match_from_json(data)

    #     return JsonResponse({"message": "插入成功"}, status=200)

    # except json.JSONDecodeError:
    #     return JsonResponse({"error": "请求体不是合法的 JSON"}, status=400)
    # except Exception as e:
    #     return JsonResponse({"error": str(e)}, status=500)

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .db_writer import insert_match_from_json
import json
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["POST"])
def general_match_view(request):
    """
    处理标签匹配数据的API接口
    
    请求格式:
    {
        "match_type": "tag1_student",
        "data": [
            {"student_id": 1, "tag1_id": [3, 5, 7]},
            {"student_id": 2, "tag1_id": 4}
        ]
    }
    """
    try:
        # 解析请求体 JSON
        body_unicode = request.body.decode("utf-8")
        data = json.loads(body_unicode)
        
        # 记录请求日志
        logger.info(f"接收到标签匹配请求: match_type={data.get('match_type')}, data_count={len(data.get('data', []))}")
        
        # 基本参数校验
        if "match_type" not in data or "data" not in data:
            return JsonResponse({
                "success": False,
                "error": "缺少 match_type 或 data 字段"
            }, status=400)
        
        if not isinstance(data["data"], list):
            return JsonResponse({
                "success": False,
                "error": "data 字段必须是列表"
            }, status=400)
        
        if not data["data"]:
            return JsonResponse({
                "success": False,
                "error": "data 列表不能为空"
            }, status=400)
        
        # 调用主逻辑函数
        insert_match_from_json(data)
        
        # 记录成功日志
        logger.info(f"标签匹配处理成功: match_type={data['match_type']}, processed_count={len(data['data'])}")
        
        return JsonResponse({
            "success": True,
            "message": f"成功处理 {len(data['data'])} 条数据",
            "match_type": data["match_type"],
            "processed_count": len(data["data"])
        }, status=200)
    
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析错误: {str(e)}")
        return JsonResponse({
            "success": False,
            "error": "请求体不是合法的 JSON"
        }, status=400)
    
    except ValueError as e:
        logger.error(f"数据验证错误: {str(e)}")
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=400)
    
    except Exception as e:
        logger.error(f"处理标签匹配时发生未知错误: {str(e)}", exc_info=True)
        return JsonResponse({
            "success": False,
            "error": f"处理失败: {str(e)}"
        }, status=500)   
