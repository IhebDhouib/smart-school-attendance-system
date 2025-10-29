#!/bin/bash
# Camera connectivity test script for Madrasati deployment
# Run this on your server to test camera access before starting containers

echo "🔍 Testing Camera Connectivity for Madrasati"
echo "============================================"

# Default camera URL (change this to match your server setup)
CAMERA_URL="${CAMERA_URL:-rtsp://admin:admin1234@10.3.8.9:554/cam/realmonitor?channel=7&subtype=0&bitrate=4096&fps=25}"

echo "📹 Testing camera URL: $CAMERA_URL"
echo ""

# Test 1: Basic connectivity (ping the IP)
CAMERA_IP=$(echo $CAMERA_URL | sed 's|rtsp://[^@]*@\([^:/]*\).*|\1|')
echo "1️⃣ Testing basic connectivity to camera IP: $CAMERA_IP"

if ping -c 3 -W 2 $CAMERA_IP >/dev/null 2>&1; then
    echo "✅ Camera IP is reachable via ping"
else
    echo "❌ Camera IP is NOT reachable via ping"
    echo "   Possible issues:"
    echo "   - Camera is offline"
    echo "   - Firewall blocking ICMP"
    echo "   - Wrong IP address for server network"
    echo "   - Network routing issues"
fi

echo ""

# Test 2: RTSP port connectivity
echo "2️⃣ Testing RTSP port (554) connectivity"
if timeout 5 bash -c "</dev/tcp/$CAMERA_IP/554" >/dev/null 2>&1; then
    echo "✅ RTSP port 554 is open"
else
    echo "❌ RTSP port 554 is NOT accessible"
    echo "   Possible issues:"
    echo "   - RTSP port blocked by firewall"
    echo "   - Camera RTSP service not running"
    echo "   - Network ACL blocking port 554"
fi

echo ""

# Test 3: Try to capture a test frame (if ffmpeg is available)
echo "3️⃣ Testing RTSP stream capture (requires ffmpeg)"
if command -v ffmpeg >/dev/null 2>&1; then
    echo "   Attempting to capture 1 second of video..."
    if timeout 10 ffmpeg -i "$CAMERA_URL" -t 1 -f null - >/dev/null 2>&1; then
        echo "✅ RTSP stream is accessible and working"
    else
        echo "❌ RTSP stream capture failed"
        echo "   Possible issues:"
        echo "   - Wrong RTSP URL format"
        echo "   - Authentication credentials incorrect"
        echo "   - Camera codec not supported"
        echo "   - Network bandwidth issues"
    fi
else
    echo "⚠️  ffmpeg not available - skipping stream test"
    echo "   Install ffmpeg to test actual RTSP stream: apt-get install ffmpeg"
fi

echo ""
echo "📋 Next Steps:"
echo "1. If all tests pass: Your camera should work with Madrasati"
echo "2. If ping fails: Check camera IP address and network connectivity"
echo "3. If port 554 fails: Check firewall rules for RTSP traffic"
echo "4. If stream fails: Verify camera credentials and RTSP URL format"
echo ""
echo "💡 To set a different camera URL for your server:"
echo "   export CAMERA_URL='rtsp://username:password@YOUR_CAMERA_IP:554/stream'"
echo "   Then run: docker-compose up -d face-fused"