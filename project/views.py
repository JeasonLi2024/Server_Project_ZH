from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from common_utils import APIResponse
from .models import Project, ProjectMember
from .serializers import (
    ProjectSerializer, ProjectCreateSerializer, ProjectUpdateSerializer,
    ProjectMemberSerializer, ProjectMemberCreateSerializer
)


class ProjectViewSet(viewsets.ModelViewSet):
    """项目视图集"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """获取查询集"""
        user = self.request.user
        # 用户可以看到自己创建的项目和参与的项目
        return Project.objects.filter(
            Q(creator=user) | Q(members=user)
        ).distinct().select_related('creator').prefetch_related('members')
    
    def get_serializer_class(self):
        """根据动作选择序列化器"""
        if self.action == 'create':
            return ProjectCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ProjectUpdateSerializer
        return ProjectSerializer
    
    def create(self, request, *args, **kwargs):
        """创建项目"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            project = serializer.save()
            project_data = ProjectSerializer(project, context={'request': request}).data
            return APIResponse.success(
                data=project_data,
                message='项目创建成功'
            )
        return APIResponse.validation_error(serializer.errors)
    
    def list(self, request, *args, **kwargs):
        """获取项目列表（支持分页）"""
        from authentication.pagination import paginate_queryset
        
        queryset = self.get_queryset()
        
        # 搜索功能
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )
        
        # 状态过滤
        is_active = request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # 角色过滤
        role = request.query_params.get('role')
        if role:
            project_ids = ProjectMember.objects.filter(
                user=request.user, role=role
            ).values_list('project_id', flat=True)
            queryset = queryset.filter(id__in=project_ids)
        
        # 按创建时间倒序排列
        queryset = queryset.order_by('-created_at')
        
        # 使用分页功能（默认每页10个项目）
        paginated_data = paginate_queryset(request, queryset, default_page_size=10)
        page_data = paginated_data['page_data']
        pagination_info = paginated_data['pagination_info']
        
        # 序列化数据
        serializer = self.get_serializer(page_data, many=True)
        
        # 返回分页数据
        response_data = {
            'results': serializer.data,
            'pagination': pagination_info,
            'search': search  # 添加搜索关键词到响应中
        }
        
        return APIResponse.success(
            data=response_data,
            message='获取项目列表成功'
        )
    
    def retrieve(self, request, *args, **kwargs):
        """获取项目详情"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return APIResponse.success(
            data=serializer.data,
            message='获取项目详情成功'
        )
    
    def update(self, request, *args, **kwargs):
        """更新项目"""
        instance = self.get_object()
        
        # 检查权限：只有项目所有者和管理员可以更新
        member = ProjectMember.objects.filter(
            project=instance, user=request.user, role__in=['owner', 'admin']
        ).first()
        
        if not member:
            return APIResponse.error(
                message='您没有权限修改此项目',
                code=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            project = serializer.save()
            project_data = ProjectSerializer(project, context={'request': request}).data
            return APIResponse.success(
                data=project_data,
                message='项目更新成功'
            )
        return APIResponse.validation_error(serializer.errors)
    
    def destroy(self, request, *args, **kwargs):
        """删除项目"""
        instance = self.get_object()
        
        # 检查权限：只有项目所有者可以删除
        member = ProjectMember.objects.filter(
            project=instance, user=request.user, role='owner'
        ).first()
        
        if not member:
            return APIResponse.error(
                message='只有项目所有者可以删除项目',
                code=status.HTTP_403_FORBIDDEN
            )
        
        instance.delete()
        return APIResponse.success(message='项目删除成功')
    
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """获取项目成员列表"""
        project = self.get_object()
        members = ProjectMember.objects.filter(project=project).select_related('user')
        serializer = ProjectMemberSerializer(members, many=True)
        return APIResponse.success(
            data=serializer.data,
            message='获取项目成员成功'
        )
    
    @action(detail=True, methods=['post'])
    def add_member(self, request, pk=None):
        """添加项目成员"""
        project = self.get_object()
        
        # 检查权限：只有项目所有者和管理员可以添加成员
        member = ProjectMember.objects.filter(
            project=project, user=request.user, role__in=['owner', 'admin']
        ).first()
        
        if not member:
            return APIResponse.error(
                message='您没有权限添加项目成员',
                code=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ProjectMemberCreateSerializer(
            data=request.data,
            context={'project': project}
        )
        
        if serializer.is_valid():
            member = serializer.save()
            member_data = ProjectMemberSerializer(member).data
            return APIResponse.success(
                data=member_data,
                message='成员添加成功'
            )
        return APIResponse.validation_error(serializer.errors)
    
    @action(detail=True, methods=['delete'])
    def remove_member(self, request, pk=None):
        """移除项目成员"""
        project = self.get_object()
        user_id = request.data.get('user_id')
        
        if not user_id:
            return APIResponse.error(message='请提供用户ID')
        
        # 检查权限：只有项目所有者和管理员可以移除成员
        current_member = ProjectMember.objects.filter(
            project=project, user=request.user, role__in=['owner', 'admin']
        ).first()
        
        if not current_member:
            return APIResponse.error(
                message='您没有权限移除项目成员',
                code=status.HTTP_403_FORBIDDEN
            )
        
        # 获取要移除的成员
        target_member = ProjectMember.objects.filter(
            project=project, user_id=user_id
        ).first()
        
        if not target_member:
            return APIResponse.error(message='该用户不是项目成员')
        
        # 不能移除项目所有者
        if target_member.role == 'owner':
            return APIResponse.error(message='不能移除项目所有者')
        
        # 管理员不能移除其他管理员（只有所有者可以）
        if (current_member.role == 'admin' and 
            target_member.role == 'admin' and 
            current_member.user != target_member.user):
            return APIResponse.error(message='管理员不能移除其他管理员')
        
        target_member.delete()
        return APIResponse.success(message='成员移除成功')
    
    @action(detail=True, methods=['patch'])
    def update_member_role(self, request, pk=None):
        """更新成员角色"""
        project = self.get_object()
        user_id = request.data.get('user_id')
        new_role = request.data.get('role')
        
        if not user_id or not new_role:
            return APIResponse.error(message='请提供用户ID和新角色')
        
        # 检查权限：只有项目所有者可以更新成员角色
        current_member = ProjectMember.objects.filter(
            project=project, user=request.user, role='owner'
        ).first()
        
        if not current_member:
            return APIResponse.error(
                message='只有项目所有者可以更新成员角色',
                code=status.HTTP_403_FORBIDDEN
            )
        
        # 获取要更新的成员
        target_member = ProjectMember.objects.filter(
            project=project, user_id=user_id
        ).first()
        
        if not target_member:
            return APIResponse.error(message='该用户不是项目成员')
        
        # 不能修改所有者角色
        if target_member.role == 'owner':
            return APIResponse.error(message='不能修改项目所有者的角色')
        
        # 验证新角色
        valid_roles = ['admin', 'member', 'viewer']
        if new_role not in valid_roles:
            return APIResponse.error(message='无效的角色')
        
        target_member.role = new_role
        target_member.save()
        
        member_data = ProjectMemberSerializer(target_member).data
        return APIResponse.success(
            data=member_data,
            message='成员角色更新成功'
        )
    
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """离开项目"""
        project = self.get_object()
        
        member = ProjectMember.objects.filter(
            project=project, user=request.user
        ).first()
        
        if not member:
            return APIResponse.error(message='您不是该项目的成员')
        
        # 项目所有者不能离开项目
        if member.role == 'owner':
            return APIResponse.error(message='项目所有者不能离开项目，请先转让所有权或删除项目')
        
        member.delete()
        return APIResponse.success(message='已成功离开项目')