# Step-by-Step Fix Guide for ExamZen

## 🚨 Current Issues
1. Database schema mismatch (missing columns)
2. Template errors (using wrong methods)
3. 500 errors on dashboard, create_exam, notifications

## ✅ STEP 1: Fix Database (MOST IMPORTANT)

### Run the migration script:
```bash
python migrate_db.py
```

**Expected output:**
```
🔄 Starting database migration...
✅ Added related_id column
✅ Added action_taken column
✅ All tables created/updated
✅ DATABASE MIGRATION COMPLETED SUCCESSFULLY!
```

### If migration fails with connection error:
Check your `app.py` or `.env` file for database connection string. It should look like:
```python
SQLALCHEMY_DATABASE_URI = 'postgresql://username:password@localhost/examzen'
```

## ✅ STEP 2: Restart Flask Server

```bash
# Stop current server (Ctrl+C)
flask run
```

## ✅ STEP 3: Test Each Feature

### Test as Teacher (Examiner):
1. Login as teacher
2. Go to Dashboard - Should work now ✅
3. Go to Create Exam - Should work now ✅
4. Go to My Classes - Should work ✅
5. Go to Notifications - Should work now ✅

### Test as Student:
1. Login as student
2. Go to Dashboard - Should work ✅
3. Go to My Classes - Should work ✅
4. Go to My Results - Should work ✅
5. Go to Notifications - Should work ✅

## 🔧 What Was Fixed

### 1. Database Schema
- ✅ Added `related_id` column to `notification` table
- ✅ Added `action_taken` column to `notification` table
- ✅ Created `organization_teacher` table

### 2. Template Fixes
- ✅ Fixed `create_exam.html`: Changed `cls.students|length` to `cls.students.count()`
- ✅ Fixed `view_class.html`: Removed reference to non-existent `classroom.creator`

### 3. Code Improvements
- ✅ Added proper error handling
- ✅ Fixed query object issues
- ✅ Added mobile responsiveness

## 📋 Checklist After Migration

- [ ] Run `python migrate_db.py`
- [ ] See success message
- [ ] Restart Flask with `flask run`
- [ ] Login as teacher
- [ ] Access dashboard (no 500 error)
- [ ] Access create exam (no 500 error)
- [ ] Access notifications (no 500 error)
- [ ] Login as student
- [ ] Access my classes
- [ ] Access my results

## 🆘 If You Still Get Errors

### Error: "column notification.related_id does not exist"
**Solution:** The migration didn't run successfully. Try:
```bash
# Option 1: Run migration again
python migrate_db.py

# Option 2: Manual SQL (in psql or pgAdmin)
ALTER TABLE notification ADD COLUMN related_id INTEGER;
ALTER TABLE notification ADD COLUMN action_taken BOOLEAN DEFAULT FALSE;
```

### Error: "TypeError: object of type 'AppenderBaseQuery' has no len()"
**Solution:** This is fixed in the templates. Make sure you pulled the latest changes.

### Error: "Class object has no attribute 'creator'"
**Solution:** This is fixed in view_class.html. The template now uses `classroom.teachers.first()`.

## 🎯 Next Steps (After Everything Works)

Once the basic functionality works, we can:
1. Implement organization-teacher invitation system
2. Add exam-taking functionality with timer
3. Add complaint system
4. Improve mobile responsiveness further
5. Add more features

## 💡 Pro Tips

1. **Always run migrations before starting the server**
2. **Check console for errors** - they tell you exactly what's wrong
3. **Test one feature at a time** - don't try to test everything at once
4. **Keep a backup** of your database before major changes

## 📞 Need Help?

If you're still stuck after following these steps, share:
1. The exact error message from console
2. Which step you're on
3. What you've tried so far
