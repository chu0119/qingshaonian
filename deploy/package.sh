#!/bin/bash
# ============================================================
# 打包当前系统为迁移包
# 在当前开发机运行: bash deploy/package.sh
# ============================================================

set -e
cd "$(dirname "$0")/.."

echo "=== 打包后端代码 ==="
tar -czf deploy/qingshaonian_backend.tar.gz \
    backend/app/ \
    backend/alembic/ \
    backend/requirements.txt \
    backend/setup_production.py \
    --exclude='__pycache__' \
    --exclude='*.pyc'
echo "  后端: deploy/qingshaonian_backend.tar.gz"

echo "=== 打包前端构建 ==="
tar -czf deploy/qingshaonian_frontend.tar.gz \
    frontend/dist/
echo "  前端: deploy/qingshaonian_frontend.tar.gz"

echo "=== 打包数据库 ==="
# 导出数据库（需要在服务器上运行）
echo "  提示: 在旧服务器上运行以下命令导出数据库:"
echo "  mysqldump -u root -p qingshaonian > deploy/qingshaonian_db.sql"

echo ""
echo "=== 打包完成 ==="
echo "文件列表:"
ls -lh deploy/*.tar.gz 2>/dev/null
echo ""
echo "部署步骤:"
echo "  1. 上传部署包到新服务器:"
echo "     scp deploy/* root@<新服务器IP>:/tmp/"
echo "  2. 在新服务器上运行迁移脚本:"
echo "     sudo bash /tmp/migrate.sh"
echo "  3. 导入数据库（如需从旧服务器迁移）:"
echo "     mysql -u root -p qingshaonian < /tmp/qingshaonian_db.sql"
