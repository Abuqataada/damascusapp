document.querySelectorAll('.solution-box').forEach(function(box) {
    box.addEventListener('touchstart', function() {
      this.classList.add('touched');
    });
    box.addEventListener('touchend', function() {
      setTimeout(() => this.classList.remove('touched'), 1000);
    });
  });











function showAlert(event) {
          event.preventDefault();
          document.getElementById('successAlert').classList.remove('d-none');
          
          // Hide after 3 seconds
          setTimeout(() => {
            document.getElementById('successAlert').classList.add('d-none');
          }, 3000);
          
          // Uncomment to actually submit the form
          // event.target.submit();
        }

document.addEventListener("DOMContentLoaded", function() {
  const alerts = document.querySelectorAll('.alert');
  alerts.forEach(function(alert) {
    setTimeout(function() {
      // uses Bootstrap built-in fade & hide
      alert.classList.add('fade');
      alert.classList.remove('show');
      setTimeout(() => alert.remove(), 300); // short wait for fade
    }, 4000);
  });
});






// Show spinner function (called on clicks/navigation)
function showLoading() {
    window.AppInventor.setWebViewString("show_spinner");
}

// Hide spinner function (called when page finishes loading)
function hideLoading() {
    window.AppInventor.setWebViewString("hide_spinner");
}

// ===== 1. Trigger Spinner on ALL BUTTON/LINK CLICKS =====
document.addEventListener("click", function(event) {
    const target = event.target;
    // Check if clicked element is a button, link, or has [onclick]
    if (target.tagName === "BUTTON" || 
        target.tagName === "A" || 
        target.hasAttribute("onclick")) {
        showLoading();
    }
});

// ===== 2. Trigger Spinner on PAGE TRANSITIONS (before unload) =====
window.addEventListener("beforeunload", function() {
    showLoading();
});

// ===== 3. Hide Spinner When New Page Finishes Loading =====
window.addEventListener("load", hideLoading);