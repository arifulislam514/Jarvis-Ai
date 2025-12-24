$(document).ready(function () {
  // Display Speak Message
  eel.expose(DisplayMessage);
  function DisplayMessage(message) {
  try {
    // Your HTML has <p class="siri-message"> ... </p> (not a <li> inside it)
    $(".siri-message").text(message);

    // Only call textillate if the plugin actually loaded
    if ($.fn && typeof $.fn.textillate === "function") {
      $(".siri-message").textillate("start");
    }
  } catch (e) {
    console.log("DisplayMessage error:", e);
    // Never throw — otherwise Eel returns status:"error"
  }
}

  eel.expose(ShowHood);
  function ShowHood() {
    $("#Oval").attr("hidden", false);
    $("#SiriWave").attr("hidden", true);
  }

  eel.expose(senderText);
  function senderText(message) {
    var chatBox = document.getElementById("chat-canvas-body");
    if (message.trim() !== "") {
      chatBox.innerHTML += `<div class="row justify-content-end mb-4">
          <div class = "width-size">
          <div class="sender_message">${message}</div>
      </div>`;

      chatBox.scrollTop = chatBox.scrollHeight;
    }
  }

  eel.expose(receiverText);
  function receiverText(message) {
    var chatBox = document.getElementById("chat-canvas-body");
    if (message.trim() !== "") {
      chatBox.innerHTML += `<div class="row justify-content-start mb-4">
          <div class = "width-size">
          <div class="receiver_message">${message}</div>
          </div>
      </div>`;

      // Scroll to the bottom of the chat box
      chatBox.scrollTop = chatBox.scrollHeight;
    }
  }
  eel.expose(hideLoader);
  function hideLoader() {
    $("#Loader").attr("hidden", true);
    $("#FaceAuth").attr("hidden", false);
  }
  // Hide Face auth and display Face Auth success animation
  eel.expose(hideFaceAuth);
  function hideFaceAuth() {
    $("#FaceAuth").attr("hidden", true);
    $("#FaceAuthSuccess").attr("hidden", false);
  }
  // Hide success and display
  eel.expose(hideFaceAuthSuccess);
  function hideFaceAuthSuccess() {
    $("#FaceAuthSuccess").attr("hidden", true);
    $("#HelloGreet").attr("hidden", false);
  }

  // Hide Start Page and display blob
  eel.expose(hideStart);
  function hideStart() {
    $("#Start").attr("hidden", true);

    setTimeout(function () {
      $("#Oval").addClass("animate__animated animate__zoomIn");
    }, 1000);
    setTimeout(function () {
      $("#Oval").attr("hidden", false);
    }, 1000);
  }

  // Notify Python that the UI is ready (so Python can safely call exposed JS functions)
  try {
    if (typeof eel !== "undefined") {
      eel.init()();
    }
  } catch (e) {
    console.log("Eel init failed:", e);
  }

});