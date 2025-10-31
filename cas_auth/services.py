import urllib.parse
import requests
import xml.etree.ElementTree as ET
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from typing import Dict, Optional, Tuple
import logging

from .models import CASAuthLog
from user.models import OrganizationUser, Student

User = get_user_model()
logger = logging.getLogger(__name__)


class BUPTCASService:
    """北邮CAS认证服务类"""
    
    def __init__(self):
        self.cas_server_url = getattr(settings, 'BUPT_CAS_SERVER_URL', '')
        self.service_url = getattr(settings, 'BUPT_CAS_SERVICE_URL', '')
        self.cas_version = getattr(settings, 'BUPT_CAS_VERSION', '3.0')
        
    def get_login_url(self, service_url: str = None) -> str:
        """生成CAS登录URL"""
        if not service_url:
            service_url = self.service_url
            
        login_url = f"{self.cas_server_url}/login"
        params = {'service': service_url}
        
        return f"{login_url}?{urllib.parse.urlencode(params)}"
    
    def get_logout_url(self, service_url: str = None) -> str:
        """生成CAS登出URL"""
        if not service_url:
            service_url = self.service_url
            
        logout_url = f"{self.cas_server_url}/logout"
        params = {'service': service_url}
        
        return f"{logout_url}?{urllib.parse.urlencode(params)}"
    
    def validate_ticket(self, ticket: str, service_url: str = None, 
                       request_info: Dict = None) -> Tuple[bool, Dict]:
        """验证CAS票据"""
        if not service_url:
            service_url = self.service_url
            
        # 记录验证开始
        log_data = {
            'action': 'validate',
            'status': 'pending',
            'ticket': ticket,
            'service_url': service_url,
        }
        
        if request_info:
            log_data.update({
                'ip_address': request_info.get('ip_address'),
                'user_agent': request_info.get('user_agent'),
            })
        
        auth_log = CASAuthLog.objects.create(**log_data)
        
        try:
            # 选择验证端点
            if self.cas_version == '2.0':
                validate_url = f"{self.cas_server_url}/serviceValidate"
            else:  # CAS 3.0
                validate_url = f"{self.cas_server_url}/p3/serviceValidate"
            
            params = {
                'ticket': ticket,
                'service': service_url,
            }
            
            # 发送验证请求
            response = requests.get(validate_url, params=params, timeout=10)
            response.raise_for_status()
            
            # 解析XML响应
            success, user_data = self._parse_cas_response(response.text)
            
            # 更新日志
            auth_log.status = 'success' if success else 'failed'
            auth_log.response_data = user_data
            if not success:
                auth_log.error_message = user_data.get('error', '票据验证失败')
            else:
                auth_log.cas_user_id = user_data.get('user_id')
            auth_log.save()
            
            return success, user_data
            
        except requests.RequestException as e:
            error_msg = f"CAS服务器请求失败: {str(e)}"
            auth_log.status = 'failed'
            auth_log.error_message = error_msg
            auth_log.save()
            
            logger.error(f"CAS ticket validation failed: {error_msg}")
            return False, {'error': error_msg}
        
        except Exception as e:
            error_msg = f"票据验证异常: {str(e)}"
            auth_log.status = 'failed'
            auth_log.error_message = error_msg
            auth_log.save()
            
            logger.error(f"CAS validation exception: {error_msg}")
            return False, {'error': error_msg}
    
    def _parse_cas_response(self, xml_content: str) -> Tuple[bool, Dict]:
        """解析CAS服务器响应，区分学生和教师身份，正确映射到对应字段"""
        try:
            root = ET.fromstring(xml_content)
            
            # 定义命名空间
            ns = {'cas': 'http://www.yale.edu/tp/cas'}
            
            # 检查是否认证成功
            success_elem = root.find('.//cas:authenticationSuccess', ns)
            if success_elem is not None:
                user_elem = success_elem.find('cas:user', ns)
                if user_elem is not None:
                    user_id = user_elem.text
                    user_data = {
                        'user_id': user_id,
                        'attributes': {}
                    }
                    
                    # 解析属性（CAS 3.0）
                    raw_attributes = {}
                    attributes_elem = success_elem.find('cas:attributes', ns)
                    if attributes_elem is not None:
                        for attr in attributes_elem:
                            attr_name = attr.tag.replace('{http://www.yale.edu/tp/cas}', '')
                            raw_attributes[attr_name] = attr.text
                    
                    # 身份识别和属性映射
                    normalized_attrs = {}
                    user_type = 'unknown'
                    
                    # 用户基本信息映射
                    if 'cn' in raw_attributes:
                        normalized_attrs['real_name'] = raw_attributes['cn']
                    elif 'displayName' in raw_attributes:
                        normalized_attrs['real_name'] = raw_attributes['displayName']
                    elif 'name' in raw_attributes:
                        normalized_attrs['real_name'] = raw_attributes['name']
                    
                    if 'mail' in raw_attributes:
                        normalized_attrs['email'] = raw_attributes['mail']
                    elif 'email' in raw_attributes:
                        normalized_attrs['email'] = raw_attributes['email']
                    
                    # 用户名映射
                    if 'uid' in raw_attributes:
                        normalized_attrs['username'] = raw_attributes['uid']
                    else:
                        normalized_attrs['username'] = user_id
                    
                    # 学生ID相关字段
                    student_id = None
                    if 'studentId' in raw_attributes:
                        student_id = raw_attributes['studentId']
                        user_type = 'student'
                    elif 'studentNumber' in raw_attributes:
                        student_id = raw_attributes['studentNumber']
                        user_type = 'student'
                    elif '学号' in raw_attributes:
                        student_id = raw_attributes['学号']
                        user_type = 'student'
                    
                    # 教师工号相关字段
                    employee_id = None
                    if 'employeeNumber' in raw_attributes:
                        employee_id = raw_attributes['employeeNumber']
                        if user_type == 'unknown':
                            user_type = 'teacher'
                    elif 'staffId' in raw_attributes:
                        employee_id = raw_attributes['staffId']
                        if user_type == 'unknown':
                            user_type = 'teacher'
                    elif 'employeeId' in raw_attributes:
                        employee_id = raw_attributes['employeeId']
                        if user_type == 'unknown':
                            user_type = 'teacher'
                    elif '工号' in raw_attributes:
                        employee_id = raw_attributes['工号']
                        if user_type == 'unknown':
                            user_type = 'teacher'
                    
                    # 如果没有明确的身份标识，根据CAS用户ID格式判断
                    if user_type == 'unknown':
                        if user_id.isdigit() and len(user_id) >= 8:
                            # 学号通常是8位以上的纯数字
                            user_type = 'student'
                            student_id = user_id
                        else:
                            # 工号通常较短或包含字母
                            user_type = 'teacher'
                            employee_id = user_id
                    
                    # 设置对应的ID字段
                    if user_type == 'student':
                        normalized_attrs['student_id'] = student_id or user_id
                        normalized_attrs['user_type'] = 'student'
                        
                        # 学生相关信息
                        if 'major' in raw_attributes:
                            normalized_attrs['major'] = raw_attributes['major']
                        elif '专业' in raw_attributes:
                            normalized_attrs['major'] = raw_attributes['专业']
                        
                        if 'grade' in raw_attributes:
                            normalized_attrs['grade'] = raw_attributes['grade']
                        elif '年级' in raw_attributes:
                            normalized_attrs['grade'] = raw_attributes['年级']
                        elif 'class' in raw_attributes:
                            normalized_attrs['grade'] = raw_attributes['class']
                        
                        if 'school' in raw_attributes:
                            normalized_attrs['school'] = raw_attributes['school']
                        elif 'college' in raw_attributes:
                            normalized_attrs['school'] = raw_attributes['college']
                        elif '学院' in raw_attributes:
                            normalized_attrs['school'] = raw_attributes['学院']
                        
                    else:  # teacher
                        normalized_attrs['employee_id'] = employee_id or user_id
                        normalized_attrs['user_type'] = 'teacher'
                        
                        # 教师相关信息
                        if 'department' in raw_attributes:
                            normalized_attrs['department'] = raw_attributes['department']
                        elif 'dept' in raw_attributes:
                            normalized_attrs['department'] = raw_attributes['dept']
                        elif '部门' in raw_attributes:
                            normalized_attrs['department'] = raw_attributes['部门']
                        elif '学院' in raw_attributes:
                            normalized_attrs['department'] = raw_attributes['学院']
                        
                        if 'position' in raw_attributes:
                            normalized_attrs['position'] = raw_attributes['position']
                        elif 'title' in raw_attributes:
                            normalized_attrs['position'] = raw_attributes['title']
                        elif '职位' in raw_attributes:
                            normalized_attrs['position'] = raw_attributes['职位']
                        elif '职称' in raw_attributes:
                            normalized_attrs['position'] = raw_attributes['职称']
                        
                        if 'organization' in raw_attributes:
                            normalized_attrs['organization'] = raw_attributes['organization']
                        elif 'org' in raw_attributes:
                            normalized_attrs['organization'] = raw_attributes['org']
                        elif '组织' in raw_attributes:
                            normalized_attrs['organization'] = raw_attributes['组织']
                    
                    user_data['attributes'] = normalized_attrs
                    user_data['raw_attributes'] = raw_attributes
                    
                    return True, user_data
            
            # 检查认证失败
            failure_elem = root.find('.//cas:authenticationFailure', ns)
            if failure_elem is not None:
                error_code = failure_elem.get('code', 'UNKNOWN')
                error_msg = failure_elem.text or '认证失败'
                return False, {
                    'error': error_msg,
                    'error_code': error_code
                }
            
            return False, {'error': '无效的CAS响应格式'}
            
        except ET.ParseError as e:
            logger.error(f"CAS XML parsing error: {str(e)}")
            return False, {'error': f'XML解析错误: {str(e)}'}
    
    def sync_cas_user(self, cas_user_data: Dict, request_info: Dict = None) -> Tuple[User, bool]:
        """同步CAS用户数据到本地数据库，根据用户身份自动存储到对应表"""
        cas_user_id = cas_user_data.get('user_id')
        attributes = cas_user_data.get('attributes', {})
        
        if not cas_user_id:
            raise ValueError("CAS用户ID不能为空")
        
        # 判断用户身份类型（学生或教师）
        user_type = attributes.get('user_type', 'unknown')
        student_id = attributes.get('student_id')
        employee_id = attributes.get('employee_id')
        
        # 根据ID格式或属性判断用户类型
        if not user_type or user_type == 'unknown':
            if student_id or (cas_user_id and len(cas_user_id) >= 8 and cas_user_id.isdigit()):
                user_type = 'student'
            elif employee_id or (cas_user_id and not cas_user_id.isdigit()):
                user_type = 'teacher'
            else:
                # 默认根据ID长度判断：学号通常较长且为纯数字，工号较短或包含字母
                if cas_user_id.isdigit() and len(cas_user_id) >= 8:
                    user_type = 'student'
                else:
                    user_type = 'teacher'
        
        with transaction.atomic():
            user = None
            created = False
            
            if user_type == 'student':
                # 处理学生用户
                user, created = self._sync_student_user(cas_user_id, attributes, request_info)
            else:
                # 处理教师用户
                user, created = self._sync_teacher_user(cas_user_id, attributes, request_info)
            
            return user, created
    
    def _sync_student_user(self, cas_user_id: str, attributes: Dict, request_info: Dict = None) -> Tuple[User, bool]:
        """同步学生用户数据"""
        student_id = attributes.get('student_id') or cas_user_id
        
        # 首先尝试通过CAS用户ID查找
        try:
            student = Student.objects.select_related('user').get(
                user__organization_profile__cas_user_id=cas_user_id
            )
            user = student.user
            created = False
        except Student.DoesNotExist:
            # 尝试通过学号查找
            try:
                student = Student.objects.select_related('user').get(
                    student_id=student_id
                )
                user = student.user
                created = False
                
                # 更新CAS信息（如果用户有组织档案）
                if hasattr(user, 'organization_profile'):
                    org_user = user.organization_profile
                    if not org_user.cas_user_id:
                        org_user.cas_user_id = cas_user_id
                        org_user.auth_source = 'cas'
                        org_user.last_cas_login = timezone.now()
                        org_user.save()
                        
            except Student.DoesNotExist:
                # 尝试通过用户名查找
                username = attributes.get('username') or student_id
                try:
                    user = User.objects.get(username=username)
                    created = False
                    
                    # 创建学生档案（如果不存在）
                    if not hasattr(user, 'student_profile'):
                        # 需要学校信息，这里使用默认值或从属性中获取
                        from organization.models import University
                        school = None
                        school_name = attributes.get('school', '北京邮电大学')
                        try:
                            school = University.objects.get(school=school_name)
                        except University.DoesNotExist:
                            # 创建默认学校或使用第一个学校
                            school = University.objects.first()
                            if not school:
                                school = University.objects.create(school=school_name)
                        
                        Student.objects.create(
                            user=user,
                            student_id=student_id,
                            school=school,
                            major=attributes.get('major', ''),
                            grade=attributes.get('grade', '2024'),
                        )
                    
                    # 更新或创建组织用户档案
                    if hasattr(user, 'organization_profile'):
                        org_user = user.organization_profile
                        org_user.cas_user_id = cas_user_id
                        org_user.auth_source = 'cas'
                        org_user.last_cas_login = timezone.now()
                        org_user.save()
                        
                except User.DoesNotExist:
                    # 创建新的学生用户
                    user_data = {
                        'username': username,
                        'email': attributes.get('email', f'{username}@bupt.edu.cn'),
                        'real_name': attributes.get('real_name', attributes.get('displayName', '')),
                        'user_type': 'student',
                        'is_active': True,
                    }
                    
                    user = User.objects.create_user(**user_data)
                    created = True
                    
                    # 创建学生档案
                    from organization.models import University
                    school = None
                    school_name = attributes.get('school', '北京邮电大学')
                    try:
                        school = University.objects.get(school=school_name)
                    except University.DoesNotExist:
                        school = University.objects.first()
                        if not school:
                            school = University.objects.create(school=school_name)
                    
                    Student.objects.create(
                        user=user,
                        student_id=student_id,
                        school=school,
                        major=attributes.get('major', ''),
                        grade=attributes.get('grade', '2024'),
                    )
        
        # 更新最后登录时间
        if not created and hasattr(user, 'student_profile'):
            student = user.student_profile
            # 更新学生信息（如果有新信息）
            if attributes.get('major') and not student.major:
                student.major = attributes.get('major')
            if attributes.get('grade') and student.grade != attributes.get('grade'):
                student.grade = attributes.get('grade')
            student.save()
        
        # 记录认证日志
        self._log_cas_auth(user, cas_user_id, 'login', 'success', cas_user_data={'user_id': cas_user_id, 'attributes': attributes}, request_info=request_info)
        
        return user, created
    
    def _sync_teacher_user(self, cas_user_id: str, attributes: Dict, request_info: Dict = None) -> Tuple[User, bool]:
        """同步教师用户数据"""
        employee_id = attributes.get('employee_id') or cas_user_id
        
        # 首先尝试通过CAS用户ID查找
        try:
            org_user = OrganizationUser.objects.select_related('user').get(
                cas_user_id=cas_user_id
            )
            user = org_user.user
            created = False
        except OrganizationUser.DoesNotExist:
            # 尝试通过工号查找
            try:
                org_user = OrganizationUser.objects.select_related('user').get(
                    employee_id=employee_id
                )
                user = org_user.user
                created = False
                
                # 更新CAS用户ID
                if not org_user.cas_user_id:
                    org_user.cas_user_id = cas_user_id
                    org_user.auth_source = 'cas'
                    org_user.last_cas_login = timezone.now()
                    org_user.save()
                    
            except OrganizationUser.DoesNotExist:
                # 尝试通过用户名查找
                username = attributes.get('username') or employee_id
                try:
                    user = User.objects.get(username=username)
                    created = False
                    
                    # 创建或更新组织用户档案
                    if hasattr(user, 'organization_profile'):
                        org_user = user.organization_profile
                        org_user.employee_id = employee_id
                        org_user.cas_user_id = cas_user_id
                        org_user.auth_source = 'cas'
                        org_user.last_cas_login = timezone.now()
                        org_user.save()
                    else:
                        # 需要组织信息，这里使用默认值
                        from organization.models import Organization
                        organization = None
                        org_name = attributes.get('organization', '北京邮电大学')
                        try:
                            organization = Organization.objects.get(name=org_name)
                        except Organization.DoesNotExist:
                            # 使用第一个组织或创建默认组织
                            organization = Organization.objects.first()
                            if not organization:
                                organization = Organization.objects.create(
                                    name=org_name,
                                    organization_type='university'
                                )
                        
                        OrganizationUser.objects.create(
                            user=user,
                            organization=organization,
                            employee_id=employee_id,
                            cas_user_id=cas_user_id,
                            auth_source='cas',
                            last_cas_login=timezone.now(),
                            position=attributes.get('position', ''),
                            department=attributes.get('department', ''),
                        )
                        
                except User.DoesNotExist:
                    # 创建新的教师用户
                    user_data = {
                        'username': username,
                        'email': attributes.get('email', f'{username}@bupt.edu.cn'),
                        'real_name': attributes.get('real_name', attributes.get('displayName', '')),
                        'user_type': 'organization',
                        'is_active': True,
                    }
                    
                    user = User.objects.create_user(**user_data)
                    created = True
                    
                    # 创建组织用户档案
                    from organization.models import Organization
                    organization = None
                    org_name = attributes.get('organization', '北京邮电大学')
                    try:
                        organization = Organization.objects.get(name=org_name)
                    except Organization.DoesNotExist:
                        organization = Organization.objects.first()
                        if not organization:
                            organization = Organization.objects.create(
                                name=org_name,
                                organization_type='university'
                            )
                    
                    OrganizationUser.objects.create(
                        user=user,
                        organization=organization,
                        employee_id=employee_id,
                        cas_user_id=cas_user_id,
                        auth_source='cas',
                        last_cas_login=timezone.now(),
                        position=attributes.get('position', ''),
                        department=attributes.get('department', ''),
                    )
        
        # 更新最后登录时间和工号信息
        if not created and hasattr(user, 'organization_profile'):
            org_user = user.organization_profile
            org_user.last_cas_login = timezone.now()
            
            # 更新工号信息（如果之前没有）
            if not org_user.employee_id:
                org_user.employee_id = employee_id
            
            # 更新职位和部门信息
            if attributes.get('position') and not org_user.position:
                org_user.position = attributes.get('position')
            if attributes.get('department') and not org_user.department:
                org_user.department = attributes.get('department')
            
            org_user.save()
        
        # 记录认证日志
        self._log_cas_auth(user, cas_user_id, 'login', 'success', cas_user_data={'user_id': cas_user_id, 'attributes': attributes}, request_info=request_info)
        
        return user, created
    
    def _log_cas_auth(self, user: User, cas_user_id: str, action: str, status: str, 
                     cas_user_data: Dict = None, request_info: Dict = None):
        """记录CAS认证日志"""
        log_data = {
            'user': user,
            'cas_user_id': cas_user_id,
            'action': action,
            'status': status,
            'response_data': cas_user_data or {},
        }
        
        if request_info:
            log_data.update({
                'ip_address': request_info.get('ip_address'),
                'user_agent': request_info.get('user_agent'),
            })
        
        CASAuthLog.objects.create(**log_data)
    
    def is_cas_enabled(self) -> bool:
        """检查CAS是否启用"""
        return bool(
            getattr(settings, 'BUPT_CAS_ENABLED', False) and
            self.cas_server_url and
            self.service_url
        )