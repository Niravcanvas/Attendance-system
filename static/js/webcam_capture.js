// static/js/webcam_capture.js
document.addEventListener('DOMContentLoaded', function() {

    // ========== CAMERA STATS OVERLAY ==========
    const statsEl = document.createElement('div');
    statsEl.id = 'cameraStats';
    statsEl.className = 'fixed left-3 top-20 bg-black/50 text-white text-xs px-3 py-2 rounded-lg z-50 hidden';
    document.body.appendChild(statsEl);

    let fps = 0, lastTime = performance.now(), frames = 0;

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

    // Auto-start camera if video element is present
    const video = document.getElementById('video');
    if (video && cameraManager) {
        cameraManager.startCamera().then(success => {
            if (success) updateStats();
        });
    }

    // ========== CAPTURE SINGLE STUDENT ==========
    // Sends captured frame directly to /api/capture_student
    const captureBtn = document.getElementById('captureBtn');
    if (captureBtn) {
        captureBtn.addEventListener('click', async function() {
            if (!cameraManager || !cameraManager.isActive) {
                toast('Camera not ready', 'error', 2000);
                return;
            }

            const studentId = document.getElementById('studentSelect')?.value;
            if (!studentId) {
                toast('Please select a student', 'error', 2000);
                return;
            }

            setLoading(captureBtn, true, 'Capturing...');
            try {
                // captureFrame('blob') returns a Promise
                const blob = await cameraManager.captureFrame('blob');
                if (!blob) { toast('Failed to capture frame', 'error'); return; }

                const formData = new FormData();
                formData.append('student_id', studentId);
                formData.append('image', blob, 'face.jpg');

                const response = await fetch('/api/capture_student', { method: 'POST', body: formData });
                const data = await response.json();

                if (data.success) {
                    toast(`Face captured for ${data.student_name}`, 'success', 2000);
                } else {
                    toast(data.error || 'Capture failed', 'error', 4000);
                }
            } catch (error) {
                console.error('Capture error:', error);
                toast('Capture failed', 'error', 4000);
            } finally {
                setLoading(captureBtn, false);
            }
        });
    }

    // ========== CAPTURE CLASS PHOTO & RECOGNIZE ==========
    // FIX: Sends image directly to /recognize (single request) instead of upload then recognize.
    // This avoids the bug where annotated files could be picked up as "latest photo".
    const captureClassBtn = document.getElementById('captureClassBtn');
    if (captureClassBtn) {
        captureClassBtn.addEventListener('click', async function() {
            if (!cameraManager || !cameraManager.isActive) {
                toast('Camera not ready', 'error', 2000);
                return;
            }

            const subjectId = document.getElementById('subjectSelectCapture')?.value;
            const teacherId = document.getElementById('teacherSelectCapture')?.value;

            if (!subjectId) {
                toast('Please select a subject', 'error', 2000);
                return;
            }

            setLoading(captureClassBtn, true, 'Recognizing...');
            showLoading('Recognizing faces...');

            try {
                const blob = await cameraManager.captureFrame('blob');
                if (!blob) { toast('Failed to capture frame', 'error'); return; }

                const formData = new FormData();
                formData.append('image', blob, 'class.jpg');
                formData.append('subject_id', subjectId);
                if (teacherId) formData.append('teacher_id', teacherId);

                const response = await fetch('/recognize', { method: 'POST', body: formData });
                hideLoading();

                const data = await response.json();
                if (data.success) {
                    toast(`Attendance marked for ${data.recognized} students`, 'success', 3000);
                    setTimeout(() => { window.location.href = '/attendance'; }, 1500);
                } else {
                    toast(data.error || 'Recognition failed', 'error', 4000);
                }
            } catch (error) {
                hideLoading();
                console.error('Class capture error:', error);
                toast('Capture failed', 'error', 4000);
            } finally {
                setLoading(captureClassBtn, false);
            }
        });
    }

    // ========== INSIGHTFACE STATUS CHECK ==========
    const insightfaceStatus = document.getElementById('insightfaceStatus');
    if (insightfaceStatus) {
        fetch('/api/insightface_status')
            .then(r => r.json())
            .then(data => {
                if (data.available) {
                    insightfaceStatus.innerHTML = `
                        <span class="flex items-center gap-1">
                            <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                            InsightFace Ready
                        </span>`;
                    insightfaceStatus.className = 'text-xs text-emerald-400';
                } else {
                    insightfaceStatus.innerHTML = `
                        <span class="flex items-center gap-1">
                            <span class="w-2 h-2 rounded-full bg-amber-500 animate-pulse"></span>
                            InsightFace Not Available
                        </span>`;
                    insightfaceStatus.className = 'text-xs text-amber-400';
                }
            })
            .catch(() => {});
    }

    // ========== CLEANUP ==========
    window.addEventListener('beforeunload', function() {
        if (cameraManager) cameraManager.stopCamera();
    });
});