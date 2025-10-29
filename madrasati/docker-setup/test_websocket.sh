#!/bin/bash
# WebSocket connectivity test script for Madrasati deployment
# Run this inside the face-fused container to test WebSocket connectivity

echo "🔍 Testing WebSocket Connectivity for Madrasati"
echo "==============================================="

# Default WebSocket URL (change this to match your server setup)
WEBSOCKET_URL="${WEBSOCKET_URL:-ws://backend:3001}"

echo "🔌 Testing WebSocket URL: $WEBSOCKET_URL"
echo ""

# Test 1: Check if backend service is reachable
echo "1️⃣ Testing backend service connectivity"
if wget --quiet --tries=1 --timeout=5 http://backend:3000/api/students -O /dev/null; then
    echo "✅ Backend HTTP service is reachable"
else
    echo "❌ Backend HTTP service is NOT reachable"
    echo "   Possible issues:"
    echo "   - Backend container not running"
    echo "   - Network connectivity issues between containers"
    echo "   - Wrong service name in docker-compose.yml"
fi

echo ""

# Test 2: Check WebSocket port connectivity
echo "2️⃣ Testing WebSocket port connectivity"
if timeout 5 bash -c "</dev/tcp/backend/3001" >/dev/null 2>&1; then
    echo "✅ WebSocket port 3001 is open"
else
    echo "❌ WebSocket port 3001 is NOT accessible"
    echo "   Possible issues:"
    echo "   - WebSocket server not started in backend"
    echo "   - Port not exposed correctly"
    echo "   - Firewall blocking WebSocket traffic"
fi

echo ""

# Test 3: Try Python WebSocket connection test
echo "3️⃣ Testing WebSocket connection with Python"
python3 -c "
import websocket
import time
import sys

try:
    ws_url = '$WEBSOCKET_URL'
    print(f'Attempting to connect to: {ws_url}')

    ws = websocket.create_connection(ws_url, timeout=10)
    print('✅ WebSocket connection successful!')

    # Send a test message
    test_msg = {'test': 'connection_check', 'timestamp': time.time()}
    ws.send(str(test_msg))
    print('✅ Test message sent successfully')

    # Try to receive response (timeout after 2 seconds)
    ws.settimeout(2.0)
    try:
        response = ws.recv()
        print(f'✅ Received response: {response}')
    except:
        print('⚠️  No response received (this is normal for a test connection)')

    ws.close()
    print('✅ WebSocket test completed successfully')

except Exception as e:
    print(f'❌ WebSocket connection failed: {e}')
    print('   Possible issues:')
    print('   - Wrong WebSocket URL')
    print('   - WebSocket server not running')
    print('   - Network isolation between containers')
    print('   - Authentication or protocol issues')
    sys.exit(1)
"

echo ""
echo "📋 Next Steps:"
echo "1. If all tests pass: WebSocket should work in the application"
echo "2. If HTTP works but WebSocket fails: Check backend WebSocket server startup"
echo "3. If both fail: Check Docker network and service dependencies"
echo "4. Check backend container logs: docker logs madrasati_backend"
echo ""
echo "💡 To run this test:"
echo "   docker exec -it madrasati_face_fused /app/docker-setup/test_websocket.sh"