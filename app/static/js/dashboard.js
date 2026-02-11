// static/js/dashboard.js - FIXED VERSION
document.addEventListener('DOMContentLoaded', function() {
    console.log('📊 Dashboard loaded');
    
    // ========== CAMERA CONTROLS ==========
    const startBtn = document.getElementById('startDashboardCamera');
    const flipBtn = document.getElementById('flipDashboardCamera');
    const quickCaptureBtn = document.getElementById('quickCaptureBtn');
    
    if (startBtn) {
        startBtn.addEventListener('click', async function() {
            console.log('🎥 Start camera clicked');
            
            if (!cameraManager) {
                console.error('Camera manager not available');
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
    
    if (quickCaptureBtn) {
        quickCaptureBtn.addEventListener('click', async function() {
            if (!cameraManager || !cameraManager.isActive) {
                toast('Please start camera first', 'warning');
                return;
            }
            
            const subject = document.getElementById('quickSubject')?.value;
            const teacher = document.getElementById('quickTeacher')?.value || "{{ session.user_id }}";
            
            if (!subject) {
                toast('Please select a subject', 'error');
                return;
            }
            
            setLoading(quickCaptureBtn, true, 'Capturing...');
            
            try {
                // Capture frame
                const imageData = cameraManager.captureFrame('dataurl');
                
                // Upload and recognize
                const formData = new FormData();
                const blob = dataURLtoBlob(imageData);
                formData.append('image', blob, 'capture.jpg');
                formData.append('subject_id', subject);
                formData.append('teacher_id', teacher);
                
                showLoading('Processing...');
                const response = await fetch('/recognize', {
                    method: 'POST',
                    body: formData
                });
                
                hideLoading();
                
                if (response.ok) {
                    const data = await response.json();
                    if (data.success) {
                        toast(`Recognized ${data.recognized} students`, 'success');
                        // Refresh page after 2 seconds
                        setTimeout(() => window.location.reload(), 2000);
                    } else {
                        toast(data.error || 'Recognition failed', 'error');
                    }
                } else {
                    toast('Server error', 'error');
                }
            } catch (error) {
                console.error('Capture error:', error);
                toast('Capture failed', 'error');
            } finally {
                setLoading(quickCaptureBtn, false);
            }
        });
    }
    
    // Helper function
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
    
    // Listen for camera events to update UI
    document.addEventListener('camera:start', function() {
        console.log('📹 Camera started event received');
        updateCameraUI(true);
    });
    
    document.addEventListener('camera:stop', function() {
        console.log('📹 Camera stopped event received');
        updateCameraUI(false);
    });
    
    function updateCameraUI(isActive) {
        // Update button text
        if (startBtn) {
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
    }
    
    // ========== OTHER FUNCTIONALITY ==========
    
    // Encode faces functionality
    const encodeBtn = document.getElementById('encodeFacesBtn');
    const encodeStatus = document.getElementById('encodeStatus');
    
    if (encodeBtn) {
        encodeBtn.addEventListener('click', async function() {
            if (!confirm('This will generate face encodings for all students. This may take a few minutes. Continue?')) {
                return;
            }
            
            setLoading(encodeBtn, true, 'Encoding...');
            
            try {
                const response = await fetch('/encode', {
                    method: 'POST'
                });
                
                if (response.ok) {
                    toast('Face encoding started', 'info');
                    
                    // Poll for status
                    const checkStatus = async () => {
                        try {
                            const statusResponse = await fetch('/encode_status');
                            const status = await statusResponse.json();
                            
                            if (status.progress >= 100) {
                                toast('Face encoding completed successfully', 'success');
                                setLoading(encodeBtn, false);
                                window.location.reload();
                            } else if (status.status === 'Encoding') {
                                encodeBtn.innerHTML = `<i class="fas fa-spinner fa-spin mr-2"></i>Encoding... ${status.progress}%`;
                                setTimeout(checkStatus, 1000);
                            } else {
                                setLoading(encodeBtn, false);
                            }
                        } catch (error) {
                            console.error('Error checking encode status:', error);
                            setLoading(encodeBtn, false);
                        }
                    };
                    
                    checkStatus();
                } else {
                    const error = await response.text();
                    toast(`Encoding failed: ${error}`, 'error');
                    setLoading(encodeBtn, false);
                }
            } catch (error) {
                console.error('Encode error:', error);
                toast('Encoding failed', 'error');
                setLoading(encodeBtn, false);
            }
        });
    }
    
    // Fetch encode status on page load
    async function fetchEncodeStatus() {
        try {
            const response = await fetch('/encode_status');
            if (response.ok) {
                const status = await response.json();
                if (encodeStatus) {
                    encodeStatus.textContent = `${status.message} (${status.progress || 0}%)`;
                    
                    if (status.progress < 100 && status.status === 'Encoding') {
                        encodeStatus.classList.remove('text-gray-400');
                        encodeStatus.classList.add('text-warning-400');
                    } else {
                        encodeStatus.classList.remove('text-warning-400');
                        encodeStatus.classList.add('text-gray-400');
                    }
                }
            }
        } catch (error) {
            console.error('Error fetching encode status:', error);
        }
    }
    
    // Initial fetch
    fetchEncodeStatus();
    
    // Auto-refresh encode status every 5 seconds
    setInterval(fetchEncodeStatus, 5000);
    
    // Auto-refresh dashboard statistics
    let refreshInterval;
    
    function startAutoRefresh() {
        if (refreshInterval) clearInterval(refreshInterval);
        
        refreshInterval = setInterval(() => {
            if (document.visibilityState === 'visible') {
                refreshDashboardStats();
            }
        }, 30000); // Refresh every 30 seconds
    }
    
    async function refreshDashboardStats() {
        try {
            const response = await fetch('/api/dashboard_stats');
            if (response.ok) {
                const data = await response.json();
                
                // Update stats cards
                const stats = data.stats || {};
                
                if (stats.total_students !== undefined) {
                    const el = document.querySelector('[data-stat="total_students"]');
                    if (el) el.textContent = stats.total_students;
                }
                
                if (stats.today_sessions !== undefined) {
                    const el = document.querySelector('[data-stat="today_sessions"]');
                    if (el) el.textContent = stats.today_sessions;
                }
                
                if (stats.today_attendance !== undefined) {
                    const el = document.querySelector('[data-stat="today_attendance"]');
                    if (el) el.textContent = stats.today_attendance;
                }
                
                console.log('Dashboard stats refreshed');
            }
        } catch (error) {
            console.error('Error refreshing dashboard stats:', error);
        }
    }
    
    // Start auto-refresh when page is visible
    document.addEventListener('visibilitychange', function() {
        if (document.visibilityState === 'visible') {
            startAutoRefresh();
            refreshDashboardStats(); // Refresh immediately
        } else {
            if (refreshInterval) {
                clearInterval(refreshInterval);
                refreshInterval = null;
            }
        }
    });
    
    // Initialize auto-refresh if page is visible
    if (document.visibilityState === 'visible') {
        startAutoRefresh();
    }
    
    // ========== DEBUG BUTTON ==========
    // Add debug button (remove in production)
    const debugBtn = document.createElement('button');
    debugBtn.innerHTML = '🔧 Test Camera';
    debugBtn.className = 'fixed bottom-4 left-4 z-50 px-3 py-2 bg-purple-600 text-white text-sm rounded-lg opacity-50 hover:opacity-100';
    debugBtn.onclick = function() {
        console.log('=== CAMERA DEBUG INFO ===');
        console.log('Camera Manager:', cameraManager);
        console.log('Video Element:', document.getElementById('video'));
        console.log('Camera Active:', cameraManager?.isActive);
        console.log('Stream:', cameraManager?.stream);
        console.log('========================');
        
        // Test camera access directly
        navigator.mediaDevices.getUserMedia({ video: true })
            .then(stream => {
                console.log('✅ Direct camera access OK');
                stream.getTracks().forEach(track => track.stop());
            })
            .catch(err => console.error('❌ Direct camera access failed:', err));
    };
    document.body.appendChild(debugBtn);
    
    console.log('✅ Dashboard initialized');
});