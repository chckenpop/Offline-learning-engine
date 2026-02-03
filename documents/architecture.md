# Architecture

- UI Layer: HTML/CSS/JS
  - Renders content
  - Collects user input
  - No learning logic

- Learning Engine: Python
  - Controls lesson flow
  - Evaluates answers
  - Saves progress
  - Runs fully offline

- Local Storage: SQLite
  - Stores progress and state

- Sync Layer (Optional): Supabase
  - Provides content updates
  - Uses delta updates
