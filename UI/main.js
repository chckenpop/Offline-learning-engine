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

    // DATA: Populated from actual project content
    lessons: [
        {
            id: "photosynthesis_intro",
            title: "Introduction to Photosynthesis",
            description: "Learn how plants transform light into life.",
            completed: false,
            concepts: [
                {
                    name: "What is Photosynthesis?",
                    explain: "Photosynthesis is the process by which green plants use sunlight, water, and carbon dioxide to make their own food and release oxygen.",
                    example: "Plants use photosynthesis during the day to produce food using sunlight.",
                    question: "What is the process called where plants make food?",
                    keywords: ["photosynthesis"]
                },
                {
                    name: "Solar Energy",
                    explain: "Sunlight provides the energy that plants need to perform photosynthesis.",
                    example: "Without sunlight, most plants cannot make their food.",
                    question: "What provides energy for photosynthesis?",
                    keywords: ["sunlight"]
                },
                {
                    name: "The Power of Chlorophyll",
                    explain: "Chlorophyll is the green pigment in plant leaves that absorbs sunlight for photosynthesis.",
                    example: "Leaves appear green because of chlorophyll.",
                    question: "What is the name of the green pigment?",
                    keywords: ["chlorophyll"]
                },
                {
                    name: "Carbon Dioxide",
                    explain: "Carbon dioxide is a gas from the air that plants use during photosynthesis to help make food.",
                    example: "Plants take in carbon dioxide through tiny openings in their leaves.",
                    question: "What gas do plants take from the air?",
                    keywords: ["carbon", "dioxide"]
                },
                {
                    name: "Water for Plants",
                    explain: "Plants absorb water through their roots, which is used in the process of photosynthesis.",
                    example: "If a plant does not get enough water, it cannot make food properly.",
                    question: "How do plants get water?",
                    keywords: ["roots"]
                }
            ]
        },
        {
            id: "fractions_intro",
            title: "Introduction to Fractions",
            description: "Master the art of parts and wholes.",
            completed: false,
            concepts: [
                {
                    name: "Parts of a Whole",
                    explain: "A fraction represents a part of a whole.",
                    example: "1/2 means one out of two equal parts.",
                    question: "What does a fraction represent?",
                    keywords: ["part", "whole"]
                },
                {
                    name: "The Numerator",
                    explain: "The numerator is the top number in a fraction. It shows how many parts are taken.",
                    example: "In the fraction 3/4, the numerator is 3.",
                    question: "Which part of the fraction is the numerator?",
                    keywords: ["top"]
                },
                {
                    name: "The Denominator",
                    explain: "The denominator is the bottom number in a fraction. It shows how many equal parts the whole is divided into.",
                    example: "In the fraction 3/4, the denominator is 4.",
                    question: "Which part shows the total equal parts?",
                    keywords: ["bottom", "denominator"]
                }
            ]
        },
        {
            id: "gravity_intro",
            title: "Introduction to Gravity",
            description: "Explore the force that pulls the universe together.",
            completed: false,
            concepts: [
                {
                    name: "What is Gravity?",
                    explain: "Gravity is the force that pulls objects toward each other, especially toward the center of the Earth.",
                    example: "When you drop a ball, it falls to the ground because of gravity.",
                    question: "What force pulls objects toward Earth?",
                    keywords: ["gravity"]
                },
                {
                    name: "Mass",
                    explain: "Mass is the amount of matter in an object.",
                    example: "A bowling ball has more mass than a tennis ball.",
                    question: "What measures the amount of matter?",
                    keywords: ["mass"]
                },
                {
                    name: "Weight",
                    explain: "Weight is the force of gravity acting on an object.",
                    example: "An astronaut weighs less on the Moon because gravity is weaker there.",
                    question: "What is the force of gravity on an object called?",
                    keywords: ["weight"]
                },
                {
                    name: "Falling Objects",
                    explain: "Objects fall toward the Earth because gravity pulls them downward.",
                    example: "Leaves fall from trees due to gravity.",
                    question: "Why do objects fall down instead of up?",
                    keywords: ["gravity", "pulls"]
                }
            ]
        }
    ],

    /**
     * INITIALIZATION
     */
    init: function () {
        this.checkNetwork();
        this.renderDashboard();
        this.renderAchievements();

        // Dynamic Network detection
        window.addEventListener('online', () => this.checkNetwork());
        window.addEventListener('offline', () => this.checkNetwork());
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
        // Find matching nav item
        const navs = document.querySelectorAll('.nav-item');
        navs.forEach(n => {
            if (n.textContent.toLowerCase().includes(id.slice(0, 5))) n.classList.add('active');
        });
    },

    /**
     * DASHBOARD
     */
    renderDashboard: function () {
        const grid = document.getElementById('lesson-grid');
        grid.innerHTML = '';
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
        document.getElementById('concept-step').innerText = `STEP ${this.currentConceptIndex + 1} OF ${total}`;
        document.getElementById('concept-title').innerText = concept.name;
        document.getElementById('explanation').innerText = concept.explain;
        document.getElementById('example-text').innerText = concept.example;
        document.getElementById('question').innerText = concept.question;
        document.getElementById('user-answer').value = '';
        document.getElementById('feedback').innerText = '';
    },

    checkAnswer: function () {
        const input = document.getElementById('user-answer').value.toLowerCase();
        const keywords = this.currentLesson.concepts[this.currentConceptIndex].keywords;
        const feedback = document.getElementById('feedback');

        const correct = keywords.every(k => input.includes(k));
        if (correct) {
            feedback.innerText = "✓ Correct!";
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
            feedback.innerText = "✗ Try again.";
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
                <div style="font-size: 3rem; margin-bottom: 1rem;">🎯</div>
                <p>0 lessons completed. Start learning to earn achievements!</p>
            </div>`;
        } else {
            list.innerHTML = '';
            completed.forEach(l => {
                const card = document.createElement('div');
                card.className = 'achievement-card';
                card.innerHTML = `
                    <div class="achievement-icon">🏆</div>
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

    mockDownload: function (name) {
        alert(`Downloading "${name}" to your dashboard...`);
        // Simulating the addition
        const newLesson = {
            id: "downloaded_" + Date.now(),
            title: name,
            description: "Newly downloaded content from the cloud.",
            completed: false,
            concepts: [{ name: "Intro", explain: "Content coming soon...", example: "N/A", question: "Is this downloaded?", keywords: ["yes"] }]
        };
        this.lessons.push(newLesson);
        this.renderDashboard();
        this.showSection('dashboard');
    }
};

window.onload = () => app.init();
