// sw-register.js — Service Worker registration + reminder API
// Exposes window.scheduleReminder() and window.cancelReminder() globally.
// Loaded in base.html before app.js.

(function () {
  "use strict";

  // Feature detect
  if (!("serviceWorker" in navigator) || !("Notification" in window)) {
    // Graceful degradation: stubs so app.js can call them without errors
    window.scheduleReminder = function () {};
    window.cancelReminder = function () {};
    window.getReminders = function (cb) {
      cb([]);
    };
    return;
  }

  var swRegistration = null;

  // Register the Service Worker
  navigator.serviceWorker
    .register("/static/js/sw.js", { scope: "/" })
    .then(function (reg) {
      swRegistration = reg;
      // Inform any waiting SW to activate immediately
      if (reg.waiting) reg.waiting.postMessage({ type: "SKIP_WAITING" });

      // On load, ask SW for the list of active reminders so we can
      // restore the "Reminder set" UI state on every page load.
      sendToSW({ type: "GET_REMINDERS" });
    })
    .catch(function (err) {
      console.warn("[SW] Registration failed:", err);
    });

  // ── Message channel from SW → page ─────────────────────────────────────────

  navigator.serviceWorker.addEventListener("message", function (e) {
    var data = e.data || {};

    if (data.type === "REMINDER_SAVED") {
      document.dispatchEvent(
        new CustomEvent("reminderSaved", { detail: { id: data.id } }),
      );
    }

    if (data.type === "REMINDERS_LIST") {
      // Restore "is-set" state on reminder bell buttons
      var ids = (data.reminders || []).map(function (r) {
        return String(r.id);
      });
      document.querySelectorAll(".reminder-bell-btn").forEach(function (btn) {
        var eventId = String(btn.dataset.eventId || "");
        if (ids.includes(eventId)) {
          btn.classList.add("is-set");
          btn.title = "Reminder set — click to cancel";
        }
      });
    }
  });

  // ── Helper: send message to active SW ──────────────────────────────────────

  function sendToSW(msg) {
    if (swRegistration && swRegistration.active) {
      swRegistration.active.postMessage(msg);
    } else {
      navigator.serviceWorker.ready.then(function (reg) {
        reg.active.postMessage(msg);
      });
    }
  }

  // ── Public API ──────────────────────────────────────────────────────────────

  /**
   * Schedules a browser notification for when an event starts.
   * @param {object} opts - { id, title, comp, startIso, url }
   */
  window.scheduleReminder = function (opts) {
    Notification.requestPermission().then(function (perm) {
      if (perm !== "granted") return;

      var fireAt = opts.startIso ? new Date(opts.startIso).getTime() : 0;
      if (fireAt <= Date.now()) {
        alert("This event has already started!");
        return;
      }

      sendToSW({
        type: "SCHEDULE_REMINDER",
        payload: {
          id: String(opts.id),
          title: opts.title,
          comp: opts.comp || "",
          fireAt: fireAt,
          url: opts.url || "/?view_mode=links",
        },
      });
    });
  };

  /**
   * Cancels a previously scheduled reminder.
   * @param {string|number} id - Event ID
   */
  window.cancelReminder = function (id) {
    sendToSW({ type: "CANCEL_REMINDER", payload: { id: String(id) } });
  };

  /**
   * Retrieves the list of active reminders from IndexedDB via the SW.
   * The result is delivered asynchronously via the 'reminderSaved' event.
   */
  window.getReminders = function () {
    sendToSW({ type: "GET_REMINDERS" });
  };
})();
