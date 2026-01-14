#!/bin/bash

npm run build
echo "Website built."
# Define the source and destination directories
SOURCE_DIR="../public"
DEST_DIR="/var/www/html"

# Remove existing files in the destination directory
sudo rm -rf ${DEST_DIR}/*

# Copy new built files to the destination directory
sudo cp -r ${SOURCE_DIR}/* ${DEST_DIR}/
echo "Files copied to ${DEST_DIR}."
# Set the correct file permissions
sudo chown -R www-data:www-data ${DEST_DIR}
sudo chmod -R 755 ${DEST_DIR}
echo "Permissions set."
# Restart Apache to apply changes
sudo systemctl restart apache2
echo "Apache restarted."

echo "✓ Deployment completed successfully."