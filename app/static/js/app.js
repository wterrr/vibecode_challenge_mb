/**
 * LearnFlow — Core Application Interactions (CP9)
 * Clean, modern vanilla JavaScript for form validation, demo fill, and delete confirmation.
 */

document.addEventListener("DOMContentLoaded", () => {
  initCreateForm();
  initDemoChips();
  initDeleteDialog();
});

/**
 * Handle learning request creation with inline validation and double-submission protection.
 */
function initCreateForm() {
  const form = document.getElementById("create-job-form");
  if (!form) return;

  const submitBtn = document.getElementById("btn-submit-create");
  const btnText = submitBtn ? submitBtn.querySelector(".btn-text") : null;
  const btnLoading = submitBtn ? submitBtn.querySelector(".btn-loading") : null;
  const errorAlert = document.getElementById("error-alert");
  const topicInput = document.getElementById("topic");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const topic = topicInput ? topicInput.value.trim() : "";
    const audience = document.getElementById("audience")?.value || "Beginner";
    const language = document.getElementById("language")?.value || "vi";
    const durationSelect = document.getElementById("target_duration_seconds");
    const targetDurationSeconds = durationSelect ? parseInt(durationSelect.value, 10) : 90;

    // Reset error box
    if (errorAlert) {
      errorAlert.style.display = "none";
      errorAlert.textContent = "";
    }

    if (!topic || topic.length < 3) {
      showError("Vui lòng nhập chủ đề bạn muốn học (tối thiểu 3 ký tự).");
      if (topicInput) topicInput.focus();
      return;
    }

    // Set loading state
    if (submitBtn) submitBtn.disabled = true;
    if (btnText) btnText.style.display = "none";
    if (btnLoading) btnLoading.style.display = "inline";

    try {
      const response = await fetch("/api/jobs", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          topic,
          audience,
          language,
          target_duration_seconds: targetDurationSeconds,
        }),
      });

      const data = await response.json().catch(() => null);

      if (response.status === 202 && data && data.page_url) {
        window.location.href = data.page_url;
      } else {
        const errorMsg = extractHumanErrorMessage(data) || "Không thể tạo bài học lúc này. Vui lòng thử lại.";
        showError(errorMsg);
        resetSubmitBtn();
      }
    } catch (err) {
      showError("Không thể kết nối đến máy chủ. Vui lòng kiểm tra lại đường truyền mạng.");
      resetSubmitBtn();
    }
  });

  function showError(msg) {
    if (errorAlert) {
      errorAlert.textContent = msg;
      errorAlert.style.display = "block";
      errorAlert.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }

  function resetSubmitBtn() {
    if (submitBtn) submitBtn.disabled = false;
    if (btnText) btnText.style.display = "inline";
    if (btnLoading) btnLoading.style.display = "none";
  }

  function extractHumanErrorMessage(data) {
    if (!data) return null;
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail) && data.detail.length > 0) {
      const item = data.detail[0];
      return item.msg || null;
    }
    return null;
  }
}

/**
 * Handle demo topic quick-fill buttons on Create page.
 */
function initDemoChips() {
  const chips = document.querySelectorAll(".demo-chip-btn");
  const topicInput = document.getElementById("topic");
  if (!chips.length || !topicInput) return;

  chips.forEach((chip) => {
    chip.addEventListener("click", () => {
      const topicText = chip.dataset.topic;
      if (topicText) {
        topicInput.value = topicText;
        topicInput.focus();
      }
    });
  });
}

/**
 * Handle accessible delete confirmation dialog using native <dialog>.
 */
function initDeleteDialog() {
  const dialog = document.getElementById("delete-dialog");
  if (!dialog) return;

  const btnCancel = document.getElementById("btn-cancel-delete");
  const btnConfirm = document.getElementById("btn-confirm-delete");
  const errorBox = document.getElementById("delete-error");

  let activeJobId = null;
  let activeTrigger = null;

  // Open dialog when any delete trigger is clicked
  document.addEventListener("click", (e) => {
    const trigger = e.target.closest(".btn-delete-trigger");
    if (!trigger) return;

    activeTrigger = trigger;
    activeJobId = trigger.dataset.jobId;

    if (errorBox) {
      errorBox.style.display = "none";
      errorBox.textContent = "";
    }

    if (btnConfirm) {
      btnConfirm.disabled = false;
      btnConfirm.textContent = "Xóa bài học";
    }

    if (typeof dialog.showModal === "function") {
      dialog.showModal();
    } else {
      dialog.setAttribute("open", "true");
    }

    if (btnCancel) {
      btnCancel.focus();
    }
  });

  // Cancel action
  if (btnCancel) {
    btnCancel.addEventListener("click", () => {
      closeDialog();
    });
  }

  // Close on Escape or click outside
  dialog.addEventListener("cancel", () => {
    closeDialog();
  });

  dialog.addEventListener("click", (e) => {
    const rect = dialog.getBoundingClientRect();
    const isInDialog = (
      rect.top <= e.clientY &&
      e.clientY <= rect.top + rect.height &&
      rect.left <= e.clientX &&
      e.clientX <= rect.left + rect.width
    );
    if (!isInDialog) {
      closeDialog();
    }
  });

  function closeDialog() {
    if (typeof dialog.close === "function") {
      dialog.close();
    } else {
      dialog.removeAttribute("open");
    }
    if (activeTrigger) {
      activeTrigger.focus();
    }
    activeJobId = null;
  }

  // Confirm delete action
  if (btnConfirm) {
    btnConfirm.addEventListener("click", async () => {
      if (!activeJobId) return;

      const targetJobId = activeJobId;
      btnConfirm.disabled = true;
      btnConfirm.textContent = "Đang xóa…";
      if (errorBox) {
        errorBox.style.display = "none";
        errorBox.textContent = "";
      }

      try {
        const response = await fetch(`/api/jobs/${targetJobId}`, {
          method: "DELETE",
        });

        if (response.status === 204) {
          // Success: preserve deleted job ID before closing dialog
          const deletedJobId = targetJobId;
          closeDialog();

          // If we are currently on the detail page of this job, navigate to /library
          const root = document.getElementById("job-detail-root");
          if (root && root.dataset.jobId === deletedJobId) {
            window.location.href = "/library";
            return;
          }

          // If on library, remove the row or reload
          const row = document.getElementById(`job-row-${deletedJobId}`);
          if (row) {
            row.remove();
            // Check if any rows left
            const remaining = document.querySelectorAll(".job-row");
            if (!remaining.length) {
              window.location.reload();
            }
          } else {
            window.location.reload();
          }
        } else if (response.status === 409) {
          showDialogError("Không thể xóa bài học đang trong quá trình chuẩn bị.");
          btnConfirm.disabled = false;
          btnConfirm.textContent = "Xóa bài học";
        } else {
          showDialogError("Không thể xóa bài học lúc này. Vui lòng thử lại.");
          btnConfirm.disabled = false;
          btnConfirm.textContent = "Xóa bài học";
        }
      } catch (err) {
        showDialogError("Lỗi kết nối khi xóa. Vui lòng kiểm tra lại mạng.");
        btnConfirm.disabled = false;
        btnConfirm.textContent = "Xóa bài học";
      }
    });
  }

  function showDialogError(msg) {
    if (errorBox) {
      errorBox.textContent = msg;
      errorBox.style.display = "block";
    }
  }
}
