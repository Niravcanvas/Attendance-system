// static/js/camera.js - COMPLETE FIXED VERSION
class CameraManager {
    constructor(options = {}) {
        this.options = {
            videoElementId: 'video',
            canvasElementId: 'canvas',
            ...options
        };
        
        this.video = null;
        this.canvas = null;
        this.ctx = null;
        this.stream = null;
        this.isActive = false;
        this.facingMode = 'user';
        
        console.log('✅ CameraManager initialized');
        
        // Try to get video element now
        this.initializeElements();
    }
    
    initializeElements() {
        // Get video element
        this.video = document.getElementById(this.options.videoElementId);
        if (this.video) {
            console.log('✅ Found video element:', this.options.videoElementId);
        } else {
            console.warn(`⚠️ Video element '${this.options.videoElementId}' not found yet`);
        }
        
        // Get or create canvas
        this.canvas = document.getElementById(this.options.canvasElementId);
        if (!this.canvas) {
            this.canvas = document.createElement('canvas');
            this.canvas.id = this.options.canvasElementId;
            this.canvas.style.display = 'none';
            document.body.appendChild(this.canvas);
            console.log('✅ Created canvas element');
        }
        
        if (this.canvas) {
            this.ctx = this.canvas.getContext('2d');
        }
    }
    
    async startCamera() {
        try {
            console.log('🚀 Starting camera...');
            
            // Get or re-get video element
            this.video = document.getElementById(this.options.videoElementId);
            if (!this.video) {
                console.error('❌ Video element not found:', this.options.videoElementId);
                this.showError('Video element not found. Please refresh the page.');
                return false;
            }
            
            // Stop any existing stream
            await this.stopCamera();
            
            // Camera constraints
            const constraints = {
                video: {
                    facingMode: this.facingMode,
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                },
                audio: false
            };
            
            console.log('📷 Requesting camera with constraints:', constraints);
            
            // Get camera stream
            this.stream = await navigator.mediaDevices.getUserMedia(constraints);
            
            // Set video source
            this.video.srcObject = this.stream;
            
            // Wait for video to be ready
            return new Promise((resolve) => {
                this.video.onloadedmetadata = () => {
                    this.video.play()
                        .then(() => {
                            this.isActive = true;
                            console.log('✅ Camera started successfully');
                            console.log('📐 Video dimensions:', this.video.videoWidth, 'x', this.video.videoHeight);
                            
                            this.updateStatus(true);
                            this.dispatchEvent('start');
                            
                            // Update any dashboard status
                            this.updateDashboardStatus(true);
                            
                            resolve(true);
                        })
                        .catch(err => {
                            console.error('❌ Error playing video:', err);
                            this.showError('Error playing video stream');
                            resolve(false);
                        });
                };
                
                // Timeout fallback
                setTimeout(() => {
                    if (!this.isActive) {
                        console.warn('⚠️ Camera load timeout');
                        resolve(false);
                    }
                }, 5000);
            });
            
        } catch (error) {
            console.error('❌ Camera start error:', error);
            const friendlyError = this.getUserFriendlyError(error);
            this.showError(friendlyError);
            return false;
        }
    }
    
    async stopCamera() {
        console.log('🛑 Stopping camera...');
        
        if (this.stream) {
            this.stream.getTracks().forEach(track => {
                console.log('📴 Stopping track:', track.kind);
                track.stop();
            });
            this.stream = null;
        }
        
        if (this.video) {
            this.video.srcObject = null;
            this.video.pause();
        }
        
        this.isActive = false;
        this.updateStatus(false);
        this.dispatchEvent('stop');
        this.updateDashboardStatus(false);
        
        console.log('✅ Camera stopped');
    }
    
    async toggleCamera() {
        console.log('🔄 Toggling camera...');
        this.facingMode = this.facingMode === 'user' ? 'environment' : 'user';
        
        if (this.isActive) {
            await this.stopCamera();
            await new Promise(resolve => setTimeout(resolve, 300));
            return await this.startCamera();
        }
        return false;
    }
    
    captureFrame(format = 'dataurl', quality = 0.9) {
        if (!this.isActive) {
            throw new Error('Camera not active');
        }
        
        if (!this.video || this.video.videoWidth === 0) {
            throw new Error('Video not ready');
        }
        
        // Ensure canvas exists
        if (!this.canvas) {
            this.canvas = document.createElement('canvas');
            this.ctx = this.canvas.getContext('2d');
        }
        
        // Set canvas size to video size
        this.canvas.width = this.video.videoWidth;
        this.canvas.height = this.video.videoHeight;
        
        // Draw video frame to canvas
        this.ctx.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
        
        // Convert to requested format
        switch (format) {
            case 'blob':
                return new Promise((resolve) => {
                    this.canvas.toBlob(
                        blob => resolve(blob),
                        'image/jpeg',
                        quality
                    );
                });
                
            case 'dataurl':
                return this.canvas.toDataURL('image/jpeg', quality);
                
            case 'base64':
                const dataUrl = this.canvas.toDataURL('image/jpeg', quality);
                return dataUrl.split(',')[1];
                
            default:
                return {
                    dataUrl: this.canvas.toDataURL('image/jpeg', quality),
                    width: this.canvas.width,
                    height: this.canvas.height,
                    timestamp: Date.now()
                };
        }
    }
    
    updateStatus(isActive) {
        // Update camera status element if exists
        const statusElement = document.getElementById('cameraStatus');
        if (statusElement) {
            if (isActive) {
                statusElement.innerHTML = `
                    <span class="status-indicator active"></span>
                    <span class="text-sm font-medium">Camera Active</span>
                `;
                statusElement.className = 'flex items-center gap-2 px-3 py-2 bg-green-900/30 rounded-lg';
            } else {
                statusElement.innerHTML = `
                    <span class="status-indicator inactive"></span>
                    <span class="text-sm font-medium">Camera Offline</span>
                `;
                statusElement.className = 'flex items-center gap-2 px-3 py-2 bg-dark-700 rounded-lg';
            }
        }
        
        // Update camera status text
        const statusText = document.getElementById('cameraStatusText');
        if (statusText) {
            if (isActive) {
                statusText.innerHTML = '<i class="fas fa-check-circle mr-1"></i>Online';
                statusText.className = 'text-sm font-medium text-success';
            } else {
                statusText.innerHTML = '<i class="fas fa-times-circle mr-1"></i>Offline';
                statusText.className = 'text-sm font-medium text-danger';
            }
        }
    }
    
    updateDashboardStatus(isActive) {
        const dashboardStatus = document.getElementById('dashboardCameraStatus');
        if (dashboardStatus) {
            if (isActive) {
                dashboardStatus.innerHTML = '<i class="fas fa-circle text-success mr-1"></i>Camera Active';
                dashboardStatus.className = 'px-2 py-1 bg-green-900/30 text-green-300 rounded text-xs';
            } else {
                dashboardStatus.innerHTML = '<i class="fas fa-circle text-danger mr-1"></i>Camera Off';
                dashboardStatus.className = 'px-2 py-1 bg-black/70 text-gray-300 rounded text-xs';
            }
        }
    }
    
    showError(message, duration = 5000) {
        console.error('Camera Error:', message);
        
        if (window.toast) {
            window.toast(`Camera Error: ${message}`, 'error', duration);
        } else {
            alert(`Camera Error: ${message}`);
        }
    }
    
    getUserFriendlyError(error) {
        if (error.name === 'NotAllowedError') {
            return 'Camera access denied. Please allow camera permissions in your browser settings.';
        } else if (error.name === 'NotFoundError') {
            return 'No camera found. Please connect a camera to your device.';
        } else if (error.name === 'NotReadableError') {
            return 'Camera is in use by another application. Please close other apps using the camera.';
        } else if (error.name === 'OverconstrainedError') {
            return 'Camera constraints could not be met. Try a different camera.';
        } else if (error.name === 'SecurityError') {
            return 'Camera access blocked for security reasons. Use HTTPS or localhost.';
        } else {
            return error.message || 'Unknown camera error. Please check console for details.';
        }
    }
    
    dispatchEvent(eventName, detail = {}) {
        const event = new CustomEvent(`camera:${eventName}`, {
            detail: {
                manager: this,
                timestamp: Date.now(),
                ...detail
            }
        });
        document.dispatchEvent(event);
    }
    
    // Utility methods
    getResolution() {
        if (this.video && this.video.videoWidth > 0) {
            return {
                width: this.video.videoWidth,
                height: this.video.videoHeight
            };
        }
        return null;
    }
    
    getState() {
        return {
            isActive: this.isActive,
            facingMode: this.facingMode,
            resolution: this.getResolution(),
            hasVideo: !!this.video,
            hasStream: !!this.stream
        };
    }
}

// Global instance
let cameraManager = null;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('📱 DOM Content Loaded - Initializing CameraManager');
    
    // Create camera manager
    cameraManager = new CameraManager();
    
    // Debug info
    console.log('🎥 CameraManager created:', cameraManager);
    console.log('📹 Video element exists:', document.getElementById('video') !== null);
    
    // Set up global event listeners
    setupGlobalCameraListeners();
    
    console.log('✅ Camera system ready');
});

function setupGlobalCameraListeners() {
    // Global camera start/stop buttons
    document.addEventListener('click', function(e) {
        const target = e.target.closest('[data-camera-action]');
        if (!target) return;
        
        const action = target.getAttribute('data-camera-action');
        
        if (!cameraManager) {
            console.error('Camera manager not initialized');
            return;
        }
        
        switch(action) {
            case 'start':
                cameraManager.startCamera();
                break;
            case 'stop':
                cameraManager.stopCamera();
                break;
            case 'toggle':
                cameraManager.toggleCamera();
                break;
            case 'capture':
                if (cameraManager.isActive) {
                    try {
                        const frame = cameraManager.captureFrame('dataurl');
                        console.log('📸 Frame captured:', frame.substring(0, 50) + '...');
                        // You can dispatch a custom event here for other scripts to handle
                        document.dispatchEvent(new CustomEvent('camera:capture', {
                            detail: { frame }
                        }));
                    } catch (error) {
                        console.error('Capture failed:', error);
                    }
                }
                break;
        }
    });
    
    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Only trigger if not typing in an input
        if (e.target.matches('input, textarea, select')) return;
        
        // Space to toggle camera
        if (e.key === ' ' && cameraManager) {
            e.preventDefault();
            if (cameraManager.isActive) {
                cameraManager.stopCamera();
            } else {
                cameraManager.startCamera();
            }
        }
        
        // F to flip camera
        if ((e.key === 'f' || e.key === 'F') && cameraManager?.isActive) {
            e.preventDefault();
            cameraManager.toggleCamera();
        }
        
        // C to capture
        if ((e.key === 'c' || e.key === 'C') && cameraManager?.isActive) {
            e.preventDefault();
            document.dispatchEvent(new CustomEvent('camera:capture'));
        }
    });
    
    // Clean up on page unload
    window.addEventListener('beforeunload', function() {
        if (cameraManager) {
            cameraManager.stopCamera();
        }
    });
}

// Export for global access
window.CameraManager = CameraManager;
window.cameraManager = cameraManager;