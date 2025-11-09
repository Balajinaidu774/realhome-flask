import csv
from app import app, db, Property
import random
import os

def clean_column_names(headers):
    """Cleans column names: lowercase, strip spaces."""
    return [col.lower().strip() for col in headers]

def seed_database():
    """
    Reads data from the Boston Housing CSV ('real_estate.csv')
    using Python's built-in CSV module, maps 'rm' and 'medv'
    to our Property model, and populates the database.
    """
    print("Starting Boston Housing database seed (robust version)...")
    
    csv_file_path = 'real_estate.csv'
    
    if not os.path.exists(csv_file_path):
        print(f"Error: '{csv_file_path}' not found.")
        print("Please make sure the Boston Housing CSV is in your project directory.")
        return

    with app.app_context():
        # Clear existing properties from the database
        try:
            db.session.query(Property).delete()
            db.session.commit()
            print("Cleared existing properties from database.")
        except Exception as e:
            db.session.rollback()
            print(f"Error clearing database: {e}")
            return

        # List of placeholder images
        image_list = [
            "https://images.pexels.com/photos/106399/pexels-photo-106399.jpeg",
            "https://images.pexels.com/photos/186077/pexels-photo-186077.jpeg",
            "https://images.pexels.com/photos/323780/pexels-photo-323780.jpeg",
            "https://images.pexels.com/photos/1396122/pexels-photo-1396122.jpeg"
        ]
        
        properties_added_count = 0
        
        try:
            with open(csv_file_path, mode='r', encoding='utf-8') as file:
                # Use DictReader to read rows as dictionaries
                reader = csv.DictReader(file)
                
                # Clean the headers (column names)
                reader.fieldnames = clean_column_names(reader.fieldnames)
                
                # --- THIS IS THE FIX ---
                # Check if the required columns 'rm' and 'medv' exist
                if 'rm' not in reader.fieldnames or 'medv' not in reader.fieldnames:
                    print("Error: The CSV file does not seem to have the 'RM' or 'MEDV' columns.")
                    return
                
                print("CSV headers found and cleaned. Starting row import...")
                
                # Iterate over each row in the CSV
                for row in reader:
                    try:
                        # Safely get and convert 'medv' (price)
                        price_in_thousands_str = row.get('medv', '0')
                        if not price_in_thousands_str:  # Handle empty string
                            price_in_thousands = 0.0
                        else:
                            price_in_thousands = float(price_in_thousands_str)
                        
                        price = int(price_in_thousands * 1000)

                        # Safely get and convert 'rm' (rooms/bedrooms)
                        num_rooms_str = row.get('rm', '0')
                        if not num_rooms_str:  # Handle empty string
                            num_rooms = 0.0
                        else:
                            num_rooms = float(num_rooms_str)
                        
                        bedrooms = int(num_rooms)

                        # --- Create the Property object ---
                        new_property = Property(
                            price=price,
                            bedrooms=bedrooms,
                            
                            # --- Fake the rest of the data ---
                            address=f"{bedrooms} Room Home in Boston",
                            city="Boston",
                            state="MA",
                            zipcode="02118",
                            bathrooms=int(num_rooms / 2) if num_rooms > 1 else 1,
                            square_feet=int(num_rooms * 700),
                            property_type="Boston Home",
                            image_url=random.choice(image_list)
                        )
                        db.session.add(new_property)
                        properties_added_count += 1
                        
                    except (ValueError, TypeError) as e:
                        # This will catch any 'NaN' or other conversion error
                        print(f"Skipping problematic row: {row}. Error: {e}")
            
            # Commit all new properties to the database at once
            db.session.commit()
            print(f"Successfully added {properties_added_count} properties to the database.")

        except Exception as e:
            db.session.rollback()
            print(f"An error occurred during seeding: {e}")

if __name__ == '__main__':
    seed_database()