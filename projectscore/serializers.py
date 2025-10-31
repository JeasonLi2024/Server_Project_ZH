from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db.models import Sum, Max
from django.db import models
from .models import (
    EvaluationCriteria,
    EvaluationIndicator,
    ProjectEvaluation,
    IndicatorScore,
    ProjectRanking
)
from project.models import Requirement
from organization.models import Organization
from common_utils import build_media_url

User = get_user_model()


class EvaluationIndicatorSerializer(serializers.ModelSerializer):
    """评分指标序列化器"""
    
    class Meta:
        model = EvaluationIndicator
        fields = [
            'id', 'name', 'description', 'weight', 'max_score',
            'order', 'is_required'
        ]
        read_only_fields = ['id']


class EvaluationCriteriaListSerializer(serializers.ModelSerializer):
    """评分标准列表序列化器"""
    creator = serializers.SerializerMethodField()
    organization = serializers.SerializerMethodField()
    template_source_name = serializers.CharField(source='template_source.name', read_only=True)
    indicator_count = serializers.SerializerMethodField()
    total_weight = serializers.SerializerMethodField()
    clone_count = serializers.SerializerMethodField()
    can_modify = serializers.SerializerMethodField()
    is_used_by_requirements = serializers.SerializerMethodField()
    related_requirements = serializers.SerializerMethodField()
    
    class Meta:
        model = EvaluationCriteria
        fields = [
            'id', 'name', 'description', 'status', 'is_template',
            'creator', 'organization',
            'template_source_name', 'indicator_count', 'total_weight',
            'clone_count', 'can_modify', 'is_used_by_requirements',
            'related_requirements', 'created_at', 'updated_at'
        ]
    
    def get_creator(self, obj):
        """获取创建者信息"""
        if obj.creator:
            request = self.context.get('request')
            # 处理头像URL
            avatar_url = None
            if obj.creator.avatar:
                avatar_url = build_media_url(obj.creator.avatar, request)
            else:
                # 如果没有头像，使用默认头像
                from authentication.utils import get_default_avatar_url
                default_avatar_path = get_default_avatar_url()
                avatar_url = build_media_url(default_avatar_path, request)
            
            return {
                'id': obj.creator.id,
                'name': obj.creator.real_name,
                'username': obj.creator.username,
                'avatar': avatar_url
            }
        return None
    
    def get_organization(self, obj):
        """获取组织信息"""
        if obj.organization:
            return {
                'id': obj.organization.id,
                'name': obj.organization.name,
                'code': obj.organization.code
            }
        return None
    
    def get_indicator_count(self, obj):
        """获取指标数量"""
        return obj.indicators.count()
    
    def get_total_weight(self, obj):
        """获取总权重"""
        return obj.get_total_weight()
    
    def get_clone_count(self, obj):
        """获取克隆次数"""
        return obj.get_clone_count()
    
    def get_can_modify(self, obj):
        """检查是否可以修改"""
        return obj.can_be_modified()
    
    def get_is_used_by_requirements(self, obj):
        """检查是否被需求使用"""
        return obj.is_used_by_requirements()
    
    def get_related_requirements(self, obj):
        """获取关联的需求对象信息"""
        from project.models import Requirement
        requirements = Requirement.objects.filter(evaluation_criteria=obj).select_related('organization', 'publish_people__user')
        
        result = []
        for req in requirements:
            result.append({
                'id': req.id,
                'title': req.title,
                'brief': req.brief,
                'status': req.status,
                'finish_time': req.finish_time,
                'budget': req.budget,
                'people_count': req.people_count,
                'organization': {
                    'id': req.organization.id,
                    'name': req.organization.name,
                    'code': req.organization.code
                } if req.organization else None,
                'publish_people': {
                    'id': req.publish_people.id,
                    'name': req.publish_people.user.real_name,
                    'username': req.publish_people.user.username
                } if req.publish_people else None,
                'created_at': req.created_at,
                'updated_at': req.updated_at
            })
        
        return result


class EvaluationCriteriaDetailSerializer(serializers.ModelSerializer):
    """评分标准详情序列化器"""
    creator = serializers.SerializerMethodField()
    organization = serializers.SerializerMethodField()
    # requirement = serializers.SerializerMethodField()  # 已移除requirement字段
    template_source_name = serializers.CharField(source='template_source.name', read_only=True)
    indicators = EvaluationIndicatorSerializer(many=True, read_only=True)
    total_weight = serializers.SerializerMethodField()
    is_weight_complete = serializers.SerializerMethodField()
    clone_count = serializers.SerializerMethodField()
    can_modify = serializers.SerializerMethodField()
    
    class Meta:
        model = EvaluationCriteria
        fields = [
            'id', 'name', 'description', 'status', 'is_template',
            'creator', 'organization',
            'template_source_name', 'indicators', 'total_weight',
            'is_weight_complete', 'clone_count',
            'can_modify', 'created_at', 'updated_at'
        ]
    
    def get_creator(self, obj):
        """获取创建者信息"""
        if obj.creator:
            request = self.context.get('request')
            # 处理头像URL
            avatar_url = None
            if obj.creator.avatar:
                avatar_url = build_media_url(obj.creator.avatar, request)
            else:
                # 如果没有头像，使用默认头像
                from authentication.utils import get_default_avatar_url
                default_avatar_path = get_default_avatar_url()
                avatar_url = build_media_url(default_avatar_path, request)
            
            return {
                'id': obj.creator.id,
                'name': obj.creator.real_name,
                'username': obj.creator.username,
                'avatar': avatar_url
            }
        return None
    
    def get_organization(self, obj):
        """获取组织信息"""
        if obj.organization:
            return {
                'id': obj.organization.id,
                'name': obj.organization.name,
                'code': obj.organization.code
            }
        return None
    
    # def get_requirement(self, obj):
    #     """获取需求信息"""
    #     # 已移除requirement字段
    #     return None
    
    def get_total_weight(self, obj):
        """获取总权重"""
        return obj.get_total_weight()
    
    def get_is_weight_complete(self, obj):
        """检查权重是否完整"""
        return obj.is_weight_complete()
    
    def get_clone_count(self, obj):
        """获取克隆次数"""
        return obj.get_clone_count()
    
    def get_can_modify(self, obj):
        """检查是否可以修改"""
        return obj.can_be_modified()


class EvaluationCriteriaCreateSerializer(serializers.ModelSerializer):
    """评分标准创建序列化器"""
    indicators = EvaluationIndicatorSerializer(many=True, write_only=True)
    
    class Meta:
        model = EvaluationCriteria
        fields = [
            'name', 'description', 'is_template', 'indicators'
        ]
    
    # def validate_requirement(self, value):
    #     """验证需求是否存在且属于当前组织"""
    #     # 已移除requirement字段
    #     return value
    
    def validate_indicators(self, value):
        """验证评分指标"""
        if not value:
            raise serializers.ValidationError('至少需要一个评分指标')
        
        total_weight = 0
        for indicator in value:
            # 验证单个指标权重范围
            weight = indicator.get('weight', 0)
            if weight < 0 or weight > 100:
                raise serializers.ValidationError(f'指标权重必须在0-100之间，当前值：{weight}')
            
            # 验证指标满分
            max_score = indicator.get('max_score', 0)
            if max_score <= 0:
                raise serializers.ValidationError('指标满分必须大于0')
            
            total_weight += weight
        
        # 验证总权重必须等于100
        if total_weight != 100:
            raise serializers.ValidationError(f'所有指标权重之和必须等于100，当前总权重：{total_weight}')
        
        return value
    
    def create(self, validated_data):
        """创建评分标准及其关联指标"""
        indicators_data = validated_data.pop('indicators', [])
        
        request = self.context.get('request')
        if request:
            validated_data['creator'] = request.user
            if hasattr(request.user, 'organization_profile'):
                validated_data['organization'] = request.user.organization_profile.organization
        
        # 创建评分标准
        criteria = super().create(validated_data)
        
        # 创建关联的评分指标
        for indicator_data in indicators_data:
            # 设置is_required默认值为True
            if 'is_required' not in indicator_data:
                indicator_data['is_required'] = True
            EvaluationIndicator.objects.create(
                criteria=criteria,
                **indicator_data
            )
        
        return criteria


class EvaluationCriteriaUpdateSerializer(serializers.ModelSerializer):
    """评分标准更新序列化器（仅非核心字段）"""
    indicators = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text='批量更新指标列表，每个元素包含id和要更新的字段'
    )
    new_indicators = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text='批量创建新指标列表，每个元素包含name、description、weight、max_score、is_required、order等字段'
    )
    
    class Meta:
        model = EvaluationCriteria
        fields = ['name', 'description', 'indicators', 'new_indicators']
    
    # def validate_requirement(self, value):
    #     """验证需求是否存在且属于当前组织"""
    #     # 已移除requirement字段
    #     return value
    
    def validate(self, attrs):
        """验证是否可以修改"""
        instance = self.instance
        
        # 检查状态是否允许修改
        if instance.status != 'active':
            raise serializers.ValidationError('只有启用状态的评分标准可以修改')
        
        # 检查是否已被使用
        if not instance.can_be_modified():
            raise serializers.ValidationError('该评分标准已用于项目评选，不可修改')
        
        # 验证批量更新指标
        indicators = attrs.get('indicators')
        new_indicators = attrs.get('new_indicators')
        
        # 验证批量更新指标
        if indicators:
            if not indicators:
                raise serializers.ValidationError('指标列表不能为空')
            
            indicator_ids = []
            names_to_check = {}
            
            for indicator_data in indicators:
                # 验证必须包含id
                if 'id' not in indicator_data:
                    raise serializers.ValidationError('每个指标必须包含id字段')
                
                indicator_id = indicator_data['id']
                
                # 验证指标是否存在且属于当前评分标准
                try:
                    indicator = instance.indicators.get(id=indicator_id)
                except EvaluationIndicator.DoesNotExist:
                    raise serializers.ValidationError(f'指标ID {indicator_id} 不存在或不属于当前评分标准')
                
                indicator_ids.append(indicator_id)
                
                # 验证权重
                if 'weight' in indicator_data:
                    weight = indicator_data['weight']
                    if not isinstance(weight, (int, float)) or weight < 0 or weight > 100:
                        raise serializers.ValidationError(f'指标ID {indicator_id} 的权重必须在0-100之间')
                
                # 验证最高分值
                if 'max_score' in indicator_data:
                    max_score = indicator_data['max_score']
                    if not isinstance(max_score, (int, float)) or max_score <= 0:
                        raise serializers.ValidationError(f'指标ID {indicator_id} 的最高分值必须大于0')
                
                # 收集名称以检查唯一性
                if 'name' in indicator_data:
                    name = indicator_data['name']
                    if name in names_to_check:
                        raise serializers.ValidationError(f'指标名称 "{name}" 在更新列表中重复')
                    names_to_check[name] = indicator_id
            
            # 检查名称唯一性
            for name, indicator_id in names_to_check.items():
                if instance.indicators.filter(name=name).exclude(id=indicator_id).exists():
                    raise serializers.ValidationError(f'指标名称 "{name}" 已存在')
            
            # 检查是否有重复的指标ID
            if len(indicator_ids) != len(set(indicator_ids)):
                raise serializers.ValidationError('指标ID不能重复')
        
        # 验证批量创建新指标
        if new_indicators:
            if not new_indicators:
                raise serializers.ValidationError('新指标列表不能为空')
            
            new_indicator_names = []
            
            for new_indicator_data in new_indicators:
                # 验证必填字段
                required_fields = ['name', 'weight', 'max_score']
                for field in required_fields:
                    if field not in new_indicator_data:
                        raise serializers.ValidationError(f'新指标必须包含 {field} 字段')
                
                # 验证权重
                weight = new_indicator_data['weight']
                if not isinstance(weight, (int, float)) or weight < 0 or weight > 100:
                    raise serializers.ValidationError(f'新指标权重必须在0-100之间，当前值：{weight}')
                
                # 验证最高分值
                max_score = new_indicator_data['max_score']
                if not isinstance(max_score, (int, float)) or max_score <= 0:
                    raise serializers.ValidationError('新指标最高分值必须大于0')
                
                # 验证名称
                name = new_indicator_data['name']
                if not name or not name.strip():
                    raise serializers.ValidationError('新指标名称不能为空')
                
                # 检查新指标名称在列表中是否重复
                if name in new_indicator_names:
                    raise serializers.ValidationError(f'新指标名称 "{name}" 在列表中重复')
                new_indicator_names.append(name)
                
                # 检查新指标名称是否与现有指标重复
                if instance.indicators.filter(name=name).exists():
                    raise serializers.ValidationError(f'新指标名称 "{name}" 与现有指标重复')
                
                # 检查新指标名称是否与要更新的指标重复
                if indicators:
                    for indicator_data in indicators:
                        if indicator_data.get('name') == name:
                            raise serializers.ValidationError(f'新指标名称 "{name}" 与更新指标名称重复')
        
        # 验证总权重
        if indicators or new_indicators:
            self._validate_total_weight(instance, indicators, new_indicators)
        
        return attrs
    
    def _validate_total_weight(self, instance, indicators_data, new_indicators_data):
        """验证所有指标的总权重"""
        from decimal import Decimal
        
        # 获取当前所有指标的权重
        current_indicators = instance.indicators.all()
        total_weight = Decimal('0')
        
        # 计算现有指标的权重（考虑更新）
        for indicator in current_indicators:
            weight = Decimal(str(indicator.weight))
            
            # 如果该指标在更新列表中，使用新权重
            if indicators_data:
                for indicator_data in indicators_data:
                    if indicator_data.get('id') == indicator.id and 'weight' in indicator_data:
                        weight = Decimal(str(indicator_data['weight']))
                        break
            
            total_weight += weight
        
        # 加上新指标的权重
        if new_indicators_data:
            for new_indicator_data in new_indicators_data:
                total_weight += Decimal(str(new_indicator_data['weight']))
        
        # 验证总权重必须等于100
        if total_weight != Decimal('100'):
            raise serializers.ValidationError(f'所有指标权重之和必须等于100，当前总权重：{total_weight}')
    
    def update(self, instance, validated_data):
        """更新评分标准"""
        indicators_data = validated_data.pop('indicators', None)
        new_indicators_data = validated_data.pop('new_indicators', None)
        
        # 更新基本字段
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # 处理指标更新
        if indicators_data:
            self.update_indicators(instance, indicators_data)
        
        # 处理新指标创建
        if new_indicators_data:
            self.create_new_indicators(instance, new_indicators_data)
        
        return instance
    
    def update_indicators(self, criteria, indicators_data):
        """批量更新指标"""
        updated_indicators = []
        
        for indicator_data in indicators_data:
            indicator_id = indicator_data.pop('id')
            
            try:
                indicator = criteria.indicators.get(id=indicator_id)
                
                # 更新指标字段
                for field, value in indicator_data.items():
                    setattr(indicator, field, value)
                
                indicator.save()
                updated_indicators.append(indicator)
                
            except EvaluationIndicator.DoesNotExist:
                continue
        
        return updated_indicators
    
    def create_new_indicators(self, criteria, new_indicators_data):
        """批量创建新指标"""
        created_indicators = []
        
        for new_indicator_data in new_indicators_data:
            # 设置默认值
            if 'is_required' not in new_indicator_data:
                new_indicator_data['is_required'] = True
            
            if 'description' not in new_indicator_data:
                new_indicator_data['description'] = ''
            
            # 如果没有指定order，设置为当前最大order + 1
            if 'order' not in new_indicator_data:
                max_order = criteria.indicators.aggregate(
                    max_order=Max('order')
                )['max_order'] or 0
                new_indicator_data['order'] = max_order + 1
            
            # 创建新指标
            indicator = EvaluationIndicator.objects.create(
                criteria=criteria,
                **new_indicator_data
            )
            created_indicators.append(indicator)
        
        return created_indicators


# ==================== 项目评分 CRUD 序列化器 ====================

class IndicatorScoreSerializer(serializers.ModelSerializer):
    """指标评分序列化器"""
    indicator_name = serializers.CharField(source='indicator.name', read_only=True)
    indicator_weight = serializers.DecimalField(source='indicator.weight', max_digits=5, decimal_places=2, read_only=True)
    indicator_max_score = serializers.IntegerField(source='indicator.max_score', read_only=True)
    weighted_score = serializers.SerializerMethodField()
    
    class Meta:
        model = IndicatorScore
        fields = [
            'id', 'indicator', 'indicator_name', 'indicator_weight', 
            'indicator_max_score', 'score', 'comment', 'weighted_score'
        ]
        read_only_fields = ['id', 'weighted_score']
    
    def get_weighted_score(self, obj):
        """获取加权得分"""
        return obj.get_weighted_score()


class ProjectEvaluationCreateSerializer(serializers.ModelSerializer):
    """项目评分创建序列化器"""
    indicator_scores = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text='指标评分列表，每个元素包含indicator_id、score、comment'
    )
    
    class Meta:
        model = ProjectEvaluation
        fields = [
            'project', 'criteria', 'overall_comment', 'indicator_scores'
        ]
    
    def validate(self, attrs):
        """验证项目评分数据"""
        project = attrs.get('project')
        criteria = attrs.get('criteria')
        indicator_scores = attrs.get('indicator_scores', [])
        
        # 验证项目状态
        if project.status != 'completed':
            raise serializers.ValidationError('只能对已完成的项目进行评分')
        
        # 验证评分标准状态
        if criteria.status != 'active':
            raise serializers.ValidationError('只能使用启用状态的评分标准')
        
        # 验证是否已存在评分记录
        request = self.context.get('request')
        if request:
            existing_evaluation = ProjectEvaluation.objects.filter(
                project=project,
                criteria=criteria,
                evaluator=request.user
            ).first()
            if existing_evaluation:
                raise serializers.ValidationError('您已对该项目进行过评分')
        
        # 验证指标评分
        if indicator_scores:
            criteria_indicators = criteria.indicators.all()
            indicator_ids = [ind.id for ind in criteria_indicators]
            
            provided_indicator_ids = []
            for score_data in indicator_scores:
                if 'indicator_id' not in score_data:
                    raise serializers.ValidationError('每个指标评分必须包含indicator_id')
                
                indicator_id = score_data['indicator_id']
                if indicator_id not in indicator_ids:
                    raise serializers.ValidationError(f'指标ID {indicator_id} 不属于该评分标准')
                
                provided_indicator_ids.append(indicator_id)
                
                # 验证分数范围
                score = score_data.get('score')
                if score is not None:
                    indicator = next(ind for ind in criteria_indicators if ind.id == indicator_id)
                    if score < 0 or score > indicator.max_score:
                        raise serializers.ValidationError(
                            f'指标 "{indicator.name}" 的分数必须在0-{indicator.max_score}之间'
                        )
            
            # 检查是否有重复的指标ID
            if len(provided_indicator_ids) != len(set(provided_indicator_ids)):
                raise serializers.ValidationError('指标ID不能重复')
        
        return attrs
    
    def create(self, validated_data):
        """创建项目评分"""
        indicator_scores_data = validated_data.pop('indicator_scores', [])
        
        request = self.context.get('request')
        if request:
            validated_data['evaluator'] = request.user
        
        # 创建评分记录
        evaluation = super().create(validated_data)
        
        # 创建指标评分记录
        criteria = evaluation.criteria
        criteria_indicators = criteria.indicators.all()
        
        # 如果提供了指标评分，创建对应记录
        if indicator_scores_data:
            for score_data in indicator_scores_data:
                indicator_id = score_data['indicator_id']
                indicator = next(ind for ind in criteria_indicators if ind.id == indicator_id)
                
                IndicatorScore.objects.create(
                    evaluation=evaluation,
                    indicator=indicator,
                    score=score_data.get('score'),
                    comment=score_data.get('comment', '')
                )
        else:
            # 如果没有提供指标评分，为所有指标创建空记录
            for indicator in criteria_indicators:
                IndicatorScore.objects.create(
                    evaluation=evaluation,
                    indicator=indicator,
                    score=None,
                    comment=''
                )
        
        # 更新项目的评分状态
        project = evaluation.project
        if not project.is_evaluated:
            project.is_evaluated = True
            project.save(update_fields=['is_evaluated'])
        
        return evaluation


class ProjectEvaluationDetailSerializer(serializers.ModelSerializer):
    """项目评分详情序列化器"""
    project = serializers.SerializerMethodField()
    criteria = serializers.SerializerMethodField()
    evaluator = serializers.SerializerMethodField()
    indicator_scores = IndicatorScoreSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ProjectEvaluation
        fields = [
            'id', 'project', 'criteria', 'evaluator', 'status', 'status_display',
            'total_score', 'weighted_score', 'overall_comment',
            'indicator_scores', 'created_at', 'updated_at'
        ]
    
    def get_project(self, obj):
        """获取项目对象信息"""
        project = obj.project
        return {
            'id': project.id,
            'title': project.title,
            'description': project.description,
            'status': project.status,
            'status_display': project.get_status_display(),
            'requirement': {
                'id': project.requirement.id,
                'title': project.requirement.title,
                'organization': {
                    'id': project.requirement.organization.id,
                    'name': project.requirement.organization.name
                }
            }
        }
    
    def get_criteria(self, obj):
        """获取评分标准对象信息"""
        criteria = obj.criteria
        return {
            'id': criteria.id,
            'name': criteria.name,
            'description': criteria.description,
            'status': criteria.status,
            'status_display': criteria.get_status_display()
        }
    
    def get_evaluator(self, obj):
        """获取评分人对象信息"""
        from common_utils import build_media_url
        
        evaluator = obj.evaluator
        request = self.context.get('request')
        
        return {
            'id': evaluator.id,
            'username': evaluator.username,
            'real_name': evaluator.real_name or evaluator.username,
            'avatar_url': build_media_url(evaluator.avatar, request)
        }


class ProjectEvaluationUpdateSerializer(serializers.ModelSerializer):
    """项目评分更新序列化器"""
    indicator_scores = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text='要更新的指标评分列表，每个元素包含indicator_id、score、comment'
    )
    
    class Meta:
        model = ProjectEvaluation
        fields = ['overall_comment', 'indicator_scores']
    
    def validate(self, attrs):
        """验证更新数据"""
        instance = self.instance
        indicator_scores = attrs.get('indicator_scores', [])
        
        # 验证评分状态
        if instance.status not in ['draft', 'in_progress']:
            raise serializers.ValidationError('只能修改草稿或进行中状态的评分')
        
        # 验证指标评分
        if indicator_scores:
            criteria = instance.criteria
            criteria_indicators = criteria.indicators.all()
            indicator_ids = [ind.id for ind in criteria_indicators]
            
            provided_indicator_ids = []
            for score_data in indicator_scores:
                if 'indicator_id' not in score_data:
                    raise serializers.ValidationError('每个指标评分必须包含indicator_id')
                
                indicator_id = score_data['indicator_id']
                if indicator_id not in indicator_ids:
                    raise serializers.ValidationError(f'指标ID {indicator_id} 不属于该评分标准')
                
                provided_indicator_ids.append(indicator_id)
                
                # 验证分数范围
                score = score_data.get('score')
                if score is not None:
                    indicator = next(ind for ind in criteria_indicators if ind.id == indicator_id)
                    if score < 0 or score > indicator.max_score:
                        raise serializers.ValidationError(
                            f'指标 "{indicator.name}" 的分数必须在0-{indicator.max_score}之间'
                        )
            
            # 检查是否有重复的指标ID
            if len(provided_indicator_ids) != len(set(provided_indicator_ids)):
                raise serializers.ValidationError('指标ID不能重复')
        
        return attrs
    
    def update(self, instance, validated_data):
        """更新项目评分"""
        indicator_scores_data = validated_data.pop('indicator_scores', [])
        
        # 更新基本信息
        instance = super().update(instance, validated_data)
        
        # 更新指标评分
        if indicator_scores_data:
            for score_data in indicator_scores_data:
                indicator_id = score_data['indicator_id']
                
                # 获取或创建指标评分记录
                indicator_score, created = IndicatorScore.objects.get_or_create(
                    evaluation=instance,
                    indicator_id=indicator_id,
                    defaults={
                        'score': score_data.get('score'),
                        'comment': score_data.get('comment', '')
                    }
                )
                
                if not created:
                    # 更新现有记录
                    if 'score' in score_data:
                        indicator_score.score = score_data['score']
                    if 'comment' in score_data:
                        indicator_score.comment = score_data['comment']
                    indicator_score.save()
        
        # 记录最近修改人
        request = self.context.get('request')
        if request:
            instance.last_modifier = request.user
            instance.save(update_fields=['last_modifier'])
        
        return instance


class ProjectRankingSerializer(serializers.ModelSerializer):
    """项目排名序列化器"""
    project_title = serializers.CharField(source='project.title', read_only=True)
    project_leader = serializers.SerializerMethodField()
    criteria_name = serializers.CharField(source='criteria.name', read_only=True)
    rank_percentage = serializers.SerializerMethodField()
    rank_level = serializers.SerializerMethodField()
    rank_level_display = serializers.SerializerMethodField()
    
    class Meta:
        model = ProjectRanking
        fields = [
            'id', 'project', 'project_title', 'project_leader',
            'criteria', 'criteria_name', 'rank', 'final_score',
            'rank_percentage', 'rank_level', 'rank_level_display',
            'published_at', 'updated_at'
        ]
    
    def get_project_leader(self, obj):
        """获取项目负责人信息"""
        from common_utils import build_media_url
        
        leader = obj.project.get_leader()
        if leader:
            request = self.context.get('request')
            avatar_url = build_media_url(leader.user.avatar, request)
            
            return {
                'id': leader.id,
                'name': leader.user.real_name,
                'school': leader.school.school if leader.school else None,
                'avatar': avatar_url
            }
        return None
    
    def get_rank_percentage(self, obj):
        """获取排名百分比"""
        return obj.get_rank_percentage()
    
    def get_rank_level(self, obj):
        """获取排名等级"""
        return obj.get_rank_level()
    
    def get_rank_level_display(self, obj):
        """获取排名等级显示"""
        return obj.get_rank_level()
    
    def update(self, instance, validated_data):
        """更新评分标准及可选的批量指标"""
        indicators = validated_data.pop('indicators', None)
        
        # 更新评分标准基本信息
        instance = super().update(instance, validated_data)
        
        # 批量更新指标信息（如果提供）
        if indicators:
            for indicator_data in indicators:
                indicator_id = indicator_data.pop('id')
                indicator = instance.indicators.get(id=indicator_id)
                for field, value in indicator_data.items():
                    if hasattr(indicator, field):
                        setattr(indicator, field, value)
                indicator.save()
        
        return instance


class EvaluationCriteriaBatchIndicatorUpdateSerializer(serializers.Serializer):
    """评分标准批量更新指标序列化器"""
    indicators = serializers.ListField(
        child=serializers.DictField(),
        help_text='要更新的指标列表，每个元素包含id和要更新的字段'
    )
    
    def validate_indicators(self, value):
        """验证指标更新数据"""
        if not value:
            raise serializers.ValidationError('指标列表不能为空')
        
        instance = self.context.get('instance')
        if not instance:
            raise serializers.ValidationError('未找到评分标准实例')
        
        # 检查状态是否允许修改
        if instance.status != 'active':
            raise serializers.ValidationError('只有启用状态的评分标准可以修改指标')
        
        # 检查是否已被使用
        if not instance.can_be_modified():
            raise serializers.ValidationError('该评分标准已用于项目评选，不可修改指标')
        
        indicator_ids = []
        names_to_check = {}
        
        for indicator_data in value:
            # 验证必须包含id
            if 'id' not in indicator_data:
                raise serializers.ValidationError('每个指标必须包含id字段')
            
            indicator_id = indicator_data['id']
            
            # 验证指标是否存在且属于当前评分标准
            try:
                indicator = instance.indicators.get(id=indicator_id)
            except EvaluationIndicator.DoesNotExist:
                raise serializers.ValidationError(f'指标ID {indicator_id} 不存在或不属于当前评分标准')
            
            indicator_ids.append(indicator_id)
            
            # 验证权重
            if 'weight' in indicator_data:
                weight = indicator_data['weight']
                if not isinstance(weight, (int, float)) or weight < 0 or weight > 100:
                    raise serializers.ValidationError(f'指标ID {indicator_id} 的权重必须在0-100之间')
            
            # 验证最高分值
            if 'max_score' in indicator_data:
                max_score = indicator_data['max_score']
                if not isinstance(max_score, int) or max_score <= 0:
                    raise serializers.ValidationError(f'指标ID {indicator_id} 的最高分值必须大于0')
            
            # 收集名称以检查唯一性
            if 'name' in indicator_data:
                name = indicator_data['name']
                if name in names_to_check:
                    raise serializers.ValidationError(f'指标名称 "{name}" 在更新列表中重复')
                names_to_check[name] = indicator_id
        
        # 检查名称唯一性
        for name, indicator_id in names_to_check.items():
            if instance.indicators.filter(name=name).exclude(id=indicator_id).exists():
                raise serializers.ValidationError(f'指标名称 "{name}" 已存在')
        
        # 检查是否有重复的指标ID
        if len(indicator_ids) != len(set(indicator_ids)):
            raise serializers.ValidationError('指标ID不能重复')
        
        return value
    
    def update_indicators(self, instance, indicators_data):
        """批量更新指标"""
        updated_indicators = []
        
        for indicator_data in indicators_data:
            indicator_id = indicator_data.pop('id')
            indicator = instance.indicators.get(id=indicator_id)
            
            # 更新指标字段
            for field, value in indicator_data.items():
                if hasattr(indicator, field):
                    setattr(indicator, field, value)
            
            indicator.save()
            updated_indicators.append(indicator)
        
        return updated_indicators


class EvaluationCriteriaStatusUpdateSerializer(serializers.Serializer):
    """评分标准状态更新序列化器"""
    status = serializers.ChoiceField(
        choices=EvaluationCriteria.STATUS_CHOICES,
        help_text='新状态：active（启用）、archived（归档）'
    )
    
    def validate_status(self, value):
        """验证状态流转是否合法"""
        instance = self.instance
        current_status = instance.status
        
        # 定义允许的状态流转
        allowed_transitions = {
            'active': ['archived'],
            'archived': ['active']  # 允许从归档状态重新激活
        }
        
        if value not in allowed_transitions.get(current_status, []):
            raise serializers.ValidationError(
                f'不支持从 {current_status} 状态流转到 {value} 状态'
            )
        
        return value


class EvaluationCriteriaCloneSerializer(serializers.Serializer):
    """评分标准复制序列化器"""
    source_criteria_id = serializers.IntegerField(help_text='源评分标准ID')
    name = serializers.CharField(
        max_length=200, 
        required=False,
        default='新的评分标准',
        help_text='新标准名称（可选，默认为"新的评分标准"）'
    )
    description = serializers.CharField(
        required=False, 
        allow_blank=True,
        default='基于模板创建的新标准',
        help_text='新标准描述（可选，默认为"基于模板创建的新标准"）'
    )
    # requirement = serializers.PrimaryKeyRelatedField(
    #     queryset=Requirement.objects.all(),
    #     required=False,
    #     allow_null=True,
    #     help_text='关联需求（可选）'
    # )  # 已移除requirement字段
    
    def validate_source_criteria_id(self, value):
        """验证源评分标准是否存在"""
        try:
            source_criteria = EvaluationCriteria.objects.get(id=value)
        except EvaluationCriteria.DoesNotExist:
            raise serializers.ValidationError('指定的源评分标准不存在')
        
        # 检查源评分标准权限（同组织或公共标准）
        request = self.context.get('request')
        if request and hasattr(request.user, 'organization_profile'):
            user_org = request.user.organization_profile.organization
            if source_criteria.organization and source_criteria.organization != user_org:
                raise serializers.ValidationError('无权限使用该评分标准')
        
        return value
    
    # def validate_requirement(self, value):
    #     """验证需求是否属于当前组织"""
    #     # 已移除requirement字段
    #     return value
    
    def create(self, validated_data):
        """基于源评分标准创建新的评分标准"""
        request = self.context.get('request')
        source_criteria_id = validated_data['source_criteria_id']
        name = validated_data.get('name', '新的评分标准')
        description = validated_data.get('description', '基于模板创建的新标准')
        # requirement = validated_data.get('requirement')  # 已移除requirement字段
        
        creator = request.user if request else None
        organization_profile = getattr(request.user, 'organization_profile', None) if request else None
        organization = organization_profile.organization if organization_profile else None
        
        # 使用模型的克隆方法
        new_criteria = EvaluationCriteria.clone_from_template(
            template_id=source_criteria_id,
            new_name=name,
            new_description=description,
            creator=creator,
            organization=organization
        )
        
        return new_criteria


class EvaluationCriteriaTemplateSerializer(serializers.ModelSerializer):
    """评分标准模板序列化器"""
    creator_name = serializers.CharField(source='creator.real_name', read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    indicator_count = serializers.SerializerMethodField()
    clone_count = serializers.SerializerMethodField()
    
    class Meta:
        model = EvaluationCriteria
        fields = [
            'id', 'name', 'description', 'creator_name',
            'organization_name', 'indicator_count', 'clone_count',
            'created_at'
        ]
    
    def get_indicator_count(self, obj):
        """获取指标数量"""
        return obj.indicators.count()
    
    def get_clone_count(self, obj):
        """获取克隆次数"""
        return obj.get_clone_count()


# ==================== 评分指标 CRUD 序列化器 ====================

class EvaluationIndicatorCreateSerializer(serializers.ModelSerializer):
    """评分指标创建序列化器"""
    is_required = serializers.BooleanField(default=True)
    
    class Meta:
        model = EvaluationIndicator
        fields = [
            'name', 'description', 'weight', 'max_score',
            'order', 'is_required'
        ]
    
    def validate_weight(self, value):
        """验证权重范围"""
        if value < 0 or value > 100:
            raise serializers.ValidationError('权重必须在0-100之间')
        return value
    
    def validate_max_score(self, value):
        """验证最高分值"""
        if value <= 0:
            raise serializers.ValidationError('最高分值必须大于0')
        return value
    
    def validate(self, attrs):
        """验证权重总和"""
        criteria = self.context.get('criteria')
        if not criteria:
            raise serializers.ValidationError('未指定评分标准')
        
        # 检查评分标准状态
        if criteria.status != 'active':
            raise serializers.ValidationError('只有启用状态的评分标准可以添加指标')
        
        # 检查是否已被使用
        if not criteria.can_be_modified():
            raise serializers.ValidationError('该评分标准已用于项目评选，不可添加指标')
        
        # 检查指标名称唯一性
        name = attrs.get('name')
        if criteria.indicators.filter(name=name).exists():
            raise serializers.ValidationError(f'指标名称 "{name}" 已存在')
        
        return attrs
    
    def create(self, validated_data):
        """创建评分指标"""
        criteria = self.context.get('criteria')
        validated_data['criteria'] = criteria
        return super().create(validated_data)


class EvaluationIndicatorBatchCreateSerializer(serializers.Serializer):
    """评分指标批量创建序列化器"""
    indicators = EvaluationIndicatorCreateSerializer(many=True)
    
    def validate_indicators(self, value):
        """验证指标列表"""
        if not value:
            raise serializers.ValidationError('至少需要一个评分指标')
        
        criteria = self.context.get('criteria')
        if not criteria:
            raise serializers.ValidationError('未指定评分标准')
        
        # 检查评分标准状态
        if criteria.status != 'active':
            raise serializers.ValidationError('只有启用状态的评分标准可以添加指标')
        
        # 检查是否已被使用
        if not criteria.can_be_modified():
            raise serializers.ValidationError('该评分标准已用于项目评选，不可添加指标')
        
        # 检查指标名称唯一性（包括现有指标和新增指标之间）
        existing_names = set(criteria.indicators.values_list('name', flat=True))
        new_names = [indicator.get('name') for indicator in value]
        
        # 检查与现有指标的重复
        for name in new_names:
            if name in existing_names:
                raise serializers.ValidationError(f'指标名称 "{name}" 已存在')
        
        # 检查新增指标之间的重复
        if len(new_names) != len(set(new_names)):
            duplicates = [name for name in new_names if new_names.count(name) > 1]
            raise serializers.ValidationError(f'新增指标中存在重复名称：{list(set(duplicates))}')
        
        return value
    
    def create(self, validated_data):
        """批量创建评分指标"""
        criteria = self.context.get('criteria')
        indicators_data = validated_data['indicators']
        
        indicators = []
        for indicator_data in indicators_data:
            indicator = EvaluationIndicator.objects.create(
                criteria=criteria,
                **indicator_data
            )
            indicators.append(indicator)
        
        return indicators


class EvaluationIndicatorUpdateSerializer(serializers.ModelSerializer):
    """评分指标更新序列化器"""
    
    class Meta:
        model = EvaluationIndicator
        fields = [
            'name', 'description', 'weight', 'max_score',
            'order', 'is_required'
        ]
    
    def validate_weight(self, value):
        """验证权重范围"""
        if value < 0 or value > 100:
            raise serializers.ValidationError('权重必须在0-100之间')
        return value
    
    def validate_max_score(self, value):
        """验证最高分值"""
        if value <= 0:
            raise serializers.ValidationError('最高分值必须大于0')
        return value
    
    def validate(self, attrs):
        """验证更新条件"""
        instance = self.instance
        criteria = instance.criteria
        
        # 检查评分标准状态
        if criteria.status != 'active':
            raise serializers.ValidationError('只有启用状态的评分标准可以修改指标')
        
        # 检查是否已被使用
        if not criteria.can_be_modified():
            raise serializers.ValidationError('该评分标准已用于项目评选，不可修改指标')
        
        # 检查指标名称唯一性（如果修改了名称）
        if 'name' in attrs:
            name = attrs['name']
            if criteria.indicators.filter(name=name).exclude(pk=instance.pk).exists():
                raise serializers.ValidationError(f'指标名称 "{name}" 已存在')
        
        return attrs