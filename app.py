from flask import Flask, request, render_template, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import cv2
import numpy as np
from pyzbar import pyzbar
import requests
import os
from datetime import datetime
import base64
from io import BytesIO
from PIL import Image

app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///movies.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

db = SQLAlchemy(app)

# Create upload directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Movie model
class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    year = db.Column(db.Integer)
    director = db.Column(db.String(100))
    genre = db.Column(db.String(100))
    format_type = db.Column(db.String(20))  # DVD, Blu-ray, 4K Blu-ray
    barcode = db.Column(db.String(20))
    tmdb_id = db.Column(db.String(20))  # TMDb ID instead of IMDb ID
    poster_url = db.Column(db.String(500))
    added_date = db.Column(db.DateTime, default=datetime.utcnow)
    location = db.Column(db.String(100))  # Where it's stored
    condition = db.Column(db.String(20), default='Good')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'year': self.year,
            'director': self.director,
            'genre': self.genre,
            'format_type': self.format_type,
            'barcode': self.barcode,
            'tmdb_id': self.tmdb_id,
            'poster_url': self.poster_url,
            'added_date': self.added_date.isoformat() if self.added_date else None,
            'location': self.location,
            'condition': self.condition
        }

# TMDb API configuration (get a free API key from https://www.themoviedb.org/settings/api)
TMDB_API_KEY = os.environ.get('TMDB_API_KEY', 'your_api_key_here')
TMDB_BASE_URL = 'https://api.themoviedb.org/3'
TMDB_IMAGE_BASE_URL = 'https://image.tmdb.org/t/p/w500'

def decode_barcode(image_data):
    """Decode barcode from image data"""
    try:
        # Convert base64 to image
        if image_data.startswith('data:image'):
            image_data = image_data.split(',')[1]
        
        image_bytes = base64.b64decode(image_data)
        image = Image.open(BytesIO(image_bytes))
        
        # Convert PIL image to OpenCV format
        opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Decode barcodes
        barcodes = pyzbar.decode(opencv_image)
        
        results = []
        for barcode in barcodes:
            barcode_data = barcode.data.decode('utf-8')
            barcode_type = barcode.type
            results.append({
                'data': barcode_data,
                'type': barcode_type
            })
        
        return results
    
    except Exception as e:
        print(f"Barcode decode error: {e}")
        return []

def clean_movie_title(title):
    """Clean movie title by removing common DVD/Blu-ray indicators"""
    if not title:
        return title
    
    # Remove common format indicators
    replacements = [
        '[DVD]', '[Blu-ray]', '[4K]', '[Ultra HD]', '[UHD]',
        '(DVD)', '(Blu-ray)', '(4K)', '(Ultra HD)', '(UHD)',
        'DVD', 'Blu-ray', 'BluRay', '4K UHD', 'Ultra HD',
        '- Special Edition', '- Director\'s Cut', '- Extended Edition',
        'Special Edition', 'Director\'s Cut', 'Extended Edition',
        '(Widescreen)', '(Full Screen)', 'Widescreen', 'Full Screen',
        '- Collector\'s Edition', 'Collector\'s Edition', 'Deluxe Edition',
        '[Region 1]', '[Region 2]', '[Region 4]', '(Region 1)', '(Region 2)', '(Region 4)'
    ]
    
    cleaned_title = title
    for replacement in replacements:
        cleaned_title = cleaned_title.replace(replacement, '')
    
    # Remove extra whitespace and common separators
    cleaned_title = cleaned_title.replace('  ', ' ').strip(' -,.')
    
    return cleaned_title

def detect_format_from_title(title):
    """Detect movie format from product title"""
    if not title:
        return None
    
    title_lower = title.lower()
    
    if '4k' in title_lower or 'ultra hd' in title_lower or 'uhd' in title_lower:
        return '4K Blu-ray'
    elif 'blu-ray' in title_lower or 'blu ray' in title_lower or 'bluray' in title_lower:
        return 'Blu-ray'
    elif 'dvd' in title_lower:
        return 'DVD'
    
    return None

def try_upcitemdb(barcode):
    """Try UPCitemdb.com API for barcode lookup"""
    try:
        print(f"Trying UPCitemdb for barcode: {barcode}")
        
        upc_url = f"https://api.upcitemdb.com/prod/trial/lookup?upc={barcode}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; MovieScanner/1.0)'
        }
        
        response = requests.get(upc_url, headers=headers, timeout=10)
        print(f"UPCitemdb response status: {response.status_code}")
        
        if response.ok:
            data = response.json()
            print(f"UPCitemdb response: {data}")
            
            if data.get('items') and len(data['items']) > 0:
                item = data['items'][0]
                title = item.get('title', '')
                brand = item.get('brand', '')
                description = item.get('description', '')
                
                # Try to extract movie title
                movie_title = clean_movie_title(title)
                
                if not movie_title or len(movie_title) < 3:
                    movie_title = clean_movie_title(description)
                
                if movie_title and len(movie_title) >= 3:
                    detected_format = detect_format_from_title(title) or detect_format_from_title(description)
                    print(f"UPCitemdb found: {movie_title}, Format: {detected_format}")
                    
                    return {
                        'title': movie_title,
                        'format_type': detected_format,
                        'source': 'UPCitemdb'
                    }
        
        print("UPCitemdb: No results found")
        return None
        
    except requests.exceptions.Timeout:
        print("UPCitemdb: Request timeout")
        return None
    except requests.exceptions.RequestException as e:
        print(f"UPCitemdb request error: {e}")
        return None
    except Exception as e:
        print(f"UPCitemdb error: {e}")
        return None

def try_openfoodfacts(barcode):
    """Try Open Food Facts API for barcode lookup"""
    try:
        print(f"Trying Open Food Facts for barcode: {barcode}")
        
        # Open Food Facts API endpoint
        off_url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
        headers = {
            'User-Agent': 'MovieScanner/1.0 (https://yourapp.com)'
        }
        
        response = requests.get(off_url, headers=headers, timeout=10)
        print(f"Open Food Facts response status: {response.status_code}")
        
        if response.ok:
            data = response.json()
            
            if data.get('status') == 1 and data.get('product'):
                product = data['product']
                
                # Check various title fields
                title = (product.get('product_name') or 
                        product.get('product_name_en') or 
                        product.get('generic_name') or '')
                
                brands = product.get('brands', '')
                categories = product.get('categories', '')
                
                print(f"Open Food Facts product: {title}, Brands: {brands}, Categories: {categories}")
                
                # Check if this might be a movie/media product
                # Open Food Facts sometimes has entertainment products
                media_indicators = ['dvd', 'blu-ray', 'bluray', 'movie', 'film', 'cinema', 'video']
                
                full_text = f"{title} {brands} {categories}".lower()
                is_media = any(indicator in full_text for indicator in media_indicators)
                
                if is_media and title:
                    movie_title = clean_movie_title(title)
                    
                    if movie_title and len(movie_title) >= 3:
                        detected_format = detect_format_from_title(full_text)
                        print(f"Open Food Facts found media: {movie_title}, Format: {detected_format}")
                        
                        return {
                            'title': movie_title,
                            'format_type': detected_format,
                            'source': 'Open Food Facts'
                        }
        
        print("Open Food Facts: No media product found")
        return None
        
    except requests.exceptions.Timeout:
        print("Open Food Facts: Request timeout")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Open Food Facts request error: {e}")
        return None
    except Exception as e:
        print(f"Open Food Facts error: {e}")
        return None

def try_barcode_lookup_api(barcode):
    """Try Barcode Lookup API as additional fallback"""
    try:
        print(f"Trying Barcode Lookup API for barcode: {barcode}")
        
        # Note: This API requires registration and API key
        # Get free API key from https://www.barcodelookup.com/api
        api_key = os.environ.get('BARCODE_LOOKUP_API_KEY')
        
        if not api_key:
            print("Barcode Lookup API: No API key provided")
            return None
        
        lookup_url = f"https://api.barcodelookup.com/v3/products?barcode={barcode}&formatted=y&key={api_key}"
        
        response = requests.get(lookup_url, timeout=10)
        print(f"Barcode Lookup API response status: {response.status_code}")
        
        if response.ok:
            data = response.json()
            
            if data.get('products') and len(data['products']) > 0:
                product = data['products'][0]
                title = product.get('title', '') or product.get('product_name', '')
                description = product.get('description', '')
                category = product.get('category', '')
                
                print(f"Barcode Lookup API product: {title}, Category: {category}")
                
                # Check if it's a movie/media product
                full_text = f"{title} {description} {category}".lower()
                media_indicators = ['dvd', 'blu-ray', 'bluray', 'movie', 'film', 'video']
                is_media = any(indicator in full_text for indicator in media_indicators)
                
                if is_media and title:
                    movie_title = clean_movie_title(title)
                    
                    if movie_title and len(movie_title) >= 3:
                        detected_format = detect_format_from_title(full_text)
                        print(f"Barcode Lookup API found media: {movie_title}, Format: {detected_format}")
                        
                        return {
                            'title': movie_title,
                            'format_type': detected_format,
                            'source': 'Barcode Lookup API'
                        }
        
        print("Barcode Lookup API: No media product found")
        return None
        
    except requests.exceptions.Timeout:
        print("Barcode Lookup API: Request timeout")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Barcode Lookup API request error: {e}")
        return None
    except Exception as e:
        print(f"Barcode Lookup API error: {e}")
        return None

def search_movie_by_barcode(barcode):
    """Search for movie information using multiple barcode databases with fallbacks"""
    try:
        print(f"Starting barcode lookup for: {barcode}")
        
        # Try each API in order of reliability/speed
        apis_to_try = [
            ('UPCitemdb', try_upcitemdb),
            ('Open Food Facts', try_openfoodfacts),
            ('Barcode Lookup API', try_barcode_lookup_api)
        ]
        
        for api_name, api_function in apis_to_try:
            print(f"Trying {api_name}...")
            
            # Get basic product info from barcode API
            product_info = api_function(barcode)
            
            if product_info and product_info.get('title'):
                movie_title = product_info['title']
                print(f"{api_name} found title: {movie_title}")
                
                # Search TMDb for complete movie details
                movie_info = search_movie_by_title(movie_title)
                
                if movie_info:
                    # Add the detected format and barcode info
                    if product_info.get('format_type'):
                        movie_info['format_type'] = product_info['format_type']
                    
                    movie_info['barcode'] = barcode
                    movie_info['lookup_source'] = product_info.get('source', api_name)
                    
                    print(f"Successfully found movie via {api_name}: {movie_info['title']}")
                    return movie_info
                else:
                    print(f"{api_name} found product but TMDb search failed for: {movie_title}")
            else:
                print(f"{api_name} found no relevant product")
        
        print("All barcode lookup APIs failed")
        return None
        
    except Exception as e:
        print(f"Barcode lookup error: {e}")
        return None

def search_movie_by_title(title):
    """Search for movie information using TMDb API"""
    try:
        print(f"Searching TMDb for: {title}")
        
        # Search for movies by title
        search_url = f"{TMDB_BASE_URL}/search/movie"
        params = {
            'api_key': TMDB_API_KEY,
            'query': title,
            'language': 'en-US'
        }

        response = requests.get(search_url, params=params, timeout=10)
        data = response.json()

        if data.get('results') and len(data['results']) > 0:
            movie = data['results'][0]  # Get the first/best match
            
            # Get additional details including director
            movie_id = movie.get('id')
            details_url = f"{TMDB_BASE_URL}/movie/{movie_id}"
            credits_url = f"{TMDB_BASE_URL}/movie/{movie_id}/credits"
            
            details_params = {'api_key': TMDB_API_KEY, 'language': 'en-US'}
            
            details_response = requests.get(details_url, params=details_params, timeout=10)
            credits_response = requests.get(credits_url, params=details_params, timeout=10)
            
            details_data = details_response.json() if details_response.ok else {}
            credits_data = credits_response.json() if credits_response.ok else {}

            # Extract director from crew
            director = None
            if credits_data.get('crew'):
                for crew_member in credits_data['crew']:
                    if crew_member.get('job') == 'Director':
                        director = crew_member.get('name')
                        break

            # Format genres
            genres = []
            if details_data.get('genres'):
                genres = [genre['name'] for genre in details_data['genres']]

            # Parse release year
            release_date = movie.get('release_date', '') or details_data.get('release_date', '')
            year = None
            if release_date and len(release_date) >= 4:
                try:
                    year = int(release_date[:4])
                except ValueError:
                    pass

            # Build poster URL
            poster_url = None
            if movie.get('poster_path'):
                poster_url = f"{TMDB_IMAGE_BASE_URL}{movie['poster_path']}"

            return {
                'title': movie.get('title'),
                'year': year,
                'director': director,
                'genre': ', '.join(genres) if genres else None,
                'tmdb_id': str(movie_id),
                'poster_url': poster_url
            }

    except requests.exceptions.Timeout:
        print("TMDb API timeout")
        return None
    except requests.exceptions.RequestException as e:
        print(f"TMDb API request error: {e}")
        return None
    except Exception as e:
        print(f"Movie search error: {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scan')
def scan():
    return render_template('scan.html')

@app.route('/collection')
def collection():
    movies = Movie.query.order_by(Movie.added_date.desc()).all()
    return render_template('collection.html', movies=movies)

@app.route('/api/scan_barcode', methods=['POST'])
def scan_barcode():
    try:
        data = request.get_json()
        image_data = data.get('image')
        
        if not image_data:
            return jsonify({'error': 'No image data provided'}), 400

        # Decode barcode
        barcodes = decode_barcode(image_data)
        
        if not barcodes:
            return jsonify({'error': 'No barcode found in image'}), 400

        return jsonify({
            'success': True,
            'barcodes': barcodes
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search_movie_barcode', methods=['POST'])
def search_movie_barcode():
    """Endpoint for barcode-based movie searches with multiple API fallbacks"""
    try:
        data = request.get_json()
        barcode = data.get('barcode')
        
        if not barcode:
            return jsonify({'error': 'No barcode provided'}), 400

        movie_info = search_movie_by_barcode(barcode)
        
        if movie_info:
            return jsonify({
                'success': True,
                'movie': movie_info
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Movie not found for this barcode',
                'barcode': barcode
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search_movie', methods=['POST'])
def search_movie():
    try:
        data = request.get_json()
        title = data.get('title')
        
        if not title:
            return jsonify({'error': 'No title provided'}), 400

        movie_info = search_movie_by_title(title)
        
        if movie_info:
            return jsonify({
                'success': True,
                'movie': movie_info
            })
        else:
            return jsonify({'error': 'Movie not found'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/add_movie', methods=['POST'])
def add_movie():
    try:
        data = request.get_json()
        
        movie = Movie(
            title=data.get('title'),
            year=data.get('year'),
            director=data.get('director'),
            genre=data.get('genre'),
            format_type=data.get('format_type'),
            barcode=data.get('barcode'),
            tmdb_id=data.get('tmdb_id'),
            poster_url=data.get('poster_url'),
            location=data.get('location'),
            condition=data.get('condition', 'Good')
        )

        db.session.add(movie)
        db.session.commit()

        return jsonify({
            'success': True,
            'movie': movie.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/movies')
def get_movies():
    movies = Movie.query.order_by(Movie.added_date.desc()).all()
    return jsonify([movie.to_dict() for movie in movies])

@app.route('/api/movies/<int:movie_id>', methods=['DELETE'])
def delete_movie(movie_id):
    try:
        movie = Movie.query.get_or_404(movie_id)
        db.session.delete(movie)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)
