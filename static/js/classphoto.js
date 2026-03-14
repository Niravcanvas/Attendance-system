// static/js/classphoto.js - Class photo capture functionality (updated to send threshold)
document.addEventListener('DOMContentLoaded', function() {
    const video      = document.getElementById('dashboardVideo');
    const startBtn   = document.getElementById('startDashboardCam');
    const captureBtn = document.getElementById('captureClassMain');
    const subjectSelect = document.getElementById('subjectSelect');
    const teacherSelect = document.getElementById('teacherSelect');
    const statusText = document.getElementById('classCaptureStatus');
    const thresholdSlider = document.getElementById('thresholdSlider'); // May be present or not

    if (!video || !cameraManager) {
        console.warn('classphoto.js: cameraManager not available yet');
        return;
    }

    // Point cameraManager at the dashboard video element if it differs from default
    if (cameraManager.options && cameraManager.options.videoElementId !== 'dashboardVideo') {
        cameraManager.options.videoElementId = 'dashboardVideo';
        cameraManager.video = video;
    }

    // ========== START / STOP CAMERA ==========
    if (startBtn) {
        startBtn.addEventListener('click', async () => {
            if (cameraManager.isActive) {
                await cameraManager.stopCamera();
                startBtn.innerHTML = '<i class="fas fa-video mr-2"></i>Start Camera';
                startBtn.classList.replace('bg-danger-600', 'bg-primary-600');
                startBtn.classList.replace('hover:bg-danger-700', 'hover:bg-primary-700');
                updateCameraStatus(false);
                setStatus('📷 Camera stopped', 'text-gray-400');
            } else {
                const success = await cameraManager.startCamera();
                if (success) {
                    startBtn.innerHTML = '<i class="fas fa-stop mr-2"></i>Stop Camera';
                    startBtn.classList.replace('bg-primary-600', 'bg-danger-600');
                    startBtn.classList.replace('hover:bg-primary-700', 'hover:bg-danger-700');
                    updateCameraStatus(true);
                    setStatus('📷 Camera ready', 'text-emerald-400');
                } else {
                    setStatus('❌ Camera access failed', 'text-red-400');
                }
            }
        });
    }

    // ========== CAPTURE & RECOGNIZE (combined, single POST) ==========
    if (captureBtn) {
        captureBtn.addEventListener('click', captureClass);
    }

    async function captureClass() {
        if (!cameraManager.isActive) {
            setStatus('❌ Please start camera first', 'text-red-400');
            toast('Please start camera first', 'warning');
            return;
        }

        const subject = subjectSelect?.value;
        const teacher = teacherSelect?.value;
        const threshold = thresholdSlider ? thresholdSlider.value : 0.5;

        if (!subject) {
            setStatus('❌ Please select a subject', 'text-red-400');
            toast('Please select a subject', 'error');
            return;
        }

        setLoading(captureBtn, true, 'Capturing...');
        setStatus('⏳ Processing class photo...', 'text-blue-400');

        try {
            const blob = await cameraManager.captureFrame('blob');
            if (!blob) { toast('Failed to capture frame', 'error'); return; }

            const formData = new FormData();
            formData.append('image', blob, 'class_photo.jpg');
            formData.append('subject_id', subject);
            formData.append('threshold', threshold);
            if (teacher) formData.append('teacher_id', teacher);

            showLoading('Uploading and recognizing faces...');
            const response = await fetch('/recognize', { method: 'POST', body: formData });
            hideLoading();

            const data = await response.json();

            if (data.success) {
                setStatus(`✅ Recognized ${data.recognized} of ${data.faces_found} faces`, 'text-emerald-400');
                toast(`Attendance marked for ${data.recognized} students`, 'success');

                if (data.annotated_image) {
                    const win = window.open('', '_blank');
                    if (win) {
                        win.document.write(`
                            <html><head><title>Recognition Results</title>
                            <style>body{margin:0;padding:20px;background:#0f172a;color:white;font-family:sans-serif;}
                            img{max-width:100%;border-radius:10px;border:2px solid #3b82f6;}
                            .info{margin-top:20px;padding:20px;background:#1e293b;border-radius:10px;}</style>
                            </head><body>
                            <h2>Recognition Results</h2>
                            <img src="${data.annotated_image}">
                            <div class="info">
                                <p><strong>Faces found:</strong> ${data.faces_found}</p>
                                <p><strong>Recognized:</strong> ${data.recognized}</p>
                                <p><strong>Rate:</strong> ${data.faces_found > 0 ? Math.round((data.recognized / data.faces_found) * 100) : 0}%</p>
                                <p><strong>Students:</strong> ${(data.marked_students || []).join(', ') || 'None'}</p>
                            </div></body></html>
                        `);
                    }
                }

                setTimeout(() => { window.location.href = '/attendance'; }, 2000);
            } else {
                setStatus(`❌ ${data.error || 'Recognition failed'}`, 'text-red-400');
                toast(data.error || 'Recognition failed', 'error');
            }
        } catch (err) {
            hideLoading();
            console.error(err);
            setStatus('❌ Network error', 'text-red-400');
            toast('Network error', 'error');
        } finally {
            setLoading(captureBtn, false);
        }
    }

    // ========== HELPERS ==========
    function setStatus(text, cls) {
        if (!statusText) return;
        statusText.textContent = text;
        statusText.className = `text-sm ${cls}`;
    }

    function updateCameraStatus(isActive) {
        const indicator = document.getElementById('dashboardCameraStatus');
        if (!indicator) return;
        if (isActive) {
            indicator.innerHTML = '<i class="fas fa-circle text-success mr-1"></i>Camera On';
            indicator.className = 'px-2 py-1 bg-green-900/30 text-green-300 rounded text-xs';
        } else {
            indicator.innerHTML = '<i class="fas fa-circle text-danger mr-1"></i>Camera Off';
            indicator.className = 'px-2 py-1 bg-black/70 text-gray-300 rounded text-xs';
        }
    }

    // ========== KEYBOARD SHORTCUTS ==========
    document.addEventListener('keydown', e => {
        if (e.target.matches('input, textarea, select')) return;
        if (e.key === ' ') { e.preventDefault(); startBtn?.click(); }
        if ((e.key === 'f' || e.key === 'F') && cameraManager.isActive) {
            e.preventDefault(); cameraManager.toggleCamera(); toast('Camera flipped', 'info');
        }
        if ((e.key === 'c' || e.key === 'C') && cameraManager.isActive) {
            e.preventDefault(); captureBtn?.click();
        }
    });

    // Sync status on load and on camera events
    updateCameraStatus(cameraManager.isActive);
    document.addEventListener('camera:start', () => updateCameraStatus(true));
    document.addEventListener('camera:stop',  () => updateCameraStatus(false));
});