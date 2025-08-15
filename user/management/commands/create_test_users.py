from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import date, timedelta
import random

from user.models import User, Student, OrganizationUser
from organization.models import Organization


class Command(BaseCommand):
    help = '创建测试用户数据（学生用户和组织用户）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='清除现有测试用户数据',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.clear_test_data()
            return

        with transaction.atomic():
            # 创建或获取测试组织
            organizations = self.create_test_organizations()
            
            # 创建学生用户
            students = self.create_student_users()
            
            # 创建组织用户
            org_users = self.create_organization_users(organizations)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'成功创建测试数据：\n'
                    f'- 组织数量: {len(organizations)}\n'
                    f'- 学生用户: {len(students)}\n'
                    f'- 组织用户: {len(org_users)}\n'
                    f'- 总用户数: {len(students) + len(org_users)}'
                )
            )

    def clear_test_data(self):
        """清除测试数据"""
        # 删除测试用户（用户名以test_开头的）
        test_users = User.objects.filter(username__startswith='test_')
        count = test_users.count()
        test_users.delete()
        
        # 删除测试组织（名称包含"测试"的）
        test_orgs = Organization.objects.filter(name__contains='测试')
        org_count = test_orgs.count()
        test_orgs.delete()
        
        self.stdout.write(
            self.style.SUCCESS(f'已清除 {count} 个测试用户和 {org_count} 个测试组织')
        )

    def create_test_organizations(self):
        """创建测试组织"""
        organizations = []
        
        # 企业组织
        enterprise_data = [
            {
                'name': '阿里巴巴测试分公司',
                'code': 'ALIBABA_TEST_001',
                'organization_type': 'enterprise',
                'enterprise_type': 'private',
                'industry_or_discipline': '互联网/电子商务',
                'scale': 'large',
                'leader_name': '张三',
                'leader_title': '总经理',
                'contact_person': '李四',
                'contact_position': '人事经理',
                'contact_phone': '010-12345678',
                'contact_email': 'hr@alibaba-test.com',
                'address': '北京市海淀区中关村软件园',
                'description': '阿里巴巴测试分公司，专注于电商技术研发',
                'status': 'verified'
            },
            {
                'name': '腾讯测试科技有限公司',
                'code': 'TENCENT_TEST_001',
                'organization_type': 'enterprise',
                'enterprise_type': 'private',
                'industry_or_discipline': '互联网/游戏',
                'scale': 'large',
                'leader_name': '王五',
                'leader_title': 'CEO',
                'contact_person': '赵六',
                'contact_position': 'HR总监',
                'contact_phone': '0755-88888888',
                'contact_email': 'hr@tencent-test.com',
                'address': '深圳市南山区腾讯大厦',
                'description': '腾讯测试科技有限公司，专注于社交和游戏',
                'status': 'verified'
            },
            {
                'name': '字节跳动测试公司',
                'code': 'BYTEDANCE_TEST_001',
                'organization_type': 'enterprise',
                'enterprise_type': 'private',
                'industry_or_discipline': '互联网/短视频',
                'scale': 'large',
                'leader_name': '孙七',
                'leader_title': '总裁',
                'contact_person': '周八',
                'contact_position': '招聘经理',
                'contact_phone': '010-99999999',
                'contact_email': 'hr@bytedance-test.com',
                'address': '北京市朝阳区字节跳动大厦',
                'description': '字节跳动测试公司，专注于内容创作和分发',
                'status': 'under_review'
            }
        ]
        
        # 大学组织
        university_data = [
            {
                'name': '北京大学测试学院',
                'code': 'PKU_TEST_001',
                'organization_type': 'university',
                'university_type': '985',
                'industry_or_discipline': '综合性大学',
                'scale': 'large',
                'leader_name': '李校长',
                'leader_title': '校长',
                'contact_person': '张教授',
                'contact_position': '教务处长',
                'contact_phone': '010-62751234',
                'contact_email': 'admin@pku-test.edu.cn',
                'address': '北京市海淀区颐和园路5号',
                'description': '北京大学测试学院，培养优秀人才',
                'status': 'verified'
            },
            {
                'name': '清华大学测试分校',
                'code': 'THU_TEST_001',
                'organization_type': 'university',
                'university_type': '985',
                'industry_or_discipline': '理工科',
                'scale': 'large',
                'leader_name': '王校长',
                'leader_title': '校长',
                'contact_person': '刘教授',
                'contact_position': '院长',
                'contact_phone': '010-62781234',
                'contact_email': 'admin@thu-test.edu.cn',
                'address': '北京市海淀区清华园1号',
                'description': '清华大学测试分校，理工科教育领先',
                'status': 'verified'
            }
        ]
        
        # 创建组织
        for org_data in enterprise_data + university_data:
            org, created = Organization.objects.get_or_create(
                code=org_data['code'],
                defaults=org_data
            )
            organizations.append(org)
            if created:
                self.stdout.write(f'创建组织: {org.name}')
        
        return organizations

    def create_student_users(self):
        """创建学生用户"""
        students = []
        
        student_data = [
            {
                'username': 'test_student_001',
                'email': 'student001@test.com',
                'real_name': '张学生',
                'user_type': 'student',
                'student_id': 'STU2024001',
                'school': '北京大学',
                'major': '计算机科学与技术',
                'grade': '2024',
                'education_level': 'undergraduate'
            },
            {
                'username': 'test_student_002',
                'email': 'student002@test.com',
                'real_name': '李学生',
                'user_type': 'student',
                'student_id': 'STU2024002',
                'school': '清华大学',
                'major': '软件工程',
                'grade': '2023',
                'education_level': 'undergraduate'
            },
            {
                'username': 'test_student_003',
                'email': 'student003@test.com',
                'real_name': '王学生',
                'user_type': 'student',
                'student_id': 'STU2024003',
                'school': '北京理工大学',
                'major': '人工智能',
                'grade': '2024',
                'education_level': 'master'
            },
            {
                'username': 'test_student_004',
                'email': 'student004@test.com',
                'real_name': '赵学生',
                'user_type': 'student',
                'student_id': 'STU2024004',
                'school': '北京航空航天大学',
                'major': '数据科学',
                'grade': '2022',
                'education_level': 'doctor'
            },
            {
                'username': 'test_student_005',
                'email': 'student005@test.com',
                'real_name': '孙学生',
                'user_type': 'student',
                'student_id': 'STU2024005',
                'school': '中国人民大学',
                'major': '经济学',
                'grade': '2024',
                'education_level': 'undergraduate'
            },
            {
                'username': 'test_student_006',
                'email': 'student006@test.com',
                'real_name': '周学生',
                'user_type': 'student',
                'student_id': 'STU2024006',
                'school': '北京师范大学',
                'major': '教育技术学',
                'grade': '2023',
                'education_level': 'master'
            },
            {
                'username': 'test_student_007',
                'email': 'student007@test.com',
                'real_name': '吴学生',
                'user_type': 'student',
                'student_id': 'STU2024007',
                'school': '对外经济贸易大学',
                'major': '国际贸易',
                'grade': '2024',
                'education_level': 'undergraduate'
            },
            {
                'username': 'test_student_008',
                'email': 'student008@test.com',
                'real_name': '郑学生',
                'user_type': 'student',
                'student_id': 'STU2024008',
                'school': '北京科技大学',
                'major': '材料科学与工程',
                'grade': '2023',
                'education_level': 'undergraduate'
            }
        ]
        
        for data in student_data:
            # 分离学生信息
            student_info = {
                'student_id': data.pop('student_id'),
                'school': data.pop('school'),
                'major': data.pop('major'),
                'grade': data.pop('grade'),
                'education_level': data.pop('education_level')
            }
            
            # 创建用户
            user, created = User.objects.get_or_create(
                username=data['username'],
                defaults={**data, 'password': 'pbkdf2_sha256$600000$test$test'}
            )
            
            if created:
                user.set_password('test123456')  # 统一密码
                user.save()
                
                # 创建学生档案
                student = Student.objects.create(
                    user=user,
                    **student_info
                )
                students.append(student)
                self.stdout.write(f'创建学生用户: {user.username} - {user.real_name}')
        
        return students

    def create_organization_users(self, organizations):
        """创建组织用户"""
        org_users = []
        
        # 为每个组织创建不同权限和状态的用户
        for i, org in enumerate(organizations):
            # 每个组织创建2-4个用户
            user_count = random.randint(2, 4)
            
            for j in range(user_count):
                user_num = i * 10 + j + 1
                
                # 根据组织类型设置不同的职位
                if org.organization_type == 'enterprise':
                    positions = ['软件工程师', '产品经理', '技术总监', '人事专员', '市场经理']
                    departments = ['技术部', '产品部', '人事部', '市场部', '运营部']
                else:  # university
                    positions = ['教授', '副教授', '讲师', '助教', '行政人员']
                    departments = ['计算机学院', '经济学院', '管理学院', '教务处', '学生处']
                
                # 设置权限和状态
                if j == 0:  # 第一个用户是管理员
                    permission = 'admin'
                    status = 'approved'
                elif j == 1:  # 第二个用户是普通成员
                    permission = 'member'
                    status = 'approved'
                else:  # 其他用户随机状态
                    permission = random.choice(['member'])
                    status = random.choice(['approved', 'pending', 'rejected'])
                
                user_data = {
                    'username': f'test_org_user_{user_num:03d}',
                    'email': f'orguser{user_num:03d}@test.com',
                    'real_name': f'组织用户{user_num:03d}',
                    'user_type': 'organization'
                }
                
                # 创建用户
                user, created = User.objects.get_or_create(
                    username=user_data['username'],
                    defaults=user_data
                )
                
                if created:
                    user.set_password('test123456')  # 统一密码
                    user.save()
                    
                    # 创建组织用户档案
                    org_user = OrganizationUser.objects.create(
                        user=user,
                        organization=org,
                        position=random.choice(positions),
                        department=random.choice(departments),
                        permission=permission,
                        status=status
                    )
                    org_users.append(org_user)
                    self.stdout.write(
                        f'创建组织用户: {user.username} - {user.real_name} '
                        f'({org.name}, {org_user.get_permission_display()}, {org_user.get_status_display()})'
                    )
        
        return org_users