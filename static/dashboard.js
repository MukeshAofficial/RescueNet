document.addEventListener('DOMContentLoaded', function () {
    const analyzeButton = document.getElementById('analyze-button');
    let map, marker;

    // Function to show map with a marker at specific lat/lng
    function showMapWithMarker(lat, lng) {
        const mapContainer = document.getElementById('map');
        mapContainer.style.display = 'block';

        // Initialize map if it's not already initialized
        if (!map) {
            map = L.map(mapContainer).setView([20.0, 95.0], 5); // Center map on Myanmar
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors'
            }).addTo(map);
        }

        // Add or update marker
        if (!marker) {
            marker = L.marker([lat, lng]).addTo(map);
        } else {
            marker.setLatLng([lat, lng]);
        }
    }

    function analyzeCameras() {
        const cameras = document.querySelectorAll('.camera');
        cameras.forEach(camera => camera.classList.add('green')); // Turn all cameras green initially

        setTimeout(() => {
            // Simulate flood threat detection
            fetch('/analyze_cameras')
                .then(response => response.json())
                .then(data => {
                    if (data.threat) {
                        const threatCamera = document.getElementById(`camera${data.cameraNumber}`);
                        if (threatCamera) {
                            threatCamera.classList.add('red');
                            showAlert(`Flood threat detected in ${threatCamera.querySelector('h3').textContent}!`);

                            // Coordinates of Myanmar regions for the map marker
                            const regionsCoords = {
                                1: [25.383412, 97.392479],  // Kachin
                                2: [21.13445, 97.251953],   // Shan
                                3: [23.165611, 93.682937],  // Chin
                                4: [22.009477, 95.153664],  // Sagaing
                                5: [16.871311, 96.199379],  // Yangon
                                6: [15.253096, 97.867537],  // Mon
                                7: [19.333739, 93.216679],  // Rakhine
                                8: [16.0306, 94.6723],      // Ayeyarwady
                                9: [19.419472, 97.040197]   // Kayah
                            };

                            // Show map with marker at detected region
                            const [lat, lng] = regionsCoords[data.cameraNumber];
                            showMapWithMarker(lat, lng);

                            // Zoom in on the marker after 1 second
                            setTimeout(() => {
                                map.setView([lat, lng], 12, { animate: true });
                            }, 1000);
                        }
                    }
                })
                .catch(error => console.error('Error:', error));
        }, 3000); // Simulate analysis delay
    }

    function showAlert(message) {
        const alertBox = document.createElement('div');
        alertBox.className = 'alert';
        alertBox.textContent = message;
        document.body.appendChild(alertBox);

        setTimeout(() => {
            alertBox.remove();
        }, 5000); // Remove alert after 5 seconds
    }

    analyzeButton.addEventListener('click', analyzeCameras);
});
