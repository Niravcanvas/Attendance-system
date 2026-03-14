// static/js/dashboard.js
document.addEventListener('DOMContentLoaded', function() {
    console.log('📊 Dashboard loaded');

    // ========== CAMERA CONTROLS ==========
    const startBtn = document.getElementById('startDashboardCamera');
    const flipBtn  = document.getElementById('flipDashboardCamera');
    const quickCaptureBtn = document.getElementById('quickCaptureBtn');
    const thresholdSlider = document.getElementById('thresholdSlider'); // May be present or not
    const thresholdValue = document.getElementById('thresholdValue');

    if (thresholdSlider && thresholdValue) {
        thresholdSlider.addEventListener('input', function() {
            thresholdValue.textContent = this.value;
        });
    }

    if (startBtn) {
        startBtn.addEventListener('click', async function() {
            if (!cameraManager) {
                toast('Camera system not loaded. Please refresh the page.', 'error');
                return;
            }
            if (cameraManager.isActive) {
                await cameraManager.stopCamera();
                this.innerHTML = '<i class="fas fa-video mr-2"></i>Start Camera';
                this.classList.remove('bg-danger-600', 'hover:bg-danger-700');
                this.classList.add('bg-dark-700', 'hover:bg-dark-600');
            } else {
                const success = await cameraManager.startCamera();
                if (success) {
                    this.innerHTML = '<i class="fas fa-stop mr-2"></i>Stop Camera';
                    this.classList.remove('bg-dark-700', 'hover:bg-dark-600');
                    this.classList.add('bg-danger-600', 'hover:bg-danger-700');
                    toast('Camera started', 'success');
                } else {
                    toast('Failed to start camera', 'error');
                }
            }
        });
    }

    if (flipBtn) {
        flipBtn.addEventListener('click', async function() {
            if (!cameraManager || !cameraManager.isActive) {
                toast('Please start camera first', 'warning');
                return;
            }
            await cameraManager.toggleCamera();
            toast('Camera flipped', 'info');
        });
    }

    // ========== QUICK CAPTURE & RECOGNIZE ==========
    if (quickCaptureBtn) {
        quickCaptureBtn.addEventListener('click', async function() {
            if (!cameraManager || !cameraManager.isActive) {
                toast('Please start camera first', 'warning');
                return;
            }

            const subject = document.getElementById('quickSubject')?.value;
            const teacher = document.getElementById('quickTeacher')?.value;
            const threshold = thresholdSlider ? thresholdSlider.value : 0.5;

            if (!subject) {
                toast('Please select a subject', 'error');
                return;
            }

            setLoading(quickCaptureBtn, true, 'Capturing...');
            try {
                const imageData = cameraManager.captureFrame('dataurl');
                const blob = dataURLtoBlob(imageData);

                const formData = new FormData();
                formData.append('image', blob, 'capture.jpg');
                formData.append('subject_id', subject);
                formData.append('threshold', threshold);
                if (teacher) formData.append('teacher_id', teacher);

                showLoading('Processing faces...');
                const response = await fetch('/recognize', { method: 'POST', body: formData });
                hideLoading();

                const data = await response.json();
                if (data.success) {
                    toast(`Recognized ${data.recognized} of ${data.faces_found} students`, 'success');
                    if (data.annotated_image) showAnnotatedResult(data);
                    setTimeout(() => window.location.reload(), 2000);
                } else {
                    toast(data.error || 'Recognition failed', 'error');
                }
            } catch (error) {
                hideLoading();
                toast('Capture failed: ' + error.message, 'error');
            } finally {
                setLoading(quickCaptureBtn, false);
            }
        });
    }

   // ========== ENCODE FACES ==========
const encodeBtn = document.getElementById('encodeFacesBtn');
const encodeStatusEl = document.getElementById('encodeStatus');
let pollTimer = null;
let pollTimeout = null;

if (encodeBtn) {
    encodeBtn.addEventListener('click', async function() {
        if (!confirm('This will generate face encodings for all students in the background. Continue?')) return;
        
        setLoading(encodeBtn, true, 'Starting...');
        encodeStatusEl.textContent = 'Starting encoding...';
        encodeStatusEl.className = 'text-xs text-warning-400 block text-right';
        
        try {
            const response = await fetch('/encode', { method: 'POST', redirect: 'follow' });
            if (!response.ok) {
                const text = await response.text();
                throw new Error(text || 'Server error');
            }
            toast('Face encoding started in background', 'info');
            pollEncodeStatus();
        } catch (error) {
            toast('Failed to start encoding: ' + error.message, 'error');
            setLoading(encodeBtn, false);
            encodeStatusEl.textContent = 'Failed to start';
            encodeStatusEl.className = 'text-xs text-danger-400 block text-right';
        }
    });
}

function pollEncodeStatus() {
    if (pollTimer) clearInterval(pollTimer);
    if (pollTimeout) clearTimeout(pollTimeout);
    
    pollTimer = setInterval(fetchEncodeStatus, 1500);
    // Stop polling after 5 minutes to avoid infinite polling
    pollTimeout = setTimeout(() => {
        if (pollTimer) {
            clearInterval(pollTimer);
            pollTimer = null;
            setLoading(encodeBtn, false);
            encodeStatusEl.textContent = 'Encoding timed out';
            encodeStatusEl.className = 'text-xs text-danger-400 block text-right';
        }
    }, 300000); // 5 minutes
}

async function fetchEncodeStatus() {
    try {
        const response = await fetch('/encode_status');
        if (!response.ok) throw new Error('Status request failed');
        const status = await response.json();

        // Update label
        if (encodeStatusEl) {
            if (status.running) {
                encodeStatusEl.textContent = `Encoding... ${status.progress || 0}% (${status.done || 0}/${status.total || 0}) - ${status.message || ''}`;
                encodeStatusEl.className = 'text-xs text-warning-400 block text-right';
            } else if (status.status === 'complete') {
                encodeStatusEl.textContent = status.message || 'Encodings ready';
                encodeStatusEl.className = 'text-xs text-success-400 block text-right';
                if (pollTimer) clearInterval(pollTimer);
                pollTimer = null;
                setLoading(encodeBtn, false);
                toast('Encoding complete!', 'success');
                // Refresh stats
                if (typeof loadStatistics === 'function') {
                    loadStatistics();
                }
            } else if (status.status === 'error') {
                encodeStatusEl.textContent = 'Error: ' + (status.error || 'Unknown');
                encodeStatusEl.className = 'text-xs text-danger-400 block text-right';
                if (pollTimer) clearInterval(pollTimer);
                pollTimer = null;
                setLoading(encodeBtn, false);
                toast('Encoding failed: ' + (status.error || 'Unknown error'), 'error');
            } else {
                const encoded = status.encoded_students || 0;
                const total = status.total_students || 0;
                encodeStatusEl.textContent = total > 0 ? `${encoded}/${total} encoded` : 'Not encoded yet';
                encodeStatusEl.className = 'text-xs text-gray-400 block text-right';
                if (pollTimer) clearInterval(pollTimer);
                pollTimer = null;
                setLoading(encodeBtn, false);
            }
        }

        // Update button
        if (encodeBtn) {
            if (status.running) {
                encodeBtn.innerHTML = `<i class="fas fa-spinner fa-spin mr-2"></i>Encoding ${status.progress || 0}%`;
                encodeBtn.disabled = true;
            } else {
                setLoading(encodeBtn, false);
            }
        }
    } catch (error) {
        console.error('Error fetching encode status:', error);
        if (encodeStatusEl) {
            encodeStatusEl.textContent = 'Status check failed';
            encodeStatusEl.className = 'text-xs text-danger-400 block text-right';
        }
        if (pollTimer) {
            clearInterval(pollTimer);
            pollTimer = null;
        }
        setLoading(encodeBtn, false);
    }
}

    // ========== CAMERA EVENTS ==========
    document.addEventListener('camera:start', () => updateCameraUI(true));
    document.addEventListener('camera:stop',  () => updateCameraUI(false));

    function updateCameraUI(isActive) {
        if (!startBtn) return;
        if (isActive) {
            startBtn.innerHTML = '<i class="fas fa-stop mr-2"></i>Stop Camera';
            startBtn.classList.remove('bg-dark-700', 'hover:bg-dark-600');
            startBtn.classList.add('bg-danger-600', 'hover:bg-danger-700');
        } else {
            startBtn.innerHTML = '<i class="fas fa-video mr-2"></i>Start Camera';
            startBtn.classList.remove('bg-danger-600', 'hover:bg-danger-700');
            startBtn.classList.add('bg-dark-700', 'hover:bg-dark-600');
        }
    }

    // ========== DASHBOARD STATS AUTO-REFRESH ==========
    let refreshInterval;

    async function refreshDashboardStats() {
        try {
            const response = await fetch('/api/dashboard_stats');
            if (!response.ok) return;
            const data = await response.json();
            const stats = data.stats || {};
            ['total_students', 'today_sessions', 'today_attendance', 'total_attendance'].forEach(key => {
                if (stats[key] !== undefined) {
                    const el = document.querySelector(`[data-stat="${key}"]`);
                    if (el) el.textContent = stats[key];
                }
            });
        } catch (e) { /* silent */ }
    }

    function startAutoRefresh() {
        if (refreshInterval) clearInterval(refreshInterval);
        refreshInterval = setInterval(() => {
            if (document.visibilityState === 'visible') refreshDashboardStats();
        }, 30000);
    }

    document.addEventListener('visibilitychange', function() {
        if (document.visibilityState === 'visible') { startAutoRefresh(); refreshDashboardStats(); }
        else { if (refreshInterval) { clearInterval(refreshInterval); refreshInterval = null; } }
    });

    if (document.visibilityState === 'visible') startAutoRefresh();

    // ========== HELPERS ==========
    function showAnnotatedResult(data) {
        const popup = window.open('', '_blank', 'width=800,height=620');
        if (!popup) return;
        popup.document.write(`<!DOCTYPE html><html><head><title>Recognition Results</title>
            <style>body{margin:0;padding:20px;background:#0f172a;color:white;font-family:sans-serif;}
            img{max-width:100%;border-radius:10px;border:2px solid #3b82f6;}
            .info{margin-top:20px;padding:20px;background:#1e293b;border-radius:10px;}</style>
            </head><body>
            <h2>Recognition Results</h2>
            <img src="${data.annotated_image}" alt="Annotated">
            <div class="info">
                <p><strong>Faces found:</strong> ${data.faces_found}</p>
                <p><strong>Recognized:</strong> ${data.recognized}</p>
                <p><strong>Students:</strong> ${(data.marked_students || []).join(', ') || 'None'}</p>
            </div></body></html>`);
    }

    function dataURLtoBlob(dataURL) {
        const arr = dataURL.split(',');
        const mime = arr[0].match(/:(.*?);/)[1];
        const bstr = atob(arr[1]);
        let n = bstr.length;
        const u8arr = new Uint8Array(n);
        while (n--) u8arr[n] = bstr.charCodeAt(n);
        return new Blob([u8arr], { type: mime });
    }

    window.dataURLtoBlob = dataURLtoBlob;

    console.log('✅ Dashboard initialized');
});