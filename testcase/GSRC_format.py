hardblocks_lines = []
pl_lines = []

with open('n30.block', 'r') as f:
    lines = f.readlines()   # 返回列表，每个元素是一行（含换行符）
    for idx, line in enumerate(lines):
        if idx<4:
            hardblocks_lines.append(line)
        elif idx < 34:
            parts = line.split()
            sb = parts[0]
            width = int(parts[1])
            height = int(parts[2])
            new_line = f'{sb} hardrectilinear 4 (0, 0) (0, {height}) ({width}, {height}) ({width}, 0) \n'
            hardblocks_lines.append(new_line)
        elif idx > 34:
            pl_line = line.replace('terminal ', '')
            pl_lines.append(pl_line)

n30_hardblocks_path = 'n30.hardblocks'
n30_pl_path = 'n30.pl'

with open(n30_hardblocks_path, 'w') as f:
    f.writelines(hardblocks_lines)
    
with open(n30_pl_path, 'w') as f:
    f.writelines(pl_lines)

            
            
            
            

            