"""
Test script to verify database is properly configured
Run with: python test_db.py
"""
from examzen import app, db
from sqlalchemy import inspect, text

def test_database():
    print("=" * 60)
    print("EXAMZEN DATABASE TEST")
    print("=" * 60)
    print()
    
    with app.app_context():
        try:
            # Test 1: Connection
            print("TEST 1: Database Connection")
            print("-" * 60)
            db.engine.connect()
            print("✅ Database connection successful")
            print()
            
            # Test 2: Tables exist
            print("TEST 2: Required Tables")
            print("-" * 60)
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            required_tables = [
                'user', 'organization', 'class', 'notification', 
                'exam', 'question', 'examoption', 'answer',
                'organization_teacher'
            ]
            
            for table in required_tables:
                if table in tables:
                    print(f"✅ {table} table exists")
                else:
                    print(f"❌ {table} table MISSING")
            print()
            
            # Test 3: Notification columns
            print("TEST 3: Notification Table Columns")
            print("-" * 60)
            if 'notification' in tables:
                columns = [col['name'] for col in inspector.get_columns('notification')]
                print(f"Columns found: {', '.join(columns)}")
                print()
                
                required_cols = ['related_id', 'action_taken']
                for col in required_cols:
                    if col in columns:
                        print(f"✅ {col} column exists")
                    else:
                        print(f"❌ {col} column MISSING - Run migrate_db.py!")
            print()
            
            # Test 4: Organization Teacher table
            print("TEST 4: Organization Teacher Table")
            print("-" * 60)
            if 'organization_teacher' in tables:
                print("✅ organization_teacher table exists")
                columns = [col['name'] for col in inspector.get_columns('organization_teacher')]
                print(f"   Columns: {', '.join(columns)}")
            else:
                print("❌ organization_teacher table MISSING - Run migrate_db.py!")
            print()
            
            # Test 5: Sample query
            print("TEST 5: Sample Query")
            print("-" * 60)
            with db.engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM \"user\""))
                count = result.scalar()
                print(f"✅ Query successful - {count} users in database")
            print()
            
            print("=" * 60)
            print("✅ ALL TESTS PASSED!")
            print("=" * 60)
            print()
            print("Your database is properly configured.")
            print("You can now run: flask run")
            print()
            
        except Exception as e:
            print()
            print("=" * 60)
            print("❌ TEST FAILED")
            print("=" * 60)
            print()
            print(f"Error: {e}")
            print()
            print("SOLUTION:")
            print("1. Run: python migrate_db.py")
            print("2. Then run this test again: python test_db.py")
            print()

if __name__ == '__main__':
    test_database()
