/**
 * LearnFlow — Job Detail & Processing Interactions (CP9)
 * Manages live stage polling, vertical step progression, terminal transitions, and title renaming.
 */

document.addEventListener("DOMContentLoaded", () => {
  initJobDetail();
  initRename();
});

const STAGE_ORDER = [
  "planning",
  "validating_plan",
  "audio",
  "rendering",
  "assembling",
  "validating_output",
];

const STAGE_LABELS = {
  planning: "1. Lập kế hoạch bài học",
  validating_plan: "2. Kiểm tra cấu trúc bài học",
  audio: "3. Tạo lời thuyết minh",
  rendering: "4. Xây dựng hình minh họa",
  assembling: "5. Ghép video",
  validating_output: "6. Kiểm tra video cuối",
};

function initJobDetail() {
  const root = document.getElementById("job-detail-root");
  if (!root) return;

  const jobId = root.dataset.jobId;
  const initialStatus = root.dataset.status;

  // If already terminal (succeeded or failed), do not start polling
  if (initialStatus === "succeeded" || initialStatus === "failed") {
    return;
  }

  // DOM Elements
  const progressTrack = document.getElementById("progress-track");
  const progressFill = document.getElementById("progress-fill");
  const progressPercentText = document.getElementById("progress-percent-text");
  const progressStageText = document.getElementById("progress-stage-text");
  const pollingNotice = document.getElementById("polling-notice");

  let inFlight = false;
  let isTerminal = false;
  let consecutiveErrors = 0;
  let pollTimer = null;

  // Initial stage render based on template dataset
  updateStages(root.dataset.stage, parseInt(root.dataset.progress, 10) || 0);

  // Start polling every 2 seconds
  schedulePoll();

  function schedulePoll() {
    if (isTerminal) return;
    clearTimeout(pollTimer);
    pollTimer = setTimeout(pollJobStatus, 2000);
  }

  async function pollJobStatus() {
    if (inFlight || isTerminal) return;
    inFlight = true;

    try {
      const response = await fetch(`/api/jobs/${jobId}`, {
        headers: { Accept: "application/json" },
      });

      if (response.status === 404) {
        // Job was deleted or does not exist
        isTerminal = true;
        window.location.href = "/library";
        return;
      }

      if (response.ok) {
        const data = await response.json();
        consecutiveErrors = 0;
        if (pollingNotice) pollingNotice.style.display = "none";

        // Update progress bar & live ARIA progress
        if (progressTrack && data.progress_percent !== undefined) {
          progressTrack.setAttribute("aria-valuenow", String(data.progress_percent));
        }
        if (progressFill && data.progress_percent !== undefined) {
          progressFill.style.width = `${data.progress_percent}%`;
        }
        if (progressPercentText && data.progress_percent !== undefined) {
          progressPercentText.textContent = `${data.progress_percent}%`;
        }

        // Update stage text
        if (progressStageText) {
          if (data.status === "queued") {
            progressStageText.textContent = "Đang xếp hàng đợi...";
          } else if (data.stage) {
            const raw = String(data.stage).toLowerCase();
            progressStageText.textContent = STAGE_LABELS[raw] || "Đang xử lý...";
          }
        }

        // Update vertical sequence
        updateStages(data.stage, data.progress_percent);

        // Check terminal states
        if (data.status === "succeeded" || data.status === "failed") {
          isTerminal = true;
          // Reload page so server delivers the authoritative Result or Failed view
          window.location.reload();
          return;
        }
      } else {
        consecutiveErrors++;
        checkErrorThreshold();
      }
    } catch (err) {
      consecutiveErrors++;
      checkErrorThreshold();
    } finally {
      inFlight = false;
      if (!isTerminal) {
        schedulePoll();
      }
    }
  }

  function checkErrorThreshold() {
    if (consecutiveErrors >= 5 && pollingNotice) {
      pollingNotice.style.display = "block";
    }
  }

  function updateStages(currentStage, progress) {
    const rawStage = currentStage ? String(currentStage).toLowerCase() : "";
    const currentIndex = STAGE_ORDER.indexOf(rawStage);

    STAGE_ORDER.forEach((stageId, idx) => {
      const stepEl = document.getElementById(`step-${stageId}`);
      if (!stepEl) return;

      stepEl.classList.remove("step-completed", "step-current", "step-future");

      if (currentIndex === -1) {
        // In queue (progress 0)
        stepEl.classList.add("step-future");
      } else if (idx < currentIndex) {
        stepEl.classList.add("step-completed");
      } else if (idx === currentIndex) {
        stepEl.classList.add("step-current");
      } else {
        stepEl.classList.add("step-future");
      }
    });
  }
}

/**
 * Handle display title inline editing on the Result page.
 */
function initRename() {
  const btnToggle = document.getElementById("btn-toggle-rename");
  const renameForm = document.getElementById("rename-form");
  const renameInput = document.getElementById("rename-input");
  const btnCancel = document.getElementById("btn-cancel-rename");
  const titleDisplay = document.getElementById("job-title-display");
  const feedback = document.getElementById("rename-feedback");
  const root = document.getElementById("job-detail-root");

  if (!btnToggle || !renameForm || !renameInput || !root) return;
  const jobId = root.dataset.jobId;

  btnToggle.addEventListener("click", () => {
    renameForm.style.display = renameForm.style.display === "none" ? "block" : "none";
    if (renameForm.style.display === "block") {
      renameInput.focus();
      renameInput.select();
    }
  });

  if (btnCancel) {
    btnCancel.addEventListener("click", () => {
      renameForm.style.display = "none";
      if (feedback) feedback.style.display = "none";
    });
  }

  renameForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const newTitle = renameInput.value.trim();
    if (!newTitle) return;

    const btnSave = document.getElementById("btn-save-rename");
    if (btnSave) btnSave.disabled = true;

    try {
      const response = await fetch(`/api/jobs/${jobId}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          display_title: newTitle,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        // Update display text safely (XSS-safe via textContent)
        if (titleDisplay) {
          titleDisplay.textContent = data.display_title || newTitle;
        }
        if (feedback) {
          feedback.textContent = "Đã lưu thay đổi.";
          feedback.style.display = "block";
          setTimeout(() => {
            feedback.style.display = "none";
            renameForm.style.display = "none";
          }, 1200);
        } else {
          renameForm.style.display = "none";
        }
      } else {
        if (feedback) {
          feedback.textContent = "Không thể lưu tiêu đề lúc này.";
          feedback.style.display = "block";
        }
      }
    } catch (err) {
      if (feedback) {
        feedback.textContent = "Lỗi kết nối khi lưu tiêu đề.";
        feedback.style.display = "block";
      }
    } finally {
      if (btnSave) btnSave.disabled = false;
    }
  });
}
