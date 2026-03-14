// static/js/camera.js - COMPLETE FIXED VERSION with orientation handling and manual rotate view
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
        this.rotation = 0; // manual rotation applied to video element (0, 90, 180, 270)
        
        console.log('✅ CameraManager initialized');
        this.initializeElements();
    }
    
    initializeElements() {
        this.video = document.getElementById(this.options.videoElementId);
        if (this.video) {
            console.log('✅ Found video element:', this.options.videoElementId);
        } else {
            console.warn(`⚠️ Video element '${this.options.videoElementId}' not found yet`);
        }
        
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
            
            this.video = document.getElementById(this.options.videoElementId);
            if (!this.video) {
                console.error('❌ Video element not found:', this.options.videoElementId);
                this.showError('Video element not found. Please refresh the page.');
                return false;
            }
            
            await this.stopCamera();
            
            const constraints = {
                video: {
                    facingMode: this.facingMode,
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                },
                audio: false
            };
            
            console.log('📷 Requesting camera with constraints:', constraints);
            
            this.stream = await navigator.mediaDevices.getUserMedia(constraints);
            this.video.srcObject = this.stream;
            
            return new Promise((resolve) => {
                this.video.onloadedmetadata = () => {
                    this.video.play()
                        .then(() => {
                            this.isActive = true;
                            console.log('✅ Camera started successfully');
                            console.log('📐 Video dimensions:', this.video.videoWidth, 'x', this.video.videoHeight);
                            
                            this.updateStatus(true);
                            this.dispatchEvent('start');
                            this.updateDashboardStatus(true);
                            
                            resolve(true);
                        })
                        .catch(err => {
                            console.error('❌ Error playing video:', err);
                            this.showError('Error playing video stream');
                            resolve(false);
                        });
                };
                
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
    
    // Manual rotation of video element (for user convenience)
    rotateView(angle = 90) {
        this.rotation = (this.rotation + angle) % 360;
        if (this.video) {
            this.video.style.transform = `rotate(${this.rotation}deg)`;
            // Optional: adjust container size? We rely on CSS object-fit.
        }
    }
    
    // Get current screen orientation in degrees (0, 90, 180, 270)
    getOrientationAngle() {
        if (window.screen && window.screen.orientation) {
            return window.screen.orientation.angle; // 0, 90, 180, 270
        }
        if (window.orientation !== undefined) {
            // iOS < 13
            return window.orientation; // -90, 0, 90, 180
        }
        return 0;
    }
    
    // Capture frame with optional rotation correction
    captureFrame(format = 'dataurl', quality = 0.9, applyOrientation = true) {
        if (!this.isActive) throw new Error('Camera not active');
        if (!this.video || this.video.videoWidth === 0) throw new Error('Video not ready');
        
        let angle = 0;
        if (applyOrientation) {
            angle = this.getOrientationAngle();
            if (angle < 0) angle += 360; // normalize negative
        }
        
        const videoWidth = this.video.videoWidth;
        const videoHeight = this.video.videoHeight;
        let canvasWidth, canvasHeight;
        
        if (angle % 180 === 0) {
            canvasWidth = videoWidth;
            canvasHeight = videoHeight;
        } else {
            canvasWidth = videoHeight;
            canvasHeight = videoWidth;
        }
        
        if (!this.canvas) {
            this.canvas = document.createElement('canvas');
            this.ctx = this.canvas.getContext('2d');
        }
        this.canvas.width = canvasWidth;
        this.canvas.height = canvasHeight;
        
        // Clear, translate, rotate, draw
        this.ctx.save();
        this.ctx.translate(canvasWidth / 2, canvasHeight / 2);
        this.ctx.rotate(angle * Math.PI / 180);
        this.ctx.drawImage(this.video, -videoWidth / 2, -videoHeight / 2);
        this.ctx.restore();
        
        // Return in requested format
        switch (format) {
            case 'blob':
                return new Promise((resolve) => {
                    this.canvas.toBlob(blob => resolve(blob), 'image/jpeg', quality);
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
        const statusElement = document.getElementById('cameraStatus');
        if (statusElement) {
            if (isActive) {
                statusElement.innerHTML = `<span class="status-indicator active"></span><span class="text-sm font-medium">Camera Active</span>`;
                statusElement.className = 'flex items-center gap-2 px-3 py-2 bg-green-900/30 rounded-lg';
            } else {
                statusElement.innerHTML = `<span class="status-indicator inactive"></span><span class="text-sm font-medium">Camera Offline</span>`;
                statusElement.className = 'flex items-center gap-2 px-3 py-2 bg-dark-700 rounded-lg';
            }
        }
        
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
        if (error.name === 'NotAllowedError') return 'Camera access denied. Please allow camera permissions in your browser settings.';
        if (error.name === 'NotFoundError') return 'No camera found. Please connect a camera to your device.';
        if (error.name === 'NotReadableError') return 'Camera is in use by another application. Please close other apps using the camera.';
        if (error.name === 'OverconstrainedError') return 'Camera constraints could not be met. Try a different camera.';
        if (error.name === 'SecurityError') return 'Camera access blocked for security reasons. Use HTTPS or localhost.';
        return error.message || 'Unknown camera error. Please check console for details.';
    }
    
    dispatchEvent(eventName, detail = {}) {
        const event = new CustomEvent(`camera:${eventName}`, {
            detail: { manager: this, timestamp: Date.now(), ...detail }
        });
        document.dispatchEvent(event);
    }
    
    getResolution() {
        if (this.video && this.video.videoWidth > 0) {
            return { width: this.video.videoWidth, height: this.video.videoHeight };
        }
        return null;
    }
    
    getState() {
        return {
            isActive: this.isActive,
            facingMode: this.facingMode,
            resolution: this.getResolution(),
            hasVideo: !!this.video,
            hasStream: !!this.stream,
            rotation: this.rotation
        };
    }
}

// Global instance
let cameraManager = null;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('📱 DOM Content Loaded - Initializing CameraManager');
    cameraManager = new CameraManager();
    window.cameraManager = cameraManager;
    console.log('🎥 CameraManager created:', cameraManager);
    console.log('📹 Video element exists:', document.getElementById('video') !== null);
    setupGlobalCameraListeners();
    console.log('✅ Camera system ready');
});

function setupGlobalCameraListeners() {
    document.addEventListener('click', function(e) {
        const target = e.target.closest('[data-camera-action]');
        if (!target) return;
        const action = target.getAttribute('data-camera-action');
        if (!window.cameraManager) {
            console.error('Camera manager not initialized');
            return;
        }
        switch(action) {
            case 'start': window.cameraManager.startCamera(); break;
            case 'stop': window.cameraManager.stopCamera(); break;
            case 'toggle': window.cameraManager.toggleCamera(); break;
            case 'rotate': window.cameraManager.rotateView(90); break; // rotate view by 90°
            case 'capture':
                if (window.cameraManager.isActive) {
                    try {
                        const frame = window.cameraManager.captureFrame('dataurl');
                        console.log('📸 Frame captured:', frame.substring(0, 50) + '...');
                        document.dispatchEvent(new CustomEvent('camera:capture', { detail: { frame } }));
                    } catch (error) {
                        console.error('Capture failed:', error);
                    }
                }
                break;
        }
    });
    
    // Keyboard shortcuts (ignore if in input)
    document.addEventListener('keydown', function(e) {
        if (e.target.matches('input, textarea, select')) return;
        if (e.key === ' ' && window.cameraManager) {
            e.preventDefault();
            if (window.cameraManager.isActive) window.cameraManager.stopCamera();
            else window.cameraManager.startCamera();
        }
        if ((e.key === 'f' || e.key === 'F') && window.cameraManager?.isActive) {
            e.preventDefault();
            window.cameraManager.toggleCamera();
        }
        if ((e.key === 'r' || e.key === 'R') && window.cameraManager?.isActive) {
            e.preventDefault();
            window.cameraManager.rotateView(90);
        }
        if ((e.key === 'c' || e.key === 'C') && window.cameraManager?.isActive) {
            e.preventDefault();
            document.dispatchEvent(new CustomEvent('camera:capture'));
        }
    });
    
    window.addEventListener('beforeunload', function() {
        if (window.cameraManager) window.cameraManager.stopCamera();
    });
}

window.CameraManager = CameraManager;