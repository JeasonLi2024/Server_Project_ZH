import pymysql

MYSQL_CONFIG = {
    "host": "100.116.251.123",
    "port": 3306,
    "user": "bupt_zh",
    "password": "123456",
    "db": "bupt_zh_db",
    "charset": "utf8mb4",
}

TABLE_CONFIG = {
    "tag1_enterprise": {
        "table": "tag1_enterprise_match",
        "primary_key": "Pid",
        "tag_field": "tag1_id",
        "extra_fields": [],
    },
    "tag2_enterprise": {
        "table": "tag2_enterprise_match",
        "primary_key": "Pid",
        "tag_field": "tag2_id",
        "extra_fields": ["required_number"],
    },
    "tag1_student": {
        "table": "tag1_stu_match",
        "primary_key": "Sid",
        "tag_field": "tag1_id",
        "extra_fields": [],
    },
    "tag2_student": {
        "table": "tag2_stu_match",
        "primary_key": "Sid",
        "tag_field": "tag2_id",
        "extra_fields": [],
    },
}

def insert_general_match(match_type, data_list):
    if match_type not in TABLE_CONFIG:
        raise ValueError(f"未知匹配类型: {match_type}")

    cfg = TABLE_CONFIG[match_type]
    table = cfg["table"]
    primary_key = cfg["primary_key"]
    tag_field = cfg["tag_field"]
    extra_fields = cfg["extra_fields"]

    conn = pymysql.connect(**MYSQL_CONFIG)
    try:
        with conn.cursor() as cursor:
            for idx, item in enumerate(data_list):
                print(f"处理第{idx+1}条数据：{item}")

                keys = item.keys()
                if primary_key not in keys or tag_field not in keys:
                    raise ValueError(f"缺少必要字段：{primary_key} 或 {tag_field}")

                pk = item[primary_key]
                if isinstance(pk, list):
                    raise ValueError(f"{primary_key} 字段不能是列表，只能是单个值: {pk}")

                tag_ids = item[tag_field]
                if not isinstance(tag_ids, list):
                    tag_ids = [tag_ids]

                if "required_number" in item and "required_number" not in extra_fields:
                    raise ValueError(f"match_type={match_type} 不支持字段 required_number，但数据中存在")

                required_numbers = []
                if "required_number" in extra_fields:
                    rn = item.get("required_number", None)
                    if rn is None:
                        required_numbers = [1] * len(tag_ids)
                    else:
                        if not isinstance(rn, list):
                            required_numbers = [rn] * len(tag_ids)
                        else:
                            required_numbers = rn
                    if len(required_numbers) != len(tag_ids):
                        raise ValueError("required_number 列表长度必须与 tag_id 数量一致")

                del_sql = f"DELETE FROM {table} WHERE {primary_key} = %s"
                cursor.execute(del_sql, (pk,))

                insert_sql = f"INSERT INTO {table} ({primary_key}, {tag_field}"
                if "required_number" in extra_fields:
                    insert_sql += ", required_number"
                insert_sql += ") VALUES "

                placeholders = []
                values = []
                for idx2, tag_id in enumerate(tag_ids):
                    placeholders.append("(%s, %s" + (", %s" if "required_number" in extra_fields else "") + ")")
                    if "required_number" in extra_fields:
                        values.extend([pk, tag_id, required_numbers[idx2]])
                    else:
                        values.extend([pk, tag_id])

                insert_sql += ",".join(placeholders)
                cursor.execute(insert_sql, values)

            conn.commit()
    finally:
        conn.close()