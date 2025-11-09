import pandas as pd
from app import app, db, Property

def seed_database():
    """
    Reads data from 'real_estate.csv' and populates the Property table.
    """
    print("Starting database seed...")
    
    try:
        # Read the CSV file
        df = pd.read_csv('real_estate.csv')
    except FileNotFoundError:
        print("Error: 'real_estate.csv' not found.")
        print("Please download it from Kaggle and place it in the project directory.")
        return
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    # Use the app context to interact with the database
    with app.app_context():
        # Optional: Clear the table first if you want to avoid duplicates on re-run
        try:
            db.session.query(Property).delete()
            db.session.commit()
            print("Cleared existing properties from database.")
        except Exception as e:
            db.session.rollback()
            print(f"Error clearing database: {e}")
            return

        # Iterate over each row in the DataFrame
        for index, row in df.iterrows():
            # Create a new Property object
            new_property = Property(
                price=row.get('price', 0),
                address=row.get('address'),
                city=row.get('city'),
                state=row.get('state'),
                zipcode=row.get('zipcode'),
                bedrooms=row.get('bedrooms'),
                bathrooms=row.get('bathrooms'),
                square_feet=row.get('square_feet'),
                property_type=row.get('property_type'),
                image_url=row.get('image_url')
            )
            
            # Add the new property to the session
            db.session.add(new_property)
        
        # Commit all new properties to the database
        try:
            db.session.commit()
            print(f"Successfully added {len(df)} properties to the database.")
        except Exception as e:
            db.session.rollback()
            print(f"Error committing to database: {e}")

if __name__ == '__main__':
    seed_database()