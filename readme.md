# Movie Collection Scanner

A Flask-based web application that allows you to scan movie barcodes and build a digital catalog of your physical movie collection.

## Features

- 📱 **Barcode Scanning**: Use your camera to scan movie barcodes
- 🎬 **Automatic Movie Lookup**: Fetches movie details from multiple APIs
- 📚 **Collection Management**: Browse and manage your movie collection
- 🎨 **Movie Posters**: Automatically downloads poster artwork
- 🔍 **Manual Search**: Search by movie title as fallback
- 💾 **Local Database**: Stores your collection locally

## APIs Used

- **TMDb API**: Movie details, posters, and metadata
- **UPCitemdb**: Primary barcode lookup
- **Open Food Facts**: Secondary barcode lookup fallback
- **Barcode Lookup API**: Tertiary fallback (optional)

## Requirements

- Python 3.7+
- Flask
- OpenCV
- PIL (Pillow)
- pyzbar
- requests
- SQLAlchemy
- nginx (this is necessarry as the camera only works over https)

## Installation

1. Clone the repository:
git clone https://github.com/yourusername/movie-collection-scanner.git
cd movie-collection-scanner

2. Install dependencies:
pip install -r requirements.txt

3. Set up environment variables:
cp .env.example .env

Edit .env with your API keys
## Environment Variables
Create a `.env` file with:
TMDB_API_KEY=your_tmdb_api_key_here
BARCODE_LOOKUP_API_KEY=your_barcode_lookup_api_key_here (optional)

4. Run the application:
python app.py

## Setup Instructions for HTTPS:
1. Create the SSL setup script:
Save the SSL setup script as setup-ssl.sh
chmod +x setup-ssl.sh
./setup-ssl.sh
2. Create the nginx.conf file (copy the content from the Nginx Configuration artifact)
3. Update your docker-compose.yml (copy the updated content)
4. Restart with HTTPS:
sudo docker-compose down
sudo docker-compose up -d --build
5. Access via HTTPS:
Go to https://localhost or https://your-server-ip
You'll get a security warning (expected with self-signed certificates)
Click "Advanced" → "Proceed to localhost"


## API Keys

- **TMDb API**: Get free key at https://www.themoviedb.org/settings/api
- **Barcode Lookup API**: Optional - get key at https://www.barcodelookup.com/api

## Usage

1. **Scan Movies**: Click "Start Scanning" and use your camera to scan movie barcodes
2. **Manual Search**: If barcode fails, search by movie title
3. **View Collection**: Browse your cataloged movies with details and artwork
4. **Edit Details**: Modify movie information before adding to collection

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.