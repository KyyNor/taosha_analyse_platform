def getacctno(v_acct: str) -> str:
    """
    计算带校验位的账号（基于MySQL存储过程的Python实现）
    
    参数:
        v_acct (str): 输入的账号（长度必须为16位）
    
    返回:
        str: 带校验位的完整账号（17位），如果输入长度不是16位则返回17个'0'
    """
    # 初始化返回值为17个0
    acct_no = '00000000000000000'
    
    # 检查表（与MySQL中的check_table完全相同）
    check_table = '100908070605040302051004090308020701080502100704010906040801050902061003020406081001030507010203040506070809060107020803090410030609010407100205070310060209050108090705030110080604100908070605040302051004090308020701080502100704010906040801050902061003020406081001030507010203040506070809'
    
    # 在账号末尾添加一个'0'（与MySQL中的temp_acct一致）
    temp_acct = v_acct + '0'
    rawlen = len(temp_acct)
    
    # 只有当输入账号长度为16时才进行计算（rawlen=17）
    if rawlen == 17:
        sub_1 = rawlen - 1  # 初始化为16（最后一个字符的位置）
        work_value = 0
        
        # 从后向前遍历每个字符
        while sub_1 >= 0:
            current_char = temp_acct[sub_1]
            # 如果当前字符不是'0'，则进行校验计算
            if current_char != '0':
                # 将字符转换为数字
                digit = int(current_char)
                
                # 计算在检查表中的位置（这个计算需要与MySQL版本保持一致）
                # 注意：Python的字符串索引从0开始，而MySQL从1开始
                pos = sub_1 * 18 + (digit - 1) * 2
                # 从检查表中截取2位数字并加到work_value上
                check_value = int(check_table[pos:pos+2])
                work_value += check_value
            
            # 移动到前一个字符
            sub_1 -= 1
        
        # 如果计算结果不为0，则生成校验位
        if work_value != 0:
            # 计算模10的余数作为校验位
            remainder = work_value % 10
            # 组合账号：前16位原始账号 + 计算出的校验位
            acct_no = v_acct[:16] + str(remainder)
    
    return acct_no