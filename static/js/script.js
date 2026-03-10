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
            const response = await fetch('/solve', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                renderSolution(data.solution);
                renderDetectedFaces(data.faces_colors);
                
                results.classList.remove('d-none');
                results.scrollIntoView({ behavior: 'smooth' });
            } else {
                showError(data.error || "Recognition failed. Please ensure high quality photos.");
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

    // --- Correction UI Logic ---
    const correctionSection = document.getElementById('correctionSection');
    const colorPalette = document.getElementById('colorPalette');
    const solveFinalBtn = document.getElementById('solveFinalBtn');
    const rescanBtn = document.getElementById('rescanBtn');
    
    let currentFacesColors = {};
    let activeSquare = null;

    function renderCorrectionUI(faces) {
        currentFacesColors = JSON.parse(JSON.stringify(faces)); // Deep copy
        const map = { 'up': 'UP', 'left': 'LEFT', 'front': 'FRONT', 'right': 'RIGHT', 'down': 'DOWN', 'back': 'BACK' };
        
        Object.keys(map).forEach(faceKey => {
            const gridId = `correct-${map[faceKey]}`;
            const grid = document.getElementById(gridId);
            if (!grid) return;
            
            grid.innerHTML = '';
            const colors = currentFacesColors[faceKey] || Array(9).fill('white');
            
            colors.forEach((color, index) => {
                const square = document.createElement('div');
                square.className = `cube-square col-${color.toLowerCase()}`;
                square.dataset.face = faceKey;
                square.dataset.index = index;
                
                square.addEventListener('click', (e) => {
                    e.stopPropagation();
                    showPalette(square, e);
                });
                
                grid.appendChild(square);
            });
        });
        
        validateCube();
    }

    function showPalette(square, event) {
        activeSquare = square;
        colorPalette.classList.remove('d-none');
        
        // Position palette near the square
        const rect = square.getBoundingClientRect();
        colorPalette.style.top = `${rect.top + window.scrollY - 80}px`;
        colorPalette.style.left = `${rect.left + window.scrollX - 40}px`;
    }

    // Hide palette when clicking elsewhere
    document.addEventListener('click', () => {
        colorPalette.classList.add('d-none');
    });

    colorPalette.addEventListener('click', (e) => {
        e.stopPropagation();
        const option = e.target.closest('.palette-option');
        if (!option || !activeSquare) return;
        
        const newColor = option.dataset.color;
        const face = activeSquare.dataset.face;
        const index = parseInt(activeSquare.dataset.index);
        
        // Update state
        currentFacesColors[face][index] = newColor;
        
        // Update UI
        activeSquare.className = `cube-square col-${newColor}`;
        
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
});
