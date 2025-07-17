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