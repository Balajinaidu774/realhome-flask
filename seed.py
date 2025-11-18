import csv
from app import app, db, Property
import os
import random
import datetime
import math

def clean_column_names(headers):
    """Cleans column names: lowercase, strip spaces."""
    return [col.lower().strip() for col in headers]

def safe_float_convert(value_str):
    """Safely converts a string to a float, handling empty strings or None."""
    if value_str is None or value_str == '':
        return 0.0
    try:
        return float(value_str)
    except (ValueError, TypeError):
        return 0.0

def safe_int_convert(value_str):
    """Safely converts a string to an int, handling empty strings or None."""
# --- REMOVED: Static image_list ---
# image_list = [ ... ]

# --- Realistic Data Lists ---
street_list = [
    "Beacon St", "Newbury St", "Commonwealth Ave", "Boylston St", "Charles St", 
    "Tremont St", "Hanover St", "Salem St", "Washington St", "School St",
    "Arlington St", "Dartmouth St", "Clarendon St", "Marlborough St", "Pinckney St"
]
type_list = [
    "Historic Brownstone", "Modern Apartment", "Cozy Condo", "Downtown Loft",
    "Family Home", "Beacon Hill Flat", "Luxury Penthouse", "Studio Apartment"
]
description_list = [
    "Charming property located in a historic Boston neighborhood. Features original hardwood floors, a newly renovated kitchen, and stunning city views. Close to public transit and local parks.",
    "A stunning example of modern architecture, this home boasts floor-to-ceiling windows, smart home technology, and a private roof deck. Ideal for professionals seeking luxury and convenience.",
    "This cozy and bright condo is the perfect urban retreat. With an open-plan living area, updated appliances, and low condo fees, it's a fantastic opportunity for first-time buyers.",
    "Spacious downtown loft with exposed brick walls, 12-foot ceilings, and industrial-chic finishes. Located in a vibrant area close to top restaurants, shops, and art galleries.",
    "Beautiful family home on a quiet, tree-lined street. Offers a large backyard, a spacious master suite, and a finished basement perfect for a playroom or home office.",
    "Quintessential Beacon Hill flat offering classic charm and modern updates. Just steps away from Boston Common and the finest shops and dining on Charles Street."
]
architect_list = [
    "Boston Design Architects", "Fenway Group", "Back Bay Planners", "Cambridge Architectural", "Unknown"
]
builder_list = [
    "Historic Homes LLC", "ModernBuild Co.", "Premium Properties", "Cityscape Developers", "Unknown"
]
# --- End of Lists ---

def seed_database():
    """
    Reads data from the Boston Housing CSV ('real_estate.csv')
    and maps ALL statistical columns to our new Property model.
    """
    print("Starting Boston Housing database seed (Statistical Model)...")
    
    csv_file_path = 'real_estate.csv'
    
    if not os.path.exists(csv_file_path):
        print(f"Error: '{csv_file_path}' not found.")
        print("Please make sure the CSV is in your project directory.")
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
        
        properties_added_count = 0
        
        try:
            with open(csv_file_path, mode='r', encoding='utf-8') as file:
                # Use DictReader to read rows as dictionaries
                reader = csv.DictReader(file)
                
                # Clean the headers (column names)
                reader.fieldnames = clean_column_names(reader.fieldnames)
                
                required_cols = ['crim', 'zn', 'indus', 'chas', 'nox', 'rm', 'age', 
                                 'dis', 'rad', 'tax', 'ptratio', 'b', 'lstat', 'medv']
                
                missing_cols = [col for col in required_cols if col not in reader.fieldnames]
                if missing_cols:
                    print(f"Error: The CSV file is missing required columns: {missing_cols}")
                    return
                
                print("CSV headers found and cleaned. Starting row import...")
                
                # IMAGE PROVIDER: 'picsum' or 'unsplash' (env var IMAGE_PROVIDER)
                IMAGE_PROVIDER = os.environ.get('IMAGE_PROVIDER', 'picsum').lower()

                # --- UPDATED: Use enumerate to get a unique index for each row ---
                for index, row in enumerate(reader):
                    try:
                        # read medv early to decide price band
                        medv_val = safe_float_convert(row.get('medv'))

                        # Determine price tier using dataset quantiles used elsewhere
                        # Tier 0: medv < 17 (lower), 1: 17-22 (lower-mid), 2: 22-26 (mid-high), 3: >26 (premium)
                        if medv_val < 17:
                            tier = 0
                        elif medv_val < 22:
                            tier = 1
                        elif medv_val < 26:
                            tier = 2
                        else:
                            tier = 3

                        # Choose keywords per tier for Unsplash
                        tier_keywords = {
                            0: 'cozy,house',
                            1: 'modern,apartment',
                            2: 'luxury,house',
                            3: 'penthouse,luxury'
                        }

                        # Generate provider-specific unique image URL
                        if IMAGE_PROVIDER == 'picsum':
                            # deterministic seed uses index and medv rounded
                            seed_val = f"{index}_{int(math.floor(medv_val*10))}"
                            unique_image_url = f"https://picsum.photos/seed/{seed_val}/800/600"
                        else:
                            # Unsplash: query by keyword per tier and use sig for uniqueness
                            kw = tier_keywords.get(tier, 'house')
                            unique_image_url = f"https://source.unsplash.com/800x600/?{kw}&sig={index + 1}"

                        fake_lat = 42.3601 + random.uniform(-0.05, 0.05)
                        fake_lon = -71.0589 + random.uniform(-0.05, 0.05)
                        street_num = random.randint(10, 999)
                        fake_street = f"{street_num} {random.choice(street_list)}"
                        fake_type = random.choice(type_list)
                        fake_desc = random.choice(description_list)
                        fake_architect = random.choice(architect_list)
                        fake_builder = random.choice(builder_list)
                        fake_verified = random.choice([True, False, False])
                        fake_date = (datetime.date.today() - datetime.timedelta(days=random.randint(30, 730))).strftime("%b %d, %Y")
                        
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
                            
                            # --- UPDATED: Use the new unique URL ---
                            image_url=unique_image_url,
                            # -------------------------------------
                            
                            lat=fake_lat,
                            lon=fake_lon,
                            property_type=fake_type,
                            street_name=fake_street,
                            description=fake_desc,
                            architect=fake_architect,
                            builder=fake_builder,
                            quality_verified=fake_verified,
                            last_verified_on=fake_date if fake_verified else None
                        )
                        db.session.add(new_property)
                        properties_added_count += 1
                        
                    except Exception as e:
                        print(f"Skipping problematic row: {row}. Error: {e}")
            
            # Commit all new properties to the database at once
            db.session.commit()
            print(f"Successfully added {properties_added_count} properties to the database.")

        except Exception as e:
            db.session.rollback()
            print(f"An error occurred during seeding: {e}")

if __name__ == '__main__':
    seed_database()