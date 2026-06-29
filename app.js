const sharedAudio = new Audio();

const state = {
  chapters: [],
  activeChapter: null,
  verseDurations: new Map(),
  queue: [],
  currentIndex: 0,
  playbackTimer: null,
  gapTimer: null,
  currentAudio: null,
  playing: false,
  speed: 1,
};

const chapterSelect = document.getElementById("chapterSelect");
const modeSelect = document.getElementById("modeSelect");
const speedSlider = document.getElementById("speedSlider");
const speedValue = document.getElementById("speedValue");
const speedDownBtn = document.getElementById("speedDownBtn");
const speedUpBtn = document.getElementById("speedUpBtn");
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
  if (number == null) {
    currentVerseLabel.textContent = "No verse playing";
    return;
  }
  const verse = state.activeChapter?.verses.find((v) => v.number === number);
  if (number === 0 || verse?.type === "intro") {
    currentVerseLabel.textContent = "Now playing intro";
  } else if (verse?.type === "colophon") {
    currentVerseLabel.textContent = "Now playing closing prayer";
  } else {
    currentVerseLabel.textContent = `Now playing verse ${number}`;
  }
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

function formatSpeed(value) {
  return `${value.toFixed(2).replace(/\.00$/, "")}x`;
}

function updateSpeedDisplay() {
  speedSlider.value = state.speed;
  speedValue.textContent = formatSpeed(state.speed);
}

function setSpeed(value) {
  const rounded = Math.round(value * 4) / 4;
  const clamped = Math.min(10, Math.max(0.25, rounded));
  state.speed = clamped;
  if (state.currentAudio) {
    state.currentAudio.playbackRate = state.speed;
  }
  updateSpeedDisplay();
  setStatus(`Playback speed set to ${formatSpeed(state.speed)}.`);
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
        <article class="verse-card" data-verse-number="${verse.number}" role="button" tabindex="0">
          <strong>${escapeHtml(verse.number)}</strong>
          <span>${duration ? `${duration.toFixed(1)}s` : "Loading..."}</span>
        </article>
      `;
    })
    .join("");

  playlist.querySelectorAll(".verse-card").forEach((card) => {
    card.addEventListener("click", () => {
      jumpToVerse(Number(card.dataset.verseNumber));
    });

    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        jumpToVerse(Number(card.dataset.verseNumber));
      }
    });
  });
}

function buildQueue() {
  if (!state.activeChapter) return [];

  const intro = state.activeChapter.verses.find((v) => v.type === "intro" || v.number === 0);
  const colophon = state.activeChapter.verses.find((v) => v.type === "colophon");
  const regular = state.activeChapter.verses.filter(
    (v) => v.type !== "intro" && v.type !== "colophon" && v.number !== 0
  );

  const mode = modeSelect.value;
  let verses;
  if (mode === "odd") {
    verses = regular.filter((v) => v.number % 2 === 1);
  } else if (mode === "even") {
    verses = regular.filter((v) => v.number % 2 === 0);
  } else {
    verses = regular;
  }

  const queue = intro ? [intro] : [];
  queue.push(...verses);
  if (colophon) queue.push(colophon);
  return queue;
}

function getGapDurationForIndex(queue, index) {
  if (index >= queue.length - 1) return 0;

  const currentVerse = queue[index];
  const followingVerse = queue[index + 1];
  if (!currentVerse || !followingVerse) return 0;

  // No gap if the next verse in the queue immediately follows in sequence
  if (followingVerse.number === currentVerse.number + 1) return 0;

  const skippedVerseNumber = currentVerse.number + 1;
  const skippedVerse = state.activeChapter.verses.find(
    (v) => v.number === skippedVerseNumber && v.type !== "colophon"
  );
  if (!skippedVerse) return 0;

  return state.verseDurations.get(skippedVerse.file) || 0;
}

function stopPlayback(resetUi = true) {
  if (state.gapTimer) {
    window.clearTimeout(state.gapTimer);
    state.gapTimer = null;
  }

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
    updateCurrentVerse(null);
    updateTimeline(0);
  }
}

function jumpToVerse(verseNumber) {
  if (!state.activeChapter) return;

  const queue = buildQueue();
  const targetIndex = queue.findIndex((verse) => verse.number === verseNumber);

  if (targetIndex === -1) {
    setStatus(`Verse ${verseNumber} is not part of the current playback mode.`);
    return;
  }

  if (state.playbackTimer) {
    window.clearTimeout(state.playbackTimer);
    state.playbackTimer = null;
  }

  if (state.currentAudio) {
    state.currentAudio.pause();
    state.currentAudio.currentTime = 0;
    state.currentAudio = null;
  }

  state.queue = queue;
  state.currentIndex = targetIndex;
  state.playing = true;
  const jumpedVerse = queue[targetIndex];
  const jumpLabel = jumpedVerse.type === "colophon" ? "closing prayer" : verseNumber === 0 ? "intro" : `verse ${verseNumber}`;
  setStatus(`Jumped to ${jumpLabel}.`);
  playNextVerse();
}

function playNextVerse() {
  if (!state.playing) return;

  if (state.currentIndex >= state.queue.length) {
    stopPlayback(false);
    setStatus("Playback complete.");
    updateCurrentVerse(null);
    updateTimeline(100);
    return;
  }

  const verse = state.queue[state.currentIndex];
  const gapDuration = getGapDurationForIndex(state.queue, state.currentIndex);

  sharedAudio.src = verse.file;
  sharedAudio.currentTime = 0;
  state.currentAudio = sharedAudio;

  sharedAudio.play().then(() => {
    sharedAudio.playbackRate = state.speed;
    updateCurrentVerse(verse.number);
    const verseDuration = state.verseDurations.get(verse.file) || sharedAudio.duration || 0;
    const totalDelayMs = ((verseDuration + gapDuration) / state.speed) * 1000;
    const verseLabel = verse.type === "colophon" ? "closing prayer" : verse.number === 0 ? "intro" : `verse ${verse.number}`;
    setStatus(`Playing ${verseLabel} at ${formatSpeed(state.speed)} with a ${(gapDuration / state.speed).toFixed(1)}s pause after it.`);

    if (gapDuration > 0) {
      const gapStartMs = (verseDuration / state.speed) * 1000;
      const skippedNum = verse.number + 1;
      state.gapTimer = window.setTimeout(() => {
        state.gapTimer = null;
        currentVerseLabel.textContent = `Chant verse ${skippedNum}`;
        setStatus(`Chant verse ${skippedNum} (${(gapDuration / state.speed).toFixed(1)}s)`);
      }, gapStartMs);
    }

    state.playbackTimer = window.setTimeout(() => {
      state.currentIndex += 1;
      playNextVerse();
    }, totalDelayMs);
  }).catch(() => {
    setStatus("Playback was blocked by the browser. Please tap play again.");
    stopPlayback(false);
  });
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
  updateSpeedDisplay();

  chapterSelect.addEventListener("change", (event) => {
    loadChapter(event.target.value);
  });

  modeSelect.addEventListener("change", () => {
    updateQueueLabel();
  });

  speedSlider.addEventListener("input", (event) => {
    setSpeed(Number(event.target.value));
  });

  speedDownBtn.addEventListener("click", () => {
    setSpeed(state.speed - 0.25);
  });

  speedUpBtn.addEventListener("click", () => {
    setSpeed(state.speed + 0.25);
  });

  playBtn.addEventListener("click", () => {
    stopPlayback(false);
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

    if (state.gapTimer) {
      window.clearTimeout(state.gapTimer);
      state.gapTimer = null;
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
