# 批量创建组织和组织用户脚本设计方案

## 1. 脚本概述

本脚本用于批量创建组织（Organization）和组织用户（OrganizationUser），支持三种组织类型：
- 大学（高校）
- 企业
- 其他组织

每个组织包含不同角色的用户：
- 1个创建者（owner）
- 3-4个管理员（admin）
- 至少5个成员（member）

## 2. 组织数据设计

### 2.1 大学（高校）数据
```python
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
        'established_date': '1898-07-03'
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
        'established_date': '1911-04-29'
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
        'established_date': '1905-09-14'
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
        'established_date': '1896-04-08'
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
        'established_date': '1937-07-07'
    }
]
```

### 2.2 企业数据
```python
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
        'established_date': '1998-11-11'
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
        'established_date': '1999-09-09'
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
        'established_date': '2000-01-01'
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
        'established_date': '1987-09-15'
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
        'established_date': '2012-03-09'
    }
]
```

### 2.3 其他组织数据
```python
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
        'established_date': '1949-11-01'
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
        'established_date': '1904-03-10'
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
        'established_date': '1953-10-23'
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
        'established_date': '1921-09-19'
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
        'established_date': '1958-05-01'
    }
]
```

## 3. 中国人姓名生成设计

### 3.1 常见姓氏（按使用频率排序）
```python
CHINESE_SURNAMES = [
    '王', '李', '张', '刘', '陈', '杨', '赵', '黄', '周', '吴',
    '徐', '孙', '胡', '朱', '高', '林', '何', '郭', '马', '罗',
    '梁', '宋', '郑', '谢', '韩', '唐', '冯', '于', '董', '萧',
    '程', '曹', '袁', '邓', '许', '傅', '沈', '曾', '彭', '吕',
    '苏', '卢', '蒋', '蔡', '贾', '丁', '魏', '薛', '叶', '阎'
]
```

### 3.2 常见名字字符
```python
# 男性常用字
MALE_NAME_CHARS = [
    '伟', '强', '磊', '军', '勇', '涛', '明', '超', '亮', '华',
    '建', '国', '峰', '学', '永', '杰', '松', '波', '民', '友',
    '志', '清', '坚', '庆', '祥', '东', '文', '辉', '力', '固',
    '之', '段', '殿', '泰', '盛', '雄', '琛', '钧', '冠', '策',
    '腾', '楠', '榕', '风', '航', '弘', '义', '兴', '良', '飞'
]

# 女性常用字
FEMALE_NAME_CHARS = [
    '秀', '娟', '英', '华', '慧', '巧', '美', '娜', '静', '淑',
    '惠', '珠', '翠', '雅', '芝', '玉', '萍', '红', '娥', '玲',
    '芬', '芳', '燕', '彩', '春', '菊', '兰', '凤', '洁', '梅',
    '琳', '素', '云', '莲', '真', '环', '雪', '荣', '爱', '妹',
    '霞', '香', '月', '莺', '媛', '艳', '瑞', '凡', '佳', '嘉'
]
```

## 4. 组织用户角色分配策略

### 4.1 角色分配规则
- **创建者（owner）**: 每个组织1个，通常是组织的主要负责人
- **管理员（admin）**: 每个组织3-4个，包括各部门负责人
- **成员（member）**: 每个组织至少5个，最多15个普通员工

### 4.2 职位分配策略

#### 大学职位
```python
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
```

#### 企业职位
```python
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
```

#### 其他组织职位
```python
OTHER_POSITIONS = {
    'owner': ['主任', '院长', '会长', '理事长', '总干事'],
    'admin': ['副主任', '副院长', '副会长', '秘书长', '部门负责人'],
    'member': ['研究员', '工程师', '专员', '助理', '秘书', '办事员']
}

OTHER_DEPARTMENTS = [
    '办公室', '人事部', '财务部', '业务部', '研发部',
    '宣传部', '组织部', '监察部', '后勤部', '信息部'
]
```

## 5. 脚本执行流程

1. **初始化环境**
   - 导入必要的模块
   - 设置Django环境
   - 连接数据库

2. **生成组织数据**
   - 创建大学组织（5个）
   - 创建企业组织（5个）
   - 创建其他组织（5个）
   - 为每个组织创建配置

3. **生成用户数据**
   - 为每个组织生成用户
   - 分配角色和权限
   - 设置职位和部门
   - 生成中国人姓名

4. **数据验证和统计**
   - 验证数据完整性
   - 输出创建统计
   - 记录执行日志

## 6. 预期输出

- **组织总数**: 15个（大学5个 + 企业5个 + 其他组织5个）
- **用户总数**: 约135-195个
  - 创建者: 15个
  - 管理员: 45-60个
  - 成员: 75-120个
- **所有用户**: 真实的中国人姓名
- **组织信息**: 基于真实存在的组织

## 7. 注意事项

1. 确保生成的组织代码（统一社会信用代码等）格式正确
2. 用户邮箱和手机号避免重复
3. 密码统一设置为 `123456`
4. 所有组织状态设为 `verified`（已认证）
5. 所有组织用户状态设为 `approved`（已通过）
6. 创建时间设置为当前时间
7. 确保数据库事务的完整性