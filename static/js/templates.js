// Add this new file for template functionality
document.addEventListener("DOMContentLoaded", function () {
  const newTemplateForm = document.getElementById("newTemplateForm");

  if (newTemplateForm) {
    newTemplateForm.addEventListener("submit", function (e) {
      e.preventDefault();

      const formData = new FormData(newTemplateForm);

      fetch("/save_template", {
        method: "POST",
        body: formData,
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.success) {
            window.location.reload();
          }
        });
    });
  }

  // Save problem as template
  document.querySelectorAll(".save-as-template").forEach((button) => {
    button.addEventListener("click", function () {
      const problemId = this.dataset.problemId;
      const templateName = prompt("שם התבנית:");

      if (templateName) {
        const formData = new FormData();
        formData.append("template_name", templateName);

        fetch(`/save_as_template/${problemId}`, {
          method: "POST",
          body: formData,
        })
          .then((response) => response.json())
          .then((data) => {
            if (data.success) {
              window.location.href = "/templates";
            }
          });
      }
    });
  });
});
