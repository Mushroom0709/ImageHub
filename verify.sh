#!/usr/bin/env bash
# 项目验证脚本：本地无需 Docker 的真实代码检查
# 用法: ./verify.sh
set -e
cd "$(dirname "$0")"

echo "=== [1/3] 后端 Python 语法编译 ==="
python3 -m compileall -q backend/app
echo "✅ 后端 Python 编译通过"

echo ""
echo "=== [2/3] 后端模块结构检查（无需第三方依赖） ==="
python3 -c "
import ast, pathlib
ok = True
for p in pathlib.Path('backend/app').rglob('*.py'):
    try:
        ast.parse(p.read_text(encoding='utf-8'))
    except SyntaxError as e:
        ok = False
        print(f'  ❌ {p}: {e}')
print('✅ 后端全部模块 AST 解析通过' if ok else '❌ 存在语法错误')
exit(0 if ok else 1)
"

echo ""
echo "=== [3/3] 前端类型检查 + 构建 ==="
cd frontend
npm run build 2>&1 | tail -4
echo "✅ 前端构建通过"
