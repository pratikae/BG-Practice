# Bhagavad Gita Practice App — Internal Notes

## Overview
This is a static web app for practicing Bhagavad Gita shlokas. It allows a user to play only odd-numbered or even-numbered verses while inserting a pause that reflects the duration of the skipped verse.

## Core User Experience
- Choose a chapter from a dropdown.
- Choose playback mode: odd verses, even verses, or all verses.
- Choose a playback speed from 0.25x to 10x in 0.25x steps.
- Press Play to start a queue of verses.
- Press Pause or Stop at any time.

## How the App Works
1. The app loads chapter data from [chapters/chapters.json](chapters/chapters.json).
2. Each chapter contains a list of verses, and each verse points to an MP3 file.
3. When Play is pressed, the app builds a queue based on the selected playback mode.
4. It plays each verse using the browser Audio API.
5. After each verse, it waits for the duration of the skipped verse before moving to the next item in the queue.
6. The playback speed is applied to all audio playback using the browser audio playback rate setting.

## File Structure
- [index.html](index.html): landing page
- [bg-practice.html](bg-practice.html): main practice interface
- [app.js](app.js): playback logic, queue building, speed control, and chapter loading
- [styles.css](styles.css): visual styling
- [chapters/chapters.json](chapters/chapters.json): chapter and verse metadata

## Extension Notes
- To add more chapters, add a new chapter object to [chapters/chapters.json](chapters/chapters.json) and place the matching MP3 files in the project.
- The current version is fully front-end based and does not require a backend.
- If later needed, the same front-end logic can be adapted to load chapter and verse data from a remote API or CMS.

## Deployment Notes
This app is designed to be static and hosted on GitHub Pages. It can also be served from any simple static host such as Netlify, Cloudflare Pages, or a basic web server.
