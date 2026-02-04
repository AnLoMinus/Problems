document.addEventListener("DOMContentLoaded", function () {
  const problemForm = document.getElementById("problemForm");
  const searchInput = document.getElementById("searchInput");
  const categoryFilter = document.getElementById("categoryFilter");
  const statusFilter = document.getElementById("statusFilter");
  const problemsGrid = document.getElementById("problemsGrid");

  // Form submission handling
  if (problemForm) {
    problemForm.addEventListener("submit", function (e) {
      e.preventDefault();
      const formData = new FormData(problemForm);
      const problemId = problemForm.dataset.problemId;
      const url = problemId ? `/edit_problem/${problemId}` : "/add_problem";

      fetch(url, {
        method: "POST",
        body: formData,
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.success) {
            window.location.href = "/";
          }
        })
        .catch((error) => console.error("Error:", error));
    });
  }

  // Filter and search functionality
  function updateProblems() {
    const searchTerm = searchInput.value;
    const category = categoryFilter.value;
    const status = statusFilter.value;

    fetch(
      `/filter_problems?search=${searchTerm}&category=${category}&status=${status}`
    )
      .then((response) => response.json())
      .then((problems) => {
        problemsGrid.innerHTML = problems
          .map(
            (problem) => `
          <div class="card mb-3">
            <div class="card-body">
              <div class="d-flex justify-content-between align-items-start">
                <h5 class="card-title">${problem.title}</h5>
                <div class="dropdown">
                  <button class="btn btn-link" type="button" data-bs-toggle="dropdown">
                    <i class="fas fa-ellipsis-v"></i>
                  </button>
                  <ul class="dropdown-menu">
                    <li><a class="dropdown-item" href="/edit_problem/${
                      problem.id
                    }">עריכה</a></li>
                    <li><a class="dropdown-item text-danger delete-problem" data-id="${
                      problem.id
                    }" href="#">מחיקה</a></li>
                  </ul>
                </div>
              </div>
              <h6 class="card-subtitle mb-2 text-muted">קטגוריה: ${
                problem.category
              }</h6>
              <p class="card-text">${problem.description}</p>
              <div class="badge bg-${
                problem.status === "closed" ? "success" : "warning"
              }">
                ${problem.status}
              </div>
              <div class="mt-2">
                <small class="text-muted">תאריך יעד: ${problem.due_date}</small>
              </div>
            </div>
          </div>
        `
          )
          .join("");

        // Reattach delete event listeners
        attachDeleteListeners();

        // Add calls to attach new listeners
        attachTimeLoggingListeners();
        attachCommentListeners();
      });
  }

  if (searchInput && categoryFilter && statusFilter) {
    searchInput.addEventListener("input", updateProblems);
    categoryFilter.addEventListener("change", updateProblems);
    statusFilter.addEventListener("change", updateProblems);
  }

  // Delete functionality
  function attachDeleteListeners() {
    document.querySelectorAll(".delete-problem").forEach((button) => {
      button.addEventListener("click", function (e) {
        e.preventDefault();
        if (confirm("האם אתה בטוח שברצונך למחוק בעיה זו?")) {
          const problemId = this.dataset.id;
          fetch(`/delete_problem/${problemId}`, {
            method: "POST",
          })
            .then((response) => response.json())
            .then((data) => {
              if (data.success) {
                updateProblems();
              }
            });
        }
      });
    });
  }

  attachDeleteListeners();

  // Add this function to handle tags input
  function handleTagsInput() {
    const tagsInput = document.getElementById("tags");
    if (tagsInput) {
      tagsInput.addEventListener("keydown", function (e) {
        if (e.key === "Enter") {
          e.preventDefault();
          const currentTags = this.value.split(",");
          const newTag = currentTags[currentTags.length - 1].trim();
          if (newTag) {
            this.value = [...currentTags.slice(0, -1), newTag].join(", ");
          }
        }
      });
    }
  }

  // Add this function to load statistics
  function loadStats() {
    fetch("/problem_stats")
      .then((response) => response.json())
      .then((stats) => {
        document.getElementById("totalProblems").textContent = stats.total;
        document.getElementById("openProblems").textContent =
          stats.by_status["open"] || 0;
        document.getElementById("overdueProblems").textContent = stats.overdue;
        document.getElementById("solvedProblems").textContent =
          stats.by_status["closed"] || 0;
      });
  }

  // Call these functions in DOMContentLoaded
  handleTagsInput();
  loadStats();

  // Refresh stats every 5 minutes
  setInterval(loadStats, 300000);

  // Handle subtask addition
  function attachSubtaskListeners() {
    document.querySelectorAll(".add-subtask").forEach((button) => {
      button.addEventListener("click", function () {
        const problemId = this.dataset.problemId;
        const title = prompt("כותרת המשימה:");

        if (title) {
          const formData = new FormData();
          formData.append("title", title);

          fetch(`/add_subtask/${problemId}`, {
            method: "POST",
            body: formData,
          })
            .then((response) => response.json())
            .then((data) => {
              if (data.success) {
                updateProblems();
              }
            });
        }
      });
    });

    document.querySelectorAll(".toggle-subtask").forEach((checkbox) => {
      checkbox.addEventListener("change", function () {
        const problemId = this.dataset.problemId;
        const subtaskId = this.dataset.subtaskId;

        fetch(`/toggle_subtask/${problemId}/${subtaskId}`, {
          method: "POST",
        })
          .then((response) => response.json())
          .then((data) => {
            if (data.success) {
              const textElement = this.nextElementSibling;
              textElement.classList.toggle("text-decoration-line-through");
            }
          });
      });
    });
  }

  // Add browser notifications
  function setupNotifications() {
    if ("Notification" in window) {
      Notification.requestPermission().then((permission) => {
        if (permission === "granted") {
          checkOverdueProblems();
        }
      });
    }
  }

  function checkOverdueProblems() {
    fetch("/problem_stats")
      .then((response) => response.json())
      .then((stats) => {
        if (stats.overdue > 0) {
          new Notification("בעיות באיחור", {
            body: `יש ${stats.overdue} בעיות שעברו את תאריך היעד`,
            icon: "/static/img/notification-icon.png",
          });
        }
      });
  }

  // Call new functions in DOMContentLoaded
  attachSubtaskListeners();
  setupNotifications();

  // Check for overdue problems every hour
  setInterval(checkOverdueProblems, 3600000);

  // Handle time logging
  function attachTimeLoggingListeners() {
    document.querySelectorAll(".log-time").forEach((button) => {
      button.addEventListener("click", function () {
        const problemId = this.dataset.problemId;
        const minutes = prompt("כמה דקות הושקעו?");
        const description = prompt("תיאור קצר של העבודה שנעשתה:");

        if (minutes && description) {
          const formData = new FormData();
          formData.append("minutes", minutes);
          formData.append("description", description);

          fetch(`/log_time/${problemId}`, {
            method: "POST",
            body: formData,
          })
            .then((response) => response.json())
            .then((data) => {
              if (data.success) {
                updateProblems();
              }
            });
        }
      });
    });
  }

  // Handle comments
  function attachCommentListeners() {
    document.querySelectorAll(".comment-form").forEach((form) => {
      form.addEventListener("submit", function (e) {
        e.preventDefault();
        const problemId = this.dataset.problemId;
        const input = this.querySelector("input");
        const text = input.value.trim();

        if (text) {
          const formData = new FormData();
          formData.append("text", text);

          fetch(`/add_comment/${problemId}`, {
            method: "POST",
            body: formData,
          })
            .then((response) => response.json())
            .then((data) => {
              if (data.success) {
                input.value = "";
                updateProblems();
              }
            });
        }
      });
    });
  }

  // Call new functions in DOMContentLoaded
  attachTimeLoggingListeners();
  attachCommentListeners();

  // Handle Kanban drag and drop
  function initKanban() {
    const kanbanItems = document.querySelectorAll(".kanban-item");
    const dropZones = document.querySelectorAll(".kanban-items");

    kanbanItems.forEach((item) => {
      item.addEventListener("dragstart", handleDragStart);
      item.addEventListener("dragend", handleDragEnd);
    });

    dropZones.forEach((zone) => {
      zone.addEventListener("dragover", handleDragOver);
      zone.addEventListener("drop", handleDrop);
    });
  }

  function handleDragStart(e) {
    e.target.classList.add("dragging");
    e.dataTransfer.setData("text/plain", e.target.dataset.problemId);
  }

  function handleDragEnd(e) {
    e.target.classList.remove("dragging");
  }

  function handleDragOver(e) {
    e.preventDefault();
  }

  function handleDrop(e) {
    e.preventDefault();
    const problemId = e.dataTransfer.getData("text/plain");
    const newStatus = e.target.closest(".kanban-column").dataset.status;

    fetch(`/update_status/${problemId}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: `status=${newStatus}`,
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          window.location.reload();
        }
      });
  }

  // Handle solutions
  function attachSolutionListeners() {
    document.querySelectorAll(".add-solution").forEach((button) => {
      button.addEventListener("click", function () {
        const problemId = this.dataset.problemId;
        const description = prompt("תיאור הפתרון:");
        const steps = prompt("שלבי ביצוע (הפרד בשורות חדשות):");
        const effectiveness = prompt("אפקטיביות (0-100):");

        if (description && steps) {
          const formData = new FormData();
          formData.append("description", description);
          formData.append("steps", steps);
          formData.append("effectiveness", effectiveness);

          fetch(`/add_solution/${problemId}`, {
            method: "POST",
            body: formData,
          })
            .then((response) => response.json())
            .then((data) => {
              if (data.success) {
                updateProblems();
              }
            });
        }
      });
    });

    document.querySelectorAll(".implement-solution").forEach((button) => {
      button.addEventListener("click", function () {
        const problemId = this.dataset.problemId;
        const solutionId = this.dataset.solutionId;

        if (confirm("האם אתה בטוח שברצונך ליישם פתרון זה?")) {
          fetch(`/implement_solution/${problemId}/${solutionId}`, {
            method: "POST",
          })
            .then((response) => response.json())
            .then((data) => {
              if (data.success) {
                updateProblems();
              }
            });
        }
      });
    });
  }

  // Call new functions
  if (document.querySelector(".kanban-container")) {
    initKanban();
  }

  attachSolutionListeners();
});
