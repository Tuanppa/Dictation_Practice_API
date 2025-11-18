"""update ranking modes to 6 modes

Revision ID: 7c4058171e17
Revises: 
Create Date: 2025-11-17 21:53:43.563370

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '7c4058171e17'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade database schema - handles all scenarios safely
    """
    
    # Get connection for raw SQL
    conn = op.get_bind()
    
    # ===== STEP 1: Check current state =====
    
    # Check if table exists
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'top_performance_overall'
        )
    """))
    table_exists = result.scalar()
    print(f"📊 Table exists: {table_exists}")
    
    # Check current enum values
    result = conn.execute(text("""
        SELECT enumlabel 
        FROM pg_enum 
        JOIN pg_type ON pg_enum.enumtypid = pg_type.oid 
        WHERE pg_type.typname = 'rankingmodeenum'
        ORDER BY enumsortorder
    """))
    current_enum_values = [row[0] for row in result]
    print(f"📋 Current enum: {current_enum_values}")
    
    expected_values = {'all_time', 'last_month', 'current_month', 'last_week', 'current_week', 'by_lesson'}
    enum_correct = set(current_enum_values) == expected_values
    
    # ===== STEP 2: Check if fully migrated =====
    
    if table_exists and enum_correct:
        print("✅ Already fully migrated! Nothing to do.")
        return
    
    # ===== STEP 3: Drop existing table and enum =====
    
    print("🔧 Dropping existing table and enum...")
    conn.execute(text("DROP TABLE IF EXISTS top_performance_overall CASCADE"))
    conn.execute(text("DROP TYPE IF EXISTS rankingmodeenum CASCADE"))
    print("✅ Dropped old table and enum")
    
    # ===== STEP 4: Create new enum =====
    
    print("🔧 Creating new enum with 6 modes...")
    conn.execute(text("""
        CREATE TYPE rankingmodeenum AS ENUM (
            'all_time',
            'last_month',
            'current_month', 
            'last_week',
            'current_week',
            'by_lesson'
        )
    """))
    print("✅ Enum created")
    
    # ===== STEP 5: Create table =====
    
    print("🔧 Creating table 'top_performance_overall'...")
    conn.execute(text("""
        CREATE TABLE top_performance_overall (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            mode rankingmodeenum NOT NULL,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            rank INTEGER NOT NULL,
            score FLOAT NOT NULL DEFAULT 0.0,
            time INTEGER NOT NULL DEFAULT 0,
            performance FLOAT NOT NULL DEFAULT 0.0,
            lesson_id UUID REFERENCES lessons(id) ON DELETE CASCADE
        )
    """))
    print("✅ Table created")
    
    # ===== STEP 6: Create indexes =====
    
    print("🔧 Creating indexes...")
    conn.execute(text("CREATE INDEX ix_top_performance_overall_id ON top_performance_overall(id)"))
    conn.execute(text("CREATE INDEX ix_top_performance_overall_mode ON top_performance_overall(mode)"))
    conn.execute(text("CREATE INDEX ix_top_performance_overall_user_id ON top_performance_overall(user_id)"))
    conn.execute(text("CREATE INDEX ix_top_performance_overall_lesson_id ON top_performance_overall(lesson_id)"))
    print("✅ Indexes created")
    
    # ===== DONE =====
    
    print("")
    print("=" * 50)
    print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
    print("=" * 50)
    print("📊 New ranking modes:")
    print("   - all_time")
    print("   - last_month (NEW)")
    print("   - current_month (NEW)")
    print("   - last_week (NEW)")
    print("   - current_week (NEW)")
    print("   - by_lesson")
    print("=" * 50)


def downgrade() -> None:
    """
    Downgrade to 4 modes
    """
    conn = op.get_bind()
    
    conn.execute(text("DROP TABLE IF EXISTS top_performance_overall CASCADE"))
    conn.execute(text("DROP TYPE IF EXISTS rankingmodeenum CASCADE"))
    
    conn.execute(text("""
        CREATE TYPE rankingmodeenum AS ENUM (
            'all_time',
            'monthly',
            'weekly',
            'by_lesson'
        )
    """))
    
    print("⬇️  Downgraded to 4 ranking modes")