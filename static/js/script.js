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

    let stream = null;
    const scanSequence = ['front', 'right', 'back', 'left', 'up', 'down'];
    let currentScanIndex = 0;
    const capturedImages = {};

    startCameraBtn.addEventListener('click', async () => {
        currentScanIndex = 0;
        thumbnailContainer.innerHTML = '';
        updateScanUI();

        try {
            stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'environment', width: { ideal: 1280 } }
            });
            cameraVideo.srcObject = stream;
        } catch (err) {
            alert("Camera access denied.");
            bootstrap.Modal.getInstance(cameraModal).hide();
        }
    });

    const stopCamera = () => {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            stream = null;
        }
    };

    cameraModal.addEventListener('hidden.bs.modal', stopCamera);

    captureBtn.addEventListener('click', () => {
        const faceName = scanSequence[currentScanIndex];
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
        
        const dataUrl = captureCanvas.toDataURL('image/jpeg', 0.9);
        capturedImages[faceName] = dataUrl;
        
        // Update Grid Preview
        const preview = document.getElementById(`preview-${faceName}`);
        const card = document.getElementById(`area-${faceName}`);
        preview.src = dataUrl;
        preview.classList.remove('d-none');
        card.classList.add('has-image');

        // Add Thumbnail to Modal
        const thumb = document.createElement('img');
        thumb.src = dataUrl;
        thumb.style.width = '40px';
        thumb.style.height = '40px';
        thumb.style.objectFit = 'cover';
        thumb.style.borderRadius = '8px';
        thumb.style.border = '1px solid var(--primary)';
        thumbnailContainer.appendChild(thumb);

        currentScanIndex++;
        if (currentScanIndex < scanSequence.length) {
            updateScanUI();
        } else {
            bootstrap.Modal.getInstance(cameraModal).hide();
            submitScannedImages();
        }
    });

    function updateScanUI() {
        const face = scanSequence[currentScanIndex].toUpperCase();
        btnFaceName.textContent = face;
        scanInstruction.textContent = `Scan ${face} Face`;
    }

    async function submitScannedImages() {
        results.classList.add('d-none');
        form.style.opacity = '0.3';
        loading.classList.remove('d-none');
        
        const payload = {};
        for (const [key, val] of Object.entries(capturedImages)) {
            payload[key] = val;
        }
        
        try {
            const resp = await fetch('/solve', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await resp.json();
            if (data.success) {
                renderSolution(data.solution);
                renderDetectedFaces(data.faces_colors);
                results.classList.remove('d-none');
                results.scrollIntoView({ behavior: 'smooth' });
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
});
