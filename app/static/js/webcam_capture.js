// static/js/webcam_capture.js - Webcam capture functionality
document.addEventListener('DOMContentLoaded', function() {
    // Camera stats overlay
    const statsEl = document.createElement('div');
    statsEl.id = 'cameraStats';
    statsEl.className = 'fixed left-3 top-20 bg-black/50 text-white text-xs px-3 py-2 rounded-lg z-50 hidden';
    document.body.appendChild(statsEl);
    
    let fps = 0;
    let lastTime = performance.now();
    let frames = 0;
    
    function updateStats() {
        if (!cameraManager || !cameraManager.isActive) {
            statsEl.classList.add('hidden');
            return;
        }
        
        const now = performance.now();
        frames++;
        
        if (now - lastTime >= 1000) {
            fps = Math.round((frames * 1000) / (now - lastTime));
            frames = 0;
            lastTime = now;
            
            // Update stats display
            const resolution = cameraManager.getResolution();
            if (resolution) {
                statsEl.innerHTML = `
                    <div class="font-medium">Camera Stats</div>
                    <div class="text-gray-300">FPS: ${fps}</div>
                    <div class="text-gray-300">Resolution: ${resolution.width}x${resolution.height}</div>
                `;
                statsEl.classList.remove('hidden');
            }
        }
        
        requestAnimationFrame(updateStats);
    }
    
    // Start camera when page loads if video element exists
    const video = document.getElementById('video');
    if (video && cameraManager) {
        cameraManager.startCamera().then(success => {
            if (success) {
                updateStats();
            }
        });
    }
    
    // Capture buttons
    const captureBtn = document.getElementById('captureBtn');
    const captureClassBtn = document.getElementById('captureClassBtn');
    
    if (captureBtn) {
        captureBtn.addEventListener('click', async function() {
            if (!cameraManager || !cameraManager.isActive) {
                toast('Camera not ready', 'error', 2000);
                return;
            }
            
            setLoading(captureBtn, true, 'Capturing...');
            
            try {
                const imageData = cameraManager.captureFrame('dataurl');
                const name = document.getElementById('studentName')?.value || 'unknown';
                const subject = document.getElementById('subjectSelectCapture')?.value || 'General';
                const teacher = document.getElementById('teacherSelectCapture')?.value || '';
                
                const formData = new FormData();
                formData.append('image', dataURLtoBlob(imageData), 'face.jpg');
                formData.append('student_name', name);
                formData.append('subject', subject);
                formData.append('teacher', teacher);
                
                const response = await fetch('/upload_photo', {
                    method: 'POST',
                    body: formData
                });
                
                if (response.ok) {
                    const data = await response.json();
                    if (data.success) {
                        toast('Face captured successfully', 'success', 2000);
                    } else {
                        toast(data.error || 'Capture failed', 'error', 4000);
                    }
                } else {
                    toast('Server error', 'error', 4000);
                }
            } catch (error) {
                console.error('Capture error:', error);
                toast('Capture failed', 'error', 4000);
            } finally {
                setLoading(captureBtn, false);
            }
        });
    }
    
    if (captureClassBtn) {
        captureClassBtn.addEventListener('click', async function() {
            if (!cameraManager || !cameraManager.isActive) {
                toast('Camera not ready', 'error', 2000);
                return;
            }
            
            setLoading(captureClassBtn, true, 'Capturing...');
            
            try {
                const imageData = cameraManager.captureFrame('dataurl');
                const subject = document.getElementById('subjectSelectCapture')?.value || 'General';
                const teacher = document.getElementById('teacherSelectCapture')?.value || '';
                
                const formData = new FormData();
                formData.append('image', dataURLtoBlob(imageData), 'class.jpg');
                formData.append('subject', subject);
                formData.append('teacher', teacher);
                
                // Upload photo
                const uploadResponse = await fetch('/upload_photo', {
                    method: 'POST',
                    body: formData
                });
                
                if (uploadResponse.ok) {
                    const uploadData = await uploadResponse.json();
                    if (uploadData.success) {
                        toast('Class photo captured, recognizing faces...', 'success', 2000);
                        
                        // Recognize faces
                        const recognizeForm = new FormData();
                        recognizeForm.append('subject', subject);
                        recognizeForm.append('teacher', teacher);
                        
                        const recognizeResponse = await fetch('/recognize', {
                            method: 'POST',
                            body: recognizeForm
                        });
                        
                        if (recognizeResponse.ok) {
                            const recognizeData = await recognizeResponse.json();
                            if (recognizeData.success) {
                                toast(`Attendance marked for ${recognizeData.recognized} students`, 'success', 3000);
                                setTimeout(() => {
                                    window.location.href = '/attendance';
                                }, 1500);
                            } else {
                                toast(recognizeData.error || 'Recognition failed', 'error', 4000);
                            }
                        } else {
                            toast('Recognition failed', 'error', 4000);
                        }
                    } else {
                        toast(uploadData.error || 'Upload failed', 'error', 4000);
                    }
                } else {
                    toast('Upload failed', 'error', 4000);
                }
            } catch (error) {
                console.error('Class capture error:', error);
                toast('Capture failed', 'error', 4000);
            } finally {
                setLoading(captureClassBtn, false);
            }
        });
    }
    
    // Helper function to convert data URL to blob
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
    
    // InsightFace status check
    const insightfaceStatus = document.getElementById('insightfaceStatus');
    if (insightfaceStatus) {
        fetch('/api/insightface_status')
            .then(response => response.json())
            .then(data => {
                if (data.available) {
                    insightfaceStatus.innerHTML = `
                        <span class="flex items-center gap-1">
                            <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                            InsightFace Ready
                        </span>
                    `;
                    insightfaceStatus.classList.remove('text-gray-400');
                    insightfaceStatus.classList.add('text-emerald-400');
                } else {
                    insightfaceStatus.innerHTML = `
                        <span class="flex items-center gap-1">
                            <span class="w-2 h-2 rounded-full bg-amber-500 animate-pulse"></span>
                            InsightFace Not Available
                        </span>
                    `;
                    insightfaceStatus.classList.remove('text-gray-400');
                    insightfaceStatus.classList.add('text-amber-400');
                }
            })
            .catch(error => {
                console.error('Error checking InsightFace status:', error);
            });
    }
    
    // Clean up on page unload
    window.addEventListener('beforeunload', function() {
        if (cameraManager) {
            cameraManager.stopCamera();
        }
    });
});