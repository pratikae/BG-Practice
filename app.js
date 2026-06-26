const state = {
  chapters: [],
  activeChapter: null,
  verseDurations: new Map(),
  queue: [],
  currentIndex: 0,
  playbackTimer: null,
  currentAudio: null,
  playing: false,
};

const chapterSelect = document.getElementById("chapterSelect");
const modeSelect = document.getElementById("modeSelect");
const playBtn = document.getElementById("playBtn");
const pauseBtn = document.getElementById("pauseBtn");
const stopBtn = document.getElementById("stopBtn");
const chapterTitle = document.getElementById("chapterTitle");
const statusText = document.getElementById("statusText");
const currentVerseLabel = document.getElementById("currentVerseLabel");
const queueLabel = document.getElementById("queueLabel");
const timelineFill = document.getElementById("timelineFill");
const playlist = document.getElementById("playlist");

function setStatus(message) {
  statusText.textContent = message;
}

function updateTimeline(percent) {
  timelineFill.style.width = `${Math.max(0, Math.min(100, percent))}%`;
}

function updateCurrentVerse(number) {
  currentVerseLabel.textContent = number ? `Now playing verse ${number}` : "No verse playing";
}

function updateQueueLabel() {
  if (!state.activeChapter) {
    queueLabel.textContent = "";
    return;
  }

  const mode = modeSelect.value;
  const selectedCount = buildQueue().length;
  queueLabel.textContent = `${selectedCount} ${mode === "all" ? "verses" : `${mode} verses`} queued`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderVerseList() {
  if (!state.activeChapter) {
    playlist.innerHTML = "";
    return;
  }

  playlist.innerHTML = state.activeChapter.verses
    .map((verse) => {
      const duration = state.verseDurations.get(verse.file);
      return `
        <article class="verse-card">
          <strong>${escapeHtml(verse.number)}</strong>
          <span>${duration ? `${duration.toFixed(1)}s` : "Loading..."}</span>
        </article>
      `;
    })
    .join("");
}

function buildQueue() {
  if (!state.activeChapter) return [];

  const mode = modeSelect.value;
  if (mode === "odd") {
    return state.activeChapter.verses.filter((verse) => verse.number % 2 === 1);
  }

  if (mode === "even") {
    return state.activeChapter.verses.filter((verse) => verse.number % 2 === 0);
  }

  return state.activeChapter.verses;
}

function getGapDurationForIndex(queue, index) {
  if (index >= queue.length - 1) return 0;

  const currentVerse = queue[index];
  const followingVerse = queue[index + 1];
  if (!currentVerse || !followingVerse) return 0;

  const skippedVerseNumber = currentVerse.number + 1;
  const skippedVerse = state.activeChapter.verses.find((verse) => verse.number === skippedVerseNumber);
  if (!skippedVerse) return 0;

  return state.verseDurations.get(skippedVerse.file) || 0;
}

function stopPlayback(resetUi = true) {
  if (state.playbackTimer) {
    window.clearTimeout(state.playbackTimer);
    state.playbackTimer = null;
  }

  if (state.currentAudio) {
    state.currentAudio.pause();
    state.currentAudio.currentTime = 0;
    state.currentAudio = null;
  }

  state.playing = false;
  state.queue = [];
  state.currentIndex = 0;

  if (resetUi) {
    updateCurrentVerse(0);
    updateTimeline(0);
  }
}

function playNextVerse() {
  if (!state.playing) return;

  if (state.currentIndex >= state.queue.length) {
    stopPlayback(false);
    setStatus("Playback complete.");
    updateCurrentVerse(0);
    updateTimeline(100);
    return;
  }

  const verse = state.queue[state.currentIndex];
  const gapDuration = getGapDurationForIndex(state.queue, state.currentIndex);
  const audio = new Audio(verse.file);
  state.currentAudio = audio;
  audio.preload = "auto";
  audio.currentTime = 0;

  const startPlayback = () => {
    audio.play().then(() => {
      updateCurrentVerse(verse.number);
      const verseDuration = state.verseDurations.get(verse.file) || audio.duration || 0;
      const totalDelayMs = (verseDuration + gapDuration) * 1000;
      setStatus(`Playing verse ${verse.number} with a ${gapDuration.toFixed(1)}s pause after it.`);
      state.playbackTimer = window.setTimeout(() => {
        state.currentIndex += 1;
        playNextVerse();
      }, totalDelayMs);
    }).catch(() => {
      setStatus("Playback was blocked by the browser. Please tap play again.");
      stopPlayback(false);
    });
  };

  if (audio.readyState >= 2) {
    startPlayback();
  } else {
    audio.addEventListener("canplaythrough", startPlayback, { once: true });
  }
}

async function loadChapter(chapterId) {
  const chapter = state.chapters.find((entry) => entry.id === chapterId);
  if (!chapter) return;

  stopPlayback(false);
  state.activeChapter = chapter;
  chapterTitle.textContent = chapter.title;
  renderVerseList();
  setStatus(`Loading ${chapter.title} audio...`);
  updateQueueLabel();

  await Promise.all(
    chapter.verses.map((verse) => loadVerseDuration(verse))
  );

  renderVerseList();
  updateQueueLabel();
  setStatus(`${chapter.title} is ready. Select a mode and start practicing.`);
}

function loadVerseDuration(verse) {
  return new Promise((resolve) => {
    const audio = new Audio(verse.file);
    audio.preload = "metadata";

    const finish = () => {
      const duration = Number.isFinite(audio.duration) ? audio.duration : 0;
      state.verseDurations.set(verse.file, duration);
      resolve(duration);
    };

    audio.addEventListener("loadedmetadata", finish, { once: true });
    audio.addEventListener("error", finish, { once: true });
  });
}

async function init() {
  const response = await fetch("chapters/chapters.json");
  const data = await response.json();
  state.chapters = data.chapters;

  chapterSelect.innerHTML = state.chapters
    .map((chapter) => `<option value="${chapter.id}">${chapter.title}</option>`)
    .join("");

  chapterSelect.value = state.chapters[0]?.id || "";
  modeSelect.value = "odd";

  chapterSelect.addEventListener("change", (event) => {
    loadChapter(event.target.value);
  });

  modeSelect.addEventListener("change", () => {
    updateQueueLabel();
  });

  playBtn.addEventListener("click", () => {
    state.queue = buildQueue();
    if (!state.queue.length) {
      setStatus("No verses are available for this selection.");
      return;
    }

    state.playing = true;
    state.currentIndex = 0;
    playNextVerse();
  });

  pauseBtn.addEventListener("click", () => {
    if (!state.playing) return;
    state.playing = false;
    if (state.currentAudio) {
      state.currentAudio.pause();
    }

    if (state.playbackTimer) {
      window.clearTimeout(state.playbackTimer);
      state.playbackTimer = null;
    }

    setStatus("Playback paused.");
  });

  stopBtn.addEventListener("click", () => {
    stopPlayback();
    setStatus("Playback stopped.");
  });

  if (state.chapters.length) {
    await loadChapter(state.chapters[0].id);
  }
}

init();
