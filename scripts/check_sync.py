import os

rutas_dir = '/app/app/rutas'
problemas = []

for root, dirs, files in os.walk(rutas_dir):
    for f in files:
        if not f.endswith('.py'):
            continue
        path = os.path.join(root, f)
        with open(path) as fh:
            lines = fh.readlines()
        for i, line in enumerate(lines):
            stripped = line.strip()
            if ('@require_auth' in stripped or '@require_role' in stripped) and not stripped.startswith('#'):
                for j in range(i+1, min(i+6, len(lines))):
                    next_line = lines[j].strip()
                    if next_line.startswith('def '):
                        short = path.replace('/app/app/', '')
                        problemas.append(short + ':' + str(j+1) + ': ' + next_line[:70])
                        break
                    elif next_line.startswith('async def') or next_line.startswith('@'):
                        break

for p in sorted(set(problemas)):
    print(p)
print('Total: ' + str(len(set(problemas))))
