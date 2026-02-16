(function () {
  const MONTHS = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december"
  ];

  const KEYWORDS = /(deadline|due|submit|submission|deliver|delivery|by\s+|before\s+)/i;

  function stripHtml(html) {
    return (html || "")
      .replace(/<style[\s\S]*?<\/style>/gi, " ")
      .replace(/<script[\s\S]*?<\/script>/gi, " ")
      .replace(/<[^>]+>/g, " ")
      .replace(/&nbsp;/gi, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function extractTextFromPart(part, collector) {
    if (!part) return;

    if (typeof part.body === "string" && part.body.trim()) {
      collector.push(part.contentType && part.contentType.includes("html")
        ? stripHtml(part.body)
        : part.body);
    }

    if (Array.isArray(part.parts)) {
      for (const child of part.parts) {
        extractTextFromPart(child, collector);
      }
    }
  }

  function hasTimeComponent(raw) {
    return /\b\d{1,2}:\d{2}\b/.test(raw) || /\b(am|pm)\b/i.test(raw);
  }

  function normalizeSlashDate(raw) {
    const m = raw.match(/^(\d{1,2})[\/.\-](\d{1,2})[\/.\-](\d{2,4})(.*)$/);
    if (!m) return raw;

    let day = Number(m[1]);
    let month = Number(m[2]);
    let year = Number(m[3]);
    const rest = (m[4] || "").trim();

    if (year < 100) year += 2000;

    if (month > 12 && day <= 12) {
      const tmp = day;
      day = month;
      month = tmp;
    }

    return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}${rest ? " " + rest : ""}`;
  }

  function containsMonthName(raw) {
    const lower = raw.toLowerCase();
    return MONTHS.some((m) => lower.includes(m));
  }

  function parseDate(raw, fallbackYear) {
    const cleaned = raw.replace(/[,.]+$/, "").trim();
    let candidate = cleaned;

    if (/^\d{1,2}[\/.\-]\d{1,2}[\/.\-]\d{2,4}/.test(cleaned)) {
      candidate = normalizeSlashDate(cleaned);
    } else if (/^\d{1,2}[\/.\-]\d{1,2}(\s+|$)/.test(cleaned) && fallbackYear) {
      const m = cleaned.match(/^(\d{1,2})[\/.\-](\d{1,2})(.*)$/);
      candidate = `${fallbackYear}-${String(Number(m[2])).padStart(2, "0")}-${String(Number(m[1])).padStart(2, "0")}${m[3] || ""}`;
    } else if (containsMonthName(cleaned) && !/\b\d{4}\b/.test(cleaned) && fallbackYear) {
      candidate = `${cleaned} ${fallbackYear}`;
    }

    const parsed = new Date(candidate);
    if (Number.isNaN(parsed.getTime())) return null;

    return {
      date: parsed,
      hasTime: hasTimeComponent(cleaned)
    };
  }

  function gatherDateCandidates(text) {
    const regexes = [
      /\b\d{4}-\d{2}-\d{2}(?:[ T]\d{1,2}:\d{2}(?:\s?(?:AM|PM|am|pm))?)?/g,
      /\b\d{1,2}[\/\.-]\d{1,2}[\/\.-]\d{2,4}(?:\s+\d{1,2}:\d{2}(?:\s?(?:AM|PM|am|pm))?)?/g,
      /\b(?:\d{1,2}[\/\.-]\d{1,2})(?:\s+\d{1,2}:\d{2}(?:\s?(?:AM|PM|am|pm))?)?/g,
      /\b(?:mon|tues|wednes|thurs|fri|satur|sun)?(?:day)?,?\s*(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{1,2}(?:,?\s*\d{4})?(?:\s+at\s+\d{1,2}:\d{2}(?:\s?(?:AM|PM|am|pm))?)?/gi,
      /\b\d{1,2}\s+(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)(?:\s+\d{4})?(?:\s+\d{1,2}:\d{2}(?:\s?(?:AM|PM|am|pm))?)?/gi
    ];

    const matches = [];
    for (const regex of regexes) {
      const found = text.match(regex) || [];
      for (const item of found) matches.push(item.trim());
    }
    return [...new Set(matches)];
  }

  function lines(text) {
    return text
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean);
  }

  function createSummary(line, subject) {
    const compressed = line.replace(/\s+/g, " ").trim();
    if (compressed.length >= 12 && compressed.length <= 120) return compressed;
    if (subject) return `Deadline: ${subject}`;
    return "Email deadline";
  }

  function extractEventsFromEmail({ subject, text, receivedAt }) {
    const eventList = [];
    const messageLines = lines(text);
    const fallbackYear = receivedAt ? new Date(receivedAt).getFullYear() : new Date().getFullYear();

    for (const line of messageLines) {
      if (!KEYWORDS.test(line)) continue;
      const dateCandidates = gatherDateCandidates(line);
      if (!dateCandidates.length) continue;

      for (const raw of dateCandidates) {
        const parsed = parseDate(raw, fallbackYear);
        if (!parsed) continue;

        const start = new Date(parsed.date);
        const end = new Date(parsed.date);
        if (parsed.hasTime) {
          end.setHours(end.getHours() + 1);
        } else {
          end.setDate(end.getDate() + 1);
        }

        eventList.push({
          summary: createSummary(line, subject),
          start,
          end,
          allDay: !parsed.hasTime,
          sourceSubject: subject || "(no subject)"
        });
      }
    }

    if (eventList.length) return dedupe(eventList);

    if (KEYWORDS.test(subject || "")) {
      const fallbackCandidates = gatherDateCandidates(text).slice(0, 3);
      for (const raw of fallbackCandidates) {
        const parsed = parseDate(raw, fallbackYear);
        if (!parsed) continue;
        const start = new Date(parsed.date);
        const end = new Date(parsed.date);
        if (parsed.hasTime) end.setHours(end.getHours() + 1);
        else end.setDate(end.getDate() + 1);

        eventList.push({
          summary: createSummary(subject || "Email deadline", subject),
          start,
          end,
          allDay: !parsed.hasTime,
          sourceSubject: subject || "(no subject)"
        });
      }
    }

    return dedupe(eventList);
  }

  function dedupe(events) {
    const seen = new Set();
    return events.filter((ev) => {
      const key = [ev.summary, ev.start.toISOString(), ev.end.toISOString(), ev.allDay].join("|");
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  function toICSDateTime(date) {
    const y = date.getUTCFullYear();
    const m = String(date.getUTCMonth() + 1).padStart(2, "0");
    const d = String(date.getUTCDate()).padStart(2, "0");
    const hh = String(date.getUTCHours()).padStart(2, "0");
    const mm = String(date.getUTCMinutes()).padStart(2, "0");
    const ss = String(date.getUTCSeconds()).padStart(2, "0");
    return `${y}${m}${d}T${hh}${mm}${ss}Z`;
  }

  function toICSDate(date) {
    const y = date.getUTCFullYear();
    const m = String(date.getUTCMonth() + 1).padStart(2, "0");
    const d = String(date.getUTCDate()).padStart(2, "0");
    return `${y}${m}${d}`;
  }

  function escapeICS(value) {
    return String(value || "")
      .replace(/\\/g, "\\\\")
      .replace(/\n/g, "\\n")
      .replace(/,/g, "\\,")
      .replace(/;/g, "\\;");
  }

  function buildICS(events, calendarName) {
    const now = new Date();
    const lines = [
      "BEGIN:VCALENDAR",
      "VERSION:2.0",
      "PRODID:-//Email2Deadline//Thunderbird Add-on//EN",
      "CALSCALE:GREGORIAN",
      `X-WR-CALNAME:${escapeICS(calendarName || "Email Deadlines")}`
    ];

    for (const [idx, event] of events.entries()) {
      const uid = `${now.getTime()}.${idx}@email2deadline.local`;
      lines.push("BEGIN:VEVENT");
      lines.push(`UID:${uid}`);
      lines.push(`DTSTAMP:${toICSDateTime(now)}`);
      lines.push(`SUMMARY:${escapeICS(event.summary)}`);
      lines.push(`DESCRIPTION:${escapeICS(`Source email: ${event.sourceSubject}`)}`);

      if (event.allDay) {
        lines.push(`DTSTART;VALUE=DATE:${toICSDate(event.start)}`);
        lines.push(`DTEND;VALUE=DATE:${toICSDate(event.end)}`);
      } else {
        lines.push(`DTSTART:${toICSDateTime(event.start)}`);
        lines.push(`DTEND:${toICSDateTime(event.end)}`);
      }

      lines.push("END:VEVENT");
    }

    lines.push("END:VCALENDAR");
    return lines.join("\r\n");
  }

  function collectBodyTextFromFullMessage(full) {
    const collector = [];
    extractTextFromPart(full, collector);
    return collector.join("\n").trim();
  }

  this.DeadlineExtractor = {
    buildICS,
    collectBodyTextFromFullMessage,
    extractEventsFromEmail
  };
})();
