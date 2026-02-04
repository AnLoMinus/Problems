document.addEventListener("DOMContentLoaded", function () {
  // Show/hide group select based on visibility
  const visibilitySelect = document.querySelector('select[name="visibility"]');
  const groupSelect = document.querySelector(".group-select");

  if (visibilitySelect) {
    visibilitySelect.addEventListener("change", function () {
      groupSelect.style.display = this.value === "group" ? "block" : "none";
    });
  }

  // Create new group
  window.createGroup = function () {
    const form = document.getElementById("newGroupForm");
    const formData = new FormData(form);

    fetch("/create_group", {
      method: "POST",
      body: formData,
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          window.location.reload();
        }
      });
  };

  // Add member to group
  document.querySelectorAll(".invite-member").forEach((button) => {
    button.addEventListener("click", function () {
      const groupId = this.dataset.groupId;
      const username = prompt("הכנס שם משתמש להוספה:");

      if (username) {
        const formData = new FormData();
        formData.append("username", username);

        fetch(`/add_member_to_group/${groupId}`, {
          method: "POST",
          body: formData,
        })
          .then((response) => response.json())
          .then((data) => {
            if (data.success) {
              window.location.reload();
            } else {
              alert("לא ניתן להוסיף את המשתמש");
            }
          });
      }
    });
  });

  // Delete group
  document.querySelectorAll(".delete-group").forEach((button) => {
    button.addEventListener("click", function () {
      if (confirm("האם אתה בטוח שברצונך למחוק את הקבוצה?")) {
        const groupId = this.dataset.groupId;
        fetch(`/delete_group/${groupId}`, {
          method: "POST",
        })
          .then((response) => response.json())
          .then((data) => {
            if (data.success) {
              window.location.reload();
            }
          });
      }
    });
  });
});
