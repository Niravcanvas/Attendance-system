// static/js/classphoto.js - Class photo capture functionality
document.addEventListener('DOMContentLoaded', function() {
    const video = document.getElementById("dashboardVideo");
    const startBtn = document.getElementById("startDashboardCam");
    const captureBtn = document.getElementById("captureClassMain");
    const subjectSelect = document.getElementById("subjectSelect");
    const teacherSelect = document.getElementById("teacherSelect");
    const statusText = document.getElementById("classCaptureStatus");
    
    if (!video || !cameraManager) {
        console.error('Camera manager not available');
        return;
    }
    
    // Start camera button
    if (startBtn) {
        startBtn.addEventListener("click", async () => {
            if (cameraManager.isActive) {
                cameraManager.stopCamera();
                startBtn.innerHTML = '<i class="fas fa-video mr-2"></i>Start Camera';
                startBtn.classList.remove('bg-danger-600', 'hover:bg-danger-700');
                startBtn.classList.add('bg-primary-600', 'hover:bg-primary-700');
                updateCameraStatus(false);
                setStatus("📷 Camera stopped", "text-gray-400");
            } else {
                const success = await cameraManager.startCamera();
                if (success) {
                    startBtn.innerHTML = '<i class="fas fa-stop mr-2"></i>Stop Camera';
                    startBtn.classList.remove('bg-primary-600', 'hover:bg-primary-700');
                    startBtn.classList.add('bg-danger-600', 'hover:bg-danger-700');
                    updateCameraStatus(true);
                    setStatus("📷 Camera ready", "text-emerald-400");
                } else {
                    setStatus("❌ Camera access failed", "text-red-400");
                }
            }
        });
    }
    
    // Capture class photo
    if (captureBtn) {
        captureBtn.addEventListener("click", captureClass);
    }
    
    async function captureClass() {
        if (!cameraManager.isActive) {
            setStatus("❌ Please start camera first", "text-red-400");
            toast('Please start camera first', 'warning');
            return;
        }
        
        const subject = subjectSelect?.value;
        const teacher = teacherSelect?.value || "{{ session.user_id }}";
        
        if (!subject) {
            setStatus("❌ Please select a subject", "text-red-400");
            toast('Please select a subject', 'error');
            return;
        }
        
        setLoading(captureBtn, true, 'Capturing...');
        setStatus("⏳ Processing class photo...", "text-blue-400");
        
        try {
            // Capture frame
            const imageData = cameraManager.captureFrame('dataurl');
            
            // Create form data
            const formData = new FormData();
            const blob = dataURLtoBlob(imageData);
            formData.append('image', blob, 'class_photo.jpg');
            formData.append('subject_id', subject);
            formData.append('teacher_id', teacher);
            
            // Upload and recognize
            showLoading('Uploading and recognizing faces...');
            const response = await fetch('/recognize', {
                method: 'POST',
                body: formData
            });
            
            hideLoading();
            
            if (response.ok) {
                const data = await response.json();
                
                if (data.success) {
                    setStatus(`✅ Recognized ${data.recognized} of ${data.faces_found} faces`, "text-emerald-400");
                    toast(`Attendance marked for ${data.recognized} students`, 'success');
                    
                    // Show preview if available
                    if (data.annotated_image) {
                        const win = window.open('', '_blank');
                        win.document.write(`
                            <html>
                            <head>
                                <title>Recognition Results</title>
                                <style>
                                    body { margin: 0; padding: 20px; background: #0f172a; color: white; }
                                    img { max-width: 100%; border-radius: 10px; border: 2px solid #3b82f6; }
                                    .info { margin-top: 20px; padding: 20px; background: #1e293b; border-radius: 10px; }
                                </style>
                            </head>
                            <body>
                                <h1>Recognition Results</h1>
                                <img src="${data.annotated_image}">
                                <div class="info">
                                    <h3>Summary</h3>
                                    <p><strong>Faces Found:</strong> ${data.faces_found}</p>
                                    <p><strong>Recognized:</strong> ${data.recognized}</p>
                                    <p><strong>Success Rate:</strong> ${Math.round((data.recognized / data.faces_found) * 100)}%</p>
                                    <p><strong>Timestamp:</strong> ${new Date().toLocaleString()}</p>
                                </div>
                            </body>
                            </html>
                        `);
                    }
                    
                    // Redirect to attendance page after 2 seconds
                    setTimeout(() => {
                        window.location.href = '/attendance';
                    }, 2000);
                } else {
                    setStatus(`❌ ${data.error || 'Recognition failed'}`, "text-red-400");
                    toast(data.error || 'Recognition failed', 'error');
                }
            } else {
                const error = await response.text();
                setStatus(`❌ Server error: ${error}`, "text-red-400");
                toast('Server error', 'error');
            }
        } catch (err) {
            console.error(err);
            setStatus("❌ Network error", "text-red-400");
            toast('Network error', 'error');
        } finally {
            setLoading(captureBtn, false);
            hideLoading();
        }
    }
    
    // Helper functions
    function setStatus(text, cls) {
        if (!statusText) return;
        statusText.textContent = text;
        statusText.className = `text-sm ${cls}`;
    }
    
    function updateCameraStatus(isActive) {
        const statusIndicator = document.getElementById('dashboardCameraStatus');
        if (statusIndicator) {
            if (isActive) {
                statusIndicator.innerHTML = '<i class="fas fa-circle text-success mr-1"></i>Camera On';
                statusIndicator.classList.remove('bg-black/70', 'text-gray-300');
                statusIndicator.classList.add('bg-green-900/30', 'text-green-300');
            } else {
                statusIndicator.innerHTML = '<i class="fas fa-circle text-danger mr-1"></i>Camera Off';
                statusIndicator.classList.remove('bg-green-900/30', 'text-green-300');
                statusIndicator.classList.add('bg-black/70', 'text-gray-300');
            }
        }
    }
    
    function dataURLtoBlob(dataURL) {
        const arr = dataURL.split(',');
        const mime = arr[0].match(/:(.*?);/)[1];
        const bstr = atob(arr[1]);
        let n = bstr.length;
        const u8arr = new Uint8Array(n);
        while (n--) {
            u8arr[n] = bstr.charCodeAt(n);
        }
        return new Blob([u8arr], { type: mime });
    }
    
    // Keyboard shortcuts
    document.addEventListener("keydown", e => {
        // Space to toggle camera
        if (e.key === ' ' && !e.target.matches('input, textarea, select')) {
            e.preventDefault();
            if (startBtn) startBtn.click();
        }
        
        // F to flip camera
        if ((e.key === 'f' || e.key === 'F') && cameraManager.isActive) {
            e.preventDefault();
            cameraManager.toggleCamera();
            toast('Camera flipped', 'info');
        }
        
        // C to capture
        if ((e.key === 'c' || e.key === 'C') && cameraManager.isActive) {
            e.preventDefault();
            if (captureBtn) captureBtn.click();
        }
    });
    
    // Initialize camera status
    updateCameraStatus(cameraManager.isActive);
    
    // Listen for camera events
    document.addEventListener('camera:start', () => updateCameraStatus(true));
    document.addEventListener('camera:stop', () => updateCameraStatus(false));
});