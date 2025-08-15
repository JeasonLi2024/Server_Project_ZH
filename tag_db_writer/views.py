from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .db_writer import insert_general_match
import json

@csrf_exempt
@require_http_methods(["POST"])
def general_match_view(request):
    try:
        data = json.loads(request.body)
        match_type = data.get('match_type')
        data_list = data.get('data_list')
        
        if not match_type or not data_list:
            return JsonResponse({
                'success': False,
                'message': '缺少必要参数: match_type 或 data_list'
            }, status=400)
        
        insert_general_match(match_type, data_list)
        
        return JsonResponse({
            'success': True,
            'message': f'成功处理 {len(data_list)} 条数据'
        })
        
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'处理失败: {str(e)}'
        }, status=500)
