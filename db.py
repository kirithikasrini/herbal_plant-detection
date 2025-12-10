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
                dbname=os.getenv("DB_NAME", "***"),
                user=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASSWORD", "***"),
                host=os.getenv("DB_HOST", "localhost"),
                port=os.getenv("DB_PORT", "5432")
            )
            print("Database connection pool created successfully")
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
        """Compute perceptual hash of an image from bytes"""
        try:
            img = Image.open(io.BytesIO(image_data))
            if img.mode == 'RGBA':
                img = img.convert('RGB')
            return imagehash.average_hash(img)
        except Exception as e:
            print(f"Error computing image hash: {e}")
            return None

    @classmethod
    def find_best_match(cls, uploaded_image_data, threshold=10):
        """Find the best matching plant for the uploaded image."""
        uploaded_hash = cls.compute_image_hash(uploaded_image_data)
        if uploaded_hash is None:
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
                    
                    # Iterate through all plants to find the best match
                    # Note: For large datasets, this should be optimized (e.g., storing hashes in DB)
                    for row in cursor.fetchall():
                        plant = dict(zip(columns, row))
                        if plant['image']:
                            try:
                                db_hash = cls.compute_image_hash(plant['image'])
                                if db_hash:
                                    distance = uploaded_hash - db_hash
                                    if distance < min_distance:
                                        min_distance = distance
                                        best_match = plant
                            except Exception as e:
                                print(f"Error comparing hash for plant {plant.get('id')}: {e}")
        
        if best_match and min_distance < threshold:
             # structure the return data
            return {
                'name': best_match['name'],
                'scientific_name': best_match['scientific_name'],
                'common_names': best_match['common_names'].split(',') if best_match['common_names'] else [],
                'medicinal_properties': best_match['medicinal_properties'] or 'No information available',
                'growing_conditions': best_match['growing_conditions'] or 'No information available',
                'harvesting_guidelines': best_match['harvesting_guidelines'] or 'No information available',
                'precautions': best_match['precautions'] or 'No information available',
                'confidence_distance': min_distance 
            }, None
        
        return None, "No matching plant found or match quality too low."

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