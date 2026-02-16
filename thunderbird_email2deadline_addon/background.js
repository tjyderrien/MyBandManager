async function getAllSelectedMessages() {
  const tab = await browser.mailTabs.getCurrent();
  let list = await browser.mailTabs.getSelectedMessages(tab.id);
  const all = [...(list.messages || [])];

  while (list.id) {
    list = await browser.messages.continueList(list.id);
    all.push(...(list.messages || []));
  }

  return all;
}

async function gatherEventsFromSelection() {
  const selectedMessages = await getAllSelectedMessages();
  const events = [];

  for (const msg of selectedMessages) {
    const full = await browser.messages.getFull(msg.id);
    const bodyText = DeadlineExtractor.collectBodyTextFromFullMessage(full);
    const fromHeaders = (full.headers && full.headers.subject && full.headers.subject[0]) || "";
    const subject = msg.subject || fromHeaders;

    const extracted = DeadlineExtractor.extractEventsFromEmail({
      subject,
      text: bodyText,
      receivedAt: msg.date
    });

    events.push(...extracted);
  }

  return events;
}

function createIcsDataUrl(icsText) {
  return `data:text/calendar;charset=utf-8,${encodeURIComponent(icsText)}`;
}

async function notify(title, message) {
  await browser.notifications.create({
    type: "basic",
    title,
    message,
    iconUrl: browser.runtime.getURL("icon.svg")
  });
}

function nowStamp() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}_${String(d.getHours()).padStart(2, "0")}-${String(d.getMinutes()).padStart(2, "0")}`;
}

browser.browserAction.onClicked.addListener(async () => {
  try {
    const events = await gatherEventsFromSelection();

    if (!events.length) {
      await notify("Email2Deadline", "No deadline found in selected emails.");
      return;
    }

    const settings = await browser.storage.local.get({
      calendarName: "Email Deadlines"
    });

    const ics = DeadlineExtractor.buildICS(events, settings.calendarName);

    await browser.downloads.download({
      url: createIcsDataUrl(ics),
      filename: `email-deadlines-${nowStamp()}.ics`,
      saveAs: true,
      conflictAction: "uniquify"
    });

    await notify("Email2Deadline", `Exported ${events.length} event(s) to ICS.`);
  } catch (error) {
    console.error("Email2Deadline failed", error);
    await notify("Email2Deadline", `Failed: ${error && error.message ? error.message : String(error)}`);
  }
});
