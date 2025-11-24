import csv
from app import app, db, Property
import os
import random
import datetime
import math
import urllib.parse

def clean_column_names(headers):
    """Cleans column names: lowercase, strip spaces."""
    return [col.lower().strip() for col in headers]

def safe_float_convert(value_str):
    if value_str is None or value_str == '':
        return 0.0
    try:
        return float(value_str)
    except (ValueError, TypeError):
        return 0.0

def safe_int_convert(value_str):
    if value_str is None or value_str == '':
        return 0
    try:
        return int(float(value_str))
    except (ValueError, TypeError):
        return 0

# --- Realistic Data Lists (Updated for Indian Context optionally, or kept mixed) ---
street_list = [
    "MG Road", "Indiranagar 100ft Rd", "Koramangala 5th Block", "Brigade Road", "Lavelle Road", 
    "Sarjapur Road", "Whitefield Main Rd", "Jayanagar 4th Block", "Richmond Road", "Vittal Mallya Rd",
    "Bandra West", "Juhu Tara Road", "Marine Drive", "Worli Sea Face", "Defense Colony"
]
type_list = [
    "Modern Apartment", "Luxury Villa", "Cozy Flat", "Penthouse Suite",
    "Independent House", "Gated Community Villa", "Studio Apartment", "Duplex"
]
description_list = [
    "Beautiful property located in a prime location with easy access to metro and tech parks.",
    "Spacious home with excellent ventilation, vaastu compliant, and premium fittings.",
    "Luxury apartment with world-class amenities including swimming pool, gym, and clubhouse.",
    "Cozy home perfect for a small family, located in a peaceful residential layout.",
    "High-end property with italian marble flooring and modular kitchen.",
    "Newly constructed property with 24/7 power backup and security."
]
architect_list = ["Hafeez Contractor", "Total Environment", "Prestige Designs", "Sobha Architects", "Unknown"]
builder_list = ["DLF", "Prestige Group", "Brigade Group", "Godrej Properties", "Unknown"]

def seed_database():
    print("Starting Real Estate database seed (INR Mode)...")
    
    csv_file_path = 'real_estate.csv'
    
    if not os.path.exists(csv_file_path):
        print(f"Error: '{csv_file_path}' not found.")
        return

    with app.app_context():
        try:
            db.session.query(Property).delete()
            db.session.commit()
            print("Cleared existing properties.")
        except Exception as e:
            db.session.rollback()
            print(f"Error clearing database: {e}")
            return
        
        properties_added_count = 0
        
        try:
            with open(csv_file_path, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                reader.fieldnames = clean_column_names(reader.fieldnames)
                
                print("Starting row import with INDIAN RUPEE (INR) settings...")

                for index, row in enumerate(reader):
                    try:
                        medv_val = safe_float_convert(row.get('medv'))
                        
                        # Determine image tier using original dataset 'medv' (medv in thousands)
                        # This keeps the stored `medv` value intact for templates which expect medv
                        # to be the original dataset value (multiplied later in templates to show currency).
                        if medv_val < 17:
                            prompt_desc = "cozy small house exterior, modest apartment building, simple facade, daytime, neighborhood street"
                            tier_tag = "Budget"
                        elif medv_val < 22:
                            prompt_desc = "modern apartment building exterior, mid-range residential complex, landscaped entrance, sunny day"
                            tier_tag = "Standard"
                        elif medv_val < 26:
                            prompt_desc = "luxury house exterior, upscale home with garden, tasteful architecture, golden hour"
                            tier_tag = "Premium"
                        else:
                            prompt_desc = "penthouse or mansion exterior, dramatic architectural lighting, pool and terrace, luxury cars visible"
                            tier_tag = "Luxury"

                        # Generate an image URL using Pollinations with a seed for stability
                        encoded_prompt = urllib.parse.quote(prompt_desc)
                        unique_image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=800&height=600&seed={index}&nologo=true"

                        fake_lat = 42.3601 + random.uniform(-0.05, 0.05)
                        fake_lon = -71.0589 + random.uniform(-0.05, 0.05)
                        street_num = random.randint(1, 100)
                        fake_street = f"{street_num}, {random.choice(street_list)}"
                        
                        new_property = Property(
                            # Copy stats mapping
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
                            
                            # Keep original dataset 'medv' (in thousands) so templates calculate prices correctly
                            medv=medv_val,
                            
                            image_url=unique_image_url,
                            lat=fake_lat,
                            lon=fake_lon,
                            property_type=random.choice(type_list),
                            street_name=fake_street,
                            description=f"[{tier_tag}] " + random.choice(description_list),
                            architect=random.choice(architect_list),
                            builder=random.choice(builder_list),
                            quality_verified=random.choice([True, False]),
                            last_verified_on=datetime.date.today()
                        )
                        db.session.add(new_property)
                        properties_added_count += 1
                        
                    except Exception as e:
                        print(f"Skipping row: {e}")
            
            db.session.commit()
            print(f"Successfully added {properties_added_count} properties with INR pricing.")

        except Exception as e:
            db.session.rollback()
            print(f"An error occurred: {e}")

if __name__ == '__main__':
    seed_database()