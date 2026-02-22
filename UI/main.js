/**
 * Bright Study - UI Logic
 * Fully optimized for low-end devices and poor networks.
 * Size constrained under 10MB project goal.
 */

// Base URL of the FastAPI backend.
const API_BASE = (typeof window !== 'undefined' && (window.location.port === '5173' || window.location.protocol === 'file:'))
    ? 'http://localhost:8000'   // Dev-server or local file
    : '';                       // Same-origin (served by FastAPI)

const app = {
    mode: null,
    currentLesson: null,
    currentConceptIndex: 0,
    isOnline: navigator.onLine,
    networkQuality: 'UNKNOWN', // 'LOW', 'AVERAGE', 'HIGH'
    speedMBps: 0,
    suggestionShownThisLesson: false,
    debugMode: localStorage.getItem('brightstudy_debug') === 'true',

    lessons: [],
    downloadedVideos: [],

    /**
     * INITIALIZATION
     */
    init: function () {
        this.checkNetwork();
        this.loadLessons();
        this.wireUpdatesUI();
        this.checkBackendHealth();

        // Run an automatic speed test on load to help the user choose a mode
        this.runSpeedTest(true);

        // Dynamic Network detection
        window.addEventListener('online', () => this.checkNetwork());
        window.addEventListener('offline', () => this.checkNetwork());
    },

    fetchLessons: async function () {
        const res = await fetch(`${API_BASE}/api/lessons`);
        if (!res.ok) {
            throw new Error(await res.text());
        }
        return res.json();
    },

    /**
     * BACKEND HEALTH CHECK
     */
    checkBackendHealth: async function () {
        try {
            const res = await fetch(`${API_BASE}/health`);
            const dot = document.getElementById('health-dot');
            const label = document.getElementById('health-label');
            if (res.ok) {
                if (dot) { dot.style.background = '#4ade80'; }
                if (label) label.textContent = 'API online';
            } else {
                if (dot) dot.style.background = '#f87171';
                if (label) label.textContent = 'API error';
            }
        } catch {
            const dot = document.getElementById('health-dot');
            const label = document.getElementById('health-label');
            if (dot) dot.style.background = '#f59e0b';
            if (label) label.textContent = 'API unreachable';
        }
    },

    /**
     * PERSIST PROGRESS TO BACKEND
     */
    persistProgress: async function (payload) {
        // Immediate local hydration
        const uid = this.currentUser ? this.currentUser.id : 'local_user';
        const iid = payload.lesson_id || payload.concept_id;
        if (iid) {
            this.userProgress[iid] = payload.status || 'completed';
            this.renderDashboard();
        }

        try {
            await fetch(`${API_BASE}/api/progress`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ...payload, user_id: uid }),
            });
        } catch {
            // Offline — progress already tracked in memory local state
        }
    },

    /**
     * LOG ADAPTIVE EVENT
     */
    logEvent: async function (eventData) {
        console.log('🔍 [Adaptive] logEvent triggered:', eventData);
        if (this.mode !== 'online' || !this.currentUser) {
            console.warn('⚠️ [Adaptive] Event skipped: Not in Online mode or no User logged in.', {
                mode: this.mode,
                user: this.currentUser ? this.currentUser.name : 'null',
                online: navigator.onLine
            });
            return;
        }

        const payload = {
            user_id: this.currentUser.id,
            ...eventData
        };

        console.log('📡 [Adaptive] Sending to server:', payload);
        try {
            const res = await fetch(`${API_BASE}/api/log_event`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            const data = await res.json();
            console.log('📨 [Adaptive] Server response:', data);

            // Update local profile with new mastery if returned
            if (data.status === 'ok' && data.new_mastery !== undefined && payload.concept_id) {
                this.userProfile[payload.concept_id] = data.new_mastery;
                console.log(`📈 [Adaptive] Local mastery for ${payload.concept_id} updated to:`, data.new_mastery);

                // Proactive Check: If student is struggling
                if (payload.correct === false && data.new_mastery < 0.3) {
                    const isAlreadyBeginner = this.currentLesson.id.includes('_beginner');

                    if (isAlreadyBeginner) {
                        console.log("💡 [Adaptive] Struggling on Beginner lesson. Boosting hint.");
                        this.showStrongHint();
                    } else if (!this.suggestionShownThisLesson) {
                        console.log("💡 [Adaptive] Suggesting module generation (Once per lesson).");
                        this.suggestionShownThisLesson = true;
                        this.recommendNextStep(data.new_mastery, 'failure');
                    }
                }
                return data.new_mastery;
            }
        } catch (e) {
            console.error('❌ [Adaptive] Network error:', e);
        }
        return null;
    },

    loadLessons: async function () {
        const grid = document.getElementById('lesson-grid');
        try {
            const data = await this.fetchLessons();
            const videoData = await fetch(`${API_BASE}/api/videos`).then(r => r.ok ? r.json() : { videos: [] });
            this.downloadedVideos = videoData.videos || [];

            const lessons = (data && data.lessons) ? data.lessons : [];
            this.lessons = lessons.map((lesson) => ({
                id: lesson.lesson_id,
                title: lesson.title || lesson.lesson_id,
                description: lesson.intro || '',
                order_index: lesson.order_index || 0, // Store for sequencing
                completed: false,
                concepts: (lesson.concepts || []).map((c) => ({
                    id: c.id,
                    name: (c.name || c.title || c.id || 'Concept')
                        .replace(/_/g, ' ')
                        .replace(/\b\w/g, (m) => m.toUpperCase()),
                    explain: c.explain || '',
                    example: c.example || '',
                    videos: c.videos || null,
                    question: (c.check && c.check.question) ? c.check.question : '',
                    keywords: (c.check && c.check.keywords) ? c.check.keywords : [],
                    desired_answer: (c.check && c.check.desired_answer) ? c.check.desired_answer : ''
                }))
            }));
            this.renderDashboard();
        } catch (e) {
            if (grid) {
                grid.innerHTML = '<div style="color: var(--text-dim);">Unable to load dashboard content.</div>';
            }
        }
    },

    /**
     * NETWORK DETECTION
     */
    checkNetwork: function () {
        this.isOnline = navigator.onLine;
        const alert = document.getElementById('network-alert');

        if (this.mode === 'online' && !this.isOnline) {
            alert.style.display = 'block';
        } else {
            alert.style.display = 'none';
        }
    },

    /**
     * MODE MANAGEMENT
     */
    setMode: async function (mode) {
        if (mode === 'online') {
            // Check if already logged in
            const storedUser = localStorage.getItem('brightstudy_user');
            if (storedUser) {
                this.currentUser = JSON.parse(storedUser);
                this.updateAuthUI();
                await this.runSpeedTest(); // Get latest speed
                this.activateApp('online');
                return;
            }

            // If we are currently "Unknown", run a quick test
            if (this.networkQuality === 'UNKNOWN') {
                await this.runSpeedTest();
            }

            // Show Auth gateway instead of main app
            document.getElementById('gateway').style.display = 'none';
            document.getElementById('auth-gateway').style.display = 'flex';
            this.authMode = 'login';
            return;
        } else {
            this.networkQuality = 'OFFLINE';
            this.updateNetworkBadge();
            this.activateApp('offline');
        }
    },

    activateApp: function (mode) {
        this.mode = mode;
        document.getElementById('gateway').style.display = 'none';
        document.getElementById('auth-gateway').style.display = 'none';
        document.getElementById('app-shell').style.display = 'flex';

        const onlineNav = document.getElementById('online-nav');
        if (onlineNav) onlineNav.style.display = mode === 'online' ? 'block' : 'none';

        // Show/Hide Video Search based on network quality
        const videoNav = document.getElementById('video-nav');
        if (videoNav) {
            videoNav.style.display = (mode === 'online' && (this.networkQuality === 'HIGH' || this.networkQuality === 'AVERAGE')) ? 'block' : 'none';
        }

        this.checkNetwork();

        // Hydrate profile data (mastery + progress) when activating
        if (mode === 'online' && this.currentUser) {
            this.fetchUserProfile();
        }
    },

    authMode: 'login',

    toggleAuthMode: function () {
        this.authMode = this.authMode === 'login' ? 'signup' : 'login';
        document.getElementById('auth-title').textContent = this.authMode === 'login' ? 'Login' : 'Sign Up';
        document.getElementById('auth-submit-btn').textContent = this.authMode === 'login' ? 'Login' : 'Create Account';
        document.getElementById('auth-toggle-text').textContent = this.authMode === 'login' ? "Don't have an account? Sign Up" : "Already have an account? Login";
        document.getElementById('signup-fields').style.display = this.authMode === 'login' ? 'none' : 'block';
        document.getElementById('password-hint').style.display = this.authMode === 'login' ? 'none' : 'block';
        document.getElementById('auth-error').style.display = 'none';
    },

    cancelAuth: function () {
        document.getElementById('auth-gateway').style.display = 'none';
        document.getElementById('gateway').style.display = 'flex';
    },

    updateAuthUI: function () {
        // Find or create user badge in topbar
        let userBadge = document.getElementById('user-profile-badge');
        if (!userBadge && this.currentUser) {
            const topbar = document.querySelector('.topbar');
            if (topbar) {
                userBadge = document.createElement('div');
                userBadge.id = 'user-profile-badge';
                userBadge.style.display = 'flex';
                userBadge.style.alignItems = 'center';
                userBadge.style.gap = '1rem';

                const logoutBtn = document.createElement('button');
                logoutBtn.className = 'ghost-btn';
                logoutBtn.textContent = 'Logout';
                logoutBtn.style.padding = '0.4rem 0.8rem';
                logoutBtn.style.fontSize = '0.75rem';
                logoutBtn.onclick = () => this.logout();

                const nameText = document.createElement('span');
                nameText.id = 'user-profile-name';
                nameText.style.fontWeight = '600';
                nameText.style.color = 'var(--text-main)';

                userBadge.appendChild(nameText);
                userBadge.appendChild(logoutBtn);
                topbar.appendChild(userBadge);
            }
        }

        if (userBadge && this.currentUser) {
            document.getElementById('user-profile-name').textContent = `Hi, ${this.currentUser.name}`;
            userBadge.style.display = 'flex';
        } else if (userBadge) {
            userBadge.style.display = 'none';
        }
    },

    logout: function () {
        localStorage.removeItem('brightstudy_user');
        this.currentUser = null;
        this.updateAuthUI();
        this.resetMode();
    },

    handleAuthSubmit: async function (e) {
        e.preventDefault();
        const errorDiv = document.getElementById('auth-error');
        errorDiv.style.display = 'none';

        const email = document.getElementById('auth-email').value.trim();
        const password = document.getElementById('auth-password').value;

        // Strict Validations
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email)) {
            errorDiv.textContent = 'Invalid email format.';
            errorDiv.style.display = 'block';
            return;
        }

        if (password.length < 8 || !/[A-Z]/.test(password) || !/[a-z]/.test(password) || !/[0-9]/.test(password) || !/[^A-Za-z0-9]/.test(password)) {
            errorDiv.textContent = 'Password must be at least 8 chars, 1 uppercase, 1 lowercase, 1 number, and 1 special character.';
            errorDiv.style.display = 'block';
            return;
        }

        let payload = { email, password };
        let endpoint = '/api/login';

        if (this.authMode === 'signup') {
            const name = document.getElementById('auth-name').value.trim();
            const age = parseInt(document.getElementById('auth-age').value);
            const phone = document.getElementById('auth-phone').value.trim();

            if (!name || /[^a-zA-Z\s]/.test(name)) {
                errorDiv.textContent = 'Name must contain only letters and spaces.';
                errorDiv.style.display = 'block';
                return;
            }
            if (isNaN(age) || age < 5 || age > 100) {
                errorDiv.textContent = 'Age must be between 5 and 100.';
                errorDiv.style.display = 'block';
                return;
            }
            if (!/^\d{10}$/.test(phone)) {
                errorDiv.textContent = 'Phone number must be exactly 10 digits.';
                errorDiv.style.display = 'block';
                return;
            }

            payload = { name, age, phone, email, password };
            endpoint = '/api/signup';
        }

        try {
            const res = await fetch(`${API_BASE}${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            let data = {};
            try {
                data = await res.json();
            } catch (jsonErr) { }

            if (!res.ok) {
                throw new Error(data.error || 'Authentication failed');
            }

            // Save session
            if (endpoint === '/api/login') {
                this.currentUser = { id: data.user_id, name: data.name };
                localStorage.setItem('brightstudy_user', JSON.stringify(this.currentUser));
                this.updateAuthUI();
            } else if (endpoint === '/api/signup') {
                alert("Account created successfully! Please login.");
                this.toggleAuthMode();
                return;
            }

            // Success! Activate Online Mode
            this.activateApp('online');

        } catch (err) {
            errorDiv.textContent = err.message;
            errorDiv.style.display = 'block';
        }
    },

    /**
     * SPEED TEST LOGIC
         * @param {boolean} isInitial - Whether this is being called from the gateway
         */
    runSpeedTest: async function (isInitial = false) {
        const overlay = document.getElementById('speed-test-overlay');
        const gatewayMsg = document.getElementById('gateway-speed-msg');
        const gatewaySpinner = document.getElementById('gateway-spinner');
        const retestBtn = document.getElementById('retest-btn');
        const onlineBtn = document.getElementById('online-btn');

        if (!isInitial) {
            overlay.style.display = 'flex';
        } else {
            if (gatewaySpinner) gatewaySpinner.style.display = 'block';
            if (gatewayMsg) gatewayMsg.textContent = 'Measuring real internet speed...';
            if (retestBtn) retestBtn.style.display = 'none';
        }

        try {
            if (!navigator.onLine) {
                throw new Error("Offline");
            }

            // Test parameters: 3 samples for averaging
            const SAMPLES = 3;
            const TEST_URL = 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js'; // ~600KB
            let totalSpeed = 0;
            let successCount = 0;

            console.log(`[SpeedTest] Starting ${SAMPLES}-sample test...`);

            for (let i = 0; i < SAMPLES; i++) {
                if (isInitial && gatewayMsg) {
                    gatewayMsg.textContent = `Analyzing stability (${Math.round(((i) / SAMPLES) * 100)}%)...`;
                }

                try {
                    const sampleStartTime = performance.now();
                    const response = await fetch(`${TEST_URL}?cb=${Date.now()}_${i}`);
                    if (!response.ok) continue;

                    const blob = await response.blob();
                    const sampleEndTime = performance.now();

                    const durationInSeconds = (sampleEndTime - sampleStartTime) / 1000;
                    const sizeInMB = blob.size / (1024 * 1024);
                    const sampleSpeed = sizeInMB / (durationInSeconds || 0.001);

                    console.log(`[SpeedTest] Sample ${i + 1}: ${sampleSpeed.toFixed(2)} MB/s`);
                    totalSpeed += sampleSpeed;
                    successCount++;

                    // Small breather to avoid saturating buffer
                    await new Promise(r => setTimeout(r, 100));
                } catch (err) {
                    console.warn(`[SpeedTest] Sample ${i + 1} failed:`, err);
                }
            }

            if (successCount === 0) throw new Error("Connection unstable (0/3 samples)");

            this.speedMBps = totalSpeed / successCount;
            const speedMbps = (this.speedMBps * 8).toFixed(1);

            console.log(`[SpeedTest] Final Average: ${speedMbps} Mbps (${this.speedMBps.toFixed(2)} MB/s)`);

            // Revised Thresholds (MBps)
            // LOW: < 0.4 (~3 Mbps)
            // AVERAGE: 0.4 - 1.2 (~3 - 10 Mbps)
            // HIGH: > 1.2 (~10+ Mbps)
            if (this.speedMBps < 0.4) {
                this.networkQuality = 'LOW';
            } else if (this.speedMBps < 1.2) {
                this.networkQuality = 'AVERAGE';
            } else {
                this.networkQuality = 'HIGH';
            }

            if (isInitial && gatewayMsg) {
                gatewayMsg.innerHTML = `${speedMbps} Mbps &bull; <strong>${this.networkQuality}</strong>`;
                if (this.networkQuality !== 'LOW') {
                    onlineBtn.classList.add('recommended');
                    gatewayMsg.style.color = 'var(--accent)';
                } else {
                    gatewayMsg.style.color = 'var(--accent-2)';
                }
            }

        } catch (e) {
            console.error("[SpeedTest] Failed:", e);
            this.networkQuality = 'LOW';
            if (isInitial && gatewayMsg) {
                gatewayMsg.textContent = 'Connection Unstable';
                gatewayMsg.style.color = 'var(--danger)';
            }
        } finally {
            if (!isInitial) {
                overlay.style.display = 'none';
            } else {
                if (gatewaySpinner) gatewaySpinner.style.display = 'none';
                if (retestBtn) retestBtn.style.display = 'block';
            }
            this.updateNetworkBadge();
        }
    },

    updateNetworkBadge: function () {
        const badge = document.getElementById('network-status');
        const text = document.querySelector('.status-text');

        if (!badge) return;

        badge.style.display = 'inline-block';
        badge.className = 'status-badge ' + this.networkQuality.toLowerCase();
        badge.textContent = this.networkQuality;
        text.textContent = this.isOnline ? 'Session Ready' : 'Offline Mode';
    },

    resetProgress: async function () {
        if (!this.currentUser) return;
        if (!confirm("Are you sure you want to reset ALL your learning progress? This cannot be undone.")) return;

        try {
            const res = await fetch(`${API_BASE}/api/reset_progress`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: this.currentUser.id }),
            });

            if (!res.ok) {
                const errText = await res.text();
                throw new Error(errText || `Server returned ${res.status}`);
            }

            const data = await res.json();
            if (data.status === 'ok') {
                this.userProfile = {};
                alert("Progress reset successfully! You can now start fresh.");
                this.renderDashboard();
            } else {
                alert("Failed to reset progress: " + data.error);
            }
        } catch (e) {
            console.error('❌ [Adaptive] Reset failed:', e);
            alert("Connection error while resetting progress.");
        }
    },

    resetMode: function () {
        document.getElementById('app-shell').style.display = 'none';
        document.getElementById('gateway').style.display = 'flex';
        this.runSpeedTest(true);
    },

    /**
     * NAVIGATION
     */
    showSection: function (id) {
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

        document.getElementById(id).classList.add('active');
        const nav = document.querySelector(`.nav-item[data-target="${id}"]`);
        if (nav) nav.classList.add('active');

        // Close sidebar on mobile after clicking
        const sidebar = document.querySelector('.sidebar');
        if (sidebar && sidebar.classList.contains('active')) {
            sidebar.classList.remove('active');
        }

        // Navigation
        if (id === 'dashboard') {
            this.renderDashboard();
        } else if (id === 'courses') {
            this.renderCourses(); // Trigger the fetch when nav is clicked
        } else if (id === 'aitutor') {
            this.initAITutor();
        } else if (id === 'scheduler') {
            this.loadSavedSchedule();
        } else if (id === 'search-videos') {
            // No init needed
        } else if (id === 'updates') {
            this.wireUpdatesUI();
        }
    },

    /**
     * DASHBOARD
     */
    renderDashboard: function () {
        const grid = document.getElementById('lesson-grid');
        grid.innerHTML = '';
        if (!this.lessons || this.lessons.length === 0) {
            grid.innerHTML = '<div style="color: var(--text-dim);">No lessons available yet.</div>';
            return;
        }
        this.lessons.forEach(lesson => {
            const card = document.createElement('div');
            card.className = 'card';
            card.onclick = () => this.startLesson(lesson.id);

            // Local Progress Check
            const isCompleted = this.userProgress[lesson.id] === 'completed' || lesson.completed;
            const progress = isCompleted ? 100 : 0;
            const statusIcon = isCompleted ? ' ✅' : '';

            card.innerHTML = `
                <h3>${lesson.title}${statusIcon}</h3>
                <p style="font-size:0.8rem; color:var(--text-dim); margin-top:0.5rem;">${lesson.description}</p>
                <div class="progress-bar"><div class="progress-fill" style="width:${progress}%"></div></div>
            `;
            grid.appendChild(card);
        });
    },

    playVideo: function (titleText, url) {
        this.showSection('lesson-player');
        const videoContainer = document.getElementById('video-container');
        const videoElement = document.getElementById('lesson-video');

        // Hide unnecessary lesson elements
        document.getElementById('concept-step').style.display = 'none';
        document.querySelector('.example-box').style.display = 'none';
        document.querySelector('.question-block').style.display = 'none';

        // Dynamic title and cinematic sizing
        const title = document.getElementById('concept-title');
        title.textContent = titleText;
        title.classList.add('centered-title');
        document.getElementById('concept-ui').classList.add('wide-panel');
        videoContainer.classList.add('wide-player');

        document.getElementById('explanation').textContent = "";
        document.getElementById('example-text').textContent = "";
        document.getElementById('question').textContent = "";

        videoElement.src = url;
        videoContainer.style.display = 'block';
    },

    /**
     * ADAPTIVE DECISION ENGINE & PROGRESS
     */
    userProfile: {},
    userProgress: {},

    fetchUserProfile: async function () {
        if (!this.currentUser) return;
        try {
            console.log('📡 [Adaptive] Fetching profile for:', this.currentUser.id);
            const res = await fetch(`${API_BASE}/api/user_profile/${this.currentUser.id}`);
            const data = await res.json();

            if (data.profile_data) {
                this.userProfile = data.profile_data.mastery || {};
                this.userProgress = data.profile_data.progress || {};
                console.log('🧠 [Adaptive] Full Profile Loaded:', {
                    masteryCount: Object.keys(this.userProfile).length,
                    progressCount: Object.keys(this.userProgress).length
                });
                this.renderDashboard(); // Refresh UI with progress
            }
        } catch (e) {
            console.error('[Adaptive] Failed to fetch profile:', e);
        }
    },

    showHint: function () {
        const concept = this.currentLesson.concepts[this.currentConceptIndex];
        const hintArea = document.getElementById('hint-area');
        const hintText = document.getElementById('hint-text');

        // Simple hint: share one keyword or the first 5 words of explanation
        const hint = concept.keywords && concept.keywords.length > 0
            ? `Look for the keyword: "${concept.keywords[0]}"`
            : concept.explain.split(' ').slice(0, 5).join(' ') + '...';

        hintText.textContent = hint;
        hintArea.style.display = 'block';
        document.getElementById('hint-btn').style.display = 'none';

        this.logEvent({
            event_type: 'hint_used',
            lesson_id: this.currentLesson.id,
            concept_id: concept.id || concept.name
        });
    },

    showStrongHint: function () {
        const concept = this.currentLesson.concepts[this.currentConceptIndex];
        const hintArea = document.getElementById('hint-area');
        const hintText = document.getElementById('hint-text');

        if (concept && concept.keywords && concept.keywords.length > 0) {
            hintArea.style.display = 'block';
            hintText.innerHTML = `<span style="color: var(--text-main); font-weight: bold;">Quick Help:</span> The answer includes keywords like "<strong>${concept.keywords[0]}</strong>".`;
        }
    },

    showDebugAnswer: function () {
        const concept = this.currentLesson.concepts[this.currentConceptIndex];
        const feedback = document.getElementById('feedback');
        if (concept) {
            const ans = concept.desired_answer || concept.keywords.join(', ');
            feedback.innerHTML = `<div style="padding: 0.8rem; background: rgba(var(--accent-rgb), 0.1); border: 1px dashed var(--accent); border-radius: 8px; margin-top: 1rem; color: var(--text);">
                <span style="color: var(--accent); font-weight: bold;">[DEBUG] Copy this:</span><br/>
                <code id="debug-copy-text" style="display: block; margin-top: 0.5rem; background: rgba(0,0,0,0.2); padding: 0.5rem; border-radius: 4px;">${ans}</code>
            </div>`;
        }
    },

    downloadVideo: function (video) {
        if (!this.downloadedVideos.find(v => v.title === video.title)) {
            this.downloadedVideos.push(video);
            alert(`Video "${video.title}" downloaded successfully!`);
            this.renderDashboard();
        } else {
            alert(`Video "${video.title}" is already downloaded.`);
        }
    },

    startLesson: function (id) {
        this.currentLesson = this.lessons.find(l => l.id === id);
        this.currentConceptIndex = 0;
        this.suggestionShownThisLesson = false;
        this.showSection('lesson-player');
        this.loadConcept();
    },

    toggleDebugMode: function () {
        this.debugMode = !this.debugMode;
        localStorage.setItem('brightstudy_debug', this.debugMode);
        alert(`Debug Mode: ${this.debugMode ? 'ON' : 'OFF'}`);
        this.loadConcept(); // Refresh UI to show/hide debug buttons
    },

    loadConcept: function () {
        const concept = this.currentLesson.concepts[this.currentConceptIndex];
        if (!concept) {
            console.error('❌ [Classroom] Concept not found at index:', this.currentConceptIndex);
            this.showSection('dashboard');
            return;
        }
        const total = this.currentLesson.concepts.length;

        // Ensure lesson elements are visible
        document.getElementById('concept-step').style.display = 'inline-flex';
        document.querySelector('.example-box').style.display = 'block';
        document.querySelector('.question-block').style.display = 'block';
        document.getElementById('concept-title').classList.remove('centered-title');
        document.getElementById('concept-ui').classList.remove('wide-panel');
        document.getElementById('video-container').classList.remove('wide-player');

        document.getElementById('concept-step').textContent = `STEP ${this.currentConceptIndex + 1} OF ${total}`;
        document.getElementById('concept-title').textContent = concept.name;
        document.getElementById('explanation').textContent = concept.explain;

        const videoContainer = document.getElementById('video-container');
        const videoElement = document.getElementById('lesson-video');

        if (this.mode === 'online' && concept.videos && this.networkQuality !== 'LOW') {
            const videoUrl = this.networkQuality === 'HIGH' ? concept.videos.high : concept.videos.low;
            if (videoUrl) {
                videoElement.src = videoUrl;
                videoContainer.style.display = 'block';
            } else {
                videoContainer.style.display = 'none';
            }
        } else {
            videoContainer.style.display = 'none';
            videoElement.src = '';
        }

        document.getElementById('example-text').textContent = concept.example;
        document.getElementById('question').textContent = concept.question;
        document.getElementById('user-answer').value = '';
        document.getElementById('feedback').textContent = '';

        // DEBUG UI: Hide/Show debug answer button
        const debugBtn = document.querySelector('button[onclick="app.showDebugAnswer()"]');
        if (debugBtn) {
            debugBtn.style.display = this.debugMode ? 'inline-block' : 'none';
        }

        if (this.debugMode && concept.keywords) {
            console.log(`[DEBUG] Keywords for "${concept.name}":`, concept.keywords);
        }

        // [DEBUG] Log answer details to console
        if (concept.keywords && concept.keywords.length > 0) {
            console.log(`📝 [Debug] Expected keywords for "${concept.name}":`, concept.keywords.join(', '));
            if (concept.desired_answer) {
                console.log(`💡 [Debug] Example answer:`, concept.desired_answer);
            }
        }

        // ADAPTIVE LOGIC: Automatically show hint if mastery is low
        const cid = concept.id || concept.name;
        // Default to 1.0 (Hidden) so hints only appear after a recorded failure
        const mastery = this.userProfile[cid] !== undefined ? this.userProfile[cid] : 1.0;

        const hintArea = document.getElementById('hint-area');
        const hintText = document.getElementById('hint-text');

        if (mastery < 0.5) {
            console.log(`🧠 [Adaptive] Low mastery (${mastery}) detected for ${cid}. Showing automatic hint.`);

            // Generate hint
            const hint = concept.keywords && concept.keywords.length > 0
                ? `Look for the keyword: "${concept.keywords[0]}"`
                : concept.explain.split(' ').slice(0, 5).join(' ') + '...';

            hintText.textContent = hint;
            if (hintArea) hintArea.style.display = 'block';

            this.logEvent({
                event_type: 'hint_auto_display',
                lesson_id: this.currentLesson.id,
                concept_id: cid
            });
        } else {
            if (hintArea) hintArea.style.display = 'none';
        }
    },

    checkAnswer: async function () {
        const input = document.getElementById('user-answer').value.toLowerCase();
        const concept = this.currentLesson.concepts[this.currentConceptIndex];
        const keywords = concept.keywords;
        const feedback = document.getElementById('feedback');

        // Case-insensitive matching: lowercase both for comparison
        const missing = keywords.filter(k => !input.includes(k.toLowerCase().trim()));
        const correct = missing.length === 0;

        if (!correct) {
            console.log(`❌ [Debug] Answer mismatch. Missing keywords:`, missing);
            console.log(`📥 [Debug] User input was: "${input}"`);
        }

        if (correct) {
            feedback.textContent = "Correct!";
            feedback.style.color = "var(--accent)";

            // Log interaction for adaptive learning
            await this.logEvent({
                event_type: 'answer',
                lesson_id: this.currentLesson.id,
                concept_id: concept.id || concept.name,
                correct: true,
                attempt: 1
            });

            if (concept.id) {
                this.persistProgress({ concept_id: concept.id, status: 'completed' });
            }

            setTimeout(() => {
                if (this.currentConceptIndex < this.currentLesson.concepts.length - 1) {
                    this.currentConceptIndex++;
                    this.loadConcept();
                } else {
                    this.completeLesson();
                }
            }, 800);
        } else {
            feedback.textContent = "Almost! Try again.";
            feedback.style.color = "var(--text-dim)";

            await this.logEvent({
                event_type: 'answer',
                lesson_id: this.currentLesson.id,
                concept_id: concept.id || concept.name,
                correct: false,
                attempt: 1
            });
        }
    },

    completeLesson: function () {
        console.log(`🏁 [Classroom] Lesson ${this.currentLesson.id} completed!`);
        this.currentLesson.completed = true;
        this.persistProgress({ lesson_id: this.currentLesson.id, status: 'completed' });

        // Show celebration or return to dashboard
        const feedback = document.getElementById('feedback');
        feedback.innerHTML = `<div style="text-align:center; padding: 2rem;">
            <h2 style="color: var(--accent);">Lesson Complete! 🏆</h2>
            <p>You've mastered all concepts in this module.</p>
            <button class="btn-primary" style="margin-top:1rem;" onclick="app.showSection('dashboard')">Back to Dashboard</button>
        </div>`;

        // Recalculate average mastery accurately from current userProfile state
        let totalMastery = 0;
        this.currentLesson.concepts.forEach(c => {
            const cid = c.id || c.name;
            totalMastery += this.userProfile[cid] || 0.1;
        });
        const avgMastery = totalMastery / this.currentLesson.concepts.length;

        console.log(`🎓 [Choice Engine] Final Lesson Mastery: ${avgMastery.toFixed(2)}`);

        this.showSection('dashboard');
        this.recommendNextStep(avgMastery, 'success');
    },

    recommendNextStep: function (avgMastery, triggerType) {
        let recommendation = null;

        if (triggerType === 'success' && avgMastery > 0.7) {
            // Suggest "Advance" AI Generation ONLY on finish/success
            recommendation = {
                type: 'advance',
                title: 'Unstoppable! 🚀',
                text: "You've mastered these basics. Want me to generate an **Advanced Module** for you right now?",
                mode: 'Advance',
                icon: '🔥'
            };
        } else if (triggerType === 'failure' && avgMastery < 0.4) {
            // Suggest "Beginner" AI Generation ONLY on struggle/failure
            recommendation = {
                type: 'beginner',
                title: 'Let\'s Break It Down 🧱',
                text: "That was tough! Want me to generate a **Simplified Beginner version** to help strengthen your foundation?",
                mode: 'Beginner',
                icon: '💡'
            };
        }

        if (recommendation) {
            this.showSuggestionModal(recommendation);
        }
    },

    showSuggestionModal: function (rec) {
        const modal = document.getElementById('suggestion-modal');
        const title = document.getElementById('suggestion-title');
        const text = document.getElementById('suggestion-text');
        const icon = document.getElementById('suggestion-icon');
        const btn = document.getElementById('suggestion-btn');

        title.textContent = rec.title;
        text.innerHTML = rec.text; // Support markdown-like bold
        icon.textContent = rec.icon;

        btn.textContent = `Generate ${rec.mode} Module`;
        btn.onclick = () => this.generateAdaptiveModule(rec.mode);

        modal.style.display = 'flex';
    },

    generateAdaptiveModule: async function (mode) {
        const downloading = document.getElementById('suggestion-downloading');
        const btn = document.getElementById('suggestion-btn');

        btn.disabled = true;
        btn.textContent = "AI Thinking...";
        const loadingText = downloading.querySelector('span:last-child');
        if (loadingText) loadingText.textContent = "Generating custom content...";
        downloading.style.display = 'block';

        try {
            const res = await fetch(`${API_BASE}/api/generate_adaptive_lesson`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    lesson_id: this.currentLesson.id,
                    mode: mode
                })
            });

            const data = await res.json();
            if (data.status === 'ok') {
                console.log(`✨ [AI] Content Ready: ${data.lesson_id}`);
                // Hot refresh lessons and start
                await this.loadLessons();
                this.closeSuggestion();
                this.startLesson(data.lesson_id);
            } else {
                throw new Error(data.error || 'AI generation failed');
            }
        } catch (e) {
            alert("AI Generation failed: " + e.message);
            console.error(e);
            this.closeSuggestion();
        } finally {
            btn.disabled = false;
        }
    },

    closeSuggestion: function () {
        document.getElementById('suggestion-modal').style.display = 'none';
        document.getElementById('suggestion-downloading').style.display = 'none';
        const btn = document.getElementById('suggestion-btn');
        if (btn) {
            btn.disabled = false;
            btn.textContent = "Let's Go"; // Default reset
        }
    },

    /**
     * COURSE BUILDER
     */
    _cbSubjectCount: 0,

    openCourseBuilder: function () {
        // Reset form
        document.getElementById('cb-title').value = '';
        document.getElementById('cb-description').value = '';
        document.getElementById('cb-thumbnail').value = '';
        document.getElementById('cb-subjects-container').innerHTML = '';
        document.getElementById('cb-error').style.display = 'none';
        this._cbSubjectCount = 0;
        document.getElementById('course-builder-modal').style.display = 'block';
        document.body.style.overflow = 'hidden';
    },

    closeCourseBuilder: function () {
        document.getElementById('course-builder-modal').style.display = 'none';
        document.body.style.overflow = '';
    },

    cb_addSubject: function () {
        const si = this._cbSubjectCount++;
        const container = document.getElementById('cb-subjects-container');
        const div = document.createElement('div');
        div.id = `cb-subj-${si}`;
        div.style.border = '1px solid var(--border)';
        div.style.borderRadius = '8px';
        div.style.padding = '1rem';
        div.style.background = 'var(--surface)';
        div.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                <strong style="font-size: 0.9rem; color: var(--accent);">Subject ${si + 1}</strong>
                <button class="ghost-btn" onclick="this.closest('#cb-subj-${si}').remove()" style="font-size: 0.8rem; padding: 0.2rem 0.5rem;">Remove</button>
            </div>
            <input type="text" id="cb-subj-title-${si}" placeholder="Subject Title *"
                style="width: 100%; padding: 0.5rem; margin-bottom: 0.5rem; background: var(--card); border: 1px solid var(--border); border-radius: var(--radius); color: var(--text-main); box-sizing: border-box;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <span style="font-size: 0.85rem; font-weight: 600;">Lessons</span>
                <button class="btn-primary" onclick="app.cb_addLesson(${si})" style="padding: 0.25rem 0.6rem; font-size: 0.8rem;">+ Lesson</button>
            </div>
            <div id="cb-lessons-${si}" style="display: flex; flex-direction: column; gap: 0.5rem;"></div>
        `;
        container.appendChild(div);
        // Auto-add first lesson
        this.cb_addLesson(si);
    },

    _cbLessonCount: {},

    cb_addLesson: function (si) {
        if (this._cbLessonCount[si] === undefined) this._cbLessonCount[si] = 0;
        const li = this._cbLessonCount[si]++;
        const container = document.getElementById(`cb-lessons-${si}`);
        if (!container) return;
        const div = document.createElement('div');
        div.id = `cb-lesson-${si}-${li}`;
        div.style.border = '1px solid var(--border)';
        div.style.borderRadius = '6px';
        div.style.padding = '0.75rem';
        div.style.background = 'var(--card)';
        div.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <small style="color: var(--text-muted);">Lesson ${li + 1}</small>
                <button class="ghost-btn" onclick="this.closest('#cb-lesson-${si}-${li}').remove()" style="font-size: 0.75rem; padding: 0.15rem 0.4rem;">✕</button>
            </div>
            <input type="text" id="cb-lesson-title-${si}-${li}" placeholder="Lesson Title *"
                style="width: 100%; padding: 0.4rem; margin-bottom: 0.5rem; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); color: var(--text-main); box-sizing: border-box;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
                <small style="font-weight: 600; color: var(--text-muted);">Concepts</small>
                <button class="btn-primary" onclick="app.cb_addConcept(${si}, ${li})" style="padding: 0.15rem 0.5rem; font-size: 0.75rem;">+ Concept</button>
            </div>
            <div id="cb-concepts-${si}-${li}" style="display: flex; flex-direction: column; gap: 0.4rem;"></div>
        `;
        container.appendChild(div);
        // Auto-add first concept
        this.cb_addConcept(si, li);
    },

    _cbConceptCount: {},

    cb_addConcept: function (si, li) {
        const key = `${si}-${li}`;
        if (this._cbConceptCount[key] === undefined) this._cbConceptCount[key] = 0;
        const ci = this._cbConceptCount[key]++;
        const container = document.getElementById(`cb-concepts-${si}-${li}`);
        if (!container) return;
        const div = document.createElement('div');
        div.id = `cb-concept-${si}-${li}-${ci}`;
        div.style.padding = '0.5rem';
        div.style.background = 'var(--surface)';
        div.style.borderRadius = '4px';
        div.style.border = '1px solid var(--border)';
        const fieldStyle = 'width: 100%; padding: 0.35rem; margin-bottom: 0.3rem; background: var(--card); border: 1px solid var(--border); border-radius: 4px; color: var(--text-main); box-sizing: border-box; font-size: 0.85rem;';
        div.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
                <small style="color: var(--text-muted); font-size: 0.75rem;">Concept ${ci + 1}</small>
                <button class="ghost-btn" onclick="this.closest('#cb-concept-${si}-${li}-${ci}').remove()" style="font-size: 0.7rem; padding: 0.1rem 0.3rem;">✕</button>
            </div>
            <input type="text" id="cb-concept-name-${si}-${li}-${ci}" placeholder="Concept Name *" style="${fieldStyle}">
            <textarea id="cb-concept-explain-${si}-${li}-${ci}" placeholder="Explanation" rows="2" style="${fieldStyle} resize: vertical;"></textarea>
            <textarea id="cb-concept-example-${si}-${li}-${ci}" placeholder="Example (optional)" rows="1" style="${fieldStyle} resize: vertical;"></textarea>
            <input type="text" id="cb-concept-q-${si}-${li}-${ci}" placeholder="Check Question (optional)" style="${fieldStyle}">
            <input type="text" id="cb-concept-kw-${si}-${li}-${ci}" placeholder="Keywords (comma separated)" style="${fieldStyle} margin-bottom: 0;">
        `;
        container.appendChild(div);
    },

    saveCourse: async function () {
        const errDiv = document.getElementById('cb-error');
        errDiv.style.display = 'none';

        const title = document.getElementById('cb-title').value.trim();
        if (!title) {
            errDiv.textContent = 'Course title is required.';
            errDiv.style.display = 'block';
            return;
        }

        const description = document.getElementById('cb-description').value.trim();
        const thumbnail_url = document.getElementById('cb-thumbnail').value.trim() || null;

        // Collect subjects
        const subjects = [];
        const subjDivs = document.querySelectorAll('[id^="cb-subj-"]');
        for (const subjDiv of subjDivs) {
            const si = subjDiv.id.replace('cb-subj-', '');
            const subjTitle = document.getElementById(`cb-subj-title-${si}`)?.value.trim();
            if (!subjTitle) continue;

            const lessons = [];
            const lessonDivs = document.querySelectorAll(`[id^="cb-lesson-${si}-"]`);
            let lessonOrder = 1;
            for (const lessonDiv of lessonDivs) {
                const parts = lessonDiv.id.split('-');
                const li = parts[parts.length - 1];
                const lessonTitle = document.getElementById(`cb-lesson-title-${si}-${li}`)?.value.trim();
                if (!lessonTitle) continue;

                const concepts = [];
                const conceptDivs = document.querySelectorAll(`[id^="cb-concept-${si}-${li}-"]`);
                for (const conceptDiv of conceptDivs) {
                    const cparts = conceptDiv.id.split('-');
                    const ci = cparts[cparts.length - 1];
                    const cname = document.getElementById(`cb-concept-name-${si}-${li}-${ci}`)?.value.trim();
                    if (!cname) continue;
                    const explain = document.getElementById(`cb-concept-explain-${si}-${li}-${ci}`)?.value.trim() || '';
                    const example = document.getElementById(`cb-concept-example-${si}-${li}-${ci}`)?.value.trim() || '';
                    const question = document.getElementById(`cb-concept-q-${si}-${li}-${ci}`)?.value.trim() || '';
                    const keywords = (document.getElementById(`cb-concept-kw-${si}-${li}-${ci}`)?.value.trim() || '')
                        .split(',').map(k => k.trim()).filter(k => k);
                    concepts.push({
                        name: cname,
                        explain,
                        example,
                        check: { question, keywords }
                    });
                }

                lessons.push({
                    id: crypto.randomUUID ? crypto.randomUUID() : `lesson-${Date.now()}-${lessonOrder}`,
                    title: lessonTitle,
                    order: lessonOrder++,
                    concepts
                });
            }

            subjects.push({
                id: crypto.randomUUID ? crypto.randomUUID() : `subj-${Date.now()}-${si}`,
                title: subjTitle,
                order: subjects.length + 1,
                lessons
            });
        }

        const payload = {
            title,
            description,
            thumbnail_url,
            subjects,
            created_by: this.currentUser?.id || null
        };

        try {
            const res = await fetch(`${API_BASE}/api/add_course`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Failed to save course');
            alert(`✅ Course "${title}" saved successfully! ID: ${data.course_id}`);
            this.closeCourseBuilder();
        } catch (err) {
            errDiv.textContent = err.message;
            errDiv.style.display = 'block';
        }
    },

    /**
     * COURSES AND CURRICULUM
     */
    renderCourses: function () {
        const grid = document.getElementById('courses-grid');
        const savedGrid = document.getElementById('saved-courses-grid');
        const detailView = document.getElementById('course-detail-view');
        if (grid) grid.style.display = 'grid';
        if (detailView) detailView.style.display = 'none';

        // Load saved courses from added_courses
        this.loadSavedCourses();

        if (!grid) return;
        grid.innerHTML = '<div style="color: var(--text-dim); padding: 2rem 0;">Type a course name to search the database.</div>';

        const searchInput = document.getElementById('course-search-input');
        const searchBtn = document.getElementById('course-search-btn');

        const doSearch = async () => {
            if (!searchInput) return;
            const query = searchInput.value.trim();
            if (!query) {
                grid.innerHTML = '<div style="color: var(--text-dim); padding: 2rem 0;">Type a course name to search the database.</div>';
                return;
            }

            grid.innerHTML = '<div style="color: var(--text-dim);">Searching database...</div>';

            try {
                const res = await fetch(`${API_BASE}/api/courses?q=${encodeURIComponent(query)}`);
                const data = await res.json();
                if (!res.ok) throw new Error(data.error || 'Failed to fetch courses');

                grid.innerHTML = '';
                const foundCourses = data.courses || [];

                if (foundCourses.length === 0) {
                    grid.innerHTML = '<div style="color: var(--text-dim);">No matching courses found.</div>';
                    return;
                }

                foundCourses.forEach(course => {
                    const card = document.createElement('div');
                    card.className = 'lesson-card';
                    const thumb = course.thumbnail_url || null;

                    card.innerHTML = `
                        ${thumb ? `<div class="thumb-container"><img src="${thumb}" alt="${course.title}"></div>` : ''}
                        <div class="lesson-info">
                            <h4>${course.title}</h4>
                            <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.25rem; line-height: 1.4;">
                                ${course.description ? course.description.substring(0, 80) + '...' : 'No description provided.'}
                            </p>
                            <div style="display: flex; gap: 0.5rem; margin-top: 0.75rem;">
                                <button class="btn-primary" style="font-size: 0.8rem; padding: 0.35rem 0.75rem;" 
                                    onclick="app.saveSearchedCourse(${JSON.stringify(course).replace(/"/g, '&quot;')})">
                                    + Save to My Courses
                                </button>
                                <button class="ghost-btn" style="font-size: 0.8rem; padding: 0.35rem 0.75rem;"
                                    onclick="app.loadCourseCurriculum(${JSON.stringify(course).replace(/"/g, '&quot;')})">
                                    View Curriculum
                                </button>
                            </div>
                        </div>
                    `;
                    grid.appendChild(card);
                });

            } catch (err) {
                grid.innerHTML = `<div style="color: var(--danger);">${err.message}</div>`;
            }
        };

        // Attach events only once
        if (searchInput && !searchInput.dataset.hasListener) {
            searchInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') doSearch();
            });
            searchInput.dataset.hasListener = "true";
        }
        if (searchBtn && !searchBtn.dataset.hasListener) {
            searchBtn.addEventListener('click', doSearch);
            searchBtn.dataset.hasListener = "true";
        }
    },

    loadSavedCourses: async function () {
        const savedGrid = document.getElementById('saved-courses-grid');
        if (!savedGrid) return;
        savedGrid.innerHTML = '<div style="color: var(--text-dim);">Loading saved courses...</div>';

        try {
            const res = await fetch(`${API_BASE}/api/saved_courses`);
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Failed to load');
            savedGrid.innerHTML = '';
            const saved = data.courses || [];
            if (saved.length === 0) {
                savedGrid.innerHTML = '<div style="color: var(--text-dim);">No saved courses yet. Use the search below to find and save courses.</div>';
                return;
            }
            saved.forEach(course => {
                const card = document.createElement('div');
                card.className = 'lesson-card';
                card.onclick = () => this.loadCourseCurriculum(course, true);
                const thumb = course.thumbnail_url || null;
                card.innerHTML = `
                    ${thumb ? `<div class="thumb-container"><img src="${thumb}" alt="${course.title}"></div>` : ''}
                    <div class="lesson-info">
                        <h4>${course.title}</h4>
                        <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.25rem;">${course.description || ''}</p>
                    </div>
                `;
                savedGrid.appendChild(card);
            });
        } catch (err) {
            savedGrid.innerHTML = `<div style="color: var(--danger);">${err.message}</div>`;
        }
    },

    saveSearchedCourse: async function (course) {
        try {
            const payload = {
                title: course.title,
                description: course.description || '',
                thumbnail_url: course.thumbnail_url || null,
                subjects: course.subjects || [],
                source_id: course.id,
                created_by: this.currentUser?.id || null
            };
            const res = await fetch(`${API_BASE}/api/add_course`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Failed to save');
            alert(`✅ "${course.title}" saved to My Courses!`);
            this.loadSavedCourses();
        } catch (err) {
            alert(`Error: ${err.message}`);
        }
    },

    loadCourseCurriculum: async function (course) {
        document.getElementById('courses-grid').style.display = 'none';
        const detailView = document.getElementById('course-detail-view');
        detailView.style.display = 'block';

        document.getElementById('detail-course-title').textContent = course.title;
        document.getElementById('detail-course-desc').textContent = course.description || '';

        const container = document.getElementById('course-curriculum-container');
        container.innerHTML = '<div style="color: var(--text-dim);">Loading curriculum...</div>';

        document.getElementById('back-to-courses-btn').onclick = () => {
            detailView.style.display = 'none';
            document.getElementById('courses-grid').style.display = 'grid';
            document.getElementById('course-search-input').value = '';
            // Reset search visibility
            const cards = document.getElementById('courses-grid').querySelectorAll('.lesson-card');
            cards.forEach(card => card.style.display = 'block');
        };

        try {
            const res = await fetch(`${API_BASE}/api/courses/${course.id}/curriculum`);
            const data = await res.json();

            if (!res.ok) throw new Error(data.error || 'Failed to fetch curriculum');

            container.innerHTML = '';
            const subjects = data.curriculum || [];

            if (subjects.length === 0) {
                container.innerHTML = '<div style="color: var(--text-dim);">No subjects have been added to this course yet.</div>';
                return;
            }

            subjects.forEach((subject, idx) => {
                const subjDiv = document.createElement('div');
                subjDiv.style.border = '1px solid var(--border)';
                subjDiv.style.borderRadius = '8px';
                subjDiv.style.overflow = 'hidden';

                // Accordion Header
                const header = document.createElement('div');
                header.style.padding = '1rem';
                header.style.background = 'var(--surface)';
                header.style.cursor = 'pointer';
                header.style.display = 'flex';
                header.style.justifyContent = 'space-between';
                header.style.alignItems = 'center';
                header.style.fontWeight = '600';
                header.innerHTML = `
                    <span>Part ${idx + 1}: ${subject.title}</span>
                    <i class="fa fa-chevron-down toggle-icon" style="transition: transform 0.2s;"></i>
                `;

                // Accordion Body (Lessons List)
                const body = document.createElement('div');
                body.style.display = 'none'; // Hidden by default
                body.style.padding = '0';
                body.style.borderTop = '1px solid var(--border)';
                body.style.background = '#1a1a1a'; // slightly darker

                if (subject.lessons && subject.lessons.length > 0) {
                    const list = document.createElement('ul');
                    list.style.listStyle = 'none';
                    list.style.margin = '0';
                    list.style.padding = '0';

                    subject.lessons.forEach((lesson, lIdx) => {
                        const li = document.createElement('li');
                        li.style.borderBottom = '1px solid var(--border)';

                        // Lesson header row
                        const lessonHeader = document.createElement('div');
                        lessonHeader.style.padding = '0.75rem 1rem';
                        lessonHeader.style.cursor = 'pointer';
                        lessonHeader.style.display = 'flex';
                        lessonHeader.style.alignItems = 'center';
                        lessonHeader.style.gap = '0.75rem';
                        lessonHeader.onmouseover = () => lessonHeader.style.background = 'var(--surface)';
                        lessonHeader.onmouseout = () => lessonHeader.style.background = 'transparent';
                        lessonHeader.innerHTML = `
                            <span style="color: var(--text-muted); font-size: 0.85rem;">${lIdx + 1}.</span>
                            <i class="fa fa-play-circle" style="color: var(--accent); font-size: 1.1rem;"></i>
                            <span style="font-size: 0.95rem; flex: 1;">${lesson.title || 'Untitled Lesson'}</span>
                            ${lesson.concepts && lesson.concepts.length > 0
                                ? `<small style="color: var(--text-muted);">${lesson.concepts.length} concept${lesson.concepts.length > 1 ? 's' : ''} ▾</small>`
                                : ''}
                        `;

                        // Concepts panel (hidden by default)
                        const conceptsPanel = document.createElement('div');
                        conceptsPanel.style.display = 'none';
                        conceptsPanel.style.padding = '0 1rem 0.75rem 2.5rem';
                        conceptsPanel.style.borderTop = '1px solid var(--border)';

                        if (lesson.concepts && lesson.concepts.length > 0) {
                            lesson.concepts.forEach((c, ci) => {
                                const conceptDiv = document.createElement('div');
                                conceptDiv.style.marginTop = '0.6rem';
                                conceptDiv.style.padding = '0.6rem 0.75rem';
                                conceptDiv.style.background = 'var(--card)';
                                conceptDiv.style.borderRadius = '6px';
                                conceptDiv.style.fontSize = '0.85rem';
                                conceptDiv.innerHTML = `
                                    <div style="font-weight: 600; color: var(--accent); margin-bottom: 0.25rem;">Concept ${ci + 1}</div>
                                    ${c.explain ? `<p style="margin: 0 0 0.25rem; color: var(--text-main);">${c.explain}</p>` : ''}
                                    ${c.example ? `<p style="margin: 0 0 0.25rem; color: var(--text-muted); font-style: italic;">Example: ${c.example}</p>` : ''}
                                    ${c.check && c.check.question ? `<p style="margin: 0; color: var(--text-dim); font-size: 0.8rem;">❓ ${c.check.question}</p>` : ''}
                                `;
                                conceptsPanel.appendChild(conceptDiv);
                            });

                            // Toggle concepts on lesson click
                            lessonHeader.onclick = () => {
                                const isOpen = conceptsPanel.style.display !== 'none';
                                conceptsPanel.style.display = isOpen ? 'none' : 'block';
                            };
                        } else {
                            lessonHeader.onclick = () => {
                                if (lesson.lesson_id) {
                                    app.startLesson(lesson.lesson_id);
                                } else {
                                    alert("Lesson ID missing.");
                                }
                            };
                        }

                        li.appendChild(lessonHeader);
                        li.appendChild(conceptsPanel);
                        list.appendChild(li);
                    });
                    // remove last border
                    if (list.lastChild) list.lastChild.style.borderBottom = 'none';
                    body.appendChild(list);
                } else {
                    body.innerHTML = '<div style="padding: 1rem; color: var(--text-muted); font-size: 0.9rem;">No lessons attached to this subject yet.</div>';
                }

                header.onclick = () => {
                    const isHidden = body.style.display === 'none';
                    body.style.display = isHidden ? 'block' : 'none';
                    const icon = header.querySelector('.toggle-icon');
                    icon.style.transform = isHidden ? 'rotate(180deg)' : 'rotate(0deg)';
                };

                subjDiv.appendChild(header);
                subjDiv.appendChild(body);
                container.appendChild(subjDiv);
            });

        } catch (err) {
            container.innerHTML = `<div style="color: var(--danger);">${err.message}</div>`;
        }
    },

    /**
     * ADD MORE LESSONS (Online - Wired to Backend)
     */
    searchLessons: async function () {
        const input = document.getElementById('search-input');
        const query = input.value.toLowerCase().trim();
        const results = document.getElementById('search-results');

        if (!query) return;

        results.innerHTML = '<p style="color:var(--text-dim);">Searching cloud...</p>';

        try {
            const res = await fetch(`${API_BASE}/api/search_cloud?q=${encodeURIComponent(query)}`);
            if (!res.ok) throw new Error(await res.text());

            const data = await res.json();
            const matches = data.results || [];

            if (matches.length > 0) {
                results.innerHTML = matches.map(m => `
                    <div class="result-item">
                        <div>
                            <strong>${m.title}</strong>
                            <div style="font-size: 0.7rem; color: var(--accent);">${m.type} ${m.version ? `(v${m.version})` : ''}</div>
                        </div>
                        <button class="add-btn" onclick="app.downloadCloudItem('${m.id}', '${m.type}', '${m.title}')">ADD +</button>
                    </div>
                `).join('');
            } else {
                results.innerHTML = '<p style="color:var(--text-dim);">No matching content found in cloud.</p>';
            }
        } catch (err) {
            results.innerHTML = `<p style="color:var(--danger);">Error searching: ${err.message}</p>`;
        }
    },

    /**
     * SEARCH VIDEOS
     */
    searchVideos: async function () {
        const input = document.getElementById('video-search-input');
        const query = input.value.toLowerCase().trim();
        const results = document.getElementById('video-search-results');

        if (!query) return;

        results.innerHTML = '<p style="color:var(--text-dim);">Searching videos in cloud...</p>';

        try {
            const res = await fetch(`${API_BASE}/api/search_videos?q=${encodeURIComponent(query)}`);
            if (!res.ok) throw new Error(await res.text());

            const data = await res.json();
            const cloudVideos = data.results || [];

            if (cloudVideos.length > 0) {
                results.innerHTML = cloudVideos.map(v => `
                    <div class="search-video-card" style="display: flex; gap: 1rem; margin-bottom: 1rem; background: var(--card); padding: 1rem; border-radius: 12px; border: 1px solid var(--border);">
                        <div class="thumb-container" style="width: 120px; aspect-ratio: 16/9; flex-shrink: 0; background: #000; border-radius: 8px; overflow: hidden;">
                            ${v.thumb ? `<img src="${v.thumb}" alt="${v.title}" style="width: 100%; height: 100%; object-fit: cover;">` : ''}
                        </div>
                        <div class="video-info" style="display: flex; flex-direction: column; justify-content: center;">
                            <h4 style="margin-bottom: 0.5rem; font-size: 1rem; font-weight: 600; color: var(--text-main);">${v.title}</h4>
                            <div class="meta-badges" style="margin-bottom: 0.5rem;">
                                <span class="badge accent">${v.length}</span>
                                <span class="badge">${v.resolution}</span>
                                <span class="badge">${v.size}</span>
                            </div>
                            <div class="video-actions">
                                <button class="add-btn" onclick="app.downloadCloudItem('${v.id}', 'video', '${v.title.replace(/'/g, "\\'")}')">DOWNLOAD</button>
                            </div>
                        </div>
                    </div>
                `).join('');
            } else {
                results.innerHTML = '<p style="color:var(--text-dim);">No matching videos found in cloud.</p>';
            }
        } catch (err) {
            results.innerHTML = `<p style="color:var(--danger);">Error searching videos: ${err.message}</p>`;
        }
    },

    /**
     * UPDATES (Online)
     */
    wireUpdatesUI: function () {
        const applyBtn = document.getElementById('applyBtn');
        const installedBtn = document.getElementById('installedBtn');
        const applyArea = document.getElementById('applyArea');
        const installedList = document.getElementById('installedList');
        const status = document.getElementById('updateStatus');

        if (!applyBtn || !installedBtn) return;

        const fetchJSON = async (path, opts) => {
            const res = await fetch(path, opts);
            if (!res.ok) throw new Error(await res.text());
            return res.json();
        };

        applyBtn.onclick = async () => {
            status.textContent = 'Status: applying updates...';
            applyArea.textContent = '(running)';
            try {
                const data = await fetchJSON('/api/apply', { method: 'POST' });
                applyArea.textContent = data.output || '(no output)';
                status.textContent = 'Status: apply finished';
            } catch (e) {
                applyArea.textContent = 'Error: ' + e.message;
                status.textContent = 'Status: error';
            }
        };

        installedBtn.onclick = async () => {
            status.textContent = 'Status: loading installed content...';
            try {
                const data = await fetchJSON('/api/installed');
                installedList.innerHTML = '';
                if (!data || !data.length) {
                    installedList.innerHTML = '<li>(none)</li>';
                } else {
                    data.forEach(it => {
                        const li = document.createElement('li');
                        li.textContent = `${it.type} ${it.content_id} v${it.version}`;
                        installedList.appendChild(li);
                    });
                }
                status.textContent = 'Status: installed loaded';
            } catch (e) {
                installedList.innerHTML = '<li>Error: ' + e.message + '</li>';
                status.textContent = 'Status: error';
            }
        };
    },

    downloadCloudItem: async function (id, type, title) {
        alert(`Download request queued for "${title}". Check the Updates tab or refresh soon.`);
        try {
            await fetch(`${API_BASE}/api/download`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id, type })
            });
            this.loadLessons();
            this.showSection('dashboard');
        } catch (err) {
            alert("Failed to queue download.");
        }
    },

    /**
     * AI TUTOR LOGIC
     */
    tutorHistory: [],
    tutorFileContent: null,
    tutorSelectedLessonContext: null,

    initAITutor: async function () {
        if (!this.currentUser) {
            document.getElementById('chat-history').innerHTML = '<div style="text-align:center; padding: 2rem; color: var(--text-dim);">Please log in to use the AI Tutor.</div>';
            return;
        }

        // Populate Lesson Dropdown
        const select = document.getElementById('tutor-lesson-select');
        select.innerHTML = '<option value="">-- None --</option>';
        if (this.lessons) {
            this.lessons.forEach(l => {
                const opt = document.createElement('option');
                opt.value = l.id;
                opt.textContent = l.title;
                select.appendChild(opt);
            });
        }

        // Fetch History
        try {
            const res = await fetch(`${API_BASE}/api/ai_tutor/history/${this.currentUser.id}`);
            if (res.ok) {
                const data = await res.json();
                this.tutorHistory = data.history || [];
                this.renderChatHistory();
            }
        } catch (e) {
            console.error("Failed to load tutor history", e);
        }
    },

    tutorLessonChanged: function () {
        const select = document.getElementById('tutor-lesson-select');
        const lessonId = select.value;
        if (!lessonId) {
            this.tutorSelectedLessonContext = null;
            return;
        }
        const lesson = this.lessons.find(l => l.id === lessonId);
        if (lesson) {
            // Build a text context from concepts
            let context = `Lesson Title: ${lesson.title}\nDescription: ${lesson.description}\n\n`;
            if (lesson.concepts) {
                lesson.concepts.forEach((c, idx) => {
                    context += `Concept ${idx + 1}: ${c.name}\nExplanation: ${c.explain}\nQuestion: ${c.question}\n\n`;
                });
            }
            this.tutorSelectedLessonContext = context.substring(0, 3000); // limit size
        }
    },

    handleTutorFileUpload: function (event) {
        const file = event.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (e) => {
            this.tutorFileContent = e.target.result.substring(0, 5000); // Limit size
            const preview = document.getElementById('file-preview-area');
            const previewText = preview.querySelector('.preview-text');
            preview.style.display = 'flex';
            if (previewText) previewText.textContent = `Attached: ${file.name} (${Math.round(file.size / 1024)}KB)`;
        };
        reader.readAsText(file);
    },

    removeTutorFile: function () {
        this.tutorFileContent = null;
        document.getElementById('file-preview-area').style.display = 'none';
        document.getElementById('tutor-file-upload').value = '';
    },

    renderChatHistory: function () {
        const container = document.getElementById('chat-history');
        if (!container) return;

        // Save welcome message if we haven't already
        if (!this.tutorWelcomeMsg) {
            this.tutorWelcomeMsg = container.querySelector('.chat-welcome');
        }

        container.innerHTML = '';

        if (this.tutorHistory.length === 0) {
            if (this.tutorWelcomeMsg) {
                container.appendChild(this.tutorWelcomeMsg.cloneNode(true));
            } else {
                container.innerHTML = '<div class="chat-welcome"><div class="welcome-icon">👋</div><h4>Hello! I\'m your AI Tutor.</h4><p>Ask me anything!</p></div>';
            }
            return;
        }

        this.tutorHistory.forEach(msg => {
            if (msg.role === 'system') return; // Hide system messages

            const bubble = document.createElement('div');
            bubble.className = `chat-bubble ${msg.role === 'user' ? 'user' : 'assistant'}`;

            const meta = document.createElement('div');
            meta.className = 'chat-bubble-meta';
            meta.textContent = msg.role === 'user' ? 'You' : 'AI Tutor';

            const content = document.createElement('div');
            // convert newlines to br 
            content.innerHTML = msg.content.replace(/\\n/g, '<br>').replace(/\n/g, '<br>');

            bubble.appendChild(meta);
            bubble.appendChild(content);
            container.appendChild(bubble);
        });

        // Scroll to bottom
        container.scrollTop = container.scrollHeight;
    },

    handleChatKeyPress: function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            this.sendChatMessage();
        }
    },

    sendChatMessage: async function () {
        if (!this.currentUser) {
            alert("Please log in to use the AI Tutor.");
            return;
        }

        const input = document.getElementById('chat-textarea');
        const text = input.value.trim();

        if (!text) return;

        // Render optimistic user message
        this.tutorHistory.push({ role: 'user', content: text });
        this.renderChatHistory();

        input.value = '';
        input.disabled = true;
        document.getElementById('chat-send-btn').disabled = true;

        // Show loading indicator
        const container = document.getElementById('chat-history');
        const loading = document.createElement('div');
        loading.className = 'chat-bubble assistant';
        loading.id = 'chat-loading';
        loading.innerHTML = '<div class="typing-indicator"><span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span></div>';
        container.appendChild(loading);
        container.scrollTop = container.scrollHeight;

        try {
            const payload = {
                user_id: this.currentUser.id,
                prompt: text,
                lesson_context: this.tutorSelectedLessonContext,
                file_text: this.tutorFileContent
            };

            const res = await fetch(`${API_BASE}/api/ai_tutor/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!res.ok) throw new Error(await res.text());

            const data = await res.json();

            // Remove loading
            document.getElementById('chat-loading').remove();

            // Render AI reply
            this.tutorHistory.push({ role: 'assistant', content: data.reply });
            this.renderChatHistory();

            // Clear file attach after sending
            this.tutorFileContent = null;
            document.getElementById('file-preview-area').style.display = 'none';
            document.getElementById('tutor-file-upload').value = '';

        } catch (e) {
            document.getElementById('chat-loading').remove();
            this.tutorHistory.push({ role: 'assistant', content: `Error: ${e.message}` });
            this.renderChatHistory();
        } finally {
            input.disabled = false;
            document.getElementById('chat-send-btn').disabled = false;
            input.focus();
        }
    },

    /**
     * EXAM STUDY SCHEDULER WIZARD
     */
    schedulerData: {
        subjects: [],
        dates: {},
        hours: 0,
        priorities: {},
        breaks: 15
    },
    schedulerCurrentStep: 0,
    schedulerSteps: [
        { id: 'subjects', q: "What subjects are you studying for? (Enter them separated by commas)", placeholder: "e.g. Mathematics, Physics, Chemistry" },
        { id: 'dates', q: "Enter the exam date for each subject (Format: Subject-Date)", placeholder: "e.g. Mathematics-2024-05-20" },
        { id: 'hours', q: "How many hours can you study per day?", placeholder: "e.g. 6", type: 'number' },
        { id: 'priorities', q: "Set priority for each subject (Subject-High/Med/Low)", placeholder: "e.g. Mathematics-High" },
        { id: 'breaks', q: "How many minutes of break do you want every hour?", placeholder: "e.g. 15", type: 'number' }
    ],

    startSchedulerWizard: function () {
        this.schedulerCurrentStep = 0;
        this.schedulerData = { subjects: [], dates: {}, hours: 0, priorities: {}, breaks: 15 };
        const container = document.getElementById('scheduler-wizard-container');
        if (!container) return;
        container.innerHTML = '';
        document.getElementById('scheduler-input-area').style.display = 'block';
        document.getElementById('generated-timetable-area').style.display = 'none';
        this.renderSchedulerQuestion();
    },

    renderSchedulerQuestion: function () {
        const step = this.schedulerSteps[this.schedulerCurrentStep];
        const container = document.getElementById('scheduler-wizard-container');
        if (!container) return;

        const bubble = document.createElement('div');
        bubble.className = 'chat-bubble assistant';
        bubble.innerHTML = `<div class="chat-bubble-meta">Planner</div><div>${step.q}</div>`;
        container.appendChild(bubble);
        container.scrollTop = container.scrollHeight;

        const input = document.getElementById('scheduler-generic-input');
        input.placeholder = step.placeholder;
        input.type = step.type || 'text';
        input.value = '';
        input.focus();

        document.getElementById('scheduler-prompt-label').textContent = `Question ${this.schedulerCurrentStep + 1} of 5`;
    },

    submitSchedulerStep: function () {
        const input = document.getElementById('scheduler-generic-input');
        const val = input.value.trim();
        if (!val) return;

        const step = this.schedulerSteps[this.schedulerCurrentStep];

        // Save data based on step
        if (step.id === 'subjects') {
            this.schedulerData.subjects = val.split(',').map(s => s.trim());
        } else if (step.id === 'dates') {
            const pairs = val.split(',');
            pairs.forEach(p => {
                const parts = p.split('-');
                if (parts.length >= 2) {
                    const sub = parts[0].trim();
                    const date = parts.slice(1).join('-').trim();
                    if (sub && date) this.schedulerData.dates[sub] = date;
                }
            });
        } else if (step.id === 'hours') {
            this.schedulerData.hours = parseInt(val) || 4;
        } else if (step.id === 'priorities') {
            const pairs = val.split(',');
            pairs.forEach(p => {
                const parts = p.split('-');
                if (parts.length >= 2) {
                    const sub = parts[0].trim();
                    const prio = parts[1].trim();
                    if (sub && prio) this.schedulerData.priorities[sub] = prio;
                }
            });
        } else if (step.id === 'breaks') {
            this.schedulerData.breaks = parseInt(val) || 15;
        }

        // Render User answer
        const container = document.getElementById('scheduler-wizard-container');
        const bubble = document.createElement('div');
        bubble.className = 'chat-bubble user';
        bubble.innerHTML = `<div class="chat-bubble-meta">You</div><div>${val}</div>`;
        container.appendChild(bubble);

        this.schedulerCurrentStep++;
        if (this.schedulerCurrentStep < this.schedulerSteps.length) {
            this.renderSchedulerQuestion();
        } else {
            this.generateStudyPlan();
        }
    },

    generateStudyPlan: function () {
        document.getElementById('scheduler-input-area').style.display = 'none';
        const area = document.getElementById('generated-timetable-area');
        area.style.display = 'block';

        const grid = document.getElementById('timetable-grid');
        grid.innerHTML = '<div style="padding: 2rem; text-align: center; color: var(--text-dim);">⚙️ Generating your optimal plan...</div>';

        // Priority weights: High = 3, Med = 2, Low = 1
        const prioWeight = { high: 3, med: 2, low: 1 };

        const sorted = this.schedulerData.subjects.map(s => {
            const rawPrio = (this.schedulerData.priorities[s] || 'Med').trim().toLowerCase();
            return {
                name: s,
                date: new Date(this.schedulerData.dates[s] || '2099-01-01'),
                prio: rawPrio  // BUG FIX: read stored priority per-subject (not defaulting all)
            };
        }).sort((a, b) => {
            // Sort by date first, then priority weight descending
            const dateDiff = a.date - b.date;
            if (dateDiff !== 0) return dateDiff;
            return prioWeight[b.prio] - prioWeight[a.prio];
        });

        // BUG FIX: Weighted hour allocation based on priority
        const totalWeight = sorted.reduce((sum, item) => sum + (prioWeight[item.prio] || 1), 0);
        const totalHours = this.schedulerData.hours || 4;
        const breakHours = (this.schedulerData.breaks / 60); // break time per hour in hours

        setTimeout(() => {
            grid.innerHTML = '';
            const today = new Date();

            // ---- Priority color & label helpers ----
            const prioColor = (p) => {
                if (p === 'high') return '#ff6b6b';
                if (p === 'med') return '#f8c95d';
                return '#94a3b8'; // low
            };
            const prioLabel = (p) => {
                if (p === 'high') return 'HIGH PRIORITY';
                if (p === 'med') return 'MED PRIORITY';
                return 'LOW PRIORITY';
            };

            // ---- Build structured EXCEL-LIKE TABLE ----
            const table = document.createElement('div');
            table.style.borderRadius = '12px';
            table.style.border = '1px solid var(--border)';
            table.style.width = '100%';

            const t = document.createElement('table');
            t.style.width = '100%';
            t.style.borderCollapse = 'collapse';
            t.style.fontSize = '0.82rem';

            // Header row
            const thStyle = 'padding:0.65rem 0.9rem; text-align:left; color:var(--text-dim); font-weight:600; border-bottom:1px solid var(--border); white-space:nowrap;';
            const thead = document.createElement('thead');
            thead.innerHTML = `
                <tr style="background: var(--bg-soft);">
                    <th style="${thStyle}">#</th>
                    <th style="${thStyle}">Subject</th>
                    <th style="${thStyle}">Priority</th>
                    <th style="${thStyle}">Exam Date</th>
                    <th style="${thStyle}">Days Left</th>
                    <th style="${thStyle}">Study hrs/day</th>
                    <th style="${thStyle}">Break / hr</th>
                    <th style="${thStyle} width:35%">Recommendation</th>
                </tr>
            `;
            t.appendChild(thead);

            const tbody = document.createElement('tbody');

            sorted.forEach((item, idx) => {
                const daysLeft = Math.ceil((item.date - today) / (1000 * 60 * 60 * 24));
                const weight = prioWeight[item.prio] || 1;

                // BUG FIX: per-subject weighted hours
                const rawHrs = (weight / totalWeight) * totalHours;
                const studyHrs = Math.round(rawHrs * 10) / 10;

                // Dynamic recommendation per subject
                let rec = '';
                if (item.prio === 'high' && daysLeft <= 7) {
                    rec = '🔴 Urgent! Study every day without gaps.';
                } else if (item.prio === 'high') {
                    rec = '📚 High focus. Use active recall & practice tests.';
                } else if (item.prio === 'med' && daysLeft <= 14) {
                    rec = '⚠️ Medium urgency. Increase to daily sessions.';
                } else if (item.prio === 'med') {
                    rec = '📝 Consistent sessions 3–4 days / week.';
                } else if (daysLeft > 60) {
                    rec = '🟢 Low urgency. Light revision once a week.';
                } else {
                    rec = '📖 Low priority. Quick review before exam.';
                }

                const row = document.createElement('tr');
                row.style.borderBottom = '1px solid var(--border)';
                row.style.background = idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)';
                row.onmouseover = () => row.style.background = 'rgba(29, 211, 176, 0.05)';
                row.onmouseout = () => row.style.background = idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)';

                row.innerHTML = `
                    <td style="padding:0.65rem 0.9rem; color:var(--text-dim); white-space:nowrap;">${idx + 1}</td>
                    <td style="padding:0.65rem 0.9rem; font-weight:600; color:var(--accent); white-space:nowrap;">${item.name}</td>
                    <td style="padding:0.65rem 0.9rem; white-space:nowrap;">
                        <span style="background:${prioColor(item.prio)}22; color:${prioColor(item.prio)}; border:1px solid ${prioColor(item.prio)}44; padding:0.15rem 0.45rem; border-radius:5px; font-size:0.72rem; font-weight:700; white-space:nowrap;">
                            ${prioLabel(item.prio)}
                        </span>
                    </td>
                    <td style="padding:0.65rem 0.9rem; font-family:monospace; font-size:0.8rem; white-space:nowrap;">${item.date.toLocaleDateString()}</td>
                    <td style="padding:0.65rem 0.9rem; font-weight:600; white-space:nowrap; color:${daysLeft <= 7 ? 'var(--danger)' : daysLeft <= 30 ? 'var(--accent-2)' : 'var(--accent)'}">
                        ${daysLeft > 0 ? daysLeft + ' days' : '⏰ Passed'}
                    </td>
                    <td style="padding:0.65rem 0.9rem; font-weight:700; color:var(--text-main); white-space:nowrap;">${studyHrs} hrs</td>
                    <td style="padding:0.65rem 0.9rem; color:var(--text-dim); white-space:nowrap;">${this.schedulerData.breaks} min</td>
                    <td style="padding:0.65rem 0.9rem; color:var(--text-main);">${rec}</td>
                `;
                tbody.appendChild(row);
            });

            t.appendChild(tbody);
            table.appendChild(t);
            grid.appendChild(table);

        }, 600);
    },

    saveScheduleToSupabase: async function () {
        if (!this.currentUser) {
            alert("Please log in to save your schedule.");
            return;
        }

        const btn = document.querySelector('[onclick="app.saveScheduleToSupabase()"]');
        const originalText = btn.textContent;
        btn.textContent = "Saving to Cloud...";
        btn.disabled = true;

        try {
            const payload = {
                user_id: this.currentUser.id,
                subjects: this.schedulerData.subjects,
                exam_dates: this.schedulerData.dates,
                daily_hours: this.schedulerData.hours,
                priority_levels: this.schedulerData.priorities,
                break_time: this.schedulerData.breaks,
                generated_timetable: this.schedulerData
            };

            const res = await fetch(`${API_BASE}/api/scheduler/save`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                // Persist to localStorage so it survives page refresh
                localStorage.setItem('brightstudy_schedule', JSON.stringify({
                    savedAt: new Date().toISOString(),
                    user_id: this.currentUser.id,
                    data: this.schedulerData
                }));
                // Update the save button to show Delete instead
                btn.textContent = '✅ Saved!';
                setTimeout(() => {
                    btn.disabled = false;
                    this._renderSavedScheduleActions();
                }, 1200);
            } else {
                throw new Error(await res.text());
            }
        } catch (e) {
            alert("Failed to save schedule: " + e.message);
            btn.textContent = originalText;
            btn.disabled = false;
        }
    },

    _renderSavedScheduleActions: function () {
        // Replace the save button area with Saved + Delete buttons
        const area = document.getElementById('generated-timetable-area');
        let btnContainer = area.querySelector('#schedule-action-btns');
        if (!btnContainer) {
            btnContainer = document.createElement('div');
            btnContainer.id = 'schedule-action-btns';
            btnContainer.style.display = 'flex';
            btnContainer.style.gap = '1rem';
            btnContainer.style.marginTop = '1rem';
            area.appendChild(btnContainer);
        }
        btnContainer.innerHTML = `
            <div style="flex:1; padding:0.8rem 1.2rem; background:rgba(29,211,176,0.12); border:1px solid var(--accent); border-radius:10px; color:var(--accent); font-weight:600; text-align:center; font-size:0.9rem;">
                ✅ Schedule saved to cloud
            </div>
            <button onclick="app.deleteSchedule()" style="padding:0.8rem 1.5rem; background:rgba(255,107,107,0.12); border:1px solid var(--danger); border-radius:10px; color:var(--danger); font-weight:600; cursor:pointer; font-size:0.9rem;">
                🗑️ Delete Schedule
            </button>
        `;
        // Hide the original save button if still present
        const saveBtn = area.querySelector('[onclick="app.saveScheduleToSupabase()"]');
        if (saveBtn) saveBtn.style.display = 'none';
    },

    loadSavedSchedule: function () {
        const saved = localStorage.getItem('brightstudy_schedule');
        if (!saved) {
            // No saved schedule — show the welcome wizard
            const container = document.getElementById('scheduler-wizard-container');
            const area = document.getElementById('generated-timetable-area');
            const inputArea = document.getElementById('scheduler-input-area');
            if (area) area.style.display = 'none';
            if (inputArea) inputArea.style.display = 'none';
            if (container) container.innerHTML = `
                <div class="chat-welcome">
                    <div class="welcome-icon">📅</div>
                    <h4>Exam Season? Let's Plan!</h4>
                    <p>I'll help you generate a perfect study schedule in 5 minutes. Ready to start?</p>
                    <button class="btn-primary" onclick="app.startSchedulerWizard()" style="margin-top: 1rem;">Start Setup Wizard</button>
                </div>
            `;
            return;
        }

        try {
            const parsed = JSON.parse(saved);
            this.schedulerData = parsed.data;
            // Restore and render
            const container = document.getElementById('scheduler-wizard-container');
            if (container) container.innerHTML = '';
            const inputArea = document.getElementById('scheduler-input-area');
            if (inputArea) inputArea.style.display = 'none';
            this.generateStudyPlan();

            // After rendering show delete + saved status
            setTimeout(() => this._renderSavedScheduleActions(), 700);
        } catch (e) {
            localStorage.removeItem('brightstudy_schedule');
        }
    },

    deleteSchedule: function () {
        if (!confirm('Delete your saved schedule? You can create a new one anytime.')) return;
        localStorage.removeItem('brightstudy_schedule');
        // Reset the area and show wizard
        const area = document.getElementById('generated-timetable-area');
        if (area) area.style.display = 'none';
        this.startSchedulerWizard();
    },

    restartSchedulerWizard: function () {
        if (confirm("Restart and create a new plan? Your current input will be cleared.")) {
            localStorage.removeItem('brightstudy_schedule');
            this.startSchedulerWizard();
        }
    }
};

if (typeof window !== 'undefined') {
    window.app = app;
    window.onload = () => app.init();
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = { app };
}
