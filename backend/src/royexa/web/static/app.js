// The only script of the pages. It fills the device time of a form and stops a second tap
// from sending the same form twice; the server enforces the single use either way.
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll("form").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      if (form.dataset.sent) {
        event.preventDefault();
        return;
      }
      form.dataset.sent = "1";
      form.querySelectorAll("input[name=device_time]").forEach(function (field) {
        field.value = new Date().toISOString();
      });
      form.querySelectorAll("button[type=submit]").forEach(function (button) {
        button.disabled = true;
      });
    });
  });
});
