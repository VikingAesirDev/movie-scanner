#!/bin/bash

# Create SSL certificate setup script
# This creates a self-signed certificate for development/local use

echo "Setting up SSL certificates for HTTPS access..."

# Create SSL directory
mkdir -p ssl

# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout ssl/key.pem \
    -out ssl/cert.pem \
    -subj "/C=US/ST=State/L=City/O=Organization/OU=OrgUnit/CN=localhost/emailAddress=admin@localhost" \
    -addext "subjectAltName=DNS:localhost,DNS:*.localhost,IP:127.0.0.1,IP:0.0.0.0"

echo "SSL certificates created in ./ssl/"
echo "You can now access the app via HTTPS at https://localhost"
echo ""
echo "Note: You'll get a security warning because it's a self-signed certificate."
echo "Click 'Advanced' and 'Proceed to localhost' to continue."