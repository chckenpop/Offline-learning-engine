# Bright Study

## Goal
Build an educational web application that works fully offline using a local learning engine, structured content, and SQLite for persistence.

## Core Principles
- Offline-first (no internet required for learning)
- Local learning engine controls flow and progress
- Structured text-based content, not media
- Internet used only for delta updates

## Tech Stack
- Python (learning engine)
- SQLite (local persistence)
- HTML, CSS, JavaScript (UI)
- Supabase (optional content updates)

## Recent Work (UI Development)
We have built a high-end web interface inside the `UI/` folder that is specially designed for low-end phones and slow internet. Here is what we added:
- **Dual Mode**: Choose "Offline" for normal studying or "Online" for extra cloud features.
- **Smart Download**: In Online mode, you can search and add new lessons from our cloud to your dashboard.
- **Real-time Progress**: Your lesson progress and achievements update immediately as you finish each step.
- **Internet Check**: The app automatically detects if your internet is on or off when using online features.
- **Ultra-Lightweight**: No heavy animations or big files, keeping the app size extremely small and fast.

## Status
In active development.
