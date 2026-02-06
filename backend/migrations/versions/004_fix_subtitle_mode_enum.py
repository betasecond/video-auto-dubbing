"""Fix subtitle mode enum to uppercase

Revision ID: 004
Revises: 003
Create Date: 2026-02-06 12:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 修改枚举值为大写以匹配 TaskStatus 的模式
    # 1. 先删除 default 约束
    op.execute("ALTER TABLE tasks ALTER COLUMN subtitle_mode DROP DEFAULT")

    # 2. 重命名旧类型
    op.execute("ALTER TYPE subtitlemode RENAME TO subtitlemode_old")

    # 3. 创建新类型（大写）
    op.execute("CREATE TYPE subtitlemode AS ENUM ('NONE', 'EXTERNAL', 'BURN')")

    # 4. 转换列类型，将小写转为大写
    op.execute("""
        ALTER TABLE tasks
        ALTER COLUMN subtitle_mode TYPE subtitlemode
        USING (CASE
            WHEN subtitle_mode::text = 'none' THEN 'NONE'::subtitlemode
            WHEN subtitle_mode::text = 'external' THEN 'EXTERNAL'::subtitlemode
            WHEN subtitle_mode::text = 'burn' THEN 'BURN'::subtitlemode
        END)
    """)

    # 5. 删除旧类型
    op.execute("DROP TYPE subtitlemode_old")

    # 6. 设置新的 default 值
    op.execute("ALTER TABLE tasks ALTER COLUMN subtitle_mode SET DEFAULT 'EXTERNAL'::subtitlemode")


def downgrade() -> None:
    # 恢复为小写
    op.execute("ALTER TABLE tasks ALTER COLUMN subtitle_mode DROP DEFAULT")
    op.execute("ALTER TYPE subtitlemode RENAME TO subtitlemode_old")
    op.execute("CREATE TYPE subtitlemode AS ENUM ('none', 'external', 'burn')")
    op.execute("""
        ALTER TABLE tasks
        ALTER COLUMN subtitle_mode TYPE subtitlemode
        USING (CASE
            WHEN subtitle_mode::text = 'NONE' THEN 'none'::subtitlemode
            WHEN subtitle_mode::text = 'EXTERNAL' THEN 'external'::subtitlemode
            WHEN subtitle_mode::text = 'BURN' THEN 'burn'::subtitlemode
        END)
    """)
    op.execute("DROP TYPE subtitlemode_old")
    op.execute("ALTER TABLE tasks ALTER COLUMN subtitle_mode SET DEFAULT 'external'::subtitlemode")
