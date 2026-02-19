/**
 * Bright Study - UI Logic
 * Fully optimized for low-end devices and poor networks.
 * Size constrained under 10MB project goal.
 */

const app = {
    mode: null,
    currentLesson: null,
    currentConceptIndex: 0,
    isOnline: navigator.onLine,

    lessons: [],

    /**
     * INITIALIZATION
     */
    init: function () {
        this.checkNetwork();
        this.loadLessons();
        this.renderAchievements();
        this.wireUpdatesUI();

        // Dynamic Network detection
        window.addEventListener('online', () => this.checkNetwork());
        window.addEventListener('offline', () => this.checkNetwork());
    },

    fetchLessons: async function () {
        const res = await fetch('/api/lessons');
        if (!res.ok) {
            throw new Error(await res.text());
        }
        return res.json();
    },

    loadLessons: async function () {
        const grid = document.getElementById('lesson-grid');
        try {
            const data = await this.fetchLessons();
            const lessons = (data && data.lessons) ? data.lessons : [];
            this.lessons = lessons.map((lesson) => ({
                id: lesson.lesson_id,
                title: lesson.title || lesson.lesson_id,
                description: lesson.intro || '',
                completed: false,
                concepts: (lesson.concepts || []).map((c) => ({
                    name: (c.name || c.title || c.id || 'Concept')
                        .replace(/_/g, ' ')
                        .replace(/\b\w/g, (m) => m.toUpperCase()),
                    explain: c.explain || '',
                    example: c.example || '',
                    question: (c.check && c.check.question) ? c.check.question : '',
                    keywords: (c.check && c.check.keywords) ? c.check.keywords : []
                }))
            }));
            this.renderDashboard();
            this.renderAchievements();
        } catch (e) {
            if (grid) {
                grid.innerHTML = '<div style="color: var(--text-dim);">Unable to load lessons.</div>';
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
    setMode: function (mode) {
        this.mode = mode;
        document.getElementById('gateway').style.display = 'none';
        document.getElementById('online-nav').style.display = mode === 'online' ? 'block' : 'none';
        this.checkNetwork();
    },

    resetMode: function () {
        document.getElementById('gateway').style.display = 'flex';
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
            const progress = lesson.completed ? 100 : 0;
            card.innerHTML = `
                <h3>${lesson.title}</h3>
                <p style="font-size:0.8rem; color:var(--text-dim); margin-top:0.5rem;">${lesson.description}</p>
                <div class="progress-bar"><div class="progress-fill" style="width:${progress}%"></div></div>
            `;
            grid.appendChild(card);
        });
    },

    /**
     * CLASSROOM
     */
    startLesson: function (id) {
        this.currentLesson = this.lessons.find(l => l.id === id);
        this.currentConceptIndex = 0;
        this.showSection('classroom');
        this.loadConcept();
    },

    loadConcept: function () {
        const concept = this.currentLesson.concepts[this.currentConceptIndex];
        const total = this.currentLesson.concepts.length;
        document.getElementById('concept-step').textContent = `STEP ${this.currentConceptIndex + 1} OF ${total}`;
        document.getElementById('concept-title').textContent = concept.name;
        document.getElementById('explanation').textContent = concept.explain;
        document.getElementById('example-text').textContent = concept.example;
        document.getElementById('question').textContent = concept.question;
        document.getElementById('user-answer').value = '';
        document.getElementById('feedback').textContent = '';
    },

    checkAnswer: function () {
        const input = document.getElementById('user-answer').value.toLowerCase();
        const keywords = this.currentLesson.concepts[this.currentConceptIndex].keywords;
        const feedback = document.getElementById('feedback');

        const correct = keywords.every(k => input.includes(k));
        if (correct) {
            feedback.textContent = "Correct!";
            feedback.style.color = "var(--accent)";
            setTimeout(() => {
                if (this.currentConceptIndex < this.currentLesson.concepts.length - 1) {
                    this.currentConceptIndex++;
                    this.loadConcept();
                } else {
                    this.completeLesson();
                }
            }, 800);
        } else {
            feedback.textContent = "Try again.";
            feedback.style.color = "var(--danger)";
        }
    },

    completeLesson: function () {
        this.currentLesson.completed = true;
        this.renderDashboard();
        this.renderAchievements();
        alert("Lesson Completed! Your achievements updated.");
        this.showSection('dashboard');
    },

    /**
     * ACHIEVEMENTS
     */
    renderAchievements: function () {
        const list = document.getElementById('achievements-list');
        const completed = this.lessons.filter(l => l.completed);

        if (completed.length === 0) {
            list.innerHTML = `<div style="text-align:center; padding: 2rem; color: var(--text-dim);">
                <div style="font-size: 0.85rem; margin-bottom: 0.75rem; letter-spacing: 0.2em;">NO ACHIEVEMENTS YET</div>
                <p>0 lessons completed. Start learning to earn achievements.</p>
            </div>`;
        } else {
            list.innerHTML = '';
            completed.forEach(l => {
                const card = document.createElement('div');
                card.className = 'achievement-card';
                card.innerHTML = `
                    <div class="achievement-icon">A+</div>
                    <div>
                        <strong>Master of ${l.title.split(' ').pop()}</strong>
                        <p style="font-size: 0.75rem; color: var(--text-dim);">Successfully completed all concepts.</p>
                    </div>
                `;
                list.appendChild(card);
            });
        }
    },

    /**
     * ADD MORE LESSONS (Online Mock)
     */
    searchLessons: function () {
        const query = document.getElementById('search-input').value.toLowerCase();
        const results = document.getElementById('search-results');

        if (!query) return;

        // "Validation Site" mock response
        const mockCloud = [
            { title: "Advanced Chemistry", type: "Lesson", id: "chem_1" },
            { title: "World History: Origins", type: "Lesson", id: "hist_1" },
            { title: "Space Exploration", type: "Concept", id: "space_1" }
        ];

        const match = mockCloud.filter(m => m.title.toLowerCase().includes(query));

        if (match.length > 0) {
            results.innerHTML = match.map(m => `
                <div class="result-item">
                    <div>
                        <strong>${m.title}</strong>
                        <div style="font-size: 0.7rem; color: var(--accent);">${m.type}</div>
                    </div>
                    <button class="add-btn" onclick="app.mockDownload('${m.title}')">ADD +</button>
                </div>
            `).join('');
        } else {
            results.innerHTML = '<p style="color:var(--text-dim);">No results found in cloud.</p>';
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

    mockDownload: function (name) {
        alert(`Download request sent for "${name}".`);
        this.loadLessons();
        this.showSection('dashboard');
    }
};

if (typeof window !== 'undefined') {
    window.app = app;
    window.onload = () => app.init();
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = { app };
}
