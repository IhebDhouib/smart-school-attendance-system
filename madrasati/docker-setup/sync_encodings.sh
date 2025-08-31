#!/bin/bash
# Script to synchronize face encodings with database

echo "🔄 Synchronizing face encodings with database..."
echo "This will remove encodings for students that have been deleted from the database"
echo ""

# Run the synchronization script
docker exec -i madrasati_face_detection python sync_encodings_with_db.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Synchronization completed successfully!"
    echo "🔄 Restarting face detection service to apply changes..."
    docker-compose restart face-detection
    echo "✅ Face detection service restarted"
else
    echo ""
    echo "❌ Synchronization failed!"
    echo "Please check the logs above for details"
fi
