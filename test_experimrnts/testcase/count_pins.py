import re

nets_lines = []
total_dgrees = 0

pattern = r'^NetDegree : '

with open('n10.nets', 'r') as f:
    lines = f.readlines()   # 返回列表，每个元素是一行（含换行符）
    for idx, line in enumerate(lines):
        if re.match(pattern, line):
            total_dgrees = int(line.split()[2])+total_dgrees
            
print(total_dgrees)

    

            
            
            
            

            