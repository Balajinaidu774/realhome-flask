import csv
from app import app, db, Property
import os
import random  # <-- IMPORT RANDOM

def clean_column_names(headers):
    """Cleans column names: lowercase, strip spaces."""
    return [col.lower().strip() for col in headers]

def safe_float_convert(value_str):
    """Safely converts a string to a float, handling empty strings or None."""
    if not value_str:
        return 0.0
    try:
        return float(value_str)
    except (ValueError, TypeError):
        return 0.0

def safe_int_convert(value_str):
    """Safely converts a string to an int, handling empty strings or None."""
    if not value_str:
        return 0
    try:
        return int(float(value_str))
    except (ValueError, TypeError):
        return 0

def seed_database():
    """
    Reads data from the Boston Housing CSV ('real_estate.csv')
    and maps ALL statistical columns to our new Property model,
    including a random placeholder image.
    """
    print("Starting Boston Housing database seed (Statistical Model)...")
    
    csv_file_path = 'real_estate.csv'
    
    if not os.path.exists(csv_file_path):
        print(f"Error: '{csv_file_path}' not found.")
        print("Please make sure the CSV is in your project directory.")
        return

    # === NEW: List of placeholder images ===
    image_list = [
        "https://images.pexels.com/photos/106399/pexels-photo-106399.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1",
        "https://images.pexels.com/photos/186077/pexels-photo-186077.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1",
        "https://images.pexels.com/photos/323780/pexels-photo-323780.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1",
        "https://images.pexels.com/photos/1396122/pexels-photo-1396122.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1",
        "https://images.pexels.com/photos/208736/pexels-photo-208736.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1",
        "https://images.pexels.com/photos/259588/pexels-photo-259588.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1"
    ]
    # ========================================

    with app.app_context():
        try:
            db.session.query(Property).delete()
            db.session.commit()
            print("Cleared existing properties from database.")
        except Exception as e:
            db.session.rollback()
            print(f"Error clearing database: {e}")
            return
        
        properties_added_count = 0
        
        try:
            with open(csv_file_path, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                reader.fieldnames = clean_column_names(reader.fieldnames)
                
                required_cols = ['crim', 'zn', 'indus', 'chas', 'nox', 'rm', 'age', 
                                 'dis', 'rad', 'tax', 'ptratio', 'b', 'lstat', 'medv']
                
                missing_cols = [col for col in required_cols if col not in reader.fieldnames]
                if missing_cols:
                    print(f"Error: The CSV file is missing required columns: {missing_cols}")
                    return
                
                print("CSV headers found and cleaned. Starting row import...")
                
                for row in reader:
                    try:
                        new_property = Property(
                            crim=safe_float_convert(row.get('crim')),
                            zn=safe_float_convert(row.get('zn')),
                            indus=safe_float_convert(row.get('indus')),
                            chas=safe_int_convert(row.get('chas')),
                            nox=safe_float_convert(row.get('nox')),
                            rm=safe_float_convert(row.get('rm')),
                            age=safe_float_convert(row.get('age')),
                            dis=safe_float_convert(row.get('dis')),
                            rad=safe_int_convert(row.get('rad')),
                            tax=safe_float_convert(row.get('tax')),
                            ptratio=safe_float_convert(row.get('ptratio')),
                            b=safe_float_convert(row.get('b')),
                            lstat=safe_float_convert(row.get('lstat')),
                            medv=safe_float_convert(row.get('medv')),
                            
                            # === NEW: Assign a random image ===
                            image_url=random.choice(image_list)
                        )
                        db.session.add(new_property)
                        properties_added_count += 1
                        
                    except Exception as e:
                        print(f"Skipping problematic row: {row}. Error: {e}")
            
            db.session.commit()
            print(f"Successfully added {properties_added_count} properties to the database.")

        except Exception as e:
            db.session.rollback()
            print(f"An error occurred during seeding: {e}")

if __name__ == '__main__':
    seed_database()