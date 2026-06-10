document.addEventListener("DOMContentLoaded", () => {
    const inputs = document.querySelectorAll('.face-input');
    
    // Handle manual image previews
    inputs.forEach(input => {
        input.addEventListener('change', function() {
            const face = this.id;
            const preview = document.getElementById(`preview-${face}`);
            const card = document.getElementById(`area-${face}`);
            
            if (this.files && this.files[0]) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    preview.src = e.target.result;
                    preview.classList.remove('d-none');
                    card.classList.add('has-image');
                }
                reader.readAsDataURL(this.files[0]);
            }
        });
    });

    const form = document.getElementById('cubeForm');
    const loading = document.getElementById('loadingOverlay');
    const results = document.getElementById('resultsSection');
    const errorAlert = document.getElementById('errorAlert');
    const errorMsg = document.getElementById('errorMessage');
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        results.classList.add('d-none');
        errorAlert.classList.add('d-none');
        form.style.opacity = '0.3';
        loading.classList.remove('d-none');
        
        const formData = new FormData(form);
        
        try {
            const response = await fetch('/analyze', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                renderCorrectionUI(data.faces_colors);
                correctionSection.classList.remove('d-none');
                correctionSection.scrollIntoView({ behavior: 'smooth' });
            } else {
                showError(data.error || "Analysis failed. Please ensure high quality photos.");
            }
            
        } catch (err) {
            showError("System offline. Please check connection.");
            console.error(err);
        } finally {
            loading.classList.add('d-none');
            form.style.opacity = '1';
        }
    });

    function showError(msg) {
        errorMsg.textContent = msg;
        errorAlert.classList.remove('d-none');
    }

    function renderSolution(moves) {
        const container = document.getElementById('solutionMoves');
        container.innerHTML = '';
        
        if (moves.length === 0) {
            container.innerHTML = '<div class="text-success fw-bold outfit">Already Solved!</div>';
            return;
        }

        moves.forEach((move, index) => {
            const el = document.createElement('div');
            el.className = 'move-token';
            el.textContent = move;
            el.style.animationDelay = `${index * 0.05}s`;
            container.appendChild(el);
        });
    }

    function renderDetectedFaces(faces) {
        const notations = ['U', 'L', 'F', 'R', 'B', 'D'];
        
        notations.forEach(face => {
            const grid = document.getElementById(`grid-${face}`);
            if(grid) {
                grid.innerHTML = '';
                const colors = faces[face] || [];
                colors.forEach(color => {
                    const cell = document.createElement('div');
                    cell.className = `mini-cell col-${color.toLowerCase()}`;
                    grid.appendChild(cell);
                });
            }
        });
    }

    // --- Premium Scanner Logic ---
    const startCameraBtn = document.getElementById('startCameraBtn');
    const cameraModal = document.getElementById('cameraModal');
    const cameraVideo = document.getElementById('cameraVideo');
    const captureBtn = document.getElementById('captureBtn');
    const captureCanvas = document.getElementById('captureCanvas');
    const ctx = captureCanvas.getContext('2d');
    const btnFaceName = document.getElementById('btnFaceName');
    const scanInstruction = document.getElementById('scanInstruction');
    const thumbnailContainer = document.getElementById('thumbnailContainer');
    const livePreviewGrid = document.getElementById('livePreviewGrid');
    const confidenceIndicator = document.getElementById('confidenceIndicator');

    let stream = null;
    let previewInterval = null;
    const scanSequence = [
        { name: 'front', color: 'RED' },
        { name: 'right', color: 'BLUE' },
        { name: 'back', color: 'ORANGE' },
        { name: 'left', color: 'GREEN' },
        { name: 'up', color: 'WHITE' },
        { name: 'down', color: 'YELLOW' }
    ];
    
    let currentScanIndex = 0;
    const capturedImages = {};

    const openCamera = async () => {
        try {
            if (!stream) {
                stream = await navigator.mediaDevices.getUserMedia({
                    video: { facingMode: 'environment', width: { ideal: 1280 } }
                });
                cameraVideo.srcObject = stream;
            }
            startRealTimePreview();
        } catch (err) {
            alert("Camera access denied.");
            bootstrap.Modal.getInstance(cameraModal).hide();
        }
    };

    const startRealTimePreview = () => {
        if (previewInterval) clearInterval(previewInterval);
        previewInterval = setInterval(updateLivePreview, 500);
    };

    const stopRealTimePreview = () => {
        if (previewInterval) {
            clearInterval(previewInterval);
            previewInterval = null;
        }
    };

    const updateLivePreview = async () => {
        if (!cameraVideo.videoWidth) return;

        const overlay = document.querySelector('.scan-overlay-target');
        const vRect = cameraVideo.getBoundingClientRect();
        const oRect = overlay.getBoundingClientRect();

        // Use a hidden canvas for light-weight preview capture
        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = 300;
        tempCanvas.height = 300;
        const tempCtx = tempCanvas.getContext('2d');

        const sX = (oRect.left - vRect.left) * (cameraVideo.videoWidth / vRect.width);
        const sY = (oRect.top - vRect.top) * (cameraVideo.videoHeight / vRect.height);
        const sW = oRect.width * (cameraVideo.videoWidth / vRect.width);
        const sH = oRect.height * (cameraVideo.videoHeight / vRect.height);

        tempCtx.drawImage(cameraVideo, sX, sY, sW, sH, 0, 0, 300, 300);
        const frameData = tempCanvas.toDataURL('image/jpeg', 0.5);

        try {
            const currentFace = scanSequence[currentScanIndex];
            const response = await fetch('/preview_colors', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    image: frameData,
                    expected_center: currentFace.color.toLowerCase()
                })
            });
            const data = await response.json();
            if (data.success) {
                updatePreviewUI(data.preview_data);
            }
        } catch (err) {
            console.error("Preview error:", err);
        }
    };

    const updatePreviewUI = (previewData) => {
        const cells = livePreviewGrid.querySelectorAll('.preview-cell');
        let lowConfidence = false;

        previewData.forEach((item, index) => {
            const cell = cells[index];
            if (cell) {
                cell.className = `preview-cell col-${item.color}`;
                if (item.confidence < 0.4) {
                    lowConfidence = true;
                    cell.style.border = '2px solid var(--accent)';
                } else {
                    cell.style.border = '1px solid rgba(255, 255, 255, 0.1)';
                }
            }
        });

        if (lowConfidence) {
            confidenceIndicator.classList.remove('d-none');
        } else {
            confidenceIndicator.classList.add('d-none');
        }
    };

    startCameraBtn.addEventListener('click', () => {
        currentScanIndex = 0;
        thumbnailContainer.innerHTML = '';
        updateScanUI();
        openCamera();
    });

    const stopCamera = () => {
        stopRealTimePreview();
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            stream = null;
        }
    };

    cameraModal.addEventListener('hidden.bs.modal', stopCamera);

    captureBtn.addEventListener('click', async () => {
        const overlay = document.querySelector('.scan-overlay-target');
        const vRect = cameraVideo.getBoundingClientRect();
        const oRect = overlay.getBoundingClientRect();

        const sX = (oRect.left - vRect.left) * (cameraVideo.videoWidth / vRect.width);
        const sY = (oRect.top - vRect.top) * (cameraVideo.videoHeight / vRect.height);
        const sW = oRect.width * (cameraVideo.videoWidth / vRect.width);
        const sH = oRect.height * (cameraVideo.videoHeight / vRect.height);
        
        captureCanvas.width = sW;
        captureCanvas.height = sH;
        ctx.drawImage(cameraVideo, sX, sY, sW, sH, 0, 0, sW, sH);

        const face = scanSequence[currentScanIndex];
        const dataUrl = captureCanvas.toDataURL('image/jpeg', 0.9);
        capturedImages[face.name] = dataUrl;
        
        // Update manual upload grid
        const preview = document.getElementById(`preview-${face.name}`);
        const card = document.getElementById(`area-${face.name}`);
        if (preview) {
            preview.src = dataUrl;
            preview.classList.remove('d-none');
        }
        if (card) card.classList.add('has-image');

        addThumbnail(dataUrl);

        currentScanIndex++;
        if (currentScanIndex < scanSequence.length) {
            updateScanUI();
        } else {
            bootstrap.Modal.getInstance(cameraModal).hide();
            submitScannedImages();
        }
    });

    function addThumbnail(dataUrl) {
        const thumb = document.createElement('img');
        thumb.src = dataUrl;
        thumb.style.width = '40px';
        thumb.style.height = '40px';
        thumb.style.objectFit = 'cover';
        thumb.style.borderRadius = '8px';
        thumb.style.border = '1px solid var(--primary)';
        thumbnailContainer.appendChild(thumb);
    }

    function updateScanUI() {
        const face = scanSequence[currentScanIndex];
        btnFaceName.textContent = face.name.toUpperCase();
        scanInstruction.innerHTML = `Scan ${face.name.toUpperCase()} Face <br><small>(Center should be ${face.color})</small>`;
    }

    async function submitScannedImages() {
        results.classList.add('d-none');
        form.style.opacity = '0.3';
        loading.classList.remove('d-none');
        
        try {
            const resp = await fetch('/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(capturedImages)
            });
            const data = await resp.json();
            if (data.success) {
                renderCorrectionUI(data.faces_colors);
                correctionSection.classList.remove('d-none');
                correctionSection.scrollIntoView({ behavior: 'smooth' });
            } else {
                showError(data.error);
            }
        } catch (err) {
            showError("Connection error.");
        } finally {
            loading.classList.add('d-none');
            form.style.opacity = '1';
        }
    }

    // --- Correction UI & 3D Rubik's Cube Controller ---
    const correctionSection = document.getElementById('correctionSection');
    const colorPalette = document.getElementById('colorPalette');
    const solveFinalBtn = document.getElementById('solveFinalBtn');
    const rescanBtn = document.getElementById('rescanBtn');
    const resetCorrectionsBtn = document.getElementById('resetCorrectionsBtn');
    const resetCubeBtn = document.getElementById('resetCubeBtn');
    
    let currentFacesColors = {};
    let originalScannedColors = null;
    let active3DSticker = null;

    let scene = null;
    let camera = null;
    let renderer = null;
    let controls = null;
    let cubeGroup = null;
    let stickerMeshes = [];
    let is3DInitialized = false;

    const colorMap = {
        'white': 0xf2f2f7,
        'yellow': 0xffcc00,
        'red': 0xff3b30,
        'orange': 0xff9500,
        'blue': 0x007aff,
        'green': 0x34c759
    };

    function getColorHex(name) {
        const lower = name ? name.toLowerCase() : 'white';
        return colorMap[lower] || 0xffffff;
    }

    function init3DScene() {
        const container = document.getElementById('cube3DViewport');
        if (!container) return;

        // Clear loading or other children
        container.querySelectorAll('canvas').forEach(c => c.remove());

        // Create Scene
        scene = new THREE.Scene();

        // Create Camera
        camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 100);
        camera.position.set(3.8, 3.8, 5.5);

        // Create Renderer
        renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        renderer.setSize(container.clientWidth, container.clientHeight);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        container.appendChild(renderer.domElement);

        // OrbitControls
        controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.enablePan = false;
        controls.minDistance = 3.5;
        controls.maxDistance = 10;
        controls.enableDamping = true;
        controls.dampingFactor = 0.05;

        // Lighting
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
        scene.add(ambientLight);

        const dirLight1 = new THREE.DirectionalLight(0xffffff, 0.85);
        dirLight1.position.set(6, 10, 6);
        scene.add(dirLight1);

        const dirLight2 = new THREE.DirectionalLight(0xffffff, 0.3);
        dirLight2.position.set(-6, -10, -6);
        scene.add(dirLight2);

        // Create Cube Group
        cubeGroup = new THREE.Group();
        scene.add(cubeGroup);

        // Generate the 27 cubies
        const cubiesMap = {};
        for (let x = -1; x <= 1; x++) {
            for (let y = -1; y <= 1; y++) {
                for (let z = -1; z <= 1; z++) {
                    const geom = new THREE.BoxGeometry(0.92, 0.92, 0.92);
                    const mat = new THREE.MeshStandardMaterial({
                        color: 0x151518,
                        roughness: 0.7,
                        metalness: 0.15
                    });
                    const cubie = new THREE.Mesh(geom, mat);
                    cubie.position.set(x, y, z);
                    cubeGroup.add(cubie);
                    cubiesMap[`${x},${y},${z}`] = cubie;
                }
            }
        }

        // Generate the 54 stickers
        const facesList = ['up', 'left', 'front', 'right', 'down', 'back'];
        stickerMeshes = [];

        facesList.forEach(face => {
            for (let i = 0; i < 9; i++) {
                const mapping = getStickerMapping(face, i);
                const key = `${mapping.x},${mapping.y},${mapping.z}`;
                const cubie = cubiesMap[key];
                if (cubie) {
                    const stickerGeom = new THREE.BoxGeometry(0.78, 0.78, 0.025);
                    const stickerMat = new THREE.MeshPhysicalMaterial({
                        color: 0xffffff,
                        roughness: 0.1,
                        clearcoat: 1.0,
                        clearcoatRoughness: 0.1
                    });
                    const sticker = new THREE.Mesh(stickerGeom, stickerMat);
                    sticker.position.copy(mapping.localPos);
                    sticker.rotation.copy(mapping.localRot);
                    
                    sticker.userData = { face: face, index: i };
                    cubie.add(sticker);
                    stickerMeshes.push(sticker);
                }
            }
        });

        // Click Handler (Separate drag from click)
        let pointerDownX = 0;
        let pointerDownY = 0;

        renderer.domElement.addEventListener('pointerdown', (e) => {
            pointerDownX = e.clientX;
            pointerDownY = e.clientY;
        });

        renderer.domElement.addEventListener('click', (e) => {
            const diffX = Math.abs(e.clientX - pointerDownX);
            const diffY = Math.abs(e.clientY - pointerDownY);
            if (diffX < 5 && diffY < 5) {
                const intersected = getIntersectedSticker(e);
                if (intersected) {
                    e.stopPropagation();
                    showPaletteForSticker(intersected, e);
                }
            }
        });

        // Hover Effect Handler
        let hoveredSticker = null;
        renderer.domElement.addEventListener('pointermove', (e) => {
            const intersected = getIntersectedSticker(e);
            if (intersected !== hoveredSticker) {
                if (hoveredSticker) {
                    hoveredSticker.material.emissive.setHex(0x000000);
                }
                hoveredSticker = intersected;
                if (hoveredSticker) {
                    hoveredSticker.material.emissive.setHex(0x333333);
                    renderer.domElement.style.cursor = 'pointer';
                } else {
                    renderer.domElement.style.cursor = 'grab';
                }
            }
        });

        // Window resize
        window.addEventListener('resize', onWindowResize);

        // Start Animation loop
        animate();

        is3DInitialized = true;
    }

    function onWindowResize() {
        if (!renderer || !camera) return;
        const container = document.getElementById('cube3DViewport');
        if (!container) return;
        camera.aspect = container.clientWidth / container.clientHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(container.clientWidth, container.clientHeight);
    }

    function animate() {
        requestAnimationFrame(animate);
        if (controls) controls.update();
        if (renderer && scene && camera) {
            renderer.render(scene, camera);
        }
    }

    function getIntersectedSticker(event) {
        if (!renderer) return null;
        const rect = renderer.domElement.getBoundingClientRect();
        const mouseX = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        const mouseY = -((event.clientY - rect.top) / rect.height) * 2 + 1;

        const raycaster = new THREE.Raycaster();
        raycaster.setFromCamera(new THREE.Vector2(mouseX, mouseY), camera);
        const intersects = raycaster.intersectObjects(stickerMeshes);
        if (intersects.length > 0) {
            return intersects[0].object;
        }
        return null;
    }

    function getStickerMapping(face, index) {
        const r = Math.floor(index / 3);
        const c = index % 3;
        let x = 0, y = 0, z = 0;
        let localPos = new THREE.Vector3();
        let localRot = new THREE.Euler();

        switch (face) {
            case 'up':
                x = c - 1;
                y = 1;
                z = r - 1;
                localPos.set(0, 0.46, 0);
                localRot.set(-Math.PI / 2, 0, 0);
                break;
            case 'down':
                x = c - 1;
                y = -1;
                z = 1 - r;
                localPos.set(0, -0.46, 0);
                localRot.set(Math.PI / 2, 0, 0);
                break;
            case 'left':
                x = -1;
                y = 1 - r;
                z = c - 1;
                localPos.set(-0.46, 0, 0);
                localRot.set(0, -Math.PI / 2, 0);
                break;
            case 'right':
                x = 1;
                y = 1 - r;
                z = 1 - c;
                localPos.set(0.46, 0, 0);
                localRot.set(0, Math.PI / 2, 0);
                break;
            case 'front':
                x = c - 1;
                y = 1 - r;
                z = 1;
                localPos.set(0, 0, 0.46);
                localRot.set(0, 0, 0);
                break;
            case 'back':
                x = 1 - c;
                y = 1 - r;
                z = -1;
                localPos.set(0, 0, -0.46);
                localRot.set(0, Math.PI, 0);
                break;
        }
        return { x, y, z, localPos, localRot };
    }

    function update3DStickerColors() {
        if (!stickerMeshes || stickerMeshes.length === 0) return;
        stickerMeshes.forEach(sticker => {
            const face = sticker.userData.face;
            const index = sticker.userData.index;
            const colorName = currentFacesColors[face][index];
            sticker.material.color.setHex(getColorHex(colorName));
        });
    }

    function renderCorrectionUI(faces) {
        currentFacesColors = JSON.parse(JSON.stringify(faces)); // Deep copy
        originalScannedColors = JSON.parse(JSON.stringify(faces)); // Copy for reset

        correctionSection.classList.remove('d-none');
        
        // Hide solution results from previous runs
        results.classList.add('d-none');
        
        if (!is3DInitialized) {
            // Give layout a brief moment to compute widths so camera aspect ratio matches
            setTimeout(() => {
                init3DScene();
                update3DStickerColors();
                const loader = document.getElementById('cube3DLoading');
                if (loader) {
                    loader.style.opacity = 0;
                    setTimeout(() => loader.classList.add('d-none'), 500);
                }
            }, 100);
        } else {
            update3DStickerColors();
            const loader = document.getElementById('cube3DLoading');
            if (loader) loader.classList.add('d-none');
        }

        validateCube();
    }

    function showPaletteForSticker(sticker, event) {
        active3DSticker = sticker;
        colorPalette.classList.remove('d-none');
        
        // Position palette near mouse click
        colorPalette.style.top = `${event.clientY + window.scrollY - 80}px`;
        colorPalette.style.left = `${event.clientX + window.scrollX - 40}px`;
    }

    // Hide palette when clicking elsewhere
    document.addEventListener('click', () => {
        colorPalette.classList.add('d-none');
    });

    colorPalette.addEventListener('click', (e) => {
        e.stopPropagation();
        const option = e.target.closest('.palette-option');
        if (!option || !active3DSticker) return;
        
        const newColor = option.dataset.color;
        const face = active3DSticker.userData.face;
        const index = active3DSticker.userData.index;
        
        // Update state
        currentFacesColors[face][index] = newColor;
        
        // Update material
        active3DSticker.material.color.setHex(getColorHex(newColor));
        
        colorPalette.classList.add('d-none');
        validateCube();
    });

    function validateCube() {
        const allColors = [];
        Object.values(currentFacesColors).forEach(faceColors => {
            allColors.push(...faceColors);
        });
        
        const counts = {};
        ['white', 'yellow', 'red', 'orange', 'blue', 'green'].forEach(c => counts[c] = 0);
        
        allColors.forEach(color => {
            if (counts[color] !== undefined) counts[color]++;
        });
        
        let isValid = true;
        Object.keys(counts).forEach(color => {
            const count = counts[color];
            const item = document.querySelector(`.counter-item[data-color="${color}"]`);
            const countSpan = item.querySelector('.count');
            
            countSpan.textContent = count;
            if (count !== 9) {
                item.classList.add('invalid');
                isValid = false;
            } else {
                item.classList.remove('invalid');
            }
        });
        
        solveFinalBtn.disabled = !isValid;
    }

    solveFinalBtn.addEventListener('click', async () => {
        results.classList.add('d-none');
        correctionSection.style.opacity = '0.3';
        loading.classList.remove('d-none');
        
        try {
            const resp = await fetch('/solve_final', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ faces_colors: currentFacesColors })
            });
            const data = await resp.json();
            if (data.success) {
                renderSolution(data.solution);
                renderDetectedFaces(data.faces_colors);
                results.classList.remove('d-none');
                results.scrollIntoView({ behavior: 'smooth' });
                correctionSection.classList.add('d-none'); // Hide correction after success
            } else {
                showError(data.error);
            }
        } catch (err) {
            showError("Solving error.");
        } finally {
            loading.classList.add('d-none');
            correctionSection.style.opacity = '1';
        }
    });

    rescanBtn.addEventListener('click', () => {
        correctionSection.classList.add('d-none');
        bootstrap.Modal.getOrCreateInstance(cameraModal).show();
        currentScanIndex = 0;
        thumbnailContainer.innerHTML = '';
        updateScanUI();
        openCamera();
    });

    if (resetCorrectionsBtn) {
        resetCorrectionsBtn.addEventListener('click', () => {
            if (originalScannedColors) {
                currentFacesColors = JSON.parse(JSON.stringify(originalScannedColors));
                update3DStickerColors();
                validateCube();
            }
        });
    }

    if (resetCubeBtn) {
        resetCubeBtn.addEventListener('click', () => {
            const facesList = ['up', 'left', 'front', 'right', 'down', 'back'];
            facesList.forEach(face => {
                // Keep the center color (index 4) and set all stickers on the face to it
                const centerColor = currentFacesColors[face][4] || 'white';
                for (let i = 0; i < 9; i++) {
                    currentFacesColors[face][i] = centerColor;
                }
            });
            update3DStickerColors();
            validateCube();
        });
    }
});
