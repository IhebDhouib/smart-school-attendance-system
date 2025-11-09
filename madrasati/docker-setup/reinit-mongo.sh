#!/bin/bash
# Script to manually run init-mongo.js on existing MongoDB container

echo "Running MongoDB initialization script..."

# Copy the init script into the container
docker cp ./init-mongo.js madrasati_mongodb:/tmp/init-mongo.js

# Execute the script using mongosh
docker exec -i madrasati_mongodb mongosh -u admin -p madrasati123 --authenticationDatabase admin < ./init-mongo.js

echo "MongoDB initialization complete!"
echo "You can now restart the backend container:"
echo "docker compose restart backend"
