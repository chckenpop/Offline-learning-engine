# Offline-First Learning Engine

A comprehensive offline-first educational platform that enables learners to engage with structured educational content without internet connectivity. The platform combines a Python-based learning engine, SQLite persistence, and structured JSON content to deliver a seamless learning experience.

## 📋 Table of Contents

- [Overview](#overview)
- [Project Goals](#project-goals)
- [Core Principles](#core-principles)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Content Organization](#content-organization)
- [Learning Engine Features](#learning-engine-features)
- [Database Schema](#database-schema)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [Content Format](#content-format)
- [Extensibility](#extensibility)
- [Development Status](#development-status)

## 🎯 Overview

The Offline-First Learning Engine is an educational platform designed to work completely offline, making quality learning accessible without internet dependency. The system uses a local Python-based learning engine to control lesson flow, evaluate student responses, and track progress through SQLite persistence. All educational content is stored as structured JSON files, allowing for easy content management and updates.

This platform prioritizes educational effectiveness by focusing on text-based, concept-driven learning rather than media-heavy content. The architecture separates concerns cleanly: the learning engine handles pedagogy and progress tracking, while content remains data-driven and reusable.

## 🎓 Project Goals

1. **Enable Offline Learning**: Provide a fully functional learning environment that requires no internet connection
2. **Structured Progression**: Create a guided learning path through interconnected concepts and lessons
3. **Progress Tracking**: Maintain detailed locally-stored records of student progress and concept mastery
4. **Scalable Content**: Support easy addition of new lessons and concepts through JSON-based content management
5. **Optional Synchronization**: Provide a foundation for delta-based content updates via Supabase when internet is available
6. **Pedagogically Sound**: Implement learning flows that validate understanding through keyword-based answer checking

## 🔑 Core Principles

- **Offline-First Architecture**: No internet required for core functionality; all learning happens locally
- **Separation of Concerns**: Clear boundaries between content (data), learning engine (logic), and UI (presentation)
- **Local Persistence**: All progress and state stored in local SQLite database
- **Text-Based Content**: Focus on text-based lessons and concepts, not media files
- **Structured Data**: All content organized in machine-readable JSON format for consistency and interoperability
- **Content Updates**: Internet connection used only for optional delta updates, not required functionality
- **Learning Validation**: Automated answer validation through keyword matching and normalization

## 🏗️ Architecture

The system follows a three-tier architecture:

### **UI Layer** (HTML/CSS/JavaScript)
- Renders educational content to the user
- Collects user input and answers
- No learning logic or decision-making
- Communicates with the learning engine via API

### **Learning Engine** (Python)
- Core business logic for education delivery
- Controls lesson flow and progression through concepts
- Evaluates student answers and validates understanding
- Manages progress tracking and state
- Runs completely offline without external dependencies
- Located in `/engine/engine.py`

### **Local Storage Layer** (SQLite)
- Persists progress data (concept completion status)
- Tracks lesson completion status
- Stores version information for content updates
- Located in `/database/progress.db`

### **Content Layer** (JSON)
- Structured lesson definitions
- Individual concept files with explanations, examples, and questions
- Lesson indices for navigation
- All content stored in `/content` directory

### **Optional Sync Layer** (Supabase)
- Enables content updates when internet is available
- Implements delta (difference-based) updates
- Does not block core functionality when unavailable

## 💾 Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Learning Engine** | Python 3 | Core logic for lesson delivery and answer evaluation |
| **Local Persistence** | SQLite 3 | Lightweight, file-based database for progress tracking |
| **Content Format** | JSON | Human-readable, structured data format for content |
| **Frontend** | HTML, CSS, JavaScript | User interface and content presentation |
| **Optional Backend** | Supabase | Cloud-based CMS for content synchronization |
| **Environment** | Python venv | Isolated Python environment for dependencies |

## 📁 Project Structure

```
Offline-learning-engine/
├── README.md                    # Project documentation
├── content/                     # All educational content
│   ├── concepts/                # Individual concept files
│   │   ├── carbon_dioxide.json
│   │   ├── chlorophyll.json
│   │   ├── denominator.json
│   │   ├── falling_objects.json
│   │   ├── fraction_definition.json
│   │   ├── gravity.json
│   │   ├── mass.json
│   │   ├── numerator.json
│   │   ├── photosynthesis.json
│   │   ├── sunlight_energy.json
│   │   ├── water_for_plants.json
│   │   └── weight.json
│   └── lessons/                 # Lesson definitions and index
│       ├── index.json           # Catalog of all available lessons
│       ├── fraction_intro.json
│       ├── gravity_intro.json
│       └── photosynthesis_intro.json
├── database/                    # SQLite database storage
│   └── progress.db              # Student progress and state (generated)
├── documents/                   # Additional documentation
│   └── architecture.md          # Detailed architecture notes
└── engine/                      # Python learning engine
    ├── engine.py                # Main learning engine logic
    └── db.py                    # Database utilities (currently empty)
```

## 📚 Content Organization

### **Lesson Structure**

Lessons are the top-level learning units that guide students through related concepts. Each lesson is a JSON file that defines:

- **Lesson ID**: Unique identifier for the lesson
- **Title**: Human-readable lesson name
- **Introduction**: Context-setting text explaining what the lesson covers
- **Concepts**: Ordered list of concept IDs that make up the lesson
- **Outro**: Completion message summarizing what was learned

**Example: Gravity Introduction Lesson**
```json
{
  "lesson_id": "gravity_intro",
  "title": "Introduction to Gravity",
  "intro": "In this lesson, you will learn about gravity and how it affects objects on Earth and in space.",
  "concepts": ["gravity", "mass", "weight", "falling_objects"],
  "outro": "You now understand how gravity influences the motion and weight of objects."
}
```

### **Concept Structure**

Concepts are atomic units of knowledge. Each concept file defines a single, focused learning objective with explanation, examples, and validation:

- **ID**: Unique identifier for the concept
- **Type**: Content type (always "concept")
- **Explain**: Detailed explanation of the concept
- **Example**: A concrete, relatable example
- **Check**: Validation rules including question, desired answer, and keywords

**Example: Gravity Concept**
```json
{
  "id": "gravity",
  "type": "concept",
  "explain": "Gravity is the force that pulls objects toward each other, especially toward the center of the Earth.",
  "example": "When you drop a ball, it falls to the ground because of gravity.",
  "check": {
    "question": "What is gravity?",
    "desired_answer": "Gravity is the force that pulls objects toward the Earth.",
    "keywords": ["force", "pull", "Earth", "objects"]
  }
}
```

### **Lesson Index**

The `lessons/index.json` file provides a catalog of all available lessons:

```json
{
  "lessons": [
    {
      "lesson_id": "fractions_intro",
      "title": "Introduction to Fractions",
      "path": "fractions_intro.json"
    },
    {
      "lesson_id": "photosynthesis_intro",
      "title": "Introduction to Photosynthesis",
      "path": "photosynthesis_intro.json"
    },
    {
      "lesson_id": "gravity_intro",
      "title": "Introduction to Gravity",
      "path": "gravity_intro.json"
    }
  ]
}
```

## 🧠 Learning Engine Features

### **Answer Validation**
The engine uses intelligent keyword-based answer checking:
- **Normalization**: Converts user answers to lowercase, removes punctuation, normalizes whitespace
- **Keyword Matching**: Checks that all required keywords appear in the normalized answer
- **Flexible Matching**: Students don't need exact wording, just key concepts

```python
def is_answer_correct(user_answer, keywords):
    user_answer = normalize(user_answer)
    return all(keyword in user_answer for keyword in keywords)
```

### **Progress Tracking**
- Tracks individual concept completion status
- Monitors lesson completion when all concepts are mastered
- Prevents repetition of already-completed content
- Persists progress locally for resume functionality

### **Learning Flow**
1. Display available lessons to user
2. Show lesson introduction and context
3. For each concept in the lesson:
   - Display concept explanation
   - Show a practical example
   - Present validation question
   - Evaluate answer with keyword checking
   - Provide feedback (correct/incorrect with expected answer)
4. Mark lesson complete when all concepts are successfully answered
5. Display completion message and lesson summary

### **State Management**
- Checks for concept/lesson completion before presenting
- Skips already-completed content
- Allows users to reattempt failed concepts later
- Maintains learning history in database

## 💾 Database Schema

### **Progress Table**
Tracks individual concept mastery:
```sql
CREATE TABLE progress (
    concept_id TEXT PRIMARY KEY,
    status TEXT
)
```
- **concept_id**: Unique identifier from concept JSON files
- **status**: Current status ("completed" or NULL for incomplete)

### **Lessons Table**
Tracks lesson-level completion:
```sql
CREATE TABLE lessons (
    lesson_id TEXT PRIMARY KEY,
    status TEXT
)
```
- **lesson_id**: Unique identifier from lesson JSON files
- **status**: Current status ("completed" or NULL for incomplete)

### **Content Versions Table** (Prepared for future use)
Ready for delta update functionality:
```sql
CREATE TABLE content_versions (
    content_id TEXT PRIMARY KEY,
    version TEXT
)
```
- **content_id**: Identifier for content item
- **version**: Version string for tracking updates

## 🚀 Getting Started

### **Prerequisites**
- Python 3.7 or higher
- SQLite 3 (usually included with Python)
- Text editor or IDE (VS Code recommended)

### **Installation**

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Offline-learning-engine
   ```

2. **Create Python virtual environment** (recommended)
   ```bash
   python -m venv venv
   ```

3. **Activate virtual environment**
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`

4. **No external dependencies required** - The engine uses only Python standard library

### **Verify Installation**
```bash
cd engine
python engine.py
```

The system will:
- Create the `/database` directory if it doesn't exist
- Initialize the SQLite database with required tables
- Present available lessons for selection

## 📖 Usage

### **Running the Learning Engine**

```bash
cd engine
python engine.py
```

### **Interactive Session Flow**

1. **Lesson Selection**: System displays numbered list of available lessons
   ```
   Available Lessons:

   1. Introduction to Fractions (not started)
   2. Introduction to Photosynthesis (completed)
   3. Introduction to Gravity (not started)

   Select a lesson number: 
   ```

2. **Lesson Introduction**: Displays context and learning objectives
   ```
   === Lesson Start ===

   Introduction to Gravity

   In this lesson, you will learn about gravity and how it affects objects on Earth and in space.
   ```

3. **Concept Learning**: For each concept, the system:
   - Explains the concept with clear language
   - Provides a practical example
   - Asks a validation question
   - Evaluates your answer

4. **Feedback Loop**:
   - Correct answers: Marks concept as completed, moves to next
   - Incorrect answers: Shows expected answer, allows retry later

5. **Lesson Completion**: When all concepts are mastered, displays completion message

### **Progress Persistence**

Progress is automatically saved to the local SQLite database. Upon returning to the application:
- Completed lessons won't be presented again
- Completed concepts within lessons are skipped
- Users can continue from where they left off

## 📝 Content Format

### **Adding a New Concept**

Create a new JSON file in `/content/concepts/` following this structure:

```json
{
  "id": "concept_identifier",
  "type": "concept",
  "explain": "Clear, detailed explanation of the concept, 2-3 sentences.",
  "example": "A concrete, relatable example that illustrates the concept.",
  "check": {
    "question": "A question to validate understanding",
    "desired_answer": "An example correct answer",
    "keywords": ["keyword1", "keyword2", "keyword3"]
  }
}
```

**Guidelines:**
- Use lowercase, underscores for concept identifiers
- Explanations should be 1-3 sentences, clear and accessible
- Examples should be tangible and relatable
- Keywords should be 3-7 key terms that indicate understanding
- Keywords are case-insensitive and punctuation-insensitive

### **Adding a New Lesson**

1. **Create lesson JSON file** in `/content/lessons/`:

```json
{
  "lesson_id": "lesson_identifier",
  "title": "Lesson Title",
  "intro": "Introduction explaining what students will learn",
  "concepts": ["concept_id_1", "concept_id_2", "concept_id_3"],
  "outro": "Completion message summarizing learning"
}
```

2. **Update lesson index** in `/content/lessons/index.json`:

```json
{
  "lessons": [
    {
      "lesson_id": "lesson_identifier",
      "title": "Lesson Title",
      "path": "lesson_identifier.json"
    }
  ]
}
```

## 🔧 Extensibility

### **Planned Features**

The system is architected to support:

1. **Content Synchronization (Supabase)**: Delta-based content updates when internet is available
2. **Version Control**: Track content versions for smart updates via the `content_versions` table
3. **Enhanced UI**: Frontend development with HTML/CSS/JavaScript
4. **Multimedia Support**: Framework supports extension with images, videos
5. **Spaced Repetition**: Architecture can accommodate learning algorithms
6. **Analytics**: Track learning patterns and student progress
7. **Multiple Languages**: JSON format supports content localization

### **Extending the Learning Engine**

The modular structure allows for:

- **New validation methods**: Replace keyword matching with NLP or rubric-based evaluation
- **New content types**: Add quizzes, exercises, or interactive simulations
- **Adaptive learning**: Implement branching paths based on performance
- **Gamification**: Add scoring, badges, or achievement systems
- **Collaborative features**: Multi-user progress tracking

### **Adding Custom Validators**

The `is_answer_correct()` function can be extended with more sophisticated validation:

```python
def is_answer_correct_advanced(user_answer, validation_rules):
    # Could implement:
    # - Fuzzy matching for minor spelling errors
    # - Multiple acceptable answers
    # - Mathematical expression evaluation
    # - Code execution for programming lessons
    pass
```

## 📊 Current Content Library

### **Available Concepts** (12 total)
- **Physics**: gravity, mass, weight, falling_objects
- **Biology**: photosynthesis, chlorophyll, sunlight_energy, water_for_plants, carbon_dioxide
- **Mathematics**: fraction_definition, numerator, denominator

### **Available Lessons** (3 total)
- Introduction to Fractions (covers: numerator, denominator, fraction_definition)
- Introduction to Photosynthesis (covers: photosynthesis, chlorophyll, sunlight_energy, water_for_plants, carbon_dioxide)
- Introduction to Gravity (covers: gravity, mass, weight, falling_objects)

## 🔄 Development Status

**Status**: In active development

### **Completed**
- ✅ Core learning engine with lesson flow control
- ✅ SQLite database persistence
- ✅ Concept and lesson JSON structure
- ✅ Answer validation with keyword matching
- ✅ Progress tracking and detection
- ✅ Content normalization and flexible matching

### **In Progress**
- 🟡 Frontend UI (HTML/CSS/JavaScript)
- 🟡 Supabase integration for content sync

### **Planned**
- 📋 Enhanced answer validation
- 📋 Multimedia support
- 📋 Spaced repetition algorithm
- 📋 Analytics dashboard
- 📋 Multi-language support
- 📋 Adaptive learning paths

## 📝 Notes

- All file paths are relative to the engine directory for portability
- The database is automatically initialized on first run
- Content can be updated and new lessons added without modifying the engine code
- The system gracefully handles already-completed content

---

**Built for offline accessibility and educational excellence.**
