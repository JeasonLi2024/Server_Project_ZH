from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from rest_framework.test import APITestCase
from rest_framework import status
from user.models import User
from .utils import assign_random_avatar, get_default_avatar_url
import os
import tempfile
import shutil


class RandomAvatarTestCase(TestCase):
    """随机头像功能测试"""
    
    def setUp(self):
        """测试前准备"""
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_assign_random_avatar(self):
        """测试随机头像分配功能"""
        # 确保用户初始没有头像
        self.assertFalse(self.test_user.avatar)
        
        # 分配随机头像
        assign_random_avatar(self.test_user)
        
        # 刷新用户对象
        self.test_user.refresh_from_db()
        
        # 验证头像已分配
        self.assertTrue(self.test_user.avatar)
        self.assertIn('avatars/user_', self.test_user.avatar.name)
    
    def test_get_default_avatar_url(self):
        """测试获取默认头像URL"""
        default_url = get_default_avatar_url()
        self.assertIsInstance(default_url, str)
        self.assertIn('/media/avatars/default/', default_url)
    
    def test_avatar_file_creation(self):
        """测试头像文件是否正确创建"""
        assign_random_avatar(self.test_user)
        self.test_user.refresh_from_db()
        
        if self.test_user.avatar:
            # 检查文件是否存在
            avatar_path = os.path.join(settings.MEDIA_ROOT, self.test_user.avatar.name)
            self.assertTrue(os.path.exists(avatar_path))
    
    def tearDown(self):
        """测试后清理"""
        # 清理测试创建的头像文件
        if self.test_user.avatar:
            avatar_path = os.path.join(settings.MEDIA_ROOT, self.test_user.avatar.name)
            if os.path.exists(avatar_path):
                os.remove(avatar_path)
            # 清理用户目录
            user_dir = os.path.dirname(avatar_path)
            if os.path.exists(user_dir) and os.path.isdir(user_dir):
                try:
                    os.rmdir(user_dir)
                except OSError:
                    pass  # 目录不为空时忽略


class AvatarUtilsTestCase(TestCase):
    """头像工具函数测试"""
    
    def test_default_avatar_directory_exists(self):
        """测试默认头像目录是否存在"""
        default_avatar_dir = os.path.join(settings.MEDIA_ROOT, 'avatars', 'default')
        self.assertTrue(os.path.exists(default_avatar_dir))
    
    def test_default_avatar_files_exist(self):
        """测试默认头像文件是否存在"""
        default_avatar_dir = os.path.join(settings.MEDIA_ROOT, 'avatars', 'default')
        expected_files = ['avatar_1.svg', 'avatar_2.svg', 'avatar_3.svg', 'avatar_4.svg', 'avatar_5.svg']
        
        for filename in expected_files:
            file_path = os.path.join(default_avatar_dir, filename)
            self.assertTrue(os.path.exists(file_path), f"默认头像文件 {filename} 不存在")
    
    def test_avatar_assignment_with_missing_default_directory(self):
        """测试默认头像目录不存在时的处理"""
        # 创建测试用户
        user = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123'
        )
        
        # 临时重命名默认头像目录
        default_avatar_dir = os.path.join(settings.MEDIA_ROOT, 'avatars', 'default')
        temp_dir = default_avatar_dir + '_temp'
        
        if os.path.exists(default_avatar_dir):
            os.rename(default_avatar_dir, temp_dir)
        
        try:
            # 尝试分配头像（应该不会崩溃）
            assign_random_avatar(user)
            user.refresh_from_db()
            
            # 验证用户仍然没有头像（因为默认目录不存在）
            self.assertFalse(user.avatar)
            
        finally:
            # 恢复默认头像目录
            if os.path.exists(temp_dir):
                os.rename(temp_dir, default_avatar_dir)
