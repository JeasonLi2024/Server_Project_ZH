from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Project, ProjectMember

User = get_user_model()


class ProjectModelTest(TestCase):
    """项目模型测试"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_project(self):
        """测试创建项目"""
        project = Project.objects.create(
            name='测试项目',
            description='这是一个测试项目',
            creator=self.user
        )
        
        self.assertEqual(project.name, '测试项目')
        self.assertEqual(project.creator, self.user)
        self.assertTrue(project.is_active)
    
    def test_project_str(self):
        """测试项目字符串表示"""
        project = Project.objects.create(
            name='测试项目',
            creator=self.user
        )
        
        self.assertEqual(str(project), '测试项目')


class ProjectMemberModelTest(TestCase):
    """项目成员模型测试"""
    
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )
        self.project = Project.objects.create(
            name='测试项目',
            creator=self.user1
        )
    
    def test_create_project_member(self):
        """测试创建项目成员"""
        member = ProjectMember.objects.create(
            project=self.project,
            user=self.user2,
            role='member'
        )
        
        self.assertEqual(member.project, self.project)
        self.assertEqual(member.user, self.user2)
        self.assertEqual(member.role, 'member')
    
    def test_unique_project_user(self):
        """测试项目用户唯一性约束"""
        ProjectMember.objects.create(
            project=self.project,
            user=self.user2,
            role='member'
        )
        
        # 尝试创建重复的项目成员应该失败
        with self.assertRaises(Exception):
            ProjectMember.objects.create(
                project=self.project,
                user=self.user2,
                role='admin'
            )


class ProjectAPITest(APITestCase):
    """项目API测试"""
    
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )
        
        self.project = Project.objects.create(
            name='测试项目',
            description='测试项目描述',
            creator=self.user1
        )
        
        # 创建项目所有者成员关系
        ProjectMember.objects.create(
            project=self.project,
            user=self.user1,
            role='owner'
        )
    
    def test_create_project_authenticated(self):
        """测试认证用户创建项目"""
        self.client.force_authenticate(user=self.user1)
        
        data = {
            'name': '新项目',
            'description': '新项目描述'
        }
        
        response = self.client.post('/api/projects/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
    
    def test_create_project_unauthenticated(self):
        """测试未认证用户创建项目"""
        data = {
            'name': '新项目',
            'description': '新项目描述'
        }
        
        response = self.client.post('/api/projects/', data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_list_projects(self):
        """测试获取项目列表"""
        self.client.force_authenticate(user=self.user1)
        
        response = self.client.get('/api/projects/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
    
    def test_get_project_detail(self):
        """测试获取项目详情"""
        self.client.force_authenticate(user=self.user1)
        
        response = self.client.get(f'/api/projects/{self.project.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
    
    def test_update_project_as_owner(self):
        """测试项目所有者更新项目"""
        self.client.force_authenticate(user=self.user1)
        
        data = {
            'name': '更新后的项目名称',
            'description': '更新后的描述'
        }
        
        response = self.client.patch(f'/api/projects/{self.project.id}/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
    
    def test_update_project_as_non_member(self):
        """测试非成员更新项目"""
        self.client.force_authenticate(user=self.user2)
        
        data = {
            'name': '更新后的项目名称'
        }
        
        response = self.client.patch(f'/api/projects/{self.project.id}/', data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_add_project_member(self):
        """测试添加项目成员"""
        self.client.force_authenticate(user=self.user1)
        
        data = {
            'user': self.user2.id,
            'role': 'member'
        }
        
        response = self.client.post(f'/api/projects/{self.project.id}/add_member/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
    
    def test_get_project_members(self):
        """测试获取项目成员"""
        self.client.force_authenticate(user=self.user1)
        
        response = self.client.get(f'/api/projects/{self.project.id}/members/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')