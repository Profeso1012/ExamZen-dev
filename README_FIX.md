# ExamZen - Database Fix & System Recovery

## 🚨 Problem Summary
Your ExamZen application has 500 errors because the database schema doesn't match the code. The models were updated but the database wasn't migrated.

## ✅ THE FIX (3 Simple Steps)

### Step 1: Run Migration
```bash
python migrate_db.py
```
**Wait for:** `✅ DATABASE MIGRATION COMPLETED SUCCESSFULLY!`

### Step 2: Test Database
```bash
python test_db.py
```
**Wait for:** `✅ ALL TESTS PASSED!`

### Step 3: Start Server
```bash
flask run
```

## 📁 Files Created to Help You

| File | Purpose |
|------|---------|
| `migrate_db.py` | Automatically fixes database schema |
| `test_db.py` | Verifies database is correctly configured |
| `QUICK_FIX.txt` | Quick reference card |
| `STEP_BY_STEP_FIX.md` | Detailed troubleshooting guide |
| `FIX_DATABASE.md` | Database migration documentation |

## 🔧 What Gets Fixed

### Database Changes:
- ✅ Adds `related_id` column to `notification` table
- ✅ Adds `action_taken` column to `notification` table
- ✅ Creates `organization_teacher` table

### Template Fixes:
- ✅ Fixed `create_exam.html` - Changed `|length` to `.count()`
- ✅ Fixed `view_class.html` - Removed non-existent `creator` reference

## 🎯 After Fix Works

Once everything is working (no 500 errors), we can systematically implement:

### Phase 1: Teacher Features ✅
- Dashboard
- Create exams
- Manage classes
- View results
- Send notifications

### Phase 2: Student Features ✅
- Take exams
- View results
- View classes
- Receive notifications
- Submit complaints

### Phase 3: Organization Features
- Invite teachers
- View all classes
- Monitor system

## 📊 Testing Checklist

After running the migration:

**Teacher Account:**
- [ ] Login successful
- [ ] Dashboard loads (no 500 error)
- [ ] Create Exam page loads
- [ ] My Exams page loads
- [ ] My Classes page loads
- [ ] Notifications page loads
- [ ] Can create a class
- [ ] Can create an exam

**Student Account:**
- [ ] Login successful
- [ ] Dashboard loads
- [ ] My Classes page loads
- [ ] My Results page loads
- [ ] Notifications page loads
- [ ] Can view class details

## 🆘 Troubleshooting

### Still getting "column notification.related_id does not exist"?

**Option A:** Run migration again
```bash
python migrate_db.py
```

**Option B:** Manual SQL (if migration fails)
```sql
-- Connect to your PostgreSQL database
psql -U your_username -d examzen

-- Run these commands:
ALTER TABLE notification ADD COLUMN related_id INTEGER;
ALTER TABLE notification ADD COLUMN action_taken BOOLEAN DEFAULT FALSE;
```

### Can't connect to database?

Check your database configuration in `app.py`:
```python
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://username:password@localhost/examzen'
```

Make sure:
1. PostgreSQL is running
2. Database `examzen` exists
3. Username and password are correct
4. User has proper permissions

### Create database if it doesn't exist:
```bash
psql -U postgres
CREATE DATABASE examzen;
\q
```

## 🚀 Quick Commands Reference

```bash
# Fix database
python migrate_db.py

# Test database
python test_db.py

# Start server
flask run

# Create new database (if needed)
psql -U postgres -c "CREATE DATABASE examzen;"

# Check database tables
python -c "from examzen import app, db; from sqlalchemy import inspect; app.app_context().push(); print(inspect(db.engine).get_table_names())"
```

## 📞 Still Need Help?

If you're still experiencing issues after following these steps:

1. Run `python test_db.py` and share the output
2. Share the exact error message from Flask console
3. Confirm you ran `python migrate_db.py` successfully

## 🎉 Success Indicators

You'll know everything is working when:
- ✅ No 500 errors on any page
- ✅ Dashboard loads for both teachers and students
- ✅ Create Exam page loads without errors
- ✅ Notifications page loads without errors
- ✅ Classes page loads without errors

---

**Remember:** Always run `python migrate_db.py` first, then `python test_db.py` to verify, then `flask run` to start the server.
