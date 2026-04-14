"""
Database migration script to add new columns and tables
Run this with: python migrate_db.py
"""
from examzen import app, db
from sqlalchemy import text, inspect

def migrate_database():
    with app.app_context():
        print("🔄 Starting database migration...\n")
        
        try:
            inspector = inspect(db.engine)
            
            # Check if notification table exists
            if 'notification' in inspector.get_table_names():
                columns = [col['name'] for col in inspector.get_columns('notification')]
                
                # Add related_id if missing
                if 'related_id' not in columns:
                    print("📝 Adding related_id column to notification table...")
                    with db.engine.begin() as conn:
                        conn.execute(text("ALTER TABLE notification ADD COLUMN related_id INTEGER"))
                    print("✅ Added related_id column\n")
                else:
                    print("✓ related_id column already exists\n")
                
                # Add action_taken if missing
                if 'action_taken' not in columns:
                    print("📝 Adding action_taken column to notification table...")
                    with db.engine.begin() as conn:
                        conn.execute(text("ALTER TABLE notification ADD COLUMN action_taken BOOLEAN DEFAULT FALSE"))
                    print("✅ Added action_taken column\n")
                else:
                    print("✓ action_taken column already exists\n")
            
            # Create all tables (including organization_teacher, class_invitation, org_class_request)
            print("📝 Creating/updating all tables...")
            db.create_all()
            print("✅ All tables created/updated\n")
            
            print("=" * 50)
            print("✅ DATABASE MIGRATION COMPLETED SUCCESSFULLY!")
            print("=" * 50)
            print("\n🚀 You can now restart your Flask server with: flask run\n")
            
        except Exception as e:
            print("\n" + "=" * 50)
            print("❌ ERROR DURING MIGRATION")
            print("=" * 50)
            print(f"\nError: {e}\n")
            print("Possible solutions:")
            print("1. Check your database connection in app.py")
            print("2. Ensure PostgreSQL is running")
            print("3. Check database user permissions")
            print("\nIf the error persists, you may need to manually run SQL commands.")
            print("See FIX_DATABASE.md for manual SQL commands.\n")

if __name__ == '__main__':
    migrate_database()
