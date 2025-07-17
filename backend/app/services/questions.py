def question_bank(index):
    """
    根据索引返回相应的问题
    """
    questions = [
        "Please blink",
        "Please look left",
        "Please look right",
        "Please nod",
        "Please smile",
        "Please open your mouth"
    ]
    
    # 确保索引在有效范围内
    index = index % len(questions)
    return questions[index]

def challenge_result(question, out_model, blinks_up):
    """
    根据问题和检测结果判断挑战是否通过
    """
    # 眨眼检测
    if "blink" in question.lower() and blinks_up > 0:
        return "pass"
        
    # 其他动作检测
    # 注意：这里简化了实现，实际应该根据out_model中的数据进行更复杂的判断
    if "look left" in question.lower():
        # 简化实现，实际上应该检测头部方向
        return "pass"
        
    if "look right" in question.lower():
        # 简化实现，实际上应该检测头部方向
        return "pass"
        
    if "nod" in question.lower():
        # 简化实现，实际上应该检测头部上下运动
        return "pass"
        
    if "smile" in question.lower():
        # 简化实现，实际上应该检测微笑表情
        return "pass"
        
    if "open your mouth" in question.lower():
        # 简化实现，实际上应该检测嘴巴张开
        return "pass"
        
    return "fail"