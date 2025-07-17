import csv
import os
import sys

# 添加 backend 目录到系统路径
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(BACKEND_DIR)

# 从 app 模块导入应用实例和数据库
from app import app  # 导入 Flask 应用实例（现在 __init__.py 中已定义）
from app import db
from app.models import Features

def import_features_from_csv():
    DLIB_BASE_DIR = os.path.abspath(os.path.join(BACKEND_DIR, 'dlib_data'))
    csv_path = os.path.join(DLIB_BASE_DIR, 'features_all.csv')
    
    print("特征文件路径：", csv_path)
    print("文件是否存在：", os.path.exists(csv_path))
    
    if not os.path.exists(csv_path):
        print("错误：文件不存在")
        return

    # 使用应用上下文执行数据库操作
    with app.app_context():
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                count = 0
                
                for row_num, row in enumerate(reader, 1):
                    if not row:
                        print(f"跳过空行：{row_num}")
                        continue
                    
                    if len(row) != 129:
                        print(f"跳过无效行 {row_num}：列数不符（预期129，实际{len(row)}）")
                        continue
                    
                    try:
                        person_name = row[0].strip()
                        features = [float(val.strip()) for val in row[1:129]]
                    except ValueError as e:
                        print(f"跳过行 {row_num}：格式错误 - {e}")
                        continue
                    
                    feature_data = {f"feature_{i+1}": features[i] for i in range(128)}
                    new_feature = Features(person_name=person_name,** feature_data)
                    db.session.add(new_feature)
                    count += 1
                    
                    if count % 100 == 0:
                        db.session.commit()
                        print(f"已导入 {count} 条数据")
                
                db.session.commit()
                print(f"导入完成，共成功导入 {count} 条数据")
        
        except Exception as e:
            db.session.rollback()
            print(f"导入失败：{e}")

if __name__ == "__main__":
    import_features_from_csv()