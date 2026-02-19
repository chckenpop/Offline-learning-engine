beforeAll(() => {
    global.navigator = { onLine: true };
});

const { app } = require("../main.js");

const baseDOM = `
    <div id="network-alert"></div>
    <div id="gateway"></div>
    <div id="online-nav"></div>
    <div id="lesson-grid"></div>
    <div id="achievements-list"></div>
    <div id="search-results"></div>
    <input id="search-input" />
    <section id="dashboard" class="view active"></section>
    <section id="achievements" class="view"></section>
    <section id="classroom" class="view"></section>
    <div class="nav-item" data-target="dashboard"></div>
    <div class="nav-item" data-target="achievements"></div>
`;

beforeEach(() => {
    document.body.innerHTML = baseDOM;
});

test("showSection activates the right view and nav item", () => {
    app.showSection("achievements");

    expect(document.getElementById("achievements").classList.contains("active")).toBe(true);
    expect(document.getElementById("dashboard").classList.contains("active")).toBe(false);

    const navItems = document.querySelectorAll(".nav-item");
    expect(navItems[1].classList.contains("active")).toBe(true);
    expect(navItems[0].classList.contains("active")).toBe(false);
});

test("checkAnswer updates feedback state", () => {
    document.body.insertAdjacentHTML(
        "beforeend",
        `
        <input id="user-answer" />
        <div id="feedback"></div>
        <div id="question"></div>
        <div id="concept-step"></div>
        <div id="concept-title"></div>
        <div id="explanation"></div>
        <div id="example-text"></div>
        `
    );

    app.currentLesson = {
        concepts: [
            {
                keywords: ["photosynthesis"],
                name: "Concept",
                explain: "Explain",
                example: "Example",
                question: "Question"
            }
        ]
    };
    app.currentConceptIndex = 0;

    document.getElementById("user-answer").value = "photosynthesis";
    app.checkAnswer();
    expect(document.getElementById("feedback").textContent).toBe("Correct!");

    document.getElementById("user-answer").value = "nope";
    app.checkAnswer();
    expect(document.getElementById("feedback").textContent).toBe("Try again.");
});
