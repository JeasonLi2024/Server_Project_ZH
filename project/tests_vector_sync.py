# 暂时禁用INSTALLED_APPS检查，避免makemigrations检查
from django.conf import settings
# 排除 admin_tool 和 audit (如果它依赖 requirement_audit_log 表但该表未迁移成功)
# 注意：audit 应用可能通过 signal 监听了 project 的模型，导致 delete 时触发 audit 逻辑
# 如果 audit 未安装或未迁移，就会报错。这里我们彻底移除 audit 相关应用。
# 另外，如果 project 本身有 migration 依赖 audit，那么这种方法可能无效。
# 经检查，project 的 migration 没有显式依赖 audit。
# 但是 models.py 中可能没有任何显式依赖。
# 问题可能在于数据库中存在某些外键约束或 signal。
# 尝试使用 SimpleTestCase 或 TransactionTestCase，或者彻底禁用 migrations。

class DisableMigrations(object):
    def __contains__(self, item):
        return True
    def __getitem__(self, item):
        return None

settings.MIGRATION_MODULES = DisableMigrations()
settings.INSTALLED_APPS = [app for app in settings.INSTALLED_APPS if app not in ['admin_tool', 'audit']]

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from user.models import OrganizationUser, Tag1, Tag2
from organization.models import Organization
from .models import Requirement
from unittest.mock import patch, MagicMock

User = get_user_model()

class VectorSyncTestCase(TestCase):
    def setUp(self):
        # 创建基础数据
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='password')
        self.org = Organization.objects.create(
            name='Test Org', 
            description='Test Desc', 
            organization_type='other', 
            other_type='other',
            status='verified',
            contact_person='Tester',
            contact_phone='12345678901',
            address='Test Addr'
        )
        self.org_user = OrganizationUser.objects.create(user=self.user, organization=self.org, permission='member')
        self.tag1 = Tag1.objects.create(value='AI')
        self.tag2 = Tag2.objects.create(post='Python', category='IT', subcategory='Backend')

    @patch('project.services.generate_embedding')
    @patch('project.services.get_or_create_collection')
    def test_sync_on_create_valid(self, mock_get_collection, mock_gen_embedding):
        """测试创建有效状态需求时触发同步"""
        mock_gen_embedding.return_value = [0.1] * 1536
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection
        
        req = Requirement.objects.create(
            title="Test Req",
            brief="Brief",
            description="Desc",
            status="under_review",
            organization=self.org,
            publish_people=self.org_user
        )
        req.tag1.add(self.tag1)
        
        # 验证 generate_embedding 被调用
        self.assertTrue(mock_gen_embedding.called)
        # 验证 insert 被调用
        self.assertTrue(mock_collection.insert.called)

    @patch('project.services.generate_embedding')
    def test_no_sync_on_draft(self, mock_gen_embedding):
        """测试创建草稿时不触发同步"""
        Requirement.objects.create(
            title="Draft Req",
            brief="Brief",
            description="Desc",
            status="draft",
            organization=self.org,
            publish_people=self.org_user
        )
        self.assertFalse(mock_gen_embedding.called)

    @patch('project.services.delete_requirement_vectors')
    def test_delete_sync(self, mock_delete):
        """测试删除需求时触发删除向量"""
        req = Requirement.objects.create(
            title="To Delete",
            brief="Brief",
            description="Desc",
            status="under_review",
            organization=self.org,
            publish_people=self.org_user
        )
        req_id = req.id
        req.delete()
        
        # 验证调用了 delete_requirement_vectors
        # 由于我们无法确切知道参数（可能有默认参数或命名参数），只验证调用
        self.assertTrue(mock_delete.called)
        # 验证第一个参数是 req_id
        args, _ = mock_delete.call_args
        self.assertEqual(args[0], req_id)

    @patch('project.signals.sync_requirement_vectors')
    @patch('project.services.delete_requirement_vectors')
    def test_status_change_sync(self, mock_delete, mock_sync):
        """测试状态变更时的同步逻辑"""
        # 注意：因为 signals.py 导入的是 project.services.sync_requirement_vectors
        # 如果我们 mock project.services.sync_requirement_vectors，
        # 那么 signals.py 中已经导入的函数对象引用可能不会变，或者变了。
        # 最好是 mock project.signals.sync_requirement_vectors
        
        # 为了确保 mock 生效，我们需要重新加载 signals 模块或者在 patch 时指定正确路径
        # 在这里我们尝试 patch project.signals.sync_requirement_vectors
        
        req = Requirement.objects.create(
            title="Status Change",
            brief="Brief",
            description="Desc",
            status="draft",
            organization=self.org,
            publish_people=self.org_user
        )
        
        # draft -> under_review (应触发 sync)
        # 重置 mock，因为 create 时可能已经调用过
        mock_sync.reset_mock()
        req.status = 'under_review'
        req.save()
        
        # 验证 sync 被调用
        # 注意：如果 test_status_change_sync 失败，可能是因为 sync_requirement_vectors 是在 project.services 中定义的
        # 而 signals.py 中导入的是 project.services.sync_requirement_vectors
        # mock patch 的是 'project.services.sync_requirement_vectors'
        # 理论上应该生效。
        # 让我们打印一下看看是否进入了 signal handler
        self.assertTrue(mock_sync.called)
        
        # under_review -> draft (应触发 delete)
        # 注意：save() 内部调用的是 sync_requirement_vectors
        # 我们的 signal 逻辑是 post_save -> sync_requirement_vectors
        # sync_requirement_vectors 内部判断 status == draft -> delete_requirement_vectors
        # 所以对于外部观察者（mock_sync），它确实被调用了
        mock_sync.reset_mock()
        req.status = 'draft'
        req.save()
        self.assertTrue(mock_sync.called)

    @patch('project.services.delete_requirement_vectors')
    def test_bulk_delete_sync(self, mock_delete):
        """测试批量删除是否触发同步"""
        # 创建多个需求
        req1 = Requirement.objects.create(
            title="Bulk 1",
            brief="Brief",
            description="Desc",
            status="under_review",
            organization=self.org,
            publish_people=self.org_user
        )
        req2 = Requirement.objects.create(
            title="Bulk 2",
            brief="Brief",
            description="Desc",
            status="under_review",
            organization=self.org,
            publish_people=self.org_user
        )
        
        # 批量删除
        Requirement.objects.all().delete()
        
        # 验证 delete_requirement_vectors 被调用了两次
        self.assertEqual(mock_delete.call_count, 2)
        # 验证调用参数
        # mock_delete.call_args_list 是一个 list of call objects
        # 每个 call object 是 (args, kwargs)
        # 我们检查 id 是否都在调用列表中
        called_ids = [args[0] for args, _ in mock_delete.call_args_list]
        self.assertIn(req1.id, called_ids)
        self.assertIn(req2.id, called_ids)
