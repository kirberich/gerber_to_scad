document.addEventListener("DOMContentLoaded", function () {
  var form = document.querySelector("form");
  if (!form) return;

  form.addEventListener("input", function (e) {
    var group = e.target.closest(".form-group");
    if (group && group.classList.contains("has-error")) {
      group.classList.remove("has-error");
      group.querySelectorAll(".js-error").forEach(function (el) { el.remove(); });
    }
  });

  form.addEventListener("submit", function (e) {
    clearErrors();

    var validationErrors = validateConditionalFields();
    if (Object.keys(validationErrors).length > 0) {
      e.preventDefault();
      showErrors(validationErrors);
    }
  });

  function validateConditionalFields() {
    var errors = {};
    var alignmentAid = form.querySelector('[name="alignment_aid"]:checked');
    var type = alignmentAid ? alignmentAid.value : null;

    if (type === "ledge") {
      if (!form.querySelector('[name="ledge__thickness"]').value) {
        errors["ledge__thickness"] = ["This field is required."];
      }
    } else if (type === "frame") {
      ["frame__width", "frame__height", "frame__thickness"].forEach(function (field) {
        if (!form.querySelector('[name="' + field + '"]').value) {
          errors[field] = ["This field is required."];
        }
      });
    }

    return errors;
  }

  function showErrors(errors) {
    for (var field in errors) {
      var messages = errors[field];
      var group = document.getElementById(field);
      if (group) {
        group.classList.add("has-error");
        var target = group.querySelector(".controls") || group;
        messages.forEach(function (msg) {
          var span = document.createElement("span");
          span.className = "help-block js-error";
          span.textContent = msg;
          target.appendChild(span);
        });
      }
    }
  }

  function clearErrors() {
    document.querySelectorAll(".js-error").forEach(function (el) { el.remove(); });
    document.querySelectorAll(".has-error").forEach(function (el) {
      el.classList.remove("has-error");
    });
  }
});
