/**
 * SatWatch Cesium Visualization Module
 * 
 * A minimal CesiumJS frontend for visualizing precomputed satellite positions.
 * 
 * Data Contract (input JSON):
 * {
 *   "epoch": "2026-01-17T21:00:00Z",
 *   "satellites": [
 *     {
 *       "id": "25544",
 *       "name": "ISS",
 *       "type": "station",
 *       "positions": [
 *         { "time": "2026-01-17T21:00:00Z", "lat": 14.3, "lon": -96.5, "alt_km": 414 }
 *       ]
 *     }
 *   ]
 * }
 */

const SatWatchCesium = (function() {
    'use strict';
    
    // Configuration
    const CONFIG = {
        // Colors by object type (Cesium.Color)
        colors: {
            station: null,   // Will be set after Cesium loads
            satellite: null,
            debris: null,
            default: null
        },
        // Point sizes by object type
        pointSizes: {
            station: 12,
            satellite: 8,
            debris: 6
        },
        // Default playback speed multiplier
        defaultSpeed: 60
    };
    
    // State
    let viewer = null;
    let dataSource = null;
    let currentData = null;
    let startTime = null;
    let stopTime = null;
    
    /**
     * Add imagery layer asynchronously (required for CesiumJS 1.104+)
     */
    async function addImageryLayer() {
        try {
            // Try ESRI World Imagery first
            const esriProvider = await Cesium.ArcGisMapServerImageryProvider.fromUrl(
                'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer'
            );
            viewer.imageryLayers.addImageryProvider(esriProvider);
            console.log('ESRI World Imagery loaded successfully');
        } catch (error) {
            console.warn('ESRI imagery failed, trying OpenStreetMap:', error);
            try {
                // Fallback to OpenStreetMap
                const osmProvider = new Cesium.OpenStreetMapImageryProvider({
                    url: 'https://a.tile.openstreetmap.org/'
                });
                viewer.imageryLayers.addImageryProvider(osmProvider);
                console.log('OpenStreetMap imagery loaded');
            } catch (osmError) {
                console.error('All imagery providers failed:', osmError);
            }
        }
    }
    
    /**
     * Generate a procedural starfield texture using canvas
     * Creates sharp, realistic stars with varying brightness
     * @param {number} size - Texture size (e.g., 2048)
     * @param {number} starCount - Number of stars per face
     * @param {boolean} addMilkyWay - Whether to add milky way glow
     * @returns {HTMLCanvasElement} Canvas with starfield
     */
    function generateStarfieldTexture(size = 2048, starCount = 3000, addMilkyWay = false) {
        const canvas = document.createElement('canvas');
        canvas.width = size;
        canvas.height = size;
        const ctx = canvas.getContext('2d');
        
        // Deep space black background
        ctx.fillStyle = '#000005';
        ctx.fillRect(0, 0, size, size);
        
        // Add subtle Milky Way glow if requested
        if (addMilkyWay) {
            const gradient = ctx.createLinearGradient(0, size * 0.3, size, size * 0.7);
            gradient.addColorStop(0, 'rgba(30, 20, 40, 0)');
            gradient.addColorStop(0.3, 'rgba(60, 40, 70, 0.15)');
            gradient.addColorStop(0.5, 'rgba(80, 60, 90, 0.25)');
            gradient.addColorStop(0.7, 'rgba(60, 40, 70, 0.15)');
            gradient.addColorStop(1, 'rgba(30, 20, 40, 0)');
            ctx.fillStyle = gradient;
            ctx.fillRect(0, 0, size, size);
            
            // Add some nebula-like clouds
            for (let i = 0; i < 20; i++) {
                const x = Math.random() * size;
                const y = size * 0.3 + Math.random() * size * 0.4;
                const radius = 50 + Math.random() * 150;
                const nebulaGradient = ctx.createRadialGradient(x, y, 0, x, y, radius);
                const hue = 240 + Math.random() * 60; // Blue to purple
                nebulaGradient.addColorStop(0, `hsla(${hue}, 50%, 30%, 0.1)`);
                nebulaGradient.addColorStop(1, 'transparent');
                ctx.fillStyle = nebulaGradient;
                ctx.fillRect(x - radius, y - radius, radius * 2, radius * 2);
            }
        }
        
        // Draw stars with varying sizes and brightness
        for (let i = 0; i < starCount; i++) {
            const x = Math.random() * size;
            const y = Math.random() * size;
            
            // Star brightness distribution (more dim stars than bright)
            const brightness = Math.pow(Math.random(), 2);
            const radius = 0.3 + brightness * 2.5;
            
            // Star color (mostly white, some blue/yellow tints)
            const colorRandom = Math.random();
            let r, g, b;
            if (colorRandom < 0.7) {
                // White stars
                const intensity = 180 + brightness * 75;
                r = g = b = intensity;
            } else if (colorRandom < 0.85) {
                // Blue stars (hot)
                r = 150 + brightness * 50;
                g = 170 + brightness * 60;
                b = 220 + brightness * 35;
            } else {
                // Yellow/orange stars (cool)
                r = 220 + brightness * 35;
                g = 190 + brightness * 50;
                b = 140 + brightness * 40;
            }
            
            // Draw star with glow for brighter stars
            if (brightness > 0.7) {
                // Add glow for bright stars
                const glowGradient = ctx.createRadialGradient(x, y, 0, x, y, radius * 4);
                glowGradient.addColorStop(0, `rgba(${r}, ${g}, ${b}, 0.8)`);
                glowGradient.addColorStop(0.3, `rgba(${r}, ${g}, ${b}, 0.3)`);
                glowGradient.addColorStop(1, 'transparent');
                ctx.fillStyle = glowGradient;
                ctx.beginPath();
                ctx.arc(x, y, radius * 4, 0, Math.PI * 2);
                ctx.fill();
            }
            
            // Draw star core (sharp point)
            ctx.fillStyle = `rgb(${Math.round(r)}, ${Math.round(g)}, ${Math.round(b)})`;
            ctx.beginPath();
            ctx.arc(x, y, radius, 0, Math.PI * 2);
            ctx.fill();
        }
        
        return canvas;
    }
    
    /**
     * Create a procedural starfield skybox (no external images needed)
     * Generates sharp, realistic stars programmatically
     */
    function createProceduralSkybox() {
        try {
            // Generate 6 unique starfield faces with Milky Way on some faces
            const sources = {
                positiveX: generateStarfieldTexture(2048, 3000, false).toDataURL(),
                negativeX: generateStarfieldTexture(2048, 3000, false).toDataURL(),
                positiveY: generateStarfieldTexture(2048, 2500, false).toDataURL(),  // Top - fewer stars
                negativeY: generateStarfieldTexture(2048, 3500, true).toDataURL(),   // Bottom - Milky Way
                positiveZ: generateStarfieldTexture(2048, 3000, true).toDataURL(),   // Front - Milky Way
                negativeZ: generateStarfieldTexture(2048, 3000, false).toDataURL()
            };
            
            const customSkybox = new Cesium.SkyBox({ sources });
            viewer.scene.skyBox = customSkybox;
            console.log('Procedural starfield skybox created (2048x2048, ~3000 stars per face)');
            return true;
        } catch (error) {
            console.error('Procedural skybox failed:', error);
            return false;
        }
    }
    
    /**
     * Create skybox from local files (for offline use with custom images)
     * Place high-res skybox images in cesium/skybox/ folder
     */
    function createLocalSkybox() {
        return new Promise((resolve) => {
            // Check if local skybox files exist by trying to load one
            const testImg = new Image();
            testImg.onload = () => {
                try {
                    const customSkybox = new Cesium.SkyBox({
                        sources: {
                            positiveX: 'skybox/px.jpg',
                            negativeX: 'skybox/nx.jpg',
                            positiveY: 'skybox/py.jpg',
                            negativeY: 'skybox/ny.jpg',
                            positiveZ: 'skybox/pz.jpg',
                            negativeZ: 'skybox/nz.jpg'
                        }
                    });
                    viewer.scene.skyBox = customSkybox;
                    console.log('Local high-resolution skybox loaded');
                    resolve(true);
                } catch (error) {
                    console.warn('Local skybox loading error:', error);
                    resolve(false);
                }
            };
            testImg.onerror = () => {
                console.log('No local skybox found, using procedural generation');
                resolve(false);
            };
            testImg.src = 'skybox/px.jpg';
        });
    }
    
    /**
     * Initialize the space background with the best available option
     */
    async function initializeSkybox() {
        // Priority: 1) Local high-res images, 2) Procedural generation
        const localLoaded = await createLocalSkybox();
        if (!localLoaded) {
            createProceduralSkybox();
        }
    }
    
    /**
     * Initialize the Cesium viewer
     * @param {string} containerId - ID of the container element
     * @returns {Cesium.Viewer} The Cesium viewer instance
     */
    function init(containerId) {
        // Set Cesium Ion access token (using default assets, no token needed for basic globe)
        // For production, you'd set: Cesium.Ion.defaultAccessToken = 'your-token';
        
        // Initialize colors after Cesium is loaded
        CONFIG.colors.station = Cesium.Color.fromCssColorString('#ff4444');
        CONFIG.colors.satellite = Cesium.Color.fromCssColorString('#4488ff');
        CONFIG.colors.debris = Cesium.Color.fromCssColorString('#ff8844');
        CONFIG.colors.default = Cesium.Color.WHITE;
        
        // Create the viewer with minimal UI (no base layer initially)
        viewer = new Cesium.Viewer(containerId, {
            // Start with no base layer - we'll add it async
            baseLayer: false,
            
            // Disable terrain (not needed for satellite viz, and avoids token requirement)
            terrain: undefined,
            
            // Disable default UI elements we don't need
            animation: true,           // Keep animation widget
            timeline: true,            // Keep timeline widget
            baseLayerPicker: false,
            geocoder: false,
            homeButton: true,
            sceneModePicker: false,
            selectionIndicator: true,
            navigationHelpButton: false,
            fullscreenButton: false,
            vrButton: false,
            infoBox: true,
            
            // Performance
            requestRenderMode: false,
            maximumRenderTimeChange: Infinity,
            
            // Clock settings
            shouldAnimate: false
        });
        
        // Add ESRI World Imagery asynchronously (required for CesiumJS 1.104+)
        addImageryLayer();
        
        // Configure the globe for satellite visualization
        viewer.scene.globe.enableLighting = true;   // Enable lighting for realistic day/night
        viewer.scene.globe.showGroundAtmosphere = true;
        viewer.scene.globe.baseColor = Cesium.Color.fromCssColorString('#0a1628'); // Very dark blue base
        
        // ===== HIGH-QUALITY SPACE BACKGROUND =====
        // Set pure black space background
        viewer.scene.backgroundColor = Cesium.Color.BLACK;
        
        // Initialize high-resolution skybox (async - tries local first, then procedural)
        initializeSkybox();
        
        // Ensure skybox is visible
        viewer.scene.skyBox.show = true;
        
        // Configure sun and moon for realistic rendering
        viewer.scene.sun.show = true;
        viewer.scene.moon.show = true;
        
        // Sky atmosphere (the blue glow around Earth's edge)
        viewer.scene.skyAtmosphere.show = true;
        viewer.scene.skyAtmosphere.brightnessShift = 0.0;  // No extra brightness
        viewer.scene.skyAtmosphere.hueShift = 0.0;
        viewer.scene.skyAtmosphere.saturationShift = 0.0;
        
        // Enable high dynamic range for better space rendering
        viewer.scene.highDynamicRange = true;
        
        // Improve star rendering - increase fog density to make stars sharper
        viewer.scene.fog.enabled = false;  // Disable fog for clearer space view
        
        // Set initial camera position (zoomed out view of Earth)
        viewer.camera.setView({
            destination: Cesium.Cartesian3.fromDegrees(-90, 20, 20000000),
            orientation: {
                heading: Cesium.Math.toRadians(0),
                pitch: Cesium.Math.toRadians(-90),
                roll: 0
            }
        });
        
        // Ensure the globe is visible
        viewer.scene.globe.show = true;
        
        // Set default clock speed
        viewer.clock.multiplier = CONFIG.defaultSpeed;
        
        // Update time display on clock tick
        viewer.clock.onTick.addEventListener(updateTimeDisplay);
        
        // Create custom data source for satellites
        dataSource = new Cesium.CustomDataSource('satellites');
        viewer.dataSources.add(dataSource);
        
        console.log('SatWatch Cesium initialized');
        return viewer;
    }
    
    /**
     * Load satellite position data
     * @param {Object} data - Position data in the specified format
     */
    function loadData(data) {
        if (!viewer) {
            console.error('Viewer not initialized');
            return;
        }
        
        if (!data || !data.satellites) {
            console.error('Invalid data format');
            return;
        }
        
        currentData = data;
        
        // Clear existing entities
        dataSource.entities.removeAll();
        
        // Determine time bounds from data
        let minTime = null;
        let maxTime = null;
        
        data.satellites.forEach(sat => {
            if (sat.positions && sat.positions.length > 0) {
                sat.positions.forEach(pos => {
                    const time = Cesium.JulianDate.fromIso8601(pos.time);
                    if (!minTime || Cesium.JulianDate.lessThan(time, minTime)) {
                        minTime = Cesium.JulianDate.clone(time);
                    }
                    if (!maxTime || Cesium.JulianDate.greaterThan(time, maxTime)) {
                        maxTime = Cesium.JulianDate.clone(time);
                    }
                });
            }
        });
        
        if (!minTime || !maxTime) {
            console.error('Could not determine time bounds from data');
            return;
        }
        
        startTime = minTime;
        stopTime = maxTime;
        
        // Configure the clock
        viewer.clock.startTime = Cesium.JulianDate.clone(startTime);
        viewer.clock.stopTime = Cesium.JulianDate.clone(stopTime);
        viewer.clock.currentTime = Cesium.JulianDate.clone(startTime);
        viewer.clock.clockRange = Cesium.ClockRange.LOOP_STOP;
        viewer.clock.shouldAnimate = false;
        
        // Configure timeline
        viewer.timeline.zoomTo(startTime, stopTime);
        
        // Create entities for each satellite
        let loadedCount = 0;
        
        data.satellites.forEach(sat => {
            if (createSatelliteEntity(sat)) {
                loadedCount++;
            }
        });
        
        // Update UI
        updateStatus('Data loaded', loadedCount);
        enableControls(true);
        
        // Fly to view all satellites
        viewer.flyTo(dataSource);
        
        console.log(`Loaded ${loadedCount} satellites`);
    }
    
    /**
     * Create a Cesium entity for a satellite with time-dynamic position
     * @param {Object} sat - Satellite data object
     * @returns {boolean} True if entity was created successfully
     */
    function createSatelliteEntity(sat) {
        if (!sat.positions || sat.positions.length === 0) {
            console.warn(`Satellite ${sat.name} has no positions`);
            return false;
        }
        
        // Get color based on type
        const color = CONFIG.colors[sat.type] || CONFIG.colors.default;
        const pointSize = CONFIG.pointSizes[sat.type] || 8;
        
        // Create SampledPositionProperty for smooth interpolation
        const positionProperty = new Cesium.SampledPositionProperty();
        
        // Set interpolation options for smooth movement
        positionProperty.setInterpolationOptions({
            interpolationDegree: 3,
            interpolationAlgorithm: Cesium.LagrangePolynomialApproximation
        });
        
        // Add position samples
        sat.positions.forEach(pos => {
            const time = Cesium.JulianDate.fromIso8601(pos.time);
            const position = Cesium.Cartesian3.fromDegrees(
                pos.lon,
                pos.lat,
                pos.alt_km * 1000  // Convert km to meters
            );
            positionProperty.addSample(time, position);
        });
        
        // Create the entity
        const entity = dataSource.entities.add({
            id: sat.id,
            name: sat.name,
            position: positionProperty,
            
            // Point visualization
            point: {
                pixelSize: pointSize,
                color: color,
                outlineColor: Cesium.Color.WHITE,
                outlineWidth: 1,
                heightReference: Cesium.HeightReference.NONE,
                disableDepthTestDistance: Number.POSITIVE_INFINITY
            },
            
            // Label
            label: {
                text: sat.name,
                font: '12px sans-serif',
                fillColor: Cesium.Color.WHITE,
                outlineColor: Cesium.Color.BLACK,
                outlineWidth: 2,
                style: Cesium.LabelStyle.FILL_AND_OUTLINE,
                verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
                pixelOffset: new Cesium.Cartesian2(0, -15),
                distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 15000000),
                disableDepthTestDistance: Number.POSITIVE_INFINITY
            },
            
            // Path trail
            path: {
                resolution: 120,
                material: new Cesium.ColorMaterialProperty(color.withAlpha(0.5)),
                width: 1,
                leadTime: 0,
                trailTime: 3600  // Show 1 hour trail
            },
            
            // Description for info box
            description: createDescription(sat)
        });
        
        // Store satellite type in entity for later use
        entity.satelliteType = sat.type;
        entity.satelliteId = sat.id;
        
        return true;
    }
    
    /**
     * Create HTML description for satellite info box
     * @param {Object} sat - Satellite data
     * @returns {string} HTML description
     */
    function createDescription(sat) {
        const typeColors = {
            station: '#ff4444',
            satellite: '#4488ff',
            debris: '#ff8844'
        };
        const typeColor = typeColors[sat.type] || '#ffffff';
        
        return `
            <table class="cesium-infoBox-defaultTable">
                <tr>
                    <td>NORAD ID</td>
                    <td>${sat.id}</td>
                </tr>
                <tr>
                    <td>Name</td>
                    <td>${sat.name}</td>
                </tr>
                <tr>
                    <td>Type</td>
                    <td><span style="color: ${typeColor}; font-weight: bold;">${sat.type.toUpperCase()}</span></td>
                </tr>
                <tr>
                    <td>Position Samples</td>
                    <td>${sat.positions ? sat.positions.length : 0}</td>
                </tr>
            </table>
        `;
    }
    
    /**
     * Update the time display
     */
    function updateTimeDisplay() {
        if (!viewer) return;
        
        const currentTime = viewer.clock.currentTime;
        const dateTime = Cesium.JulianDate.toDate(currentTime);
        
        const timeStr = dateTime.toISOString().replace('T', ' ').substring(0, 19) + ' UTC';
        document.getElementById('currentTime').textContent = timeStr;
    }
    
    /**
     * Update status display
     * @param {string} status - Status message
     * @param {number} count - Object count
     */
    function updateStatus(status, count) {
        document.getElementById('statusValue').textContent = status;
        document.getElementById('statusValue').classList.add('live');
        document.getElementById('objectCount').textContent = count || 0;
        
        if (startTime && stopTime) {
            const start = Cesium.JulianDate.toDate(startTime);
            const stop = Cesium.JulianDate.toDate(stopTime);
            const durationMs = stop - start;
            const durationMin = Math.round(durationMs / 60000);
            document.getElementById('timeRange').textContent = `${durationMin} minutes`;
        }
    }
    
    /**
     * Enable/disable playback controls
     * @param {boolean} enabled - Whether to enable controls
     */
    function enableControls(enabled) {
        document.getElementById('playBtn').disabled = !enabled;
        document.getElementById('pauseBtn').disabled = !enabled;
        document.getElementById('resetBtn').disabled = !enabled;
    }
    
    /**
     * Start playback
     */
    function play() {
        if (viewer) {
            viewer.clock.shouldAnimate = true;
            console.log('Playback started');
        }
    }
    
    /**
     * Pause playback
     */
    function pause() {
        if (viewer) {
            viewer.clock.shouldAnimate = false;
            console.log('Playback paused');
        }
    }
    
    /**
     * Reset to start time
     */
    function reset() {
        if (viewer && startTime) {
            viewer.clock.currentTime = Cesium.JulianDate.clone(startTime);
            viewer.clock.shouldAnimate = false;
            console.log('Playback reset');
        }
    }
    
    /**
     * Set playback speed
     * @param {number} multiplier - Speed multiplier
     */
    function setSpeed(multiplier) {
        if (viewer) {
            viewer.clock.multiplier = multiplier;
            console.log(`Playback speed set to ${multiplier}x`);
        }
    }
    
    /**
     * Get the Cesium viewer instance
     * @returns {Cesium.Viewer} The viewer instance
     */
    function getViewer() {
        return viewer;
    }
    
    /**
     * Get currently loaded data
     * @returns {Object} The loaded data
     */
    function getData() {
        return currentData;
    }
    
    // Public API
    return {
        init: init,
        loadData: loadData,
        play: play,
        pause: pause,
        reset: reset,
        setSpeed: setSpeed,
        getViewer: getViewer,
        getData: getData
    };
})();
