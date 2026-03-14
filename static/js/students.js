// static/js/students.js - Student management functionality
document.addEventListener("DOMContentLoaded", () => {
    // Student modal functionality
    const studentModal = document.getElementById("studentModal");
    const studentModalTitle = document.getElementById("studentModalTitle");
    const studentModalBody = document.getElementById("studentModalBody");
    const studentModalClose = document.getElementById("studentModalClose");
    
    if (studentModalClose) {
        studentModalClose.addEventListener("click", () => {
            studentModal.classList.add("hidden");
            document.body.style.overflow = "";
        });
    }
    
    // Open student modal
    window.openStudentModal = function(name) {
        studentModalTitle.textContent = name;
        studentModalBody.innerHTML = '<div class="text-center py-8"><i class="fas fa-spinner fa-spin text-primary-400 text-2xl"></i><p class="text-gray-400 mt-2">Loading student details...</p></div>';
        studentModal.classList.remove("hidden");
        document.body.style.overflow = "hidden";
        
        // Fetch student attendance data
        fetchStudentAttendance(name);
    };
    
    async function fetchStudentAttendance(studentName) {
        try {
            const response = await fetch(`/api/student_attendance?name=${encodeURIComponent(studentName)}`);
            if (response.ok) {
                const data = await response.json();
                displayStudentAttendance(data);
            } else {
                throw new Error('Failed to fetch student data');
            }
        } catch (error) {
            console.error('Error fetching student attendance:', error);
            studentModalBody.innerHTML = `
                <div class="text-center py-8">
                    <i class="fas fa-exclamation-circle text-danger-400 text-2xl mb-3"></i>
                    <p class="text-gray-400">Failed to load student data</p>
                    <p class="text-sm text-gray-500 mt-1">${error.message}</p>
                </div>
            `;
        }
    }
    
    function displayStudentAttendance(data) {
        if (!data || data.length === 0) {
            studentModalBody.innerHTML = `
                <div class="text-center py-8">
                    <i class="fas fa-user-graduate text-gray-500 text-2xl mb-3"></i>
                    <p class="text-gray-400">No attendance records found</p>
                    <p class="text-sm text-gray-500 mt-1">This student hasn't attended any sessions yet</p>
                </div>
            `;
            return;
        }
        
        let html = `
            <div class="space-y-4">
                <div class="bg-gray-900/50 rounded-xl p-4">
                    <div class="grid grid-cols-2 gap-4 text-sm">
                        <div>
                            <div class="text-gray-400">Total Sessions</div>
                            <div class="text-white font-semibold">${data.total_sessions || 0}</div>
                        </div>
                        <div>
                            <div class="text-gray-400">Present Count</div>
                            <div class="text-success font-semibold">${data.present_count || 0}</div>
                        </div>
                        <div>
                            <div class="text-gray-400">Absent Count</div>
                            <div class="text-danger font-semibold">${data.absent_count || 0}</div>
                        </div>
                        <div>
                            <div class="text-gray-400">Attendance %</div>
                            <div class="text-primary font-semibold">${data.attendance_percent || 0}%</div>
                        </div>
                    </div>
                </div>
                
                <div>
                    <h4 class="font-medium text-white mb-3">Recent Attendance</h4>
                    <div class="space-y-2 max-h-64 overflow-y-auto pr-2">
        `;
        
        if (data.recent_attendance && data.recent_attendance.length > 0) {
            data.recent_attendance.forEach(record => {
                html += `
                    <div class="flex items-center justify-between p-3 bg-gray-900/30 rounded-lg hover:bg-gray-900 transition-colors">
                        <div>
                            <div class="font-medium text-white">${record.subject_name}</div>
                            <div class="text-xs text-gray-400">${record.date} • ${record.teacher_name}</div>
                        </div>
                        <span class="px-2 py-1 rounded text-xs font-medium ${
                            record.status === 'present' 
                            ? 'bg-success-900/30 text-success-300' 
                            : 'bg-danger-900/30 text-danger-300'
                        }">
                            ${record.status === 'present' ? 'Present' : 'Absent'}
                        </span>
                    </div>
                `;
            });
        } else {
            html += `
                <div class="text-center py-4 text-gray-500">
                    <i class="fas fa-calendar-times text-xl mb-2"></i>
                    <p>No recent attendance records</p>
                </div>
            `;
        }
        
        html += `
                    </div>
                </div>
            </div>
        `;
        
        studentModalBody.innerHTML = html;
    }
    
    // Student row click handler
    document.addEventListener("click", (ev) => {
        const row = ev.target.closest('.student-row');
        if (row) {
            const name = row.dataset.name || row.querySelector('.font-medium.text-white')?.textContent.trim();
            if (name) {
                openStudentModal(name);
            }
        }
    });
    
    // Delete confirmation
    document.querySelectorAll("form[action^='/students/delete']").forEach(form => {
        form.addEventListener('submit', (ev) => {
            if (!confirm('Delete student and all associated data (attendance records, face images)? This action cannot be undone.')) {
                ev.preventDefault();
            }
        });
    });
    
    // Image upload preview
    const imageUpload = document.getElementById('faceImages');
    const imagePreview = document.getElementById('imagePreviews');
    
    if (imageUpload && imagePreview) {
        imageUpload.addEventListener('change', function() {
            imagePreview.innerHTML = '';
            
            if (this.files.length > 0) {
                imagePreview.classList.remove('hidden');
                
                for (let i = 0; i < Math.min(this.files.length, 5); i++) {
                    const file = this.files[i];
                    const reader = new FileReader();
                    
                    reader.onload = function(e) {
                        const preview = document.createElement('div');
                        preview.className = 'relative group';
                        preview.innerHTML = `
                            <img src="${e.target.result}" class="w-full h-20 object-cover rounded-lg">
                            <button type="button" class="absolute top-1 right-1 p-1 bg-danger-600 hover:bg-danger-700 text-white rounded-full text-xs opacity-0 group-hover:opacity-100 transition-opacity"
                                    onclick="this.parentElement.remove(); updateFileInput()">
                                <i class="fas fa-times"></i>
                            </button>
                        `;
                        imagePreview.appendChild(preview);
                    };
                    
                    reader.readAsDataURL(file);
                }
                
                if (this.files.length > 5) {
                    toast('Only the first 5 images will be uploaded', 'warning');
                }
            } else {
                imagePreview.classList.add('hidden');
            }
        });
    }
    
    // Update file input after removing preview
    window.updateFileInput = function() {
        const previews = imagePreview.querySelectorAll('img');
        if (previews.length === 0) {
            imagePreview.classList.add('hidden');
        }
    };
    
    // Drag and drop for image upload
    const dropzone = document.querySelector('.upload-dropzone');
    if (dropzone) {
        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('drag-over');
        });
        
        dropzone.addEventListener('dragleave', () => {
            dropzone.classList.remove('drag-over');
        });
        
        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('drag-over');
            
            if (imageUpload) {
                imageUpload.files = e.dataTransfer.files;
                imageUpload.dispatchEvent(new Event('change'));
            }
        });
    }
    
    // Form validation
    const studentForm = document.querySelector('form[action="{{ url_for("students") }}"]');
    if (studentForm) {
        studentForm.addEventListener('submit', function(e) {
            const nameInput = this.querySelector('input[name="name"]');
            if (nameInput && !nameInput.value.trim()) {
                e.preventDefault();
                toast('Student name is required', 'error');
                nameInput.focus();
                return;
            }
            
            // Show loading state
            const submitBtn = this.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Saving...';
            }
        });
    }
    
    // Search functionality
    const searchInput = document.querySelector('input[name="search"]');
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                this.form.submit();
            }, 500);
        });
    }
});