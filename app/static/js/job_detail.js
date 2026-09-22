/**
 * LearnFlow AI — Job Detail Polling and Interactions
 */

document.addEventListener("DOMContentLoaded", () => {
  initJobDetail();
});

function initJobDetail() {
  const root = document.getElementById("job-detail-root");
  if (!root) return;

  const jobId = root.dataset.jobId;
  let currentStatus = root.dataset.status;

  // DOM Elements
  const statusBadge = document.getElementById("job-status-badge");
  const progressLabel = document.getElementById("progress-label");
  const progressText = document.getElementById("progress-text");
  const progressBarFill = document.getElementById("progress-bar-fill");
  const simulationPanel = document.getElementById("simulation-panel");
  const errorPanel = document.getElementById("error-panel");
  const btnDeleteJob = document.getElementById("btn-delete-job");
  const deleteHint = document.getElementById("delete-hint");
  const editForm = document.getElementById("edit-job-form");
  const editFeedback = document.getElementById("edit-feedback");
  const titleDisplay = document.getElementById("job-title-display");
  const metaAttempts = document.getElementById("meta-attempts");
  const metaUpdated = document.getElementById("meta-updated");

  let terminal = currentStatus === "succeeded" || currentStatus === "failed";

  // Start polling if not terminal
  if (!terminal) {
    setTimeout(pollStatus, 2000);
  }

  async function pollStatus() {
    try {
      const response = await fetch(`/api/jobs/${jobId}`);
      if (response.status === 404) {
        terminal = true;
        return;
      }
      if (response.ok) {
        const data = await response.json();
        updateUI(data);
        if (data.status === "succeeded" || data.status === "failed") {
          terminal = true;
        }
      }
    } catch (err) {
      console.warn("Polling error for job", jobId, err);
    } finally {
      if (!terminal) {
        setTimeout(pollStatus, 2000);
      }
    }
  }

  function updateUI(data) {
    currentStatus = data.status;

    // Update status badge
    if (statusBadge) {
      statusBadge.className = `badge badge-${data.status} badge-lg`;
      statusBadge.textContent = data.status;
    }

    // Update progress bar
    if (progressText) {
      progressText.textContent = `${data.progress_percent}%`;
    }
    if (progressBarFill) {
      progressBarFill.style.width = `${data.progress_percent}%`;
      progressBarFill.className = `progress-bar-fill ${
        data.status === "failed" ? "fill-error" : data.status === "succeeded" ? "fill-success" : ""
      }`;
    }

    // Update progress label & stage
    if (progressLabel) {
      if (data.status === "queued") {
        progressLabel.textContent = "Đang chờ trong hàng đợi...";
      } else if (data.status === "running") {
        const stageName = data.stage || "Khởi động";
        progressLabel.innerHTML = `Đang xử lý: Giai đoạn <strong>${stageName}</strong>`;
      } else if (data.status === "succeeded") {
        progressLabel.textContent = "Hoàn thành";
      } else if (data.status === "failed") {
        progressLabel.textContent = "Xử lý thất bại";
      }
    }

    // Update meta
    if (metaAttempts && data.attempt_count !== undefined) {
      metaAttempts.textContent = data.attempt_count;
    }
    if (metaUpdated && data.updated_at) {
      try {
        const d = new Date(data.updated_at);
        metaUpdated.textContent = d.toLocaleTimeString() + " " + d.toLocaleDateString();
      } catch (e) {
        metaUpdated.textContent = data.updated_at;
      }
    }

    // Update panels & delete button for terminal states
    if (data.status === "succeeded") {
      if (simulationPanel) simulationPanel.style.display = "block";
      if (errorPanel) errorPanel.style.display = "none";
      enableDeleteBtn();
    } else if (data.status === "failed") {
      if (simulationPanel) simulationPanel.style.display = "none";
      if (errorPanel) {
        errorPanel.style.display = "block";
        const errStage = document.getElementById("error-stage");
        const errMsg = document.getElementById("error-message");
        if (errStage && data.error) errStage.textContent = data.error.stage || "Không xác định";
        if (errMsg && data.error) errMsg.textContent = data.error.message || "Lỗi không xác định";
      }
      enableDeleteBtn();
    }
  }

  function enableDeleteBtn() {
    if (btnDeleteJob) {
      btnDeleteJob.disabled = false;
      btnDeleteJob.removeAttribute("title");
    }
    if (deleteHint) {
      deleteHint.textContent = "Xóa hoàn toàn công việc và các tệp liên quan.";
    }
  }

  // Handle Edit Metadata
  if (editForm) {
    editForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const titleInput = document.getElementById("display_title_input");
      const noteInput = document.getElementById("note_input");
      const newTitle = titleInput ? titleInput.value.trim() : "";
      const newNote = noteInput ? noteInput.value.trim() : "";

      try {
        const response = await fetch(`/api/jobs/${jobId}`, {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            display_title: newTitle || null,
            note: newNote || null,
          }),
        });

        if (response.ok) {
          const updated = await response.json();
          if (titleDisplay) {
            titleDisplay.textContent = updated.display_title || updated.topic;
          }
          if (editFeedback) {
            editFeedback.textContent = "Đã cập nhật thông tin thành công!";
            editFeedback.style.display = "block";
            setTimeout(() => {
              editFeedback.style.display = "none";
            }, 3000);
          }
        } else {
          alert("Không thể cập nhật thông tin. Vui lòng thử lại.");
        }
      } catch (err) {
        alert("Lỗi kết nối khi cập nhật thông tin.");
      }
    });
  }

  // Handle Delete
  if (btnDeleteJob) {
    btnDeleteJob.addEventListener("click", async () => {
      if (btnDeleteJob.disabled) return;

      const confirmed = window.confirm(
        "Bạn có chắc chắn muốn xóa bài giảng này không? Thao tác này không thể hoàn tác."
      );
      if (!confirmed) return;

      btnDeleteJob.disabled = true;
      btnDeleteJob.textContent = "Đang xóa...";

      try {
        const response = await fetch(`/api/jobs/${jobId}`, {
          method: "DELETE",
        });

        if (response.status === 204) {
          window.location.href = "/library";
        } else {
          const data = await response.json().catch(() => ({}));
          alert(`Không thể xóa: ${data.detail || "Lỗi máy chủ"}`);
          btnDeleteJob.disabled = false;
          btnDeleteJob.textContent = "Xóa bài giảng";
        }
      } catch (err) {
        alert("Lỗi kết nối khi xóa bài giảng.");
        btnDeleteJob.disabled = false;
        btnDeleteJob.textContent = "Xóa bài giảng";
      }
    });
  }
}
