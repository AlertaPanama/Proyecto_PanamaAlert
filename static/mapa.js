document.addEventListener('DOMContentLoaded', function() {
    // Ensure Leaflet is loaded before initializing the map
    if (typeof L !== 'undefined') {
        initMap();
    } else {
        console.error('Leaflet library not loaded');
    }

    function initMap() {
        // Create map container if it doesn't exist
        if (!document.getElementById('map')) {
            const mapContainer = document.createElement('div');
            mapContainer.id = 'map';
            mapContainer.style.height = '100vh';
            mapContainer.style.width = '100%';
            document.body.appendChild(mapContainer);
        }

        // Initialize map
        const map = L.map('map').setView([8.983333, -79.516667], 12);

        // Add tile layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);

        // Load existing pings
        loadPings(map);

        // Add new ping on map click
        map.on('click', function(e) {
            const info = prompt("Ingrese información para este ping:");
            if (info !== null && info.trim() !== "") {
                addNewPing(map, e.latlng.lat, e.latlng.lng, info);
            }
        });

        // Store map in window to make it accessible globally if needed
        window.map = map;
    }

    function loadPings(map) {
        fetch('/get_pings')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Error en la carga de pings');
                }
                return response.json();
            })
            .then(data => {
                data.forEach(ping => {
                    addPingToMap(map, ping._id, ping.lat, ping.lng, ping.info);
                });
            })
            .catch(error => {
                console.error('Error cargando pings:', error);
                window.location.href = '/login';
            });
    }

    function addPingToMap(map, id, lat, lng, info) {
        const marker = L.marker([lat, lng])
            .addTo(map)
            .bindPopup(`
                <div>
                    <p>${info}</p>
                    <button onclick="deletePingFromMap('${id}')">Eliminar</button>
                    <button onclick="editPing('${id}', '${info}')">Editar</button>
                </div>
            `);

        // Store markers for later reference
        if (!window.markers) window.markers = new Map();
        window.markers.set(id, marker);
    }

    function addNewPing(map, lat, lng, info) {
        fetch('/add_ping', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ lat, lng, info })
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    addPingToMap(map, data.id, lat, lng, info);
                }
            })
            .catch(error => {
                console.error('Error agregando ping:', error);
            });
    }

    // Global functions for popup buttons
    window.deletePingFromMap = function(id) {
        fetch(`/delete_ping/${id}`, {
            method: 'DELETE'
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const markers = window.markers;
                    const marker = markers.get(id);
                    if (marker) {
                        window.map.removeLayer(marker);
                        markers.delete(id);
                    }
                }
            })
            .catch(error => {
                console.error('Error eliminando ping:', error);
            });
    }

    window.editPing = function(id, currentInfo) {
        const newInfo = prompt("Edite la información del ping:", currentInfo);
        if (newInfo !== null && newInfo.trim() !== "") {
            const marker = window.markers.get(id);
            const [lat, lng] = marker.getLatLng();

            fetch(`/update_ping/${id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ lat, lng, info: newInfo })
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        marker.bindPopup(`
                        <div>
                            <p>${newInfo}</p>
                            <button onclick="deletePingFromMap('${id}')">Eliminar</button>
                            <button onclick="editPing('${id}', '${newInfo}')">Editar</button>
                        </div>
                    `).openPopup();
                    }
                })
                .catch(error => {
                    console.error('Error editando ping:', error);
                });
        }
    }
});
