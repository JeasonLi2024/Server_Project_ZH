from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.core.files.storage import default_storage
from django.conf import settings
from django.db import transaction
from django.http import Http404
from .models import File, Requirement, Resource, generate_unique_filename, create_virtual_folder, parse_file_path_structure
from .serializers import FileSerializer
from user.models import OrganizationUser
from organization.models import Organization
from studentproject.models import ProjectDeliverable, StudentProject, ProjectParticipant
from common_utils import build_media_url, APIResponse
import os
import uuid
import json


class VirtualFileViewSet(viewsets.ModelViewSet):
    """
    虚拟文件系统视图集
    
    提供完整的文件管理功能：
    - 文件上传
    - 文件列表获取
    - 文件详情查看
    - 文件夹创建
    - 文件/文件夹重命名
    - 文件/文件夹移动
    - 文件/文件夹删除
    - 文件树结构获取
    - 面包屑导航
    """
    
    serializer_class = FileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """获取查询集，根据requirement_id、resource_id或deliverable_id过滤"""
        requirement_id = self.request.query_params.get('requirement_id')
        resource_id = self.request.query_params.get('resource_id')
        deliverable_id = self.request.query_params.get('deliverable_id')
        
        if requirement_id:
            try:
                requirement = Requirement.objects.get(id=requirement_id)
                return requirement.files.all()
            except Requirement.DoesNotExist:
                return File.objects.none()
        elif resource_id:
            try:
                resource = Resource.objects.get(id=resource_id)
                return resource.files.all()
            except Resource.DoesNotExist:
                return File.objects.none()
        elif deliverable_id:
            try:
                deliverable = ProjectDeliverable.objects.get(id=deliverable_id)
                return deliverable.files.all()
            except ProjectDeliverable.DoesNotExist:
                return File.objects.none()
        else:
            return File.objects.none()
    
    def list(self, request, *args, **kwargs):
        """获取文件列表"""
        requirement_id = request.query_params.get('requirement_id')
        resource_id = request.query_params.get('resource_id')
        deliverable_id = request.query_params.get('deliverable_id')
        path = request.query_params.get('parent_path', '/')
        file_type = request.query_params.get('file_type')
        search = request.query_params.get('search')
        
        # 验证参数
        param_count = sum([bool(requirement_id), bool(resource_id), bool(deliverable_id)])
        if param_count == 0:
            return APIResponse.error(
                message="必须指定requirement_id、resource_id或deliverable_id中的一个",
                code=400,
                errors={"parameter": ["requirement_id、resource_id和deliverable_id不能同时为空"]}
            )
        
        if param_count > 1:
            return APIResponse.error(
                message="只能指定requirement_id、resource_id或deliverable_id中的一个",
                code=400,
                errors={"parameter": ["requirement_id、resource_id和deliverable_id不能同时指定"]}
            )
        
        # 权限检查
        if not self._check_permission(requirement_id, resource_id, deliverable_id, 'read'):
            return APIResponse.forbidden(
                message="您没有权限访问此文件系统"
            )
        
        # 获取文件列表
        queryset = self.get_queryset()
        
        # 文件类型过滤（按文件后缀名）
        if file_type:
            if file_type == 'folder':
                queryset = queryset.filter(is_folder=True)
                # 对于文件夹类型，仍然需要路径过滤
                if path and path != '/':
                    path = path.rstrip('/')
                    queryset = queryset.filter(parent_path=path)
                else:
                    # 筛选根目录文件夹
                    from django.db.models import Q
                    queryset = queryset.filter(
                        Q(parent_path='') | Q(parent_path='/') | 
                        Q(parent_path__isnull=True) | Q(parent_path='None')
                    )
            else:
                # 按文件后缀名筛选，只筛选非文件夹的文件
                # 当指定文件类型时，搜索所有路径下的该类型文件，不限制路径
                queryset = queryset.filter(is_folder=False, name__iendswith=f'.{file_type}')
        else:
             # 没有指定文件类型时，进行路径过滤
             if path and path != '/':
                 path = path.rstrip('/')
                 queryset = queryset.filter(parent_path=path)
             # 如果path为'/'且明确指定了parent_path参数，显示根目录文件和文件夹
             elif path == '/' and 'parent_path' in request.query_params:
                 # 筛选根目录文件，包含空字符串、'/'、None值和'None'字符串
                 from django.db.models import Q
                 queryset = queryset.filter(
                     Q(parent_path='') | Q(parent_path='/') | 
                     Q(parent_path__isnull=True) | Q(parent_path='None')
                 )
             # 如果没有明确指定parent_path参数，返回所有文件
             # else: 不进行路径过滤，返回所有文件
        
        # 搜索过滤
        if search:
            # 当使用搜索时，搜索所有路径下的文件，不限制路径
            queryset = self.get_queryset().filter(name__icontains=search)
        
        # 排序
        queryset = queryset.order_by('is_folder', 'name')
        
        serializer = self.get_serializer(queryset, many=True)
        
        return APIResponse.success(
            data=serializer.data,
            message="操作成功"
        )
    
    def retrieve(self, request, *args, **kwargs):
        """获取单个文件详情"""
        try:
            pk = kwargs.get('pk')
            instance = File.objects.get(pk=pk)
        except File.DoesNotExist:
            return APIResponse.not_found(
                message="文件不存在"
            )
        
        # 所有认证用户都可以访问文件详情，无需额外权限验证
        # 用户认证已在视图集级别通过authentication_classes处理
        
        serializer = self.get_serializer(instance)
        return APIResponse.success(
            data=serializer.data,
            message="操作成功"
        )
    
    @action(detail=False, methods=['delete'])
    def file_delete(self, request, *args, **kwargs):
        """批量删除文件或文件夹"""
        
        # 获取要删除的文件ID列表，支持从请求体或查询参数获取
        file_ids = request.data.get('file_ids', []) or request.query_params.get('file_ids', [])
        if not file_ids:
            return APIResponse.error(
                message="必须指定要删除的文件ID",
                code=400,
                errors={"parameter": ["file_ids不能为空"]}
            )
        
        # 处理file_ids格式：支持列表、单个值或逗号分隔的字符串
        if isinstance(file_ids, str):
            # 如果是字符串，按逗号分割
            file_ids = [id.strip() for id in file_ids.split(',') if id.strip()]
        elif not isinstance(file_ids, list):
            # 如果不是列表也不是字符串，转为列表
            file_ids = [file_ids]
        
        # 转换为整数列表
        try:
            file_ids = [int(id) for id in file_ids]
        except (ValueError, TypeError):
            return APIResponse.error(
                message="文件ID格式错误，必须为数字",
                code=400,
                errors={"parameter": ["file_ids必须为数字或数字列表"]}
            )
        
        # 获取文件列表
        files_to_delete = File.objects.filter(id__in=file_ids)
        
        if not files_to_delete.exists():
            return APIResponse.not_found(
                message="未找到要删除的文件"
            )
        
        # 检查是否所有文件都存在
        found_ids = set(files_to_delete.values_list('id', flat=True))
        requested_ids = set(file_ids)
        missing_ids = requested_ids - found_ids
        
        if missing_ids:
            return APIResponse.error(
                message=f"文件不存在: {list(missing_ids)}",
                code=404,
                errors={"not_found": [f"文件ID {list(missing_ids)} 不存在"]}
            )
        
        # 权限检查：检查用户是否有权限删除这些文件
        user = request.user
        for file_obj in files_to_delete:
            has_permission = False
            
            # 检查需求相关的文件权限
            if file_obj.requirement_set.exists():
                for requirement in file_obj.requirement_set.all():
                    if self._check_permission(requirement.id, None, None, 'write'):
                        has_permission = True
                        break
            
            # 检查资源相关的文件权限
            if not has_permission and file_obj.resource_set.exists():
                for resource in file_obj.resource_set.all():
                    if self._check_permission(None, resource.id, None, 'write'):
                        has_permission = True
                        break
            
            # 检查成果相关的文件权限
            if not has_permission and file_obj.deliverables.exists():
                for deliverable in file_obj.deliverables.all():
                    if self._check_permission(None, None, deliverable.id, 'write'):
                        has_permission = True
                        break
            
            if not has_permission:
                return APIResponse.forbidden(
                    message=f"您没有权限删除文件: {file_obj.name}"
                )
        
        deleted_files = []
        failed_files = []
        
        try:
            with transaction.atomic():
                for instance in files_to_delete:
                    try:
                        # 获取文件信息用于响应
                        file_info = {
                            "id": instance.id,
                            "name": instance.name,
                            "path": instance.path,
                            "size": instance.size,
                            "url": instance.url,
                            "is_folder": instance.is_folder,
                            "created_at": instance.created_at
                        }
                        
                        # 如果是文件夹，递归删除所有子文件
                        if instance.is_folder:
                            self._delete_folder_recursive(instance)
                        else:
                            # 删除实际文件
                            if instance.real_path and default_storage.exists(instance.real_path):
                                default_storage.delete(instance.real_path)
                        
                        # 删除数据库记录
                        instance.delete()
                        deleted_files.append(file_info)
                        
                    except Exception as e:
                        failed_files.append({
                            "id": instance.id,
                            "name": instance.name,
                            "error": str(e)
                        })
                
                # 如果有文件被成功删除，更新相关对象的updated_at字段和修改者信息
                if deleted_files:
                    from django.utils import timezone
                    
                    # 获取所有被删除文件关联的对象
                    updated_objects = set()
                    
                    for file_info in deleted_files:
                        # 查找关联的需求、资源和项目成果
                        from project.models import Requirement, Resource
                        from studentproject.models import ProjectDeliverable
                        
                        # 查找关联的需求
                        requirements = Requirement.objects.filter(files__id=file_info['id'])
                        for req in requirements:
                            updated_objects.add(('requirement', req.id))
                        
                        # 查找关联的资源
                        resources = Resource.objects.filter(files__id=file_info['id'])
                        for res in resources:
                            updated_objects.add(('resource', res.id))
                        
                        # 查找关联的项目成果
                        deliverables = ProjectDeliverable.objects.filter(files__id=file_info['id'])
                        for deliv in deliverables:
                            updated_objects.add(('deliverable', deliv.id))
                    
                    # 更新所有相关对象
                    for obj_type, obj_id in updated_objects:
                        if obj_type == 'requirement':
                            Requirement.objects.filter(id=obj_id).update(updated_at=timezone.now())
                        elif obj_type == 'resource':
                            Resource.objects.filter(id=obj_id).update(updated_at=timezone.now())
                        elif obj_type == 'deliverable':
                            ProjectDeliverable.objects.filter(id=obj_id).update(
                                last_modifier=request.user.student_profile,
                                is_updated=True,
                                updated_at=timezone.now()
                            )
            
            # 构建响应
            response_data = {
                "deleted_count": len(deleted_files),
                "failed_count": len(failed_files),
                "deleted_files": deleted_files
            }
            
            if failed_files:
                response_data["failed_files"] = failed_files
                message = f"部分删除成功，成功删除{len(deleted_files)}个文件，失败{len(failed_files)}个文件"
            else:
                message = f"成功删除{len(deleted_files)}个文件"
            
            return APIResponse.success(
                data=response_data,
                message=message
            )
            
        except Exception as e:
            return APIResponse.error(
                message=f"删除失败: {str(e)}",
                code=500,
                errors={"delete": [str(e)]}
            )
    
    @action(detail=False, methods=['post'])
    def upload_file(self, request):
        """上传文件"""
        requirement_id = request.query_params.get('requirement_id')
        resource_id = request.query_params.get('resource_id')
        deliverable_id = request.query_params.get('deliverable_id')
        
        # 验证参数
        param_count = sum([bool(requirement_id), bool(resource_id), bool(deliverable_id)])
        if param_count == 0:
            return APIResponse.error(
                message="必须指定requirement_id、resource_id或deliverable_id中的一个",
                code=400,
                errors={"parameter": ["requirement_id、resource_id和deliverable_id不能同时为空"]}
            )
        
        if param_count > 1:
            return APIResponse.error(
                message="只能指定requirement_id、resource_id或deliverable_id中的一个",
                code=400,
                errors={"parameter": ["requirement_id、resource_id和deliverable_id不能同时指定"]}
            )
        
        # 权限检查
        if not self._check_permission(requirement_id, resource_id, deliverable_id, 'write'):
            return APIResponse.forbidden(
                message="您没有权限上传文件"
            )
        
        # 获取上传的文件
        files = request.FILES.getlist('files')
        if not files:
            return APIResponse.error(
                message="没有上传文件",
                code=400,
                errors={"files": ["请选择要上传的文件"]}
            )
        
        # 获取虚拟路径
        virtual_path = request.data.get('virtual_folder_path', '/')
        if not virtual_path.startswith('/'):
            virtual_path = '/' + virtual_path
        if not virtual_path.endswith('/'):
            virtual_path += '/'
        
        uploaded_files = []
        
        try:
            with transaction.atomic():
                # 获取目标对象
                target_obj = None
                if requirement_id:
                    target_obj = get_object_or_404(Requirement, id=requirement_id)
                elif resource_id:
                    target_obj = get_object_or_404(Resource, id=resource_id)
                else:
                    target_obj = get_object_or_404(ProjectDeliverable, id=deliverable_id)
                
                for uploaded_file in files:
                    # 生成唯一文件名
                    unique_filename = generate_unique_filename(uploaded_file.name)
                    
                    # 构建存储路径
                    if requirement_id:
                        storage_path = f'uploads/files/requirement/{unique_filename}'
                    elif resource_id:
                        storage_path = f'uploads/files/resource/{unique_filename}'
                    else:
                        storage_path = f'uploads/files/deliverable/{unique_filename}'
                    
                    # 保存文件
                    saved_path = default_storage.save(storage_path, uploaded_file)
                    
                    # 构建虚拟路径
                    file_virtual_path = virtual_path.rstrip('/') + '/' + uploaded_file.name
                    if file_virtual_path.startswith('//'):
                        file_virtual_path = file_virtual_path[1:]
                    
                    # 构建父级路径
                    parent_path = virtual_path.rstrip('/')
                    if not parent_path:
                        parent_path = '/'
                    
                    # 创建文件记录
                    file_obj = File.objects.create(
                        name=uploaded_file.name,
                        path=file_virtual_path,
                        real_path=saved_path,
                        parent_path=parent_path if parent_path != '/' else '',
                        is_folder=False,
                        size=uploaded_file.size,
                        url=build_media_url(saved_path, request)
                    )
                    
                    # 关联到需求或资源
                    target_obj.files.add(file_obj)
                    
                    uploaded_files.append({
                        "id": file_obj.id,
                        "name": file_obj.name,
                        "path": file_obj.path,
                        "url": file_obj.url,
                        "size": file_obj.size,
                        "is_folder": file_obj.is_folder,
                        "created_at": file_obj.created_at
                    })
                
                # 更新目标对象的updated_at字段和修改者信息
                from django.utils import timezone
                if deliverable_id:
                    # 对于项目成果，更新修改者信息
                    target_obj.last_modifier = request.user.student_profile
                    target_obj.is_updated = True
                    target_obj.updated_at = timezone.now()
                    target_obj.save(update_fields=['last_modifier', 'is_updated', 'updated_at'])
                else:
                    # 对于需求和资源，只更新updated_at
                    target_obj.updated_at = timezone.now()
                    target_obj.save(update_fields=['updated_at'])
        
        except Exception as e:
            return APIResponse.error(
                message=f"文件上传失败: {str(e)}",
                code=500,
                errors={"upload": [str(e)]}
            )
        
        return APIResponse.success(
             data=uploaded_files,
             message="文件上传成功",
             code=201
         )
    
    @action(detail=False, methods=['post'])
    def create_folder(self, request):
        """创建文件夹"""
        requirement_id = request.query_params.get('requirement_id')
        resource_id = request.query_params.get('resource_id')
        deliverable_id = request.query_params.get('deliverable_id')
        
        # 验证参数
        param_count = sum([bool(requirement_id), bool(resource_id), bool(deliverable_id)])
        if param_count == 0:
            return APIResponse.error(
                message="必须指定requirement_id、resource_id或deliverable_id中的一个",
                code=400,
                errors={"parameter": ["requirement_id、resource_id和deliverable_id不能同时为空"]}
            )
        
        if param_count > 1:
            return APIResponse.error(
                message="只能指定requirement_id、resource_id或deliverable_id中的一个",
                code=400,
                errors={"parameter": ["requirement_id、resource_id和deliverable_id不能同时指定"]}
            )
        
        # 权限检查
        if not self._check_permission(requirement_id, resource_id, deliverable_id, 'write'):
            return APIResponse.forbidden(
                message="您没有权限创建文件夹"
            )
        
        folder_name = request.data.get('name')
        parent_path = request.data.get('parent_path', '/')
        
        if not folder_name:
            return APIResponse.error(
                message="文件夹名称不能为空",
                code=400,
                errors={"folder_name": ["文件夹名称是必需的"]}
            )
        
        try:
            with transaction.atomic():
                # 获取目标对象
                target_obj = None
                if requirement_id:
                    target_obj = get_object_or_404(Requirement, id=requirement_id)
                elif resource_id:
                    target_obj = get_object_or_404(Resource, id=resource_id)
                else:
                    target_obj = get_object_or_404(ProjectDeliverable, id=deliverable_id)
                
                # 构建虚拟路径
                if parent_path and parent_path != '/':
                    parent_path = parent_path.rstrip('/')
                    folder_path = f"{parent_path}/{folder_name}"
                else:
                    parent_path = ''
                    folder_path = f"/{folder_name}"
                
                # 检查文件夹是否已存在
                if target_obj.files.filter(path=folder_path, is_folder=True).exists():
                    return APIResponse.error(
                        message="文件夹已存在",
                        code=400,
                        errors={"folder_name": ["同名文件夹已存在"]}
                    )
                
                # 创建文件夹
                folder_obj = File.objects.create(
                    name=folder_name,
                    path=folder_path,
                    parent_path=parent_path,
                    is_folder=True,
                    size=0
                )
                
                # 关联到需求或资源
                target_obj.files.add(folder_obj)
                
                # 更新目标对象的updated_at字段和修改者信息
                from django.utils import timezone
                if deliverable_id:
                    # 对于项目成果，更新修改者信息
                    target_obj.last_modifier = request.user.student_profile
                    target_obj.is_updated = True
                    target_obj.updated_at = timezone.now()
                    target_obj.save(update_fields=['last_modifier', 'is_updated', 'updated_at'])
                else:
                    # 对于需求和资源，只更新updated_at
                    target_obj.updated_at = timezone.now()
                    target_obj.save(update_fields=['updated_at'])
                
                return APIResponse.success(
                     data={
                         "id": folder_obj.id,
                         "name": folder_obj.name,
                         "path": folder_obj.path,
                         "is_folder": folder_obj.is_folder,
                         "created_at": folder_obj.created_at
                     },
                     message="文件夹创建成功",
                     code=201
                 )
        
        except Exception as e:
            return APIResponse.error(
                message=f"文件夹创建失败: {str(e)}",
                code=500,
                errors={"create": [str(e)]}
            )
    
    @action(detail=True, methods=['patch'])
    def rename(self, request, pk=None):
        """重命名文件或文件夹"""
        requirement_id = request.query_params.get('requirement_id')
        resource_id = request.query_params.get('resource_id')
        deliverable_id = request.query_params.get('deliverable_id')
        
        # 验证参数
        param_count = sum([bool(requirement_id), bool(resource_id), bool(deliverable_id)])
        if param_count == 0:
            return APIResponse.error(
                message="必须指定requirement_id、resource_id或deliverable_id中的一个",
                code=400,
                errors={"parameter": ["requirement_id、resource_id和deliverable_id不能同时为空"]}
            )
        
        if param_count > 1:
            return APIResponse.error(
                message="只能指定requirement_id、resource_id或deliverable_id中的一个",
                code=400,
                errors={"parameter": ["requirement_id、resource_id和deliverable_id不能同时指定"]}
            )
        
        # 权限检查
        if not self._check_permission(requirement_id, resource_id, deliverable_id, 'write'):
            return APIResponse.forbidden(
                message="您没有权限重命名文件"
            )
        
        new_name = request.data.get('name')
        if not new_name:
            return APIResponse.error(
                message="新名称不能为空",
                code=400,
                errors={"name": ["新名称是必需的"]}
            )
        
        try:
            instance = self.get_object()
        except Http404:
            return Response({
                "status": "error",
                "code": 404,
                "message": "文件不存在",
                "data": {},
                "error": {"file": ["文件未找到"]}
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            with transaction.atomic():
                # 构建新路径
                old_path = instance.path
                parent_path = instance.parent_path or ''
                
                if parent_path:
                    new_path = f"{parent_path}/{new_name}"
                else:
                    new_path = f"/{new_name}"
                
                # 更新文件信息
                instance.name = new_name
                instance.path = new_path
                instance.save()
                
                # 如果是文件夹，需要更新所有子文件的路径
                if instance.is_folder:
                    self._update_children_paths(old_path, new_path)
                
                # 更新相关对象的updated_at字段和修改者信息
                from django.utils import timezone
                from project.models import Requirement, Resource
                from studentproject.models import ProjectDeliverable
                
                # 查找关联的需求、资源和项目成果
                requirements = Requirement.objects.filter(files=instance)
                resources = Resource.objects.filter(files=instance)
                deliverables = ProjectDeliverable.objects.filter(files=instance)
                
                # 更新需求的updated_at
                if requirements.exists():
                    requirements.update(updated_at=timezone.now())
                
                # 更新资源的updated_at
                if resources.exists():
                    resources.update(updated_at=timezone.now())
                
                # 更新项目成果的修改者信息
                if deliverables.exists():
                    deliverables.update(
                        last_modifier=request.user.student_profile,
                        is_updated=True,
                        updated_at=timezone.now()
                    )
                
                serializer = self.get_serializer(instance)
                
                return APIResponse.success(
                    data=serializer.data,
                    message="重命名成功"
                )
        
        except Exception as e:
            return APIResponse.error(
                message=f"重命名失败: {str(e)}",
                code=500,
                errors={"rename": [str(e)]}
            )
    
    @action(detail=True, methods=['post'])
    def move(self, request, pk=None):
        """移动文件或文件夹"""
        requirement_id = request.query_params.get('requirement_id')
        resource_id = request.query_params.get('resource_id')
        deliverable_id = request.query_params.get('deliverable_id')
        
        # 验证参数
        param_count = sum([bool(requirement_id), bool(resource_id), bool(deliverable_id)])
        if param_count == 0:
            return APIResponse.error(
                message="必须指定requirement_id、resource_id或deliverable_id中的一个",
                code=400,
                errors={"parameter": ["requirement_id、resource_id和deliverable_id不能同时为空"]}
            )
        
        if param_count > 1:
            return APIResponse.error(
                message="只能指定requirement_id、resource_id或deliverable_id中的一个",
                code=400,
                errors={"parameter": ["requirement_id、resource_id和deliverable_id不能同时指定"]}
            )
        
        # 权限检查
        if not self._check_permission(requirement_id, resource_id, deliverable_id, 'write'):
            return APIResponse.forbidden(
                message="您没有权限移动此文件"
            )
        
        new_path = request.data.get('parent_path')
        if new_path is None:
            return APIResponse.error(
                message="新路径不能为空",
                code=400,
                errors={"new_path": ["新路径是必需的"]}
            )
        
        try:
            instance = self.get_object()
        except Http404:
            return Response({
                "status": "error",
                "code": 404,
                "message": "文件不存在",
                "data": {},
                "error": {"file": ["文件未找到"]}
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            with transaction.atomic():
                # 构建新的完整路径
                old_path = instance.path
                new_parent_path = new_path.rstrip('/')
                if not new_parent_path:
                    new_parent_path = ''
                
                if new_parent_path:
                    new_full_path = f"{new_parent_path}/{instance.name}"
                else:
                    new_full_path = f"/{instance.name}"
                
                # 更新文件信息
                instance.path = new_full_path
                instance.parent_path = new_parent_path
                instance.save()
                
                # 如果是文件夹，需要更新所有子文件的路径
                if instance.is_folder:
                    self._update_children_paths(old_path, new_full_path)
                
                # 更新相关对象的updated_at字段和修改者信息
                from django.utils import timezone
                from project.models import Requirement, Resource
                from studentproject.models import ProjectDeliverable
                
                # 查找关联的需求、资源和项目成果
                requirements = Requirement.objects.filter(files=instance)
                resources = Resource.objects.filter(files=instance)
                deliverables = ProjectDeliverable.objects.filter(files=instance)
                
                # 更新需求的updated_at
                if requirements.exists():
                    requirements.update(updated_at=timezone.now())
                
                # 更新资源的updated_at
                if resources.exists():
                    resources.update(updated_at=timezone.now())
                
                # 更新项目成果的修改者信息
                if deliverables.exists():
                    deliverables.update(
                        last_modifier=request.user.student_profile,
                        is_updated=True,
                        updated_at=timezone.now()
                    )
                
                serializer = self.get_serializer(instance)
                
                return APIResponse.success(
                    data=serializer.data,
                    message="移动成功"
                )
        
        except Exception as e:
            return APIResponse.error(
                message=f"移动失败: {str(e)}",
                code=500,
                errors={"move": [str(e)]}
            )
    
    @action(detail=False, methods=['get'])
    def tree_structure(self, request):
        """获取文件树结构"""
        requirement_id = request.query_params.get('requirement_id')
        resource_id = request.query_params.get('resource_id')
        deliverable_id = request.query_params.get('deliverable_id')
        
        # 验证参数
        param_count = sum([bool(requirement_id), bool(resource_id), bool(deliverable_id)])
        if param_count == 0:
            return APIResponse.error(
                message="必须指定requirement_id、resource_id或deliverable_id中的一个",
                code=400,
                errors={"parameter": ["requirement_id、resource_id和deliverable_id不能同时为空"]}
            )
        
        if param_count > 1:
            return APIResponse.error(
                message="只能指定requirement_id、resource_id或deliverable_id中的一个",
                code=400,
                errors={"parameter": ["requirement_id、resource_id和deliverable_id不能同时指定"]}
            )
        
        # 权限检查
        if not self._check_permission(requirement_id, resource_id, deliverable_id, 'read'):
            return APIResponse.forbidden(
                message="您没有权限访问此文件系统"
            )
        
        # 获取所有文件
        queryset = self.get_queryset().order_by('path')
        
        # 构建树结构
        tree = self._build_tree_structure(queryset)
        
        return APIResponse.success(
            data=tree,
            message="操作成功"
        )
    
    @action(detail=False, methods=['get'])
    def breadcrumb(self, request):
        """获取面包屑导航"""
        requirement_id = request.query_params.get('requirement_id')
        resource_id = request.query_params.get('resource_id')
        deliverable_id = request.query_params.get('deliverable_id')
        path = request.query_params.get('path', '/')
        
        # 验证参数
        param_count = sum([bool(requirement_id), bool(resource_id), bool(deliverable_id)])
        if param_count == 0:
            return APIResponse.error(
                message="必须指定requirement_id、resource_id或deliverable_id中的一个",
                code=400,
                errors={"parameter": ["requirement_id、resource_id和deliverable_id不能同时为空"]}
            )
        
        if param_count > 1:
            return APIResponse.error(
                message="只能指定requirement_id、resource_id或deliverable_id中的一个",
                code=400,
                errors={"parameter": ["requirement_id、resource_id和deliverable_id不能同时指定"]}
            )
        
        # 权限检查
        if not self._check_permission(requirement_id, resource_id, deliverable_id, 'read'):
            return APIResponse.forbidden(
                message="您没有权限访问此文件系统"
            )
        
        # 构建面包屑
        breadcrumb = self._build_breadcrumb(path)
        
        return APIResponse.success(
            data=breadcrumb,
            message="操作成功"
        )
    
    @action(detail=True, methods=['get'])
    def download_url(self, request, pk=None):
        """获取文件下载链接"""
        try:
            # 获取文件对象
            file_obj = get_object_or_404(File, pk=pk)
            
            # 检查文件是否为文件夹
            if file_obj.is_folder:
                return APIResponse.error(
                    message="文件夹无法获取下载链接",
                    code=400,
                    errors={"file_type": ["指定的ID对应的是文件夹，不是文件"]}
                )
            
            # 构建下载URL
            download_url = None
            if file_obj.url:
                # 如果文件有URL字段，直接使用
                download_url = file_obj.url
            elif hasattr(file_obj, 'get_url'):
                # 如果文件有get_url方法，使用该方法
                download_url = file_obj.get_url()
            elif file_obj.file:
                # 使用Django的文件字段构建URL
                download_url = build_media_url(file_obj.file.url)
            
            # 构建响应数据
            response_data = {
                'id': file_obj.id,
                'name': file_obj.name,
                'size': file_obj.size,
                'download_url': download_url,
                'created_at': file_obj.created_at,
                'updated_at': file_obj.updated_at
            }
            
            return APIResponse.success(
                data=response_data,
                message="获取文件下载链接成功"
            )
            
        except File.DoesNotExist:
            return APIResponse.not_found(
                message="文件不存在"
            )
        except Exception as e:
            return APIResponse.server_error(
                message="获取文件下载链接失败，请稍后重试",
                errors={'exception': str(e)}
            )
    
    def _check_permission(self, requirement_id, resource_id, deliverable_id, action):
        """检查用户权限"""
        user = self.request.user
        
        if requirement_id:
            try:
                requirement = Requirement.objects.get(id=requirement_id)
                
                # 对于读操作，认证用户即可访问
                if action == 'read':
                    return True
                
                # 对于写操作，需要是需求发布者或组织管理员
                if action == 'write':
                    # 检查是否是需求发布者
                    if requirement.publish_people.user == user:
                        return True
                    
                    # 检查是否是组织所有者或管理员
                    try:
                        org_user = OrganizationUser.objects.get(
                            user=user, 
                            organization=requirement.organization
                        )
                        return org_user.role in ['owner', 'admin']
                    except OrganizationUser.DoesNotExist:
                        return False
                
            except Requirement.DoesNotExist:
                return False
        
        elif resource_id:
            try:
                resource = Resource.objects.get(id=resource_id)
                
                # 对于读操作，认证用户即可访问
                if action == 'read':
                    return True
                
                # 对于写操作，需要是资源创建者或组织管理员
                if action == 'write':
                    # 检查是否是资源创建者
                    if resource.create_person.user == user:
                        return True
                    
                    # 检查是否是组织所有者或管理员
                    try:
                        org_user = OrganizationUser.objects.get(
                            user=user, 
                            organization=resource.create_person.organization
                        )
                        return org_user.role in ['owner', 'admin']
                    except OrganizationUser.DoesNotExist:
                        return False
                
            except Resource.DoesNotExist:
                return False
        
        elif deliverable_id:
            try:
                deliverable = ProjectDeliverable.objects.get(id=deliverable_id)
                project = deliverable.project
                
                # 对于读操作，项目参与者即可访问
                if action == 'read':
                    # 检查是否是项目参与者（包括负责人和成员）
                    try:
                        participant = ProjectParticipant.objects.get(
                            project=project,
                            student__user=user,
                            status='approved'
                        )
                        return True
                    except ProjectParticipant.DoesNotExist:
                        return False
                
                # 对于写操作，需要是项目负责人或项目参与者
                if action == 'write':
                    # 检查是否是项目参与者（负责人或成员都可以管理文件）
                    try:
                        participant = ProjectParticipant.objects.get(
                            project=project,
                            student__user=user,
                            status='approved'
                        )
                        return True
                    except ProjectParticipant.DoesNotExist:
                        return False
                
            except ProjectDeliverable.DoesNotExist:
                return False
        
        return False
    
    def _delete_folder_recursive(self, folder):
        """递归删除文件夹及其所有子文件"""
        # 获取所有子文件和子文件夹
        children = File.objects.filter(parent_path=folder.path)
        
        for child in children:
            if child.is_folder:
                # 递归删除子文件夹
                self._delete_folder_recursive(child)
            else:
                # 删除实际文件
                if child.real_path and default_storage.exists(child.real_path):
                    default_storage.delete(child.real_path)
            
            # 删除数据库记录
            child.delete()
    
    def _update_children_paths(self, old_parent_path, new_parent_path):
        """更新子文件的路径"""
        children = File.objects.filter(parent_path=old_parent_path)
        
        for child in children:
            # 更新子文件的路径
            child.parent_path = new_parent_path
            child.path = f"{new_parent_path}/{child.name}"
            child.save()
            
            # 如果子文件是文件夹，递归更新其子文件
            if child.is_folder:
                old_child_path = f"{old_parent_path}/{child.name}"
                new_child_path = f"{new_parent_path}/{child.name}"
                self._update_children_paths(old_child_path, new_child_path)
    
    def _build_tree_structure(self, files):
        """构建文件树结构"""
        # 创建根节点
        tree = {
            "name": "根目录",
            "path": "/",
            "is_folder": True,
            "children": []
        }
        
        # 按路径深度排序
        files_list = list(files)
        files_list.sort(key=lambda x: x.path.count('/'))
        
        # 构建路径到节点的映射
        path_to_node = {"/": tree}
        
        for file_obj in files_list:
            node = {
                "id": file_obj.id,
                "name": file_obj.name,
                "path": file_obj.path,
                "is_folder": file_obj.is_folder,
                "created_at": file_obj.created_at
            }
            
            if not file_obj.is_folder:
                node.update({
                    "size": file_obj.size,
                    "url": file_obj.url
                })
            else:
                node["children"] = []
            
            # 找到父节点
            parent_path = file_obj.parent_path or "/"
            parent_node = path_to_node.get(parent_path)
            
            if parent_node:
                parent_node["children"].append(node)
                if file_obj.is_folder:
                    path_to_node[file_obj.path] = node
        
        return tree
    
    def _build_breadcrumb(self, path):
        """构建面包屑导航"""
        if not path or path == '/':
            return [{"name": "根目录", "path": "/"}]
        
        breadcrumb = [{"name": "根目录", "path": "/"}]
        
        # 分割路径
        parts = [part for part in path.split('/') if part]
        current_path = ""
        
        for part in parts:
            current_path += f"/{part}"
            breadcrumb.append({
                "name": part,
                "path": current_path
            })
        
        return breadcrumb