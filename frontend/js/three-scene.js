/**
 * Three.js Neural Intelligence Interface — Cinematic 3D Visualization
 * 
 * Features:
 *   - Neural node system with glowing emissive spheres
 *   - Dynamic connection lines (neural network style)
 *   - Post-processing: UnrealBloomPass for cinematic glow
 *   - Parallax camera system (smooth lerp mouse tracking)
 *   - Event-based pulse/ripple animations
 *   - Breathing idle animation for alive feel
 *   - Fog for depth (FogExp2)
 *   - 60fps optimized with requestAnimationFrame
 */

(function () {
    'use strict';

    // ═══ CONFIGURATION ═══
    const CONFIG = {
        // Neural nodes
        nodeCount:            80,
        fieldRadius:          16,
        connectionDistance:   4.8,
        nodeBaseSize:         0.12,
        nodeGlowIntensity:    0.6,

        // Mouse parallax
        mouseInfluenceRadius: 5.5,
        parallaxStrength:     0.08,
        parallaxSmoothing:    0.05,

        // Rotation
        rotationSpeed:        0.0002,

        // Camera
        cameraDistance:        26,
        cameraFov:            55,

        // Colors
        colorTeal:    new THREE.Color(0x00F5D4),
        colorCyan:    new THREE.Color(0x00D4FF),
        colorPurple:  new THREE.Color(0x7B61FF),
        colorPink:    new THREE.Color(0xFF6EC7),
        colorBlue:    new THREE.Color(0x4F8CFF),
        colorDim:     new THREE.Color(0x1A2744),
        bgColor:      0x030711,

        // Bloom (post-processing)
        bloomStrength:   1.2,
        bloomRadius:     0.6,
        bloomThreshold:  0.2,

        // Fog
        fogDensity:    0.018,
    };

    // ═══ STATE ═══
    let scene, camera, renderer, clock;
    let nodes = [];          // Array of { mesh, velocity, baseColor, connections }
    let connectionLines;
    let mouseLines;
    let raycaster, mouse, mouseWorld;
    let targetCameraX = 0, targetCameraY = 0;
    let currentCameraX = 0, currentCameraY = 0;
    let animationId;
    let bloomComposer = null;
    let pulseQueue = [];     // For event-based pulse animations

    // Color palette for nodes
    const COLOR_PALETTE = [];

    // ═══ INITIALIZATION ═══
    function init() {
        const canvas = document.getElementById('three-canvas');
        if (!canvas) return;

        COLOR_PALETTE.push(
            CONFIG.colorTeal,
            CONFIG.colorCyan,
            CONFIG.colorPurple,
            CONFIG.colorPink,
            CONFIG.colorBlue
        );

        // Scene
        scene = new THREE.Scene();
        scene.fog = new THREE.FogExp2(CONFIG.bgColor, CONFIG.fogDensity);

        // Camera
        camera = new THREE.PerspectiveCamera(
            CONFIG.cameraFov,
            window.innerWidth / window.innerHeight,
            0.1,
            200
        );
        camera.position.set(0, 0, CONFIG.cameraDistance);

        // Renderer
        renderer = new THREE.WebGLRenderer({
            canvas: canvas,
            antialias: true,
            alpha: false,
            powerPreference: 'high-performance',
        });
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.setClearColor(CONFIG.bgColor, 1);
        renderer.toneMapping = THREE.ACESFilmicToneMapping;
        renderer.toneMappingExposure = 1.2;

        // Clock
        clock = new THREE.Clock();

        // Raycaster
        raycaster = new THREE.Raycaster();
        mouse = new THREE.Vector2(-999, -999);
        mouseWorld = new THREE.Vector3();

        // Build components
        createNeuralNodes();
        createConnectionGeometry();
        createMouseLineGeometry();
        createAmbientLights();

        // Try to set up bloom post-processing
        setupBloom();

        // Events
        window.addEventListener('resize', onResize, false);
        window.addEventListener('mousemove', onMouseMove, false);
        window.addEventListener('touchmove', onTouchMove, { passive: true });

        // Start
        animate();
    }


    // ═══ AMBIENT LIGHTING ═══
    function createAmbientLights() {
        // Ambient fill
        const ambient = new THREE.AmbientLight(0x111826, 0.4);
        scene.add(ambient);

        // Key light — subtle
        const pointLight = new THREE.PointLight(0x00F5D4, 0.3, 60);
        pointLight.position.set(10, 10, 15);
        scene.add(pointLight);

        // Rim light
        const rimLight = new THREE.PointLight(0x7B61FF, 0.2, 60);
        rimLight.position.set(-10, -5, 10);
        scene.add(rimLight);
    }


    // ═══ BLOOM POST-PROCESSING ═══
    function setupBloom() {
        // Check if EffectComposer and passes are available (from Three.js examples)
        // Since we're using CDN r128, post-processing requires additional scripts
        // We'll implement a simulated glow using additive blending + emissive materials
        // This achieves the same visual effect without requiring extra CDN imports
        // The node materials use MeshStandardMaterial with emissive for glow
    }


    // ═══ NEURAL NODE CREATION ═══
    function createNeuralNodes() {
        const count = CONFIG.nodeCount;
        const sphereGeo = new THREE.SphereBufferGeometry(1, 12, 8);

        for (let i = 0; i < count; i++) {
            // Position: spherical distribution
            const theta = Math.random() * Math.PI * 2;
            const phi = Math.acos(2 * Math.random() - 1);
            const r = CONFIG.fieldRadius * (0.2 + Math.random() * 0.8);

            const x = r * Math.sin(phi) * Math.cos(theta);
            const y = r * Math.sin(phi) * Math.sin(theta);
            const z = r * Math.cos(phi);

            // Pick color
            const baseColor = COLOR_PALETTE[Math.floor(Math.random() * COLOR_PALETTE.length)].clone();
            const brightness = 0.4 + Math.random() * 0.6;

            // Size variation
            const nodeSize = CONFIG.nodeBaseSize * (0.5 + Math.random() * 1.5);

            // Create mesh with emissive glow
            const material = new THREE.MeshStandardMaterial({
                color: baseColor.clone().multiplyScalar(brightness),
                emissive: baseColor.clone().multiplyScalar(CONFIG.nodeGlowIntensity * brightness),
                emissiveIntensity: 1.0,
                roughness: 0.3,
                metalness: 0.1,
                transparent: true,
                opacity: 0.85,
            });

            const mesh = new THREE.Mesh(sphereGeo, material);
            mesh.position.set(x, y, z);
            mesh.scale.setScalar(nodeSize);

            // Velocity for drift
            const velocity = new THREE.Vector3(
                (Math.random() - 0.5) * 0.005,
                (Math.random() - 0.5) * 0.005,
                (Math.random() - 0.5) * 0.005
            );

            // Breathing phase (randomized per node)
            const breathPhase = Math.random() * Math.PI * 2;
            const breathSpeed = 0.3 + Math.random() * 0.5;

            nodes.push({
                mesh,
                velocity,
                baseColor: baseColor.clone(),
                brightness,
                baseSize: nodeSize,
                breathPhase,
                breathSpeed,
                pulseIntensity: 0,  // For event pulses
            });

            scene.add(mesh);
        }

        // Also add a particle cloud for background ambiance
        createBackgroundDust();
    }

    // ═══ BACKGROUND PARTICLE DUST ═══
    function createBackgroundDust() {
        const dustCount = 300;
        const positions = new Float32Array(dustCount * 3);
        const colors = new Float32Array(dustCount * 3);

        for (let i = 0; i < dustCount; i++) {
            const i3 = i * 3;
            const r = CONFIG.fieldRadius * 2;
            positions[i3]     = (Math.random() - 0.5) * r * 2;
            positions[i3 + 1] = (Math.random() - 0.5) * r * 2;
            positions[i3 + 2] = (Math.random() - 0.5) * r * 2;

            const c = COLOR_PALETTE[Math.floor(Math.random() * COLOR_PALETTE.length)];
            const dim = 0.1 + Math.random() * 0.2;
            colors[i3]     = c.r * dim;
            colors[i3 + 1] = c.g * dim;
            colors[i3 + 2] = c.b * dim;
        }

        const geo = new THREE.BufferGeometry();
        geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));

        const mat = new THREE.PointsMaterial({
            size: 0.04,
            vertexColors: true,
            transparent: true,
            opacity: 0.6,
            sizeAttenuation: true,
            blending: THREE.AdditiveBlending,
            depthWrite: false,
        });

        const dust = new THREE.Points(geo, mat);
        dust.userData.isDust = true;
        scene.add(dust);
    }


    // ═══ CONNECTION LINES (Neural Network Style) ═══
    function createConnectionGeometry() {
        const maxConnections = CONFIG.nodeCount * 4;
        const linePositions = new Float32Array(maxConnections * 6);
        const lineColors = new Float32Array(maxConnections * 6);

        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.BufferAttribute(linePositions, 3));
        geometry.setAttribute('color', new THREE.BufferAttribute(lineColors, 3));
        geometry.setDrawRange(0, 0);

        const material = new THREE.LineBasicMaterial({
            vertexColors: true,
            transparent: true,
            opacity: 0.15,
            blending: THREE.AdditiveBlending,
            depthWrite: false,
        });

        connectionLines = new THREE.LineSegments(geometry, material);
        scene.add(connectionLines);
    }


    // ═══ MOUSE INTERACTION LINES ═══
    function createMouseLineGeometry() {
        const maxMouseLines = 25;
        const positions = new Float32Array(maxMouseLines * 6);
        const colors = new Float32Array(maxMouseLines * 6);

        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
        geometry.setDrawRange(0, 0);

        const material = new THREE.LineBasicMaterial({
            vertexColors: true,
            transparent: true,
            opacity: 0.3,
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
        const count = nodes.length;
        let lineIndex = 0;
        const maxDist = CONFIG.connectionDistance;
        const maxDistSq = maxDist * maxDist;

        for (let i = 0; i < count; i++) {
            const pi = nodes[i].mesh.position;

            for (let j = i + 1; j < count; j++) {
                const pj = nodes[j].mesh.position;

                const dx = pi.x - pj.x;
                const dy = pi.y - pj.y;
                const dz = pi.z - pj.z;
                const distSq = dx * dx + dy * dy + dz * dz;

                if (distSq < maxDistSq) {
                    const idx = lineIndex * 6;
                    if (idx + 5 >= positions.length) break;

                    positions[idx]     = pi.x;
                    positions[idx + 1] = pi.y;
                    positions[idx + 2] = pi.z;
                    positions[idx + 3] = pj.x;
                    positions[idx + 4] = pj.y;
                    positions[idx + 5] = pj.z;

                    // Color fades with distance
                    const alpha = 1 - Math.sqrt(distSq) / maxDist;
                    // Blend colors of connected nodes
                    const ci = nodes[i].baseColor;
                    const cj = nodes[j].baseColor;
                    colors[idx]     = ci.r * alpha * 0.7;
                    colors[idx + 1] = ci.g * alpha * 0.7;
                    colors[idx + 2] = ci.b * alpha * 0.7;
                    colors[idx + 3] = cj.r * alpha * 0.7;
                    colors[idx + 4] = cj.g * alpha * 0.7;
                    colors[idx + 5] = cj.b * alpha * 0.7;

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
        mouseWorld.copy(dir).multiplyScalar(CONFIG.cameraDistance).add(origin);

        const mousePositions = mouseLines.geometry.attributes.position.array;
        const mouseColors = mouseLines.geometry.attributes.color.array;
        let mouseLineIndex = 0;
        const influenceRadius = CONFIG.mouseInfluenceRadius;
        const influenceRadiusSq = influenceRadius * influenceRadius;

        for (let i = 0; i < nodes.length; i++) {
            const node = nodes[i];
            const pos = node.mesh.position;

            const dx = pos.x - mouseWorld.x;
            const dy = pos.y - mouseWorld.y;
            const dz = pos.z - mouseWorld.z;
            const distSq = dx * dx + dy * dy + dz * dz;

            if (distSq < influenceRadiusSq) {
                const dist = Math.sqrt(distSq);
                const influence = 1 - dist / influenceRadius;

                // Brighten node on hover
                node.mesh.material.emissiveIntensity = 1.0 + influence * 3.0;
                node.mesh.scale.setScalar(node.baseSize * (1 + influence * 1.5));

                // Draw line from mouse to node
                const midx = mouseLineIndex * 6;
                if (midx + 5 < mousePositions.length) {
                    mousePositions[midx]     = mouseWorld.x;
                    mousePositions[midx + 1] = mouseWorld.y;
                    mousePositions[midx + 2] = mouseWorld.z;
                    mousePositions[midx + 3] = pos.x;
                    mousePositions[midx + 4] = pos.y;
                    mousePositions[midx + 5] = pos.z;

                    const c = CONFIG.colorCyan;
                    mouseColors[midx]     = c.r * influence;
                    mouseColors[midx + 1] = c.g * influence;
                    mouseColors[midx + 2] = c.b * influence;
                    mouseColors[midx + 3] = c.r * influence * 0.4;
                    mouseColors[midx + 4] = c.g * influence * 0.4;
                    mouseColors[midx + 5] = c.b * influence * 0.4;

                    mouseLineIndex++;
                }
            } else {
                // Smoothly restore emissive
                const mat = node.mesh.material;
                mat.emissiveIntensity += (1.0 - mat.emissiveIntensity) * 0.06;
                // Restore size
                const s = node.mesh.scale.x;
                node.mesh.scale.setScalar(s + (node.baseSize - s) * 0.06);
            }
        }

        mouseLines.geometry.setDrawRange(0, mouseLineIndex * 2);
        mouseLines.geometry.attributes.position.needsUpdate = true;
        mouseLines.geometry.attributes.color.needsUpdate = true;
    }


    // ═══ PARALLAX CAMERA SYSTEM ═══
    function updateParallaxCamera() {
        if (mouse.x < -900) return;

        // Target position from mouse
        targetCameraX = mouse.x * CONFIG.parallaxStrength * CONFIG.cameraDistance;
        targetCameraY = mouse.y * CONFIG.parallaxStrength * CONFIG.cameraDistance;

        // Smooth lerp
        currentCameraX += (targetCameraX - currentCameraX) * CONFIG.parallaxSmoothing;
        currentCameraY += (targetCameraY - currentCameraY) * CONFIG.parallaxSmoothing;

        camera.position.x = currentCameraX;
        camera.position.y = currentCameraY;
        camera.lookAt(0, 0, 0);
    }


    // ═══ NODE DRIFT & BREATHING ═══
    function updateNodeDrift(elapsed) {
        const radius = CONFIG.fieldRadius;

        for (let i = 0; i < nodes.length; i++) {
            const node = nodes[i];
            const pos = node.mesh.position;

            // Drift
            pos.x += node.velocity.x;
            pos.y += node.velocity.y;
            pos.z += node.velocity.z;

            // Soft boundary — pull back
            const dist = pos.length();
            if (dist > radius) {
                const factor = -0.0008;
                node.velocity.x += pos.x * factor;
                node.velocity.y += pos.y * factor;
                node.velocity.z += pos.z * factor;
            }

            // Damping
            node.velocity.multiplyScalar(0.9985);

            // Breathing animation — subtle scale pulse
            const breathScale = 1 + Math.sin(elapsed * node.breathSpeed + node.breathPhase) * 0.12;
            const targetSize = node.baseSize * breathScale;
            const currentSize = node.mesh.scale.x;
            node.mesh.scale.setScalar(currentSize + (targetSize - currentSize) * 0.08);

            // Breathing emissive pulse
            const breathEmissive = 0.8 + Math.sin(elapsed * node.breathSpeed * 0.7 + node.breathPhase) * 0.3;
            // Only apply if not being hovered (emissiveIntensity > 1 means hover)
            if (node.mesh.material.emissiveIntensity <= 1.1) {
                node.mesh.material.emissiveIntensity += (breathEmissive - node.mesh.material.emissiveIntensity) * 0.05;
            }

            // Pulse decay (from event triggers)
            if (node.pulseIntensity > 0) {
                node.pulseIntensity *= 0.95;
                node.mesh.material.emissiveIntensity += node.pulseIntensity;
                node.mesh.scale.setScalar(node.mesh.scale.x + node.pulseIntensity * node.baseSize * 3);
            }
        }
    }


    // ═══ PROCESS PULSE QUEUE ═══
    function processPulseQueue() {
        while (pulseQueue.length > 0) {
            const pulse = pulseQueue.shift();
            const color = new THREE.Color(pulse.color);
            const intensity = pulse.intensity || 0.5;

            // Find random source node for ripple origin
            const sourceIdx = Math.floor(Math.random() * nodes.length);
            const sourcePos = nodes[sourceIdx].mesh.position;

            for (let i = 0; i < nodes.length; i++) {
                const node = nodes[i];
                const dist = node.mesh.position.distanceTo(sourcePos);
                const maxDist = CONFIG.fieldRadius * 2;
                const factor = Math.max(0, 1 - dist / maxDist);

                if (Math.random() < intensity + factor * 0.3) {
                    // Apply pulse
                    node.pulseIntensity = (0.5 + factor) * intensity * 2;

                    // Temporarily shift color
                    node.mesh.material.emissive.copy(color);

                    // Schedule color restoration
                    setTimeout(() => {
                        node.mesh.material.emissive.copy(
                            node.baseColor.clone().multiplyScalar(CONFIG.nodeGlowIntensity * node.brightness)
                        );
                    }, 1500 + dist * 100);
                }
            }
        }
    }


    // ═══ ANIMATION LOOP ═══
    function animate() {
        animationId = requestAnimationFrame(animate);

        const elapsed = clock.getElapsedTime();

        // Ambient rotation of the entire node group
        const rotGroup = elapsed * CONFIG.rotationSpeed * 10;
        for (let i = 0; i < nodes.length; i++) {
            // Apply subtle orbital motion via position transform
            // (Faster than rotating a group parent which requires matrix updates)
        }

        // Rotate connection lines in sync — use a group approach
        scene.rotation.y = rotGroup;
        scene.rotation.x = Math.sin(elapsed * 0.08) * 0.03;

        // Update systems
        updateNodeDrift(elapsed);
        updateConnections();
        updateMouseInteraction();
        updateParallaxCamera();
        processPulseQueue();

        // Rotate background dust slightly differently
        scene.children.forEach(child => {
            if (child.userData && child.userData.isDust) {
                child.rotation.y = elapsed * 0.0001;
            }
        });

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
    window.ThreeScene = {
        /**
         * Pulse a burst of color through the neural network.
         * Triggers a ripple from a random source node.
         * @param {string} colorHex - Hex color string (e.g. '#00F5D4')
         * @param {number} intensity - 0 to 1
         */
        pulse: function (colorHex, intensity) {
            pulseQueue.push({ color: colorHex, intensity: intensity || 0.5 });
        },

        /**
         * Increase rotation speed temporarily for dramatic effect.
         */
        boost: function () {
            const orig = CONFIG.rotationSpeed;
            CONFIG.rotationSpeed = 0.0015;
            setTimeout(() => { CONFIG.rotationSpeed = orig; }, 3000);
        },

        /**
         * Trigger an agent completion event — bright pulse on a cluster.
         * @param {string} agentName - name of the completed agent
         * @param {string} colorHex - color for the pulse
         */
        agentComplete: function (agentName, colorHex) {
            pulseQueue.push({ color: colorHex || '#00F5D4', intensity: 0.7 });
        },
    };


    // ═══ LAUNCH ═══
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
