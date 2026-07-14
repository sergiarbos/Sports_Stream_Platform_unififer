// sw.js — Sports Stream Platform Service Worker
// Handles persistent event reminders via IndexedDB + Notifications API.
// Registered by sw-register.js; communicates via postMessage.

const DB_NAME = "sports-reminders-v1";
const STORE_NAME = "reminders";
const SW_VERSION = "1.0.0";

// ── IndexedDB helpers ────────────────────────────────────────────────────────

function openDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: "id" });
      }
    };
    req.onsuccess = (e) => resolve(e.target.result);
    req.onerror = (e) => reject(e.target.error);
  });
}

async function saveReminder(reminder) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    tx.objectStore(STORE_NAME).put(reminder);
    tx.oncomplete = resolve;
    tx.onerror = (e) => reject(e.target.error);
  });
}

async function deleteReminder(id) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    tx.objectStore(STORE_NAME).delete(id);
    tx.oncomplete = resolve;
    tx.onerror = (e) => reject(e.target.error);
  });
}

async function getAllReminders() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readonly");
    const req = tx.objectStore(STORE_NAME).getAll();
    req.onsuccess = (e) => resolve(e.target.result);
    req.onerror = (e) => reject(e.target.error);
  });
}

// ── SW Lifecycle ─────────────────────────────────────────────────────────────

self.addEventListener("install", (e) => {
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(self.clients.claim());
  // Start the reminder check loop once active
  checkAndFireReminders();
});

// ── Message handler (from sw-register.js) ────────────────────────────────────

self.addEventListener("message", (e) => {
  const { type, payload } = e.data || {};

  if (type === "SCHEDULE_REMINDER") {
    e.waitUntil(
      saveReminder(payload).then(() => {
        // Acknowledge back to the page
        e.source &&
          e.source.postMessage({ type: "REMINDER_SAVED", id: payload.id });
      }),
    );
  }

  if (type === "CANCEL_REMINDER") {
    e.waitUntil(deleteReminder(payload.id));
  }

  if (type === "GET_REMINDERS") {
    e.waitUntil(
      getAllReminders().then((reminders) => {
        e.source && e.source.postMessage({ type: "REMINDERS_LIST", reminders });
      }),
    );
  }
});

// ── Periodic reminder check ───────────────────────────────────────────────────
// Checks every 30 seconds whether any reminder should fire.
// This loop runs as long as the SW is active (browser open).

async function checkAndFireReminders() {
  const reminders = await getAllReminders();
  const now = Date.now();

  for (const reminder of reminders) {
    if (reminder.fireAt <= now) {
      await fireNotification(reminder);
      await deleteReminder(reminder.id);
    }
  }

  // Reschedule check every 30 s
  setTimeout(checkAndFireReminders, 30_000);
}

async function fireNotification(reminder) {
  const title = "🔴 Starting now!";
  const body = (reminder.comp ? reminder.comp + " · " : "") + reminder.title;

  await self.registration.showNotification(title, {
    body,
    icon: "/static/favicon.ico",
    badge: "/static/favicon.ico",
    tag: "event-" + reminder.id,
    data: { url: reminder.url || "/" },
    requireInteraction: false,
    vibrate: [200, 100, 200],
  });
}

// ── Notification click ────────────────────────────────────────────────────────

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const targetUrl = (e.notification.data && e.notification.data.url) || "/";

  e.waitUntil(
    self.clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then((clients) => {
        // Focus existing tab if already open
        for (const client of clients) {
          if (client.url === targetUrl && "focus" in client) {
            return client.focus();
          }
        }
        // Otherwise open a new tab
        return self.clients.openWindow(targetUrl);
      }),
  );
});
