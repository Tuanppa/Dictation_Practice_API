"""update_ranking_mode_enum_fixed

Revision ID: 5bf3b48e17e7
Revises: 
Create Date: 2025-11-17 16:35:50.390328

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5bf3b48e17e7'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    """
    Upgrade: Change enum from 4 values to 6 values
    """
    
    # Step 1: Drop NOT NULL constraint temporarily
    op.execute(
        "ALTER TABLE top_performance_overall "
        "ALTER COLUMN mode DROP NOT NULL"
    )
    
    # Step 2: Convert column to text type temporarily
    op.execute(
        "ALTER TABLE top_performance_overall "
        "ALTER COLUMN mode TYPE text"
    )
    
    # Step 3: Drop old enum type
    op.execute("DROP TYPE IF EXISTS rankingmodeenum")
    
    # Step 4: Create new enum type with all 6 values
    op.execute("""
        CREATE TYPE rankingmodeenum AS ENUM (
            'all_time',
            'last_month',
            'current_month',
            'last_week',
            'current_week',
            'by_lesson'
        )
    """)
    
    # Step 5: Convert column back to enum type
    op.execute("""
        ALTER TABLE top_performance_overall 
        ALTER COLUMN mode TYPE rankingmodeenum 
        USING mode::rankingmodeenum
    """)
    
    # Step 6: Restore NOT NULL constraint
    op.execute(
        "ALTER TABLE top_performance_overall "
        "ALTER COLUMN mode SET NOT NULL"
    )
    
    # Step 7: Recreate index
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_top_performance_overall_mode 
        ON top_performance_overall(mode)
    """)
    
    print("✅ Migration completed!")


def downgrade():
    """
    Downgrade: Rollback to old enum
    """
    
    op.execute(
        "ALTER TABLE top_performance_overall "
        "ALTER COLUMN mode DROP NOT NULL"
    )
    
    op.execute(
        "ALTER TABLE top_performance_overall "
        "ALTER COLUMN mode TYPE text"
    )
    
    op.execute("DROP TYPE IF EXISTS rankingmodeenum")
    
    op.execute("""
        CREATE TYPE rankingmodeenum AS ENUM (
            'all_time',
            'monthly',
            'weekly',
            'by_lesson'
        )
    """)
    
    op.execute("""
        ALTER TABLE top_performance_overall 
        ALTER COLUMN mode TYPE rankingmodeenum 
        USING mode::rankingmodeenum
    """)
    
    op.execute(
        "ALTER TABLE top_performance_overall "
        "ALTER COLUMN mode SET NOT NULL"
    )
    
    print("✅ Downgrade completed!")
