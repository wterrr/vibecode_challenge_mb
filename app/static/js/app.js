/**
 * LearnFlow AI — Core Application JavaScript
 */

document.addEventListener("DOMContentLoaded", () => {
  initCreateForm();
});

function initCreateForm() {
  const form = document.getElementById("create-job-form");
  if (!form) return;

  const submitBtn = document.getElementById("btn-submit-create");
  const btnText = submitBtn ? submitBtn.querySelector(".btn-text") : null;
  const btnSpinner = submitBtn ? submitBtn.querySelector(".btn-spinner") : null;
  const errorAlert = document.getElementById("error-alert");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const topic = document.getElementById("topic").value.trim();
    const audience = document.getElementById("audience").value;
    const language = document.getElementById("language").value;
    const targetDurationSeconds = parseInt(
      document.getElementById("target_duration_seconds").value,
      10
    );

    if (errorAlert) {
      errorAlert.style.display = "none";
      errorAlert.textContent = "";
    }

    if (!topic || topic.length < 3) {
      showError("Vui lòng nhập chủ đề có ít nhất 3 ký tự.");
      return;
    }

    // Set loading state
    if (submitBtn) submitBtn.disabled = true;
    if (btnText) btnText.style.display = "none";
    if (btnSpinner) btnSpinner.style.display = "inline";

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

      const data = await response.json();

      if (response.status === 202 && data.page_url) {
        window.location.href = data.page_url;
      } else {
        const errorMsg = extractErrorMessage(data) || "Không thể tạo bài giảng. Vui lòng thử lại.";
        showError(errorMsg);
        resetSubmitBtn();
      }
    } catch (err) {
      showError("Lỗi kết nối máy chủ. Vui lòng kiểm tra lại mạng.");
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
    if (btnSpinner) btnSpinner.style.display = "none";
  }

  function extractErrorMessage(data) {
    if (!data) return null;
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail) && data.detail.length > 0) {
      const first = data.detail[0];
      return first.msg ? `${first.loc?.join(".") || "Dữ liệu"}: ${first.msg}` : null;
    }
    return null;
  }
}
