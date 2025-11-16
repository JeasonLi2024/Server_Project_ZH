#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import django
import random
from datetime import date, timedelta
from django.contrib.auth.hashers import make_password

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Project_Zhihui.settings')
django.setup()

from user.models import User, Student, Tag1, Tag2, Tag1StuMatch, Tag2StuMatch
from organization.models import University

# 中国大学名称列表
CHINESE_UNIVERSITIES = [
    '北京邮电大学', '清华大学', '北京大学', '中国人民大学', '北京理工大学',
    '北京航空航天大学', '北京师范大学', '中央财经大学', '对外经济贸易大学', '北京外国语大学',
    '复旦大学', '上海交通大学', '同济大学', '华东师范大学', '上海财经大学',
    '华东理工大学', '东华大学', '上海外国语大学', '上海大学', '华东政法大学',
    '浙江大学', '杭州电子科技大学', '浙江工业大学', '宁波大学', '浙江师范大学',
    '南京大学', '东南大学', '南京理工大学', '南京航空航天大学', '河海大学',
    '南京师范大学', '苏州大学', '中国矿业大学', '江南大学', '南京农业大学',
    '中山大学', '华南理工大学', '暨南大学', '华南师范大学', '深圳大学',
    '南方科技大学', '广东工业大学', '华南农业大学', '广州大学', '汕头大学',
    '华中科技大学', '武汉大学', '华中师范大学', '中南财经政法大学', '武汉理工大学',
    '华中农业大学', '中国地质大学', '湖北大学', '武汉科技大学', '三峡大学',
    '四川大学', '电子科技大学', '西南交通大学', '西南财经大学', '四川师范大学',
    '成都理工大学', '西南石油大学', '四川农业大学', '西南科技大学', '成都信息工程大学',
    '西安交通大学', '西北工业大学', '西安电子科技大学', '长安大学', '西北大学',
    '陕西师范大学', '西安理工大学', '西安建筑科技大学', '西北农林科技大学', '西安科技大学',
    '天津大学', '南开大学', '天津师范大学', '天津工业大学', '天津理工大学',
    '重庆大学', '西南大学', '重庆邮电大学', '重庆交通大学', '重庆理工大学',
    '山东大学', '中国海洋大学', '中国石油大学', '山东师范大学', '青岛大学',
    '济南大学', '山东科技大学', '青岛科技大学', '山东理工大学', '烟台大学',
    '大连理工大学', '东北大学', '辽宁大学', '大连海事大学', '东北财经大学',
    '沈阳工业大学', '辽宁师范大学', '大连大学', '沈阳大学', '辽宁工程技术大学',
    '吉林大学', '东北师范大学', '长春理工大学', '东北电力大学', '吉林师范大学',
    '哈尔滨工业大学', '哈尔滨工程大学', '东北林业大学', '东北农业大学', '哈尔滨师范大学',
    '河北工业大学', '燕山大学', '河北大学', '河北师范大学', '石家庄铁道大学',
    '郑州大学', '河南大学', '河南师范大学', '河南理工大学', '华北水利水电大学',
    '湖南大学', '中南大学', '湖南师范大学', '湘潭大学', '长沙理工大学',
    '南昌大学', '江西师范大学', '江西财经大学', '华东交通大学', '江西理工大学',
    '福州大学', '厦门大学', '华侨大学', '福建师范大学', '集美大学',
    '安徽大学', '中国科学技术大学', '合肥工业大学', '安徽师范大学', '安徽理工大学',
    '广西大学', '广西师范大学', '桂林电子科技大学', '桂林理工大学', '广西民族大学',
    '海南大学', '海南师范大学', '海南医学院', '琼州学院', '海南热带海洋学院',
    '云南大学', '昆明理工大学', '云南师范大学', '云南农业大学', '西南林业大学',
    '贵州大学', '贵州师范大学', '贵阳医学院', '贵州财经大学', '遵义医学院',
    '西藏大学', '西藏民族大学', '西藏农牧学院', '拉萨师范高等专科学校',
    '兰州大学', '西北师范大学', '兰州理工大学', '兰州交通大学', '甘肃农业大学',
    '青海大学', '青海师范大学', '青海民族大学', '青海医学院',
    '宁夏大学', '北方民族大学', '宁夏师范学院', '宁夏医科大学',
    '新疆大学', '石河子大学', '新疆师范大学', '新疆农业大学', '新疆医科大学',
    '内蒙古大学', '内蒙古工业大学', '内蒙古师范大学', '内蒙古农业大学', '内蒙古科技大学'
]

# 中国人常见姓氏
CHINESE_SURNAMES = [
    '王', '李', '张', '刘', '陈', '杨', '赵', '黄', '周', '吴',
    '徐', '孙', '胡', '朱', '高', '林', '何', '郭', '马', '罗',
    '梁', '宋', '郑', '谢', '韩', '唐', '冯', '于', '董', '萧',
    '程', '曹', '袁', '邓', '许', '傅', '沈', '曾', '彭', '吕',
    '苏', '卢', '蒋', '蔡', '贾', '丁', '魏', '薛', '叶', '阎',
    '余', '潘', '杜', '戴', '夏', '钟', '汪', '田', '任', '姜',
    '范', '方', '石', '姚', '谭', '廖', '邹', '熊', '金', '陆',
    '郝', '孔', '白', '崔', '康', '毛', '邱', '秦', '江', '史',
    '顾', '侯', '邵', '孟', '龙', '万', '段', '漕', '钱', '汤'
]

# 中国人常见名字（男性）
CHINESE_MALE_NAMES = [
    '伟', '强', '磊', '军', '洋', '勇', '艳', '娟', '静', '敏',
    '杰', '涛', '明', '超', '亮', '刚', '平', '辉', '鹏', '华',
    '建', '国', '民', '永', '健', '世', '广', '志', '义', '兴',
    '良', '海', '山', '仁', '波', '宁', '贵', '福', '生', '龙',
    '元', '全', '国', '胜', '学', '祥', '才', '发', '武', '新',
    '利', '清', '飞', '彬', '富', '顺', '信', '子', '杰', '涛',
    '昌', '成', '康', '星', '光', '天', '达', '安', '岩', '中',
    '茂', '进', '林', '有', '坚', '和', '彪', '博', '诚', '先',
    '敬', '震', '振', '壮', '会', '思', '群', '豪', '心', '邦',
    '承', '乐', '绍', '功', '松', '善', '厚', '庆', '磊', '民'
]

# 中国人常见名字（女性）
CHINESE_FEMALE_NAMES = [
    '秀', '娟', '英', '华', '慧', '巧', '美', '娜', '静', '淑',
    '惠', '珠', '翠', '雅', '芝', '玉', '萍', '红', '娥', '玲',
    '芬', '芳', '燕', '彩', '春', '菊', '兰', '凤', '洁', '梅',
    '琳', '素', '云', '莲', '真', '环', '雪', '荣', '爱', '妹',
    '霞', '香', '月', '莺', '媛', '艳', '瑞', '凡', '佳', '嘉',
    '琼', '勤', '珍', '贞', '莉', '桂', '娣', '叶', '璧', '璐',
    '娅', '琦', '晶', '妍', '茜', '秋', '珊', '莎', '锦', '黛',
    '青', '倩', '婷', '姣', '婉', '娴', '瑾', '颖', '露', '瑶',
    '怡', '婵', '雁', '蓓', '纨', '仪', '荷', '丹', '蓉', '眉',
    '君', '琴', '蕊', '薇', '菁', '梦', '岚', '苑', '婕', '馨'
]

# 专业列表
MAJORS = [
    '计算机科学与技术', '软件工程', '网络工程', '信息安全', '数据科学与大数据技术',
    '人工智能', '物联网工程', '数字媒体技术', '电子信息工程', '通信工程',
    '自动化', '电气工程及其自动化', '机械设计制造及其自动化', '车辆工程', '材料科学与工程',
    '化学工程与工艺', '生物工程', '环境工程', '土木工程', '建筑学',
    '工商管理', '市场营销', '会计学', '财务管理', '人力资源管理',
    '国际经济与贸易', '金融学', '经济学', '法学', '汉语言文学',
    '英语', '新闻学', '广告学', '心理学', '教育学',
    '数学与应用数学', '物理学', '化学', '生物科学', '地理科学',
    '临床医学', '护理学', '药学', '中医学', '口腔医学',
    '艺术设计', '音乐学', '美术学', '舞蹈学', '戏剧影视文学'
]

def generate_chinese_name(gender='random'):
    """生成中国人姓名"""
    surname = random.choice(CHINESE_SURNAMES)
    
    if gender == 'random':
        gender = random.choice(['male', 'female'])
    
    if gender == 'male':
        # 男性名字，1-2个字
        if random.random() < 0.7:  # 70%概率是两个字的名字
            name = random.choice(CHINESE_MALE_NAMES) + random.choice(CHINESE_MALE_NAMES)
        else:
            name = random.choice(CHINESE_MALE_NAMES)
    else:
        # 女性名字，1-2个字
        if random.random() < 0.7:  # 70%概率是两个字的名字
            name = random.choice(CHINESE_FEMALE_NAMES) + random.choice(CHINESE_FEMALE_NAMES)
        else:
            name = random.choice(CHINESE_FEMALE_NAMES)
    
    return surname + name, gender

def generate_student_id(school, year):
    """生成学号"""
    # 简单的学号生成规则：年份后两位 + 学校代码 + 4位随机数
    school_code = str(hash(school) % 100).zfill(2)
    random_num = str(random.randint(1000, 9999))
    return f"{year}{school_code}{random_num}"

def generate_email(name, student_id):
    """生成邮箱"""
    # 使用拼音或学号生成邮箱
    domains = ['163.com', 'qq.com', 'gmail.com', 'sina.com', 'bupt.edu.cn', 'stu.bupt.edu.cn']
    return f"{student_id}@{random.choice(domains)}"

def create_students(count=500):
    """创建学生用户"""
    print(f"开始创建 {count} 个学生用户...")
    
    # 获取所有Tag1和Tag2
    all_tag1 = list(Tag1.objects.all())
    all_tag2 = list(Tag2.objects.all())
    
    if not all_tag1 or not all_tag2:
        print("错误：没有找到Tag1或Tag2数据，请先创建标签数据")
        return
    
    # 获取所有大学
    all_universities = list(University.objects.all())
    if not all_universities:
        print("错误：没有找到大学数据，请先导入大学信息")
        return
    
    print(f"找到 {len(all_tag1)} 个兴趣标签，{len(all_tag2)} 个能力标签，{len(all_universities)} 所大学")
    
    created_count = 0
    failed_count = 0
    
    for i in range(count):
        try:
            # 生成基本信息
            real_name, gender = generate_chinese_name()
            university = random.choice(all_universities)
            major = random.choice(MAJORS)
            grade = random.choice(['2021', '2022', '2023', '2024'])
            student_id = generate_student_id(university.school, grade)
            
            # 确保学号唯一
            while Student.objects.filter(student_id=student_id).exists():
                student_id = generate_student_id(school, grade)
            
            username = f"student_{student_id}"
            email = generate_email(real_name, student_id)
            
            # 确保用户名和邮箱唯一
            counter = 1
            original_username = username
            original_email = email
            
            while User.objects.filter(username=username).exists():
                username = f"{original_username}_{counter}"
                counter += 1
            
            counter = 1
            while User.objects.filter(email=email).exists():
                email_parts = original_email.split('@')
                email = f"{email_parts[0]}_{counter}@{email_parts[1]}"
                counter += 1
            
            # 创建用户
            user = User.objects.create(
                username=username,
                email=email,
                real_name=real_name,
                gender=gender,
                age=random.randint(18, 25),
                user_type='student',
                password=make_password('123456'),  # 默认密码
                bio=f"我是来自{university.school}{major}专业的学生，很高兴认识大家！"
            )
            
            # 创建学生档案
            expected_graduation = date(int(grade) + 4, 6, 30)  # 假设4年制本科
            
            student = Student.objects.create(
                user=user,
                student_id=student_id,
                school=university,
                major=major,
                grade=grade,
                education_level='undergraduate',
                status='studying',
                expected_graduation=expected_graduation
            )
            
            # 随机关联3-5个Tag1（兴趣标签）
            tag1_count = random.randint(3, 5)
            selected_tag1 = random.sample(all_tag1, min(tag1_count, len(all_tag1)))
            
            for tag1 in selected_tag1:
                Tag1StuMatch.objects.create(student=student, tag1=tag1)
            
            # 随机关联2-3个Tag2（能力标签）
            tag2_count = random.randint(2, 3)
            selected_tag2 = random.sample(all_tag2, min(tag2_count, len(all_tag2)))
            
            for tag2 in selected_tag2:
                Tag2StuMatch.objects.create(student=student, tag2=tag2)
            
            created_count += 1
            
            if created_count % 50 == 0:
                print(f"已创建 {created_count} 个学生用户...")
                
        except Exception as e:
            failed_count += 1
            print(f"创建第 {i+1} 个学生时出错: {str(e)}")
            continue
    
    print(f"\n创建完成！")
    print(f"成功创建: {created_count} 个学生用户")
    print(f"创建失败: {failed_count} 个")
    print(f"\n统计信息:")
    print(f"总用户数: {User.objects.count()}")
    print(f"学生用户数: {Student.objects.count()}")
    print(f"Tag1关联数: {Tag1StuMatch.objects.count()}")
    print(f"Tag2关联数: {Tag2StuMatch.objects.count()}")

if __name__ == '__main__':
    create_students(500)