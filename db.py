import os
import psycopg2
from psycopg2 import pool
from contextlib import contextmanager
from dotenv import load_dotenv
from typing import Optional, List, Dict, Any, Union, Tuple
from PIL import Image
import imagehash
import io

# Load environment variables from .env file
load_dotenv()

class Database:
    _connection_pool = None

    @classmethod
    def initialize(cls):
        """Initialize the database connection pool."""
        try:
            cls._connection_pool = pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                dbname=os.getenv("DB_NAME", "image_db"),
                user=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASSWORD", "Rajam@03"),
                host=os.getenv("DB_HOST", "localhost"),
                port=os.getenv("DB_PORT", "5432")
            )
            print("Database connection pool created successfully")
            cls.create_tables() # Ensure tables exist
            return cls._connection_pool
        except Exception as e:
            print(f"Error creating connection pool: {e}")
            raise

    @classmethod
    def create_tables(cls):
        """Create necessary tables if they don't exist."""
        create_history_query = """
            CREATE TABLE IF NOT EXISTS public.scan_history (
                id SERIAL PRIMARY KEY,
                plant_id INTEGER REFERENCES public.plants(id),
                scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        with cls.get_connection_context() as conn:
            with conn.cursor() as cursor:
                cursor.execute(create_history_query)
        print("Tables checked/created.")

    @classmethod
    def initialize(cls):
        """Initialize the database connection pool."""
        try:
            cls._connection_pool = pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                dbname=os.getenv("DB_NAME", "image_db"),
                user=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASSWORD", "Rajam@03"),
                host=os.getenv("DB_HOST", "localhost"),
                port=os.getenv("DB_PORT", "5432")
            )
            print("Database connection pool created successfully")
            cls.create_tables() # Ensure tables exist
            return cls._connection_pool
        except Exception as e:
            print(f"Error creating connection pool: {e}")
            raise

    @classmethod
    def get_connection(cls):
        """Get a connection from the pool."""
        if cls._connection_pool is None:
            cls.initialize()
        return cls._connection_pool.getconn()

    @classmethod
    def return_connection(cls, connection):
        """Return a connection to the pool."""
        if cls._connection_pool:
            cls._connection_pool.putconn(connection)

    @classmethod
    def close_all_connections(cls):
        """Close all connections in the pool."""
        if cls._connection_pool:
            cls._connection_pool.closeall()
            print("All database connections closed")

    @classmethod
    @contextmanager
    def get_connection_context(cls):
        """Context manager for database connections."""
        conn = cls.get_connection()
        try:
            yield conn
        except Exception as e:
            print(f"Database error: {e}")
            conn.rollback()
            raise
        else:
            conn.commit()
        finally:
            cls.return_connection(conn)

    @classmethod
    def get_plant_by_id(cls, plant_id: int) -> Optional[Dict[str, Any]]:
        """Get plant details by ID."""
        query = """
            SELECT 
                id, name, scientific_name, common_names, image,
                medicinal_properties, growing_conditions, 
                harvesting_guidelines, precautions, last_shown_date
            FROM public.plants
            WHERE id = %s
        """
        with cls.get_connection_context() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (plant_id,))
                if cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    result = cursor.fetchone()
                    return dict(zip(columns, result)) if result else None
                return None

    @classmethod
    def get_all_plants(cls, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all plants with pagination."""
        query = """
            SELECT 
                id, name, scientific_name, common_names,
                SUBSTRING(medicinal_properties, 1, 100) || '...' as short_description
            FROM public.plants
            ORDER BY name
            LIMIT %s
        """
        with cls.get_connection_context() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (limit,))
                if cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    return [dict(zip(columns, row)) for row in cursor.fetchall()]
                return []

    @classmethod
    def compute_image_hash(cls, image_data):
        """Compute BOTH dHash (structure) and aHash (color/tone) for hybrid matching."""
        try:
            img = Image.open(io.BytesIO(image_data))
            if img.mode == 'RGBA':
                img = img.convert('RGB')
            
            # Compute both hashes
            d_hash = imagehash.dhash(img)
            a_hash = imagehash.average_hash(img)
            return d_hash, a_hash
        except Exception as e:
            print(f"Error computing image hash: {e}")
            return None, None

    @classmethod
    def find_best_match(cls, uploaded_image_data, threshold=20):
        """Find the best matching plant using Hybrid Hashing (Structure + Tone)."""
        uploaded_dhash, uploaded_ahash = cls.compute_image_hash(uploaded_image_data)
        
        if uploaded_dhash is None:
            return None, "Could not process the uploaded image"

        query = """
            SELECT id, name, scientific_name, common_names, 
                   medicinal_properties, growing_conditions, 
                   harvesting_guidelines, precautions, image
            FROM public.plants
            WHERE image IS NOT NULL
        """
        
        best_match = None
        min_distance = float('inf')

        with cls.get_connection_context() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                if cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    
                    for row in cursor.fetchall():
                        plant = dict(zip(columns, row))
                        if plant['image']:
                            try:
                                # Re-compute DB hashes
                                db_dhash, db_ahash = cls.compute_image_hash(plant['image'])
                                
                                if db_dhash and db_ahash:
                                    # Calculate distances
                                    dist_d = uploaded_dhash - db_dhash
                                    dist_a = uploaded_ahash - db_ahash
                                    
                                    # Weighted Distance: 
                                    # Structure (dHash) is much more important for distinguishing leaves (70%)
                                    # Tone (aHash) helps but shouldn't dominate (30%)
                                    raw_hybrid_dist = (dist_d * 0.7) + (dist_a * 0.3)
                                    
                                    if raw_hybrid_dist < min_distance:
                                        min_distance = raw_hybrid_dist
                                        best_match = plant
                            except Exception as e:
                                print(f"Error comparing hash for plant {plant.get('id')}: {e}")
        
        # Threshold: 20 is a reasonable balance for hybrid (avg of dHash and aHash)
        if best_match and min_distance < threshold:
             # structure the return data
            return {
                'id': best_match['id'],
                'name': best_match['name'],
                'scientific_name': best_match['scientific_name'],
                'common_names': best_match['common_names'].split(',') if best_match['common_names'] else [],
                'medicinal_properties': best_match['medicinal_properties'] or 'No information available',
                'growing_conditions': best_match['growing_conditions'] or 'No information available',
                'harvesting_guidelines': best_match['harvesting_guidelines'] or 'No information available',
                'precautions': best_match['precautions'] or 'No information available',
                'confidence_distance': min_distance 
            }, None
        
        return None, f"No matching plant found (Closest match: {best_match['name'] if best_match else 'None'} at distance {min_distance})"

    @classmethod
    def log_scan(cls, plant_id: int):
        """Log a scan event for a plant."""
        query = "INSERT INTO public.scan_history (plant_id) VALUES (%s)"
        try:
            with cls.get_connection_context() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (plant_id,))
        except Exception as e:
            print(f"Error logging scan: {e}")

    @classmethod
    def get_garden_stats(cls):
        """Get analytics for the garden with proper names."""
        query = """
            SELECT p.name, p.common_names, p.scientific_name, COUNT(h.id) as count
            FROM public.scan_history h
            JOIN public.plants p ON h.plant_id = p.id
            GROUP BY p.id, p.name, p.common_names, p.scientific_name
            ORDER BY count DESC
            LIMIT 5
        """
        stats = {}
        with cls.get_connection_context() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                if cursor.description:
                    for row in cursor.fetchall():
                        # row: 0=name, 1=common_names, 2=scientific_name, 3=count
                        raw_name = row[0]
                        common_names = row[1]
                        scientific_name = row[2]
                        count = row[3]

                        # Logic to pick best display name
                        display_name = raw_name
                        if common_names:
                            display_name = common_names.split(',')[0].strip()
                        elif scientific_name:
                            display_name = scientific_name
                        
                        stats[display_name] = count
        return stats

    @classmethod
    def get_recent_scans(cls, limit=10):
        """Get recent scans with plant details (prioritizing common name)."""
        query = """
            SELECT p.name, p.scientific_name, p.common_names, h.scanned_at
            FROM public.scan_history h
            JOIN public.plants p ON h.plant_id = p.id
            ORDER BY h.scanned_at DESC
            LIMIT %s
        """
        scans = []
        with cls.get_connection_context() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (limit,))
                if cursor.description:
                    for row in cursor.fetchall():
                        # row: 0=name, 1=scientific, 2=common, 3=date
                        raw_name = row[0]
                        scientific = row[1]
                        common = row[2]
                        date = row[3]

                        display_name = raw_name
                        if common:
                            display_name = common.split(',')[0].strip()
                        elif scientific:
                            display_name = scientific

                        scans.append({
                            'name': display_name,
                            'scientific_name': scientific,
                            'scanned_at': date
                        })
        return scans

    @classmethod
    def get_medicinal_plants(cls):
        """Get all plants with medicinal properties for the doctor feature, deduplicated and cleaned."""
        # Added scientific_name to query
        query = """
            SELECT id, name, common_names, scientific_name, medicinal_properties, image
            FROM public.plants
            WHERE medicinal_properties IS NOT NULL AND medicinal_properties != ''
        """
        unique_plants = {}
        
        with cls.get_connection_context() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                if cursor.description:
                    for row in cursor.fetchall():
                        # row: 0=id, 1=name, 2=common_names, 3=scientific_name, 4=medicinal_properties, 5=image
                        raw_name = row[1]
                        common_names = row[2]
                        scientific_name = row[3]
                        medicinal_props = row[4]
                        
                        # Determine best display name
                        display_name = raw_name
                        
                        # Prioritize Common Name -> Scientific Name -> Cleaned Filename
                        if common_names and len(common_names.strip()) > 0:
                             display_name = common_names.split(',')[0].strip()
                        elif scientific_name and len(scientific_name.strip()) > 0:
                             display_name = scientific_name
                        elif raw_name and '.' in raw_name: 
                             display_name = raw_name.rsplit('.', 1)[0]

                        # Deduplicate based on the Display Name
                        # We use the first entry we find for any given name
                        if display_name not in unique_plants:
                            unique_plants[display_name] = {
                                'id': row[0],
                                'name': display_name, 
                                'common_names': common_names,
                                'scientific_name': scientific_name,
                                'medicinal_properties': medicinal_props,
                            }
                            
        # Return sorted list for better UI
        return sorted(list(unique_plants.values()), key=lambda x: x['name'])

# Initialize the connection pool when the module is imported
try:
    Database.initialize()
except Exception as e:
    print(f"Failed to initialize database: {e}")

# Example usage:
if __name__ == "__main__":
    try:
        # Test the database connection
        plants = Database.get_all_plants(5)
        print(f"Found {len(plants)} plants in the database")
        if plants:
            print(f"First plant: {plants[0].get('name')}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        Database.close_all_connections()