# Database Migration Fix Guide

## Problem
The database schema in the code doesn't match the actual database. New columns and tables were added to models.py but the database wasn't updated.

## Solution - Run Migration

### Step 1: Run the migration script
```bash
python migrate_db.py
```

This will:
- Add `related_id` column to `notification` table
- Add `action_taken` column to `notification` table  
- Create `organization_teacher` table

### Step 2: Verify the migration
After running the script, you should see:
```
✓ Added related_id column
✓ Added action_taken column
✓ All tables created/updated
✅ Database migration completed successfully!
```

### Step 3: Restart your Flask server
```bash
flask run
```

## Alternative: Fresh Database (if migration fails)

If the migration script fails, you can recreate the database:

### Option A: Drop and recreate (CAUTION: This deletes all data!)
```python
# In Python shell or create a script
from examzen import app, db

with app.app_context():
    db.drop_all()  # Deletes all tables
    db.create_all()  # Recreates with new schema
```

### Option B: Manual SQL (PostgreSQL)
```sql
-- Add columns to notification table
ALTER TABLE notification ADD COLUMN related_id INTEGER;
ALTER TABLE notification ADD COLUMN action_taken BOOLEAN DEFAULT FALSE;

-- Create organization_teacher table
CREATE TABLE organization_teacher (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER REFERENCES organization(id),
    teacher_id INTEGER REFERENCES "user"(id),
    status VARCHAR(20) DEFAULT 'pending',
    invited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    responded_at TIMESTAMP
);
```

## Errors Fixed

### 1. ❌ `column notification.related_id does not exist`
**Fixed by:** Adding `related_id` column to notification table

### 2. ❌ `TypeError: object of type 'AppenderBaseQuery' has no len()`
**Fixed by:** Changed `cls.students|length` to `cls.students.count()` in templates

### 3. ❌ `'Class object' has no attribute 'creator'`
**Fixed by:** Using `classroom.teachers.first()` instead of `classroom.creator`

## Next Steps After Migration

1. ✅ Run `python migrate_db.py`
2. ✅ Restart Flask server
3. ✅ Test teacher dashboard
4. ✅ Test student dashboard
5. ✅ Test notifications
6. ✅ Test class creation

## If You Still Have Issues

Check the console output for specific errors and share them. Common issues:
- Database connection problems
- Permission issues
- Conflicting data in existing tables
