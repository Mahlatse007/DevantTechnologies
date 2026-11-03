(function () {
  "use strict";
  if (document.body.dataset.page !== "tutor") return;

  const subjectsMsg = document.getElementById("subjects-msg");
  const slotMsg = document.getElementById("slot-msg");
  const scheduleMsg = document.getElementById("schedule-msg");

  function el(tag, cls, text) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;
    return e;
  }
  function tile(id, value) {
    document.getElementById(id).textContent = String(value);
  }
  function dayLabel(d) {
    return d.toLocaleDateString("en-ZA", {
      weekday: "long",
      day: "numeric",
      month: "long",
    });
  }
  function timeLabel(d) {
    return d.toLocaleTimeString("en-ZA", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  }
  function pad(n) {
    return String(n).padStart(2, "0");
  }
  function localValue(d) {
    return (
      d.getFullYear() +
      "-" +
      pad(d.getMonth() + 1) +
      "-" +
      pad(d.getDate()) +
      "T" +
      pad(d.getHours()) +
      ":" +
      pad(d.getMinutes())
    );
  }

  // ---- subjects ----
  function countSubjects() {
    tile(
      "tile-subjects",
      document.querySelectorAll("#subject-checks input:checked").length,
    );
  }

  async function loadSubjects() {
    const box = document.getElementById("subject-checks");
    const r = await api("/api/tutor/subjects");
    box.replaceChildren();
    if (!r.ok) return show(subjectsMsg, errorText(r), false);
    r.data.forEach(function (s) {
      const label = el("label");
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.value = String(s.id);
      cb.checked = s.selected;
      cb.addEventListener("change", countSubjects);
      label.appendChild(cb);
      label.appendChild(el("span", null, s.name));
      box.appendChild(label);
    });
    countSubjects();
  }

  document
    .getElementById("save-subjects")
    .addEventListener("click", async function () {
      const ids = Array.from(
        document.querySelectorAll("#subject-checks input:checked"),
      ).map(function (i) {
        return Number(i.value);
      });
      const r = await api("/api/tutor/subjects", "PUT", { subject_ids: ids });
      show(subjectsMsg, r.ok ? r.data.message : errorText(r), r.ok);
    });

  // ---- add availability ----
  const when = document.getElementById("slot-when");
  when.min = localValue(new Date(Date.now() + 3600 * 1000));

  document
    .getElementById("slot-form")
    .addEventListener("submit", async function (e) {
      e.preventDefault();
      slotMsg.textContent = "";
      if (!when.value)
        return show(slotMsg, "Choose a date and start time.", false);

      const weeks = Number(document.getElementById("slot-repeat").value);
      const first = new Date(when.value);
      let added = 0,
        skipped = 0,
        failed = null;
      for (let i = 0; i < weeks; i++) {
        const d = new Date(first.getTime());
        d.setDate(d.getDate() + 7 * i);
        const r = await api("/api/tutor/slots", "POST", {
          starts_at: d.toISOString(),
        });
        if (r.ok) added++;
        else if (r.status === 409) skipped++;
        else {
          failed = r;
          break;
        }
      }
      if (failed) {
        const text =
          failed.status === 422
            ? "Choose a time between 1 hour and 90 days from now."
            : errorText(failed);
        show(
          slotMsg,
          added ? "Added " + added + ", then stopped: " + text : text,
          false,
        );
      } else {
        show(
          slotMsg,
          "Added " +
            added +
            (added === 1 ? " time" : " times") +
            (skipped ? " (" + skipped + " already existed)" : "") +
            ".",
          added > 0,
        );
      }
      loadSchedule();
    });

  // ---- schedule ----
  async function loadSchedule() {
    const box = document.getElementById("schedule");
    const r = await api("/api/tutor/slots");
    box.replaceChildren();
    if (!r.ok) return show(scheduleMsg, errorText(r), false);

    const booked = r.data.filter(function (s) {
      return s.booked;
    }).length;
    tile("tile-booked", booked);
    tile("tile-open", r.data.length - booked);

    if (r.data.length === 0) {
      box.appendChild(
        el("p", "muted", "No times yet. Add your available times above."),
      );
      return;
    }
    r.data.forEach(function (s) {
      const d = new Date(s.starts_at);
      const row = el("div", "lesson");
      const left = el("div");
      left.appendChild(el("b", null, dayLabel(d) + ", " + timeLabel(d)));
      const meta = el("span", "meta");
      if (s.booked) {
        meta.appendChild(
          document.createTextNode(s.subject + " with " + s.student),
        );
        if (s.student_contact) {
          meta.appendChild(document.createTextNode(" \u00b7 "));
          const a = el("a", null, s.student_contact);
          a.href = "tel:" + s.student_contact.replace(/\s+/g, "");
          meta.appendChild(a);
        }
      } else {
        meta.textContent = "Open: students can book this time";
      }
      left.appendChild(meta);
      row.appendChild(left);

      const side = el("div", "side");
      side.appendChild(
        el(
          "span",
          s.booked ? "pill on" : "pill open",
          s.booked ? "Booked" : "Open",
        ),
      );
      const remove = el(
        "button",
        "btn small secondary",
        s.booked ? "Cancel lesson" : "Remove",
      );
      remove.type = "button";
      remove.addEventListener("click", async function () {
        const question = s.booked
          ? "Cancel this booked lesson? The student will need to book another time."
          : "Remove this time?";
        if (!window.confirm(question)) return;
        const res = await api("/api/tutor/slots/" + s.id, "DELETE");
        show(scheduleMsg, res.ok ? res.data.message : errorText(res), res.ok);
        loadSchedule();
      });
      side.appendChild(remove);
      row.appendChild(side);
      box.appendChild(row);
    });
  }

  loadSubjects();
  loadSchedule();
})();
