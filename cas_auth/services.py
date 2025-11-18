import urllib.parse
import requests
import xml.etree.ElementTree as ET
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from django.db.utils import IntegrityError
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
            
            response = requests.get(validate_url, params=params, timeout=10)
            response.raise_for_status()
            raw_xml = response.text
            success, user_data = self._parse_cas_response(raw_xml)
            
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
        try:
            root = ET.fromstring(xml_content)
            ns = {'cas': 'http://www.yale.edu/tp/cas'}
            success_elem = root.find('.//cas:authenticationSuccess', ns)
            if success_elem is not None:
                user_elem = success_elem.find('cas:user', ns)
                if user_elem is not None:
                    user_id = user_elem.text or ''
                    raw_attributes = {}
                    attributes_elem = success_elem.find('cas:attributes', ns)
                    if attributes_elem is not None:
                        for attr in attributes_elem:
                            attr_name = attr.tag.replace('{http://www.yale.edu/tp/cas}', '')
                            raw_attributes[attr_name] = attr.text
                    normalized_attrs = {
                        'username': user_id,
                        'real_name': raw_attributes.get('name', ''),
                        'employee_id': raw_attributes.get('employeeNumber')
                    }
                    return True, {
                        'user_id': user_id,
                        'attributes': normalized_attrs,
                        'raw_attributes': raw_attributes
                    }
            failure_elem = root.find('.//cas:authenticationFailure', ns)
            if failure_elem is not None:
                error_code = failure_elem.get('code', 'UNKNOWN')
                error_msg = failure_elem.text or '认证失败'
                return False, {'error': error_msg, 'error_code': error_code}
            return False, {'error': '无效的CAS响应格式'}
        except ET.ParseError as e:
            logger.error(f"CAS XML parsing error: {str(e)}")
            return False, {'error': f'XML解析错误: {str(e)}'}
    
    def sync_cas_user(self, cas_user_data: Dict, request_info: Dict = None) -> Tuple[User, bool]:
        """基于 `<cas:user>` 作为用户名查询/创建，并按前缀规则分流存储"""
        cas_user_id = cas_user_data.get('user_id')
        attributes = cas_user_data.get('attributes', {})
        if not cas_user_id:
            raise ValueError("CAS用户ID不能为空")
        username = cas_user_id
        real_name = attributes.get('real_name') or attributes.get('name') or ''
        employee_number = attributes.get('employee_id') or None

        # 先用 CAS 返回的唯一编号（employeeNumber 或 user_id）匹配本地档案，决定用户与角色
        # 优先匹配教师档案（OrganizationUser.employee_id == employeeNumber 或 == user_id）
        from user.models import Student as StudentModel
        from user.models import OrganizationUser as OrgUserModel
        org_match = None
        stu_match = None
        if employee_number:
            org_match = OrgUserModel.objects.select_related('user').filter(employee_id=employee_number).first()
            stu_match = StudentModel.objects.select_related('user').filter(student_id=employee_number).first()
        else:
            # 无 employeeNumber 时用 cas_user_id 兜底匹配
            org_match = OrgUserModel.objects.select_related('user').filter(employee_id=username).first()
            stu_match = StudentModel.objects.select_related('user').filter(student_id=username).first()

        is_teacher = bool(org_match)

        # 常量：北京邮电大学ID（学校与组织）
        from django.conf import settings as dj_settings
        university_id = getattr(dj_settings, 'BUPT_UNIVERSITY_ID', 13)
        organization_id = getattr(dj_settings, 'BUPT_ORGANIZATION_ID', 1)

        with transaction.atomic():
            # 若已有档案匹配，直接复用对应的用户对象
            if org_match:
                user = org_match.user
                created = False
            elif stu_match:
                user = stu_match.user
                created = False
            else:
                email = f"{username}@bupt.edu.cn"
                user_type = 'organization' if is_teacher else 'student'
                existing_by_email = User.objects.filter(email=email).first()
                if existing_by_email:
                    user = existing_by_email
                    if user.username != username:
                        user.username = username
                    user.real_name = real_name
                    user.user_type = user_type
                    user.is_active = True
                    user.save()
                    created = False
                else:
                    try:
                        user = User.objects.create_user(
                            username=username,
                            email=email,
                            real_name=real_name,
                            user_type=user_type,
                            is_active=True,
                        )
                        created = True
                    except IntegrityError:
                        user = User.objects.get(email=email)
                        if user.username != username:
                            user.username = username
                        user.real_name = real_name
                        user.user_type = user_type
                        user.is_active = True
                        user.save()
                        created = False

            # 学生分支：创建/补全 Student，并确保 school=北京邮电大学，grade=前四位
            if not is_teacher:
                from organization.models import University
                year = username[:4] if username[:4].isdigit() else '2024'
                # 获取或创建学校
                try:
                    school = University.objects.get(id=university_id)
                except University.DoesNotExist:
                    school = University.objects.first()
                    if not school:
                        school = University.objects.create(id=university_id, school='北京邮电大学')
                # 获取或创建学生档案
                if hasattr(user, 'student_profile'):
                    stu = user.student_profile
                    if not stu.student_id:
                        stu.student_id = username
                    if not stu.grade:
                        stu.grade = year
                    if not stu.school_id:
                        stu.school = school
                    stu.save()
                else:
                    # 若此前按 employeeNumber 已匹配到学生档案，保证其 user 一致
                    if stu_match:
                        user = stu_match.user
                    else:
                        StudentModel.objects.get_or_create(
                            user=user,
                            defaults={
                                'student_id': username,
                                'school': school,
                                'major': '',
                                'grade': year,
                            }
                        )
            else:
                # 教师分支：创建/补全 OrganizationUser，权限=member，状态=approved，组织=北京邮电大学
                from organization.models import Organization
                try:
                    org = Organization.objects.get(id=organization_id)
                except Organization.DoesNotExist:
                    org = Organization.objects.first()
                    if not org:
                        org = Organization.objects.create(id=organization_id, name='北京邮电大学', organization_type='university')
                if hasattr(user, 'organization_profile'):
                    org_user = user.organization_profile
                    org_user.organization = org
                    ident = employee_number or username
                    if not org_user.employee_id:
                        org_user.employee_id = ident
                    elif org_user.employee_id != ident:
                        org_user.employee_id = ident
                    org_user.permission = 'member'
                    org_user.status = 'approved'
                    org_user.cas_user_id = username
                    org_user.auth_source = 'cas'
                    org_user.last_cas_login = timezone.now()
                    org_user.save()
                else:
                    OrganizationUser.objects.create(
                        user=user,
                        organization=org,
                        employee_id=employee_number or username,
                        position='',
                        department='',
                        permission='member',
                        status='approved',
                        cas_user_id=username,
                        auth_source='cas',
                        last_cas_login=timezone.now(),
                    )

            # 记录认证日志
            self._log_cas_auth(user, cas_user_id, 'login', 'success', cas_user_data={'user_id': cas_user_id, 'attributes': attributes}, request_info=request_info)
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