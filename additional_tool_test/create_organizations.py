#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量创建组织和组织用户脚本

功能：
1. 创建三种类型的组织：大学、企业、其他组织
2. 为每个组织创建不同角色的用户：创建者、管理员、成员
3. 生成真实的中国人姓名
4. 设置合理的职位和部门信息

作者：AI Assistant
创建时间：2024年
"""

import os
import sys
import django
import random
from datetime import datetime, date
from django.contrib.auth import get_user_model
from django.db import transaction
from faker import Faker

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Project_Zhihui.settings')
django.setup()

# 导入模型
from organization.models import Organization, OrganizationConfig
from user.models import OrganizationUser

User = get_user_model()
fake = Faker('zh_CN')

# 常见中国姓氏（按使用频率排序）
CHINESE_SURNAMES = [
    '王', '李', '张', '刘', '陈', '杨', '赵', '黄', '周', '吴',
    '徐', '孙', '胡', '朱', '高', '林', '何', '郭', '马', '罗',
    '梁', '宋', '郑', '谢', '韩', '唐', '冯', '于', '董', '萧',
    '程', '曹', '袁', '邓', '许', '傅', '沈', '曾', '彭', '吕',
    '苏', '卢', '蒋', '蔡', '贾', '丁', '魏', '薛', '叶', '阎'
]

# 男性常用名字字符
MALE_NAME_CHARS = [
    '伟', '强', '磊', '军', '勇', '涛', '明', '超', '亮', '华',
    '建', '国', '峰', '学', '永', '杰', '松', '波', '民', '友',
    '志', '清', '坚', '庆', '祥', '东', '文', '辉', '力', '固',
    '之', '段', '殿', '泰', '盛', '雄', '琛', '钧', '冠', '策',
    '腾', '楠', '榕', '风', '航', '弘', '义', '兴', '良', '飞'
]

# 女性常用名字字符
FEMALE_NAME_CHARS = [
    '秀', '娟', '英', '华', '慧', '巧', '美', '娜', '静', '淑',
    '惠', '珠', '翠', '雅', '芝', '玉', '萍', '红', '娥', '玲',
    '芬', '芳', '燕', '彩', '春', '菊', '兰', '凤', '洁', '梅',
    '琳', '素', '云', '莲', '真', '环', '雪', '荣', '爱', '妹',
    '霞', '香', '月', '莺', '媛', '艳', '瑞', '凡', '佳', '嘉'
]

# 大学数据
UNIVERSITIES = [
    {
        'name': '北京大学',
        'code': '10001',
        'organization_type': 'university',
        'university_type': '985',
        'leader_name': '龚旗煌',
        'leader_title': '校长',
        'industry_or_discipline': '综合性大学',
        'scale': 'giant',
        'contact_person': '招生办公室',
        'contact_position': '主任',
        'contact_phone': '010-62751407',
        'contact_email': 'zsb@pku.edu.cn',
        'address': '北京市海淀区颐和园路5号',
        'postal_code': '100871',
        'description': '北京大学创办于1898年，初名京师大学堂，是中国第一所国立综合性大学。',
        'website': 'https://www.pku.edu.cn',
        'status': 'verified',
        'established_date': date(1898, 7, 3)
    },
    {
        'name': '清华大学',
        'code': '10003',
        'organization_type': 'university',
        'university_type': '985',
        'leader_name': '王希勤',
        'leader_title': '校长',
        'industry_or_discipline': '理工科大学',
        'scale': 'giant',
        'contact_person': '招生办公室',
        'contact_position': '主任',
        'contact_phone': '010-62770334',
        'contact_email': 'zsb@tsinghua.edu.cn',
        'address': '北京市海淀区清华园1号',
        'postal_code': '100084',
        'description': '清华大学始建于1911年，是中国著名高等学府。',
        'website': 'https://www.tsinghua.edu.cn',
        'status': 'verified',
        'established_date': date(1911, 4, 29)
    },
    {
        'name': '复旦大学',
        'code': '10246',
        'organization_type': 'university',
        'university_type': '985',
        'leader_name': '金力',
        'leader_title': '校长',
        'industry_or_discipline': '综合性大学',
        'scale': 'large',
        'contact_person': '招生办公室',
        'contact_position': '主任',
        'contact_phone': '021-55666668',
        'contact_email': 'admission@fudan.edu.cn',
        'address': '上海市杨浦区邯郸路220号',
        'postal_code': '200433',
        'description': '复旦大学创建于1905年，原名复旦公学。',
        'website': 'https://www.fudan.edu.cn',
        'status': 'verified',
        'established_date': date(1905, 9, 14)
    },
    {
        'name': '上海交通大学',
        'code': '10248',
        'organization_type': 'university',
        'university_type': '985',
        'leader_name': '丁奎岭',
        'leader_title': '校长',
        'industry_or_discipline': '理工科大学',
        'scale': 'large',
        'contact_person': '招生办公室',
        'contact_position': '主任',
        'contact_phone': '021-34200000',
        'contact_email': 'zsb@sjtu.edu.cn',
        'address': '上海市闵行区东川路800号',
        'postal_code': '200240',
        'description': '上海交通大学是我国历史最悠久、享誉海内外的著名高等学府之一。',
        'website': 'https://www.sjtu.edu.cn',
        'status': 'verified',
        'established_date': date(1896, 4, 8)
    },
    {
        'name': '中国人民大学',
        'code': '10002',
        'organization_type': 'university',
        'university_type': '985',
        'leader_name': '林尚立',
        'leader_title': '校长',
        'industry_or_discipline': '人文社科类',
        'scale': 'large',
        'contact_person': '招生就业处',
        'contact_position': '处长',
        'contact_phone': '010-62511340',
        'contact_email': 'zsb@ruc.edu.cn',
        'address': '北京市海淀区中关村大街59号',
        'postal_code': '100872',
        'description': '中国人民大学是中国共产党创办的第一所新型正规大学。',
        'website': 'https://www.ruc.edu.cn',
        'status': 'verified',
        'established_date': date(1937, 7, 7)
    }
]

# 企业数据
ENTERPRISES = [
    {
        'name': '腾讯科技（深圳）有限公司',
        'code': '91440300708461136T',
        'organization_type': 'enterprise',
        'enterprise_type': 'listed',
        'leader_name': '马化腾',
        'leader_title': '董事会主席兼首席执行官',
        'industry_or_discipline': '互联网和相关服务',
        'scale': 'giant',
        'contact_person': '人力资源部',
        'contact_position': '招聘经理',
        'contact_phone': '0755-86013388',
        'contact_email': 'hr@tencent.com',
        'address': '广东省深圳市南山区科技中一路腾讯大厦',
        'postal_code': '518057',
        'description': '腾讯成立于1998年11月，是一家以互联网为基础的科技与文化公司。',
        'website': 'https://www.tencent.com',
        'status': 'verified',
        'established_date': date(1998, 11, 11)
    },
    {
        'name': '阿里巴巴（中国）有限公司',
        'code': '91330100MA27XF6T8K',
        'organization_type': 'enterprise',
        'enterprise_type': 'listed',
        'leader_name': '张勇',
        'leader_title': '董事长兼首席执行官',
        'industry_or_discipline': '电子商务',
        'scale': 'giant',
        'contact_person': '人才发展部',
        'contact_position': '招聘总监',
        'contact_phone': '0571-85022088',
        'contact_email': 'talent@alibaba-inc.com',
        'address': '浙江省杭州市余杭区文一西路969号',
        'postal_code': '311121',
        'description': '阿里巴巴集团创立于1999年，是全球领先的数字经济体。',
        'website': 'https://www.alibaba.com',
        'status': 'verified',
        'established_date': date(1999, 9, 9)
    },
    {
        'name': '百度在线网络技术（北京）有限公司',
        'code': '91110000802100433B',
        'organization_type': 'enterprise',
        'enterprise_type': 'listed',
        'leader_name': '李彦宏',
        'leader_title': '董事长兼首席执行官',
        'industry_or_discipline': '互联网信息服务',
        'scale': 'giant',
        'contact_person': '人力资源部',
        'contact_position': '校园招聘负责人',
        'contact_phone': '010-59928888',
        'contact_email': 'zhaopin@baidu.com',
        'address': '北京市海淀区上地十街10号百度大厦',
        'postal_code': '100085',
        'description': '百度公司创立于2000年1月1日，是全球最大的中文搜索引擎。',
        'website': 'https://www.baidu.com',
        'status': 'verified',
        'established_date': date(2000, 1, 1)
    },
    {
        'name': '华为技术有限公司',
        'code': '91440300279860880X',
        'organization_type': 'enterprise',
        'enterprise_type': 'private',
        'leader_name': '任正非',
        'leader_title': '总裁',
        'industry_or_discipline': '通信设备制造',
        'scale': 'giant',
        'contact_person': '全球招聘中心',
        'contact_position': '招聘经理',
        'contact_phone': '0755-28780808',
        'contact_email': 'career@huawei.com',
        'address': '广东省深圳市龙岗区坂田华为总部办公楼',
        'postal_code': '518129',
        'description': '华为创立于1987年，是全球领先的ICT基础设施和智能终端提供商。',
        'website': 'https://www.huawei.com',
        'status': 'verified',
        'established_date': date(1987, 9, 15)
    },
    {
        'name': '字节跳动有限公司',
        'code': '91110108MA00A1QU8R',
        'organization_type': 'enterprise',
        'enterprise_type': 'private',
        'leader_name': '梁汝波',
        'leader_title': '首席执行官',
        'industry_or_discipline': '互联网信息服务',
        'scale': 'giant',
        'contact_person': '人才发展中心',
        'contact_position': '招聘负责人',
        'contact_phone': '010-82600000',
        'contact_email': 'talent@bytedance.com',
        'address': '北京市海淀区北三环西路甲18号',
        'postal_code': '100098',
        'description': '字节跳动成立于2012年，致力于用技术丰富人们的生活。',
        'website': 'https://www.bytedance.com',
        'status': 'verified',
        'established_date': date(2012, 3, 9)
    }
]

# 其他组织数据
OTHER_ORGANIZATIONS = [
    {
        'name': '中国科学院',
        'code': '12100000400000624D',
        'organization_type': 'other',
        'other_type': 'research_institute',
        'organization_nature': 'public',
        'leader_name': '侯建国',
        'leader_title': '院长',
        'industry_or_discipline': '科学研究',
        'scale': 'giant',
        'business_scope': '自然科学基础研究、应用研究和高技术创新研究',
        'regulatory_authority': '国务院',
        'contact_person': '人事局',
        'contact_position': '局长',
        'contact_phone': '010-68597289',
        'contact_email': 'rsc@cashq.ac.cn',
        'address': '北京市海淀区中关村北一条15号',
        'postal_code': '100190',
        'description': '中国科学院成立于1949年11月，是国家在科学技术方面的最高学术机构。',
        'website': 'https://www.cas.cn',
        'status': 'verified',
        'established_date': date(1949, 11, 1)
    },
    {
        'name': '中国红十字会',
        'code': '53100000500020462H',
        'organization_type': 'other',
        'other_type': 'ngo',
        'organization_nature': 'public',
        'leader_name': '陈竺',
        'leader_title': '会长',
        'industry_or_discipline': '人道主义救援',
        'scale': 'large',
        'business_scope': '救灾救助、应急救护、人道救助',
        'regulatory_authority': '民政部',
        'service_target': 'public',
        'contact_person': '组织部',
        'contact_position': '部长',
        'contact_phone': '010-65139999',
        'contact_email': 'info@redcross.org.cn',
        'address': '北京市东城区北新桥三条8号',
        'postal_code': '100007',
        'description': '中国红十字会成立于1904年，是中华人民共和国统一的红十字组织。',
        'website': 'https://www.redcross.org.cn',
        'status': 'verified',
        'established_date': date(1904, 3, 10)
    },
    {
        'name': '中华全国工商业联合会',
        'code': '51100000500000024G',
        'organization_type': 'other',
        'other_type': 'chamber',
        'organization_nature': 'national',
        'leader_name': '高云龙',
        'leader_title': '主席',
        'industry_or_discipline': '工商业服务',
        'scale': 'large',
        'business_scope': '工商业者利益代表、经济服务、政治参与、教育培训',
        'regulatory_authority': '统战部',
        'service_target': 'enterprises',
        'contact_person': '组织部',
        'contact_position': '部长',
        'contact_phone': '010-65232143',
        'contact_email': 'webmaster@acfic.org.cn',
        'address': '北京市朝阳门外大街225号',
        'postal_code': '100020',
        'description': '中华全国工商业联合会成立于1953年，是中国工商界组织的人民团体。',
        'website': 'https://www.acfic.org.cn',
        'status': 'verified',
        'established_date': date(1953, 10, 23)
    },
    {
        'name': '北京协和医院',
        'code': '12100000400000629A',
        'organization_type': 'other',
        'other_type': 'hospital',
        'organization_nature': 'public',
        'leader_name': '张抒扬',
        'leader_title': '院长',
        'industry_or_discipline': '医疗卫生',
        'scale': 'large',
        'business_scope': '医疗服务、医学教育、医学研究',
        'regulatory_authority': '国家卫健委',
        'service_target': 'patients',
        'contact_person': '人事处',
        'contact_position': '处长',
        'contact_phone': '010-69156114',
        'contact_email': 'hr@pumch.cn',
        'address': '北京市东城区帅府园1号',
        'postal_code': '100730',
        'description': '北京协和医院建于1921年，是集医疗、教学、科研于一体的现代化综合三级甲等医院。',
        'website': 'https://www.pumch.cn',
        'status': 'verified',
        'established_date': date(1921, 9, 19)
    },
    {
        'name': '中央电视台',
        'code': '12100000400001282K',
        'organization_type': 'other',
        'other_type': 'media',
        'organization_nature': 'public',
        'leader_name': '沈海雄',
        'leader_title': '台长',
        'industry_or_discipline': '广播电视',
        'scale': 'giant',
        'business_scope': '电视节目制作播出、新闻报道、文艺娱乐',
        'regulatory_authority': '国家广电总局',
        'service_target': 'public',
        'contact_person': '人事局',
        'contact_position': '局长',
        'contact_phone': '010-68508000',
        'contact_email': 'hr@cctv.com',
        'address': '北京市海淀区复兴路11号中央电视台',
        'postal_code': '100859',
        'description': '中央电视台成立于1958年，是中华人民共和国的国家电视台。',
        'website': 'https://www.cctv.com',
        'status': 'verified',
        'established_date': date(1958, 5, 1)
    }
]

# 职位和部门配置
UNIVERSITY_POSITIONS = {
    'owner': ['校长', '党委书记'],
    'admin': ['副校长', '教务处长', '学生处长', '科研处长', '人事处长'],
    'member': ['教授', '副教授', '讲师', '助教', '行政人员', '辅导员', '实验员']
}

UNIVERSITY_DEPARTMENTS = [
    '计算机学院', '经济管理学院', '外国语学院', '数学学院', '物理学院',
    '化学学院', '生命科学学院', '教务处', '学生处', '科研处', '人事处',
    '财务处', '后勤处', '图书馆', '网络中心'
]

ENTERPRISE_POSITIONS = {
    'owner': ['董事长', '总经理', '首席执行官'],
    'admin': ['副总经理', '技术总监', '人事总监', '财务总监', '市场总监'],
    'member': ['软件工程师', '产品经理', 'UI设计师', '测试工程师', '运营专员',
              '销售代表', '客服专员', '财务专员', '人事专员', '行政助理']
}

ENTERPRISE_DEPARTMENTS = [
    '技术部', '产品部', '设计部', '测试部', '运营部',
    '销售部', '市场部', '客服部', '人事部', '财务部',
    '行政部', '法务部', '采购部', '质量部'
]

OTHER_POSITIONS = {
    'owner': ['主任', '院长', '会长', '理事长', '总干事'],
    'admin': ['副主任', '副院长', '副会长', '秘书长', '部门负责人'],
    'member': ['研究员', '工程师', '专员', '助理', '秘书', '办事员']
}

OTHER_DEPARTMENTS = [
    '办公室', '人事部', '财务部', '业务部', '研发部',
    '宣传部', '组织部', '监察部', '后勤部', '信息部'
]


def generate_chinese_name(gender='random'):
    """
    生成中国人姓名
    
    Args:
        gender: 'male', 'female', 'random'
    
    Returns:
        str: 生成的中文姓名
    """
    surname = random.choice(CHINESE_SURNAMES)
    
    if gender == 'random':
        gender = random.choice(['male', 'female'])
    
    if gender == 'male':
        name_chars = MALE_NAME_CHARS
    else:
        name_chars = FEMALE_NAME_CHARS
    
    # 生成1-2个字的名字
    name_length = random.choices([1, 2], weights=[30, 70])[0]
    
    if name_length == 1:
        given_name = random.choice(name_chars)
    else:
        given_name = ''.join(random.sample(name_chars, 2))
    
    return surname + given_name


def generate_username(real_name, organization_name):
    """
    根据真实姓名和组织名称生成用户名
    
    Args:
        real_name: 真实姓名
        organization_name: 组织名称
    
    Returns:
        str: 生成的用户名
    """
    # 取组织名称的前几个字符作为前缀
    org_prefix = ''.join([c for c in organization_name if c.isalnum()])[:3]
    
    # 生成随机数字后缀
    suffix = random.randint(1000, 9999)
    
    # 组合用户名
    username = f"{org_prefix}_{real_name}_{suffix}"
    
    # 确保用户名唯一
    while User.objects.filter(username=username).exists():
        suffix = random.randint(1000, 9999)
        username = f"{org_prefix}_{real_name}_{suffix}"
    
    return username


def generate_email(username):
    """
    生成邮箱地址
    
    Args:
        username: 用户名
    
    Returns:
        str: 生成的邮箱地址
    """
    domains = ['163.com', 'qq.com', '126.com', 'gmail.com', 'sina.com']
    domain = random.choice(domains)
    
    # 简化用户名用于邮箱
    email_prefix = username.lower().replace('_', '')
    email = f"{email_prefix}@{domain}"
    
    # 确保邮箱唯一
    counter = 1
    while User.objects.filter(email=email).exists():
        email = f"{email_prefix}{counter}@{domain}"
        counter += 1
    
    return email


def generate_phone():
    """
    生成手机号码
    
    Returns:
        str: 生成的手机号码
    """
    prefixes = ['130', '131', '132', '133', '134', '135', '136', '137', '138', '139',
                '150', '151', '152', '153', '155', '156', '157', '158', '159',
                '180', '181', '182', '183', '184', '185', '186', '187', '188', '189']
    
    prefix = random.choice(prefixes)
    suffix = ''.join([str(random.randint(0, 9)) for _ in range(8)])
    phone = prefix + suffix
    
    # 确保手机号唯一
    while User.objects.filter(phone=phone).exists():
        suffix = ''.join([str(random.randint(0, 9)) for _ in range(8)])
        phone = prefix + suffix
    
    return phone


def create_organization(org_data):
    """
    创建组织
    
    Args:
        org_data: 组织数据字典
    
    Returns:
        Organization: 创建的组织对象
    """
    organization = Organization.objects.create(**org_data)
    
    # 创建组织配置
    OrganizationConfig.objects.create(
        organization=organization,
        auto_approve_members=True,
        require_email_verification=False,
        allow_member_invite=True,
        admin_can_manage_admins=True,
        member_can_view_all=True,
        max_members=1000,
        welcome_message=f"欢迎加入{organization.name}！"
    )
    
    return organization


def create_organization_user(organization, role, position_config, department_config):
    """
    创建组织用户
    
    Args:
        organization: 组织对象
        role: 用户角色 ('owner', 'admin', 'member')
        position_config: 职位配置字典
        department_config: 部门配置列表
    
    Returns:
        tuple: (User对象, OrganizationUser对象)
    """
    # 生成用户基本信息
    gender = random.choice(['male', 'female'])
    real_name = generate_chinese_name(gender)
    username = generate_username(real_name, organization.name)
    email = generate_email(username)
    phone = generate_phone()
    
    # 创建用户
    user = User.objects.create_user(
        username=username,
        email=email,
        password='123456',  # 默认密码
        real_name=real_name,
        phone=phone,
        gender=gender,
        age=random.randint(22, 55),
        user_type='organization',
        bio=f"我是{organization.name}的{random.choice(position_config[role])}，很高兴认识大家！"
    )
    
    # 创建组织用户
    org_user = OrganizationUser.objects.create(
        user=user,
        organization=organization,
        position=random.choice(position_config[role]),
        department=random.choice(department_config),
        permission=role,
        status='approved'
    )
    
    return user, org_user


def create_organizations():
    """
    批量创建组织和组织用户
    """
    print("开始创建组织和组织用户...")
    print("=" * 50)
    
    # 统计信息
    stats = {
        'organizations_created': 0,
        'users_created': 0,
        'owners_created': 0,
        'admins_created': 0,
        'members_created': 0,
        'universities': 0,
        'enterprises': 0,
        'other_orgs': 0
    }
    
    try:
        with transaction.atomic():
            # 创建大学
            print("\n1. 创建大学组织...")
            for i, uni_data in enumerate(UNIVERSITIES, 1):
                print(f"  创建大学 {i}: {uni_data['name']}")
                organization = create_organization(uni_data)
                stats['organizations_created'] += 1
                stats['universities'] += 1
                
                # 创建用户
                # 1个创建者
                user, org_user = create_organization_user(
                    organization, 'owner', UNIVERSITY_POSITIONS, UNIVERSITY_DEPARTMENTS
                )
                print(f"    创建者: {user.real_name} ({user.username})")
                stats['users_created'] += 1
                stats['owners_created'] += 1
                
                # 3-4个管理员
                admin_count = random.randint(3, 4)
                for j in range(admin_count):
                    user, org_user = create_organization_user(
                        organization, 'admin', UNIVERSITY_POSITIONS, UNIVERSITY_DEPARTMENTS
                    )
                    print(f"    管理员: {user.real_name} ({user.username})")
                    stats['users_created'] += 1
                    stats['admins_created'] += 1
                
                # 5-8个成员
                member_count = random.randint(5, 8)
                for j in range(member_count):
                    user, org_user = create_organization_user(
                        organization, 'member', UNIVERSITY_POSITIONS, UNIVERSITY_DEPARTMENTS
                    )
                    print(f"    成员: {user.real_name} ({user.username})")
                    stats['users_created'] += 1
                    stats['members_created'] += 1
            
            # 创建企业
            print("\n2. 创建企业组织...")
            for i, ent_data in enumerate(ENTERPRISES, 1):
                print(f"  创建企业 {i}: {ent_data['name']}")
                organization = create_organization(ent_data)
                stats['organizations_created'] += 1
                stats['enterprises'] += 1
                
                # 创建用户
                # 1个创建者
                user, org_user = create_organization_user(
                    organization, 'owner', ENTERPRISE_POSITIONS, ENTERPRISE_DEPARTMENTS
                )
                print(f"    创建者: {user.real_name} ({user.username})")
                stats['users_created'] += 1
                stats['owners_created'] += 1
                
                # 3-4个管理员
                admin_count = random.randint(3, 4)
                for j in range(admin_count):
                    user, org_user = create_organization_user(
                        organization, 'admin', ENTERPRISE_POSITIONS, ENTERPRISE_DEPARTMENTS
                    )
                    print(f"    管理员: {user.real_name} ({user.username})")
                    stats['users_created'] += 1
                    stats['admins_created'] += 1
                
                # 5-8个成员
                member_count = random.randint(5, 8)
                for j in range(member_count):
                    user, org_user = create_organization_user(
                        organization, 'member', ENTERPRISE_POSITIONS, ENTERPRISE_DEPARTMENTS
                    )
                    print(f"    成员: {user.real_name} ({user.username})")
                    stats['users_created'] += 1
                    stats['members_created'] += 1
            
            # 创建其他组织
            print("\n3. 创建其他组织...")
            for i, other_data in enumerate(OTHER_ORGANIZATIONS, 1):
                print(f"  创建其他组织 {i}: {other_data['name']}")
                organization = create_organization(other_data)
                stats['organizations_created'] += 1
                stats['other_orgs'] += 1
                
                # 创建用户
                # 1个创建者
                user, org_user = create_organization_user(
                    organization, 'owner', OTHER_POSITIONS, OTHER_DEPARTMENTS
                )
                print(f"    创建者: {user.real_name} ({user.username})")
                stats['users_created'] += 1
                stats['owners_created'] += 1
                
                # 3-4个管理员
                admin_count = random.randint(3, 4)
                for j in range(admin_count):
                    user, org_user = create_organization_user(
                        organization, 'admin', OTHER_POSITIONS, OTHER_DEPARTMENTS
                    )
                    print(f"    管理员: {user.real_name} ({user.username})")
                    stats['users_created'] += 1
                    stats['admins_created'] += 1
                
                # 5-8个成员
                member_count = random.randint(5, 8)
                for j in range(member_count):
                    user, org_user = create_organization_user(
                        organization, 'member', OTHER_POSITIONS, OTHER_DEPARTMENTS
                    )
                    print(f"    成员: {user.real_name} ({user.username})")
                    stats['users_created'] += 1
                    stats['members_created'] += 1
        
        # 输出统计信息
        print("\n" + "=" * 50)
        print("创建完成！统计信息：")
        print(f"总组织数: {stats['organizations_created']}")
        print(f"  - 大学: {stats['universities']}")
        print(f"  - 企业: {stats['enterprises']}")
        print(f"  - 其他组织: {stats['other_orgs']}")
        print(f"总用户数: {stats['users_created']}")
        print(f"  - 创建者: {stats['owners_created']}")
        print(f"  - 管理员: {stats['admins_created']}")
        print(f"  - 成员: {stats['members_created']}")
        
        # 数据库统计
        print("\n数据库统计：")
        print(f"组织总数: {Organization.objects.count()}")
        print(f"组织用户总数: {OrganizationUser.objects.count()}")
        print(f"用户总数: {User.objects.count()}")
        
        print("\n所有数据创建成功！")
        
    except Exception as e:
        print(f"\n创建过程中出现错误: {str(e)}")
        raise


if __name__ == '__main__':
    create_organizations()