// Add this new file for reminders functionality
document.addEventListener("DOMContentLoaded", function () {
  const reminderSettingsForm = document.getElementById("reminderSettingsForm");

  if (reminderSettingsForm) {
    reminderSettingsForm.addEventListener("submit", function (e) {
      e.preventDefault();

      const formData = new FormData(reminderSettingsForm);

      fetch("/save_reminder_settings", {
        method: "POST",
        body: formData,
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.success) {
            alert("ההגדרות נשמרו בהצלחה");
          }
        });
    });
  }
});
