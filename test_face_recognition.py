import sys
print("Python版本:", sys.version)

try:
    import dlib
    print("dlib版本:", dlib.__version__)
    print("dlib导入成功")
except ImportError as e:
    print("dlib导入失败:", e)
    
try:
    import face_recognition
    print("face_recognition导入成功")
except ImportError as e:
    print("face_recognition导入失败:", e) 