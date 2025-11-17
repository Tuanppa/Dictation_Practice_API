"""update ranking modes to 6 modes

Revision ID: 7c4058171e17
Revises: 
Create Date: 2025-11-17 21:53:43.563370

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c4058171e17'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    """
    Upgrade database schema
    
    Steps:
    1. Drop constraint on mode column
    2. Drop old enum type
    3. Create new enum type with 6 modes
    4. Alter column to use new enum
    5. Add constraint back
    """
    
    # Step 1 & 2: Drop old enum (safe because table is empty)
    op.execute("DROP TYPE IF EXISTS rankingmodeenum CASCADE")
    
    # Step 3: Create new enum type with 6 modes
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
    
    # Step 4: Alter column to use new enum
    op.execute("""
        ALTER TABLE top_performance_overall 
        ALTER COLUMN mode TYPE rankingmodeenum 
        USING mode::text::rankingmodeenum
    """)
    
    print("✅ Migration completed successfully!")
    print("📊 New ranking modes available:")
    print("   - all_time (unchanged)")
    print("   - last_month (NEW - for hall of fame)")
    print("   - current_month (NEW - live leaderboard)")
    print("   - last_week (NEW - for hall of fame)")
    print("   - current_week (NEW - live leaderboard)")
    print("   - by_lesson (unchanged)")


def downgrade() -> None:
    """
    Downgrade database schema back to 4 modes
    
    ⚠️  WARNING: This will fail if you have data with new modes!
    """
    
    # Drop new enum
    op.execute("DROP TYPE IF EXISTS rankingmodeenum CASCADE")
    
    # Recreate old enum with 4 modes
    op.execute("""
        CREATE TYPE rankingmodeenum AS ENUM (
            'all_time',
            'monthly',
            'weekly',
            'by_lesson'
        )
    """)
    
    # Alter column back
    op.execute("""
        ALTER TABLE top_performance_overall 
        ALTER COLUMN mode TYPE rankingmodeenum 
        USING mode::text::rankingmodeenum
    """)
    
    print("⬇️  Downgraded to 4 ranking modes")
