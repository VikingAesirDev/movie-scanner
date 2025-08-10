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

## Installation

1. Clone the repository:
