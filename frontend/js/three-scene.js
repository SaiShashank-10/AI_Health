/**
 * Three.js 3D Particle Network — AI Orchestrator Visualization
 * 
 * Features:
 *   - Procedural particle cloud with BufferGeometry (no external files)
 *   - Dynamic connection lines between nearest neighbors
 *   - Raycaster-based mouse interaction (glow, expand, cursor lines)
 *   - Ambient orbital rotation
 *   - Smooth window resize handling
 *   - Color scheme matches the UI theme (teal, cyan, purple)
 */

(function () {
    'use strict';

    // ═══ CONFIGURATION ═══
    const CONFIG = {
        particleCount: 220,
        fieldRadius: 14,
        connectionDistance: 3.2,
        mouseInfluenceRadius: 4.5,
        rotationSpeed: 0.0003,
        particleSizeBase: 0.08,
        particleSizeHover: 0.18,
        connectionOpacity: 0.12,
        mouseLineOpacity: 0.35,
        cameraDistance: 22,
        colorTeal: new THREE.Color(0x00F5D4),
        colorCyan: new THREE.Color(0x00D4FF),
        colorPurple: new THREE.Color(0x7B61FF),
        colorPink: new THREE.Color(0xFF6EC7),
        colorDim: new THREE.Color(0x1A2744),
        bgColor: 0x060B18,
    };

    // ═══ STATE ═══
    let scene, camera, renderer, clock;
    let particleSystem, connectionLines, mouseLines;
    let particlePositions, particleVelocities, particleColors, particleSizes;
    let originalColors;
    let raycaster, mouse, mouseWorld;
    let animationId;

    // ═══ INITIALIZATION ═══
    function init() {
        const canvas = document.getElementById('three-canvas');
        if (!canvas) return;

        // Scene
        scene = new THREE.Scene();
        scene.fog = new THREE.FogExp2(CONFIG.bgColor, 0.02);

        // Camera
        camera = new THREE.PerspectiveCamera(
            60,
            window.innerWidth / window.innerHeight,
            0.1,
            100
        );
        camera.position.set(0, 0, CONFIG.cameraDistance);

        // Renderer
        renderer = new THREE.WebGLRenderer({
            canvas: canvas,
            antialias: true,
            alpha: false,
        });
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.setClearColor(CONFIG.bgColor, 1);

        // Clock
        clock = new THREE.Clock();

        // Raycaster
        raycaster = new THREE.Raycaster();
        raycaster.params.Points.threshold = 0.6;
        mouse = new THREE.Vector2(-999, -999);
        mouseWorld = new THREE.Vector3();

        // Build scene
        createParticles();
        createConnectionGeometry();
        createMouseLineGeometry();

        // Events
        window.addEventListener('resize', onResize, false);
        window.addEventListener('mousemove', onMouseMove, false);
        window.addEventListener('touchmove', onTouchMove, { passive: true });

        // Start
        animate();
    }


    // ═══ PARTICLE CREATION ═══
    function createParticles() {
        const count = CONFIG.particleCount;
        const geometry = new THREE.BufferGeometry();

        particlePositions = new Float32Array(count * 3);
        particleVelocities = new Float32Array(count * 3);
        particleColors = new Float32Array(count * 3);
        particleSizes = new Float32Array(count);
        originalColors = new Float32Array(count * 3);

        const colorPalette = [
            CONFIG.colorTeal,
            CONFIG.colorCyan,
            CONFIG.colorPurple,
            CONFIG.colorPink,
        ];

        for (let i = 0; i < count; i++) {
            const i3 = i * 3;

            // Position: spherical distribution with slight clustering
            const theta = Math.random() * Math.PI * 2;
            const phi = Math.acos(2 * Math.random() - 1);
            const r = CONFIG.fieldRadius * (0.3 + Math.random() * 0.7);

            particlePositions[i3] = r * Math.sin(phi) * Math.cos(theta);
            particlePositions[i3 + 1] = r * Math.sin(phi) * Math.sin(theta);
            particlePositions[i3 + 2] = r * Math.cos(phi);

            // Velocity: very slow drift
            particleVelocities[i3] = (Math.random() - 0.5) * 0.004;
            particleVelocities[i3 + 1] = (Math.random() - 0.5) * 0.004;
            particleVelocities[i3 + 2] = (Math.random() - 0.5) * 0.004;

            // Color
            const color = colorPalette[Math.floor(Math.random() * colorPalette.length)];
            const dimFactor = 0.3 + Math.random() * 0.7;
            particleColors[i3] = color.r * dimFactor;
            particleColors[i3 + 1] = color.g * dimFactor;
            particleColors[i3 + 2] = color.b * dimFactor;

            originalColors[i3] = particleColors[i3];
            originalColors[i3 + 1] = particleColors[i3 + 1];
            originalColors[i3 + 2] = particleColors[i3 + 2];

            // Size
            particleSizes[i] = CONFIG.particleSizeBase * (0.5 + Math.random());
        }

        geometry.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));
        geometry.setAttribute('color', new THREE.BufferAttribute(particleColors, 3));
        geometry.setAttribute('size', new THREE.BufferAttribute(particleSizes, 1));

        const material = new THREE.PointsMaterial({
            size: CONFIG.particleSizeBase,
            vertexColors: true,
            transparent: true,
            opacity: 0.85,
            sizeAttenuation: true,
            blending: THREE.AdditiveBlending,
            depthWrite: false,
        });

        particleSystem = new THREE.Points(geometry, material);
        scene.add(particleSystem);
    }


    // ═══ CONNECTION LINES ═══
    function createConnectionGeometry() {
        const maxConnections = CONFIG.particleCount * 3;
        const linePositions = new Float32Array(maxConnections * 6);
        const lineColors = new Float32Array(maxConnections * 6);

        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.BufferAttribute(linePositions, 3));
        geometry.setAttribute('color', new THREE.BufferAttribute(lineColors, 3));
        geometry.setDrawRange(0, 0);

        const material = new THREE.LineBasicMaterial({
            vertexColors: true,
            transparent: true,
            opacity: CONFIG.connectionOpacity,
            blending: THREE.AdditiveBlending,
            depthWrite: false,
        });

        connectionLines = new THREE.LineSegments(geometry, material);
        scene.add(connectionLines);
    }


    // ═══ MOUSE INTERACTION LINES ═══
    function createMouseLineGeometry() {
        const maxMouseLines = 30;
        const positions = new Float32Array(maxMouseLines * 6);
        const colors = new Float32Array(maxMouseLines * 6);

        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
        geometry.setDrawRange(0, 0);

        const material = new THREE.LineBasicMaterial({
            vertexColors: true,
            transparent: true,
            opacity: CONFIG.mouseLineOpacity,
            blending: THREE.AdditiveBlending,
            depthWrite: false,
        });

        mouseLines = new THREE.LineSegments(geometry, material);
        scene.add(mouseLines);
    }


    // ═══ UPDATE CONNECTIONS ═══
    function updateConnections() {
        const positions = connectionLines.geometry.attributes.position.array;
        const colors = connectionLines.geometry.attributes.color.array;
        const count = CONFIG.particleCount;
        let lineIndex = 0;
        const maxDist = CONFIG.connectionDistance;
        const maxDistSq = maxDist * maxDist;

        for (let i = 0; i < count; i++) {
            const ix = particlePositions[i * 3];
            const iy = particlePositions[i * 3 + 1];
            const iz = particlePositions[i * 3 + 2];

            for (let j = i + 1; j < count; j++) {
                const jx = particlePositions[j * 3];
                const jy = particlePositions[j * 3 + 1];
                const jz = particlePositions[j * 3 + 2];

                const dx = ix - jx;
                const dy = iy - jy;
                const dz = iz - jz;
                const distSq = dx * dx + dy * dy + dz * dz;

                if (distSq < maxDistSq) {
                    const idx = lineIndex * 6;
                    if (idx + 5 >= positions.length) break;

                    positions[idx] = ix;
                    positions[idx + 1] = iy;
                    positions[idx + 2] = iz;
                    positions[idx + 3] = jx;
                    positions[idx + 4] = jy;
                    positions[idx + 5] = jz;

                    const alpha = 1 - Math.sqrt(distSq) / maxDist;
                    const c = CONFIG.colorTeal;
                    colors[idx] = c.r * alpha;
                    colors[idx + 1] = c.g * alpha;
                    colors[idx + 2] = c.b * alpha;
                    colors[idx + 3] = c.r * alpha;
                    colors[idx + 4] = c.g * alpha;
                    colors[idx + 5] = c.b * alpha;

                    lineIndex++;
                }
            }
            if (lineIndex * 6 >= positions.length - 6) break;
        }

        connectionLines.geometry.setDrawRange(0, lineIndex * 2);
        connectionLines.geometry.attributes.position.needsUpdate = true;
        connectionLines.geometry.attributes.color.needsUpdate = true;
    }


    // ═══ MOUSE INTERACTION ═══
    function updateMouseInteraction() {
        if (mouse.x < -900) return;

        // Project mouse into 3D space
        raycaster.setFromCamera(mouse, camera);
        const dir = raycaster.ray.direction;
        const origin = raycaster.ray.origin;
        // Place mouseWorld at a depth near the center of the particle field
        mouseWorld.copy(dir).multiplyScalar(CONFIG.cameraDistance).add(origin);

        const mousePositions = mouseLines.geometry.attributes.position.array;
        const mouseColors = mouseLines.geometry.attributes.color.array;
        let mouseLineIndex = 0;
        const influenceRadius = CONFIG.mouseInfluenceRadius;
        const influenceRadiusSq = influenceRadius * influenceRadius;

        for (let i = 0; i < CONFIG.particleCount; i++) {
            const i3 = i * 3;
            const px = particlePositions[i3];
            const py = particlePositions[i3 + 1];
            const pz = particlePositions[i3 + 2];

            const dx = px - mouseWorld.x;
            const dy = py - mouseWorld.y;
            const dz = pz - mouseWorld.z;
            const distSq = dx * dx + dy * dy + dz * dz;

            if (distSq < influenceRadiusSq) {
                const dist = Math.sqrt(distSq);
                const influence = 1 - dist / influenceRadius;

                // Brighten particle
                particleColors[i3] = originalColors[i3] + (1 - originalColors[i3]) * influence * 0.8;
                particleColors[i3 + 1] = originalColors[i3 + 1] + (1 - originalColors[i3 + 1]) * influence * 0.8;
                particleColors[i3 + 2] = originalColors[i3 + 2] + (1 - originalColors[i3 + 2]) * influence * 0.8;

                // Expand particle
                particleSizes[i] = CONFIG.particleSizeBase * (1 + influence * 2.5);

                // Draw line from mouse to particle
                const midx = mouseLineIndex * 6;
                if (midx + 5 < mousePositions.length) {
                    mousePositions[midx] = mouseWorld.x;
                    mousePositions[midx + 1] = mouseWorld.y;
                    mousePositions[midx + 2] = mouseWorld.z;
                    mousePositions[midx + 3] = px;
                    mousePositions[midx + 4] = py;
                    mousePositions[midx + 5] = pz;

                    const c = CONFIG.colorCyan;
                    mouseColors[midx] = c.r * influence;
                    mouseColors[midx + 1] = c.g * influence;
                    mouseColors[midx + 2] = c.b * influence;
                    mouseColors[midx + 3] = c.r * influence * 0.5;
                    mouseColors[midx + 4] = c.g * influence * 0.5;
                    mouseColors[midx + 5] = c.b * influence * 0.5;

                    mouseLineIndex++;
                }
            } else {
                // Restore original color smoothly
                particleColors[i3] += (originalColors[i3] - particleColors[i3]) * 0.05;
                particleColors[i3 + 1] += (originalColors[i3 + 1] - particleColors[i3 + 1]) * 0.05;
                particleColors[i3 + 2] += (originalColors[i3 + 2] - particleColors[i3 + 2]) * 0.05;

                // Restore size
                particleSizes[i] += (CONFIG.particleSizeBase * (0.5 + Math.random() * 0.5) - particleSizes[i]) * 0.03;
            }
        }

        mouseLines.geometry.setDrawRange(0, mouseLineIndex * 2);
        mouseLines.geometry.attributes.position.needsUpdate = true;
        mouseLines.geometry.attributes.color.needsUpdate = true;
    }


    // ═══ PARTICLE DRIFT ═══
    function updateParticleDrift() {
        const count = CONFIG.particleCount;
        const radius = CONFIG.fieldRadius;

        for (let i = 0; i < count; i++) {
            const i3 = i * 3;

            particlePositions[i3] += particleVelocities[i3];
            particlePositions[i3 + 1] += particleVelocities[i3 + 1];
            particlePositions[i3 + 2] += particleVelocities[i3 + 2];

            // Soft boundary — pull back if too far
            const dist = Math.sqrt(
                particlePositions[i3] ** 2 +
                particlePositions[i3 + 1] ** 2 +
                particlePositions[i3 + 2] ** 2
            );

            if (dist > radius) {
                const factor = -0.001;
                particleVelocities[i3] += particlePositions[i3] * factor;
                particleVelocities[i3 + 1] += particlePositions[i3 + 1] * factor;
                particleVelocities[i3 + 2] += particlePositions[i3 + 2] * factor;
            }

            // Damping
            particleVelocities[i3] *= 0.999;
            particleVelocities[i3 + 1] *= 0.999;
            particleVelocities[i3 + 2] *= 0.999;
        }
    }


    // ═══ ANIMATION LOOP ═══
    function animate() {
        animationId = requestAnimationFrame(animate);

        const elapsed = clock.getElapsedTime();

        // Ambient rotation
        if (particleSystem) {
            particleSystem.rotation.y = elapsed * CONFIG.rotationSpeed * 10;
            particleSystem.rotation.x = Math.sin(elapsed * 0.1) * 0.05;
            connectionLines.rotation.copy(particleSystem.rotation);
            mouseLines.rotation.copy(particleSystem.rotation);
        }

        // Update particles
        updateParticleDrift();
        updateConnections();
        updateMouseInteraction();

        // Flag updates
        if (particleSystem) {
            particleSystem.geometry.attributes.position.needsUpdate = true;
            particleSystem.geometry.attributes.color.needsUpdate = true;
            particleSystem.geometry.attributes.size.needsUpdate = true;
        }

        renderer.render(scene, camera);
    }


    // ═══ EVENT HANDLERS ═══
    function onResize() {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    }

    function onMouseMove(e) {
        mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
        mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;
    }

    function onTouchMove(e) {
        if (e.touches.length > 0) {
            mouse.x = (e.touches[0].clientX / window.innerWidth) * 2 - 1;
            mouse.y = -(e.touches[0].clientY / window.innerHeight) * 2 + 1;
        }
    }


    // ═══ PUBLIC API ═══
    // Allow app.js to trigger visual effects on the particle system
    window.ThreeScene = {
        /**
         * Pulse a burst of color through the particle system.
         * @param {string} colorHex - Hex color string
         * @param {number} intensity - 0 to 1
         */
        pulse: function (colorHex, intensity) {
            if (!particleSystem) return;
            const c = new THREE.Color(colorHex);
            const count = CONFIG.particleCount;
            for (let i = 0; i < count; i++) {
                const i3 = i * 3;
                if (Math.random() < intensity) {
                    originalColors[i3] = c.r;
                    originalColors[i3 + 1] = c.g;
                    originalColors[i3 + 2] = c.b;
                }
            }
            // Slowly restore after 2 seconds
            setTimeout(() => {
                const palette = [CONFIG.colorTeal, CONFIG.colorCyan, CONFIG.colorPurple, CONFIG.colorPink];
                for (let i = 0; i < count; i++) {
                    const i3 = i * 3;
                    const color = palette[Math.floor(Math.random() * palette.length)];
                    const dim = 0.3 + Math.random() * 0.7;
                    originalColors[i3] = color.r * dim;
                    originalColors[i3 + 1] = color.g * dim;
                    originalColors[i3 + 2] = color.b * dim;
                }
            }, 2000);
        },

        /** Increase rotation speed temporarily */
        boost: function () {
            const orig = CONFIG.rotationSpeed;
            CONFIG.rotationSpeed = 0.002;
            setTimeout(() => { CONFIG.rotationSpeed = orig; }, 3000);
        },
    };


    // ═══ LAUNCH ═══
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
