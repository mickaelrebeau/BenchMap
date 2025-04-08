<template>
    <div id="map" class="map-container"></div>
</template>

<script setup>
import { onMounted } from 'vue'
import L from 'leaflet'
import 'leaflet.markercluster'

const loadBenches = async () => {
    const response = await fetch('/benches_paris.json')
    return await response.json()
}

const getIcon = (color) => {
    return L.icon({
        iconUrl: `https://chart.googleapis.com/chart?chst=d_map_pin_icon&chld=bench|${color}`,
        iconSize: [30, 50],
        iconAnchor: [15, 50],
        popupAnchor: [0, -45],
    })
}

onMounted(async () => {
    const map = L.map('map').setView([48.8566, 2.3522], 13)

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map)

    const benches = await loadBenches()

    // Créer le groupe cluster
    const markerCluster = L.markerClusterGroup()

    benches.forEach(bench => {
        const { latitude, longitude, tags, photo_url } = bench
        const backrest = tags?.backrest?.toLowerCase()

        let color = 'blue'
        if (backrest === 'yes') color = 'green'
        else if (backrest === 'no') color = 'red'

        const marker = L.marker([latitude, longitude], {
            icon: getIcon(color)
        })

        const popupText = `
      <strong>Banc ID:</strong> ${bench.id}<br/>
      ${Object.entries(tags).map(([k, v]) => `<strong>${k}:</strong> ${v}`).join('<br/>')}
      ${photo_url ? `<br/><img src="${photo_url}" width="200" style="margin-top:5px;border-radius:6px;">` : ''}
    `

        marker.bindPopup(popupText)
        markerCluster.addLayer(marker)
    })

    map.addLayer(markerCluster)
})
</script>

<style scoped>
.map-container {
    width: 100%;
    height: 100vh;
}
</style>
