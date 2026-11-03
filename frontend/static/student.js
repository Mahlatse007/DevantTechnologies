(function () {
  "use strict";
  if (document.body.dataset.page !== "student") return;

  const msg = document.getElementById("book-msg");
  const state = { subject: null, tutor: null, slot: null };

  function el(tag, cls, text) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;
    return e;
  }
  function reveal(id, on) {
    document.getElementById(id).classList.toggle("hidden", !on);
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

  function choose(container, btn) {
    container.querySelectorAll("button").forEach(function (b) {
      b.classList.remove("selected");
      b.setAttribute("aria-pressed", "false");
    });
    btn.classList.add("selected");
    btn.setAttribute("aria-pressed", "true");
  }

  function optionButton(cls) {
    const b = el("button", cls);
    b.type = "button";
    b.setAttribute("aria-pressed", "false");
    return b;
  }

  // ---- step 1: subjects ----
  async function loadSubjects() {
    const box = document.getElementById("subject-list");
    const r = await api("/api/subjects");
    if (!r.ok) return show(msg, errorText(r), false);
    r.data.forEach(function (s) {
      const b = optionButton("chip");
      b.textContent = s.name;
      b.addEventListener("click", function () {
        choose(box, b);
        state.subject = s;
        state.tutor = null;
        state.slot = null;
        loadTutors();
      });
      box.appendChild(b);
    });
  }

  // ---- step 2: tutors ----
  async function loadTutors() {
    msg.textContent = "";
    reveal("step-slot", false);
    reveal("step-confirm", false);
    const box = document.getElementById("tutor-list");
    box.replaceChildren();
    reveal("step-tutor", true);

    const r = await api("/api/student/tutors?subject_id=" + state.subject.id);
    if (!r.ok) return show(msg, errorText(r), false);
    if (r.data.length === 0) {
      box.appendChild(
        el(
          "p",
          "muted",
          "No tutors have open times for " +
            state.subject.name +
            " yet. Please check back soon or contact us.",
        ),
      );
      return;
    }
    r.data.forEach(function (t) {
      const b = optionButton("choice");
      b.appendChild(el("strong", null, t.name));
      b.appendChild(
        el(
          "span",
          null,
          t.open_slots + (t.open_slots === 1 ? " open time" : " open times"),
        ),
      );
      b.addEventListener("click", function () {
        choose(box, b);
        state.tutor = t;
        state.slot = null;
        loadSlots();
      });
      box.appendChild(b);
    });
  }

  // ---- step 3: times ----
  async function loadSlots() {
    reveal("step-confirm", false);
    const box = document.getElementById("slot-list");
    box.replaceChildren();
    reveal("step-slot", true);

    const r = await api(
      "/api/student/slots?subject_id=" +
        state.subject.id +
        "&tutor_id=" +
        state.tutor.id,
    );
    if (!r.ok) return show(msg, errorText(r), false);
    if (r.data.length === 0) {
      box.appendChild(el("p", "muted", "No open times left for this tutor."));
      return;
    }
    let lastDay = "",
      row = null;
    r.data.forEach(function (s) {
      const d = new Date(s.starts_at);
      const label = dayLabel(d);
      if (label !== lastDay) {
        box.appendChild(el("h4", "day", label));
        row = el("div", "chips");
        box.appendChild(row);
        lastDay = label;
      }
      const b = optionButton("chip");
      b.textContent = timeLabel(d);
      b.addEventListener("click", function () {
        choose(box, b);
        state.slot = { id: s.id, date: d };
        document.getElementById("summary").textContent =
          state.subject.name +
          " with " +
          state.tutor.name +
          " on " +
          label +
          " at " +
          timeLabel(d) +
          " (1 hour)";
        reveal("step-confirm", true);
      });
      row.appendChild(b);
    });
  }

  // ---- confirm ----
  function resetWizard() {
    state.subject = state.tutor = state.slot = null;
    reveal("step-tutor", false);
    reveal("step-slot", false);
    reveal("step-confirm", false);
    const box = document.getElementById("subject-list");
    box.querySelectorAll("button").forEach(function (b) {
      b.classList.remove("selected");
      b.setAttribute("aria-pressed", "false");
    });
  }

  document
    .getElementById("confirm-btn")
    .addEventListener("click", async function () {
      if (!state.slot) return;
      const btn = this;
      btn.disabled = true;
      const r = await api("/api/student/bookings", "POST", {
        slot_id: state.slot.id,
        subject_id: state.subject.id,
      });
      btn.disabled = false;
      if (!r.ok) {
        show(msg, errorText(r), false);
        if (r.status === 409 || r.status === 404) {
          state.slot = null;
          reveal("step-confirm", false);
          loadSlots();
        }
        return;
      }
      resetWizard();
      show(msg, "Lesson booked! You'll find it under My lessons.", true);
      loadLessons();
    });

  // ---- my lessons ----
  async function loadLessons() {
    const box = document.getElementById("my-lessons");
    const r = await api("/api/student/bookings");
    box.replaceChildren();
    if (!r.ok) {
      box.appendChild(el("p", "msg error", errorText(r)));
      return;
    }
    if (r.data.length === 0) {
      box.appendChild(el("p", "muted", "You haven't booked any lessons yet."));
      return;
    }
    const now = Date.now(),
      hour = 3600 * 1000;
    const upcoming = r.data
      .filter(function (b) {
        return new Date(b.starts_at).getTime() > now - hour;
      })
      .reverse();
    const past = r.data.filter(function (b) {
      return new Date(b.starts_at).getTime() <= now - hour;
    });

    upcoming.concat(past).forEach(function (b) {
      const d = new Date(b.starts_at);
      const isUpcoming = d.getTime() > now - hour;
      const row = el("div", "lesson");
      const left = el("div");
      left.appendChild(el("b", null, dayLabel(d) + ", " + timeLabel(d)));
      left.appendChild(el("span", "meta", b.subject + " with " + b.tutor));
      row.appendChild(left);

      const side = el("div", "side");
      side.appendChild(
        el(
          "span",
          isUpcoming ? "pill on" : "pill open",
          isUpcoming ? "Upcoming" : "Completed",
        ),
      );
      if (d.getTime() - now > 2 * hour) {
        const cancel = el("button", "btn small secondary", "Cancel");
        cancel.type = "button";
        cancel.addEventListener("click", async function () {
          if (!window.confirm("Cancel this lesson?")) return;
          const res = await api("/api/student/bookings/" + b.id, "DELETE");
          show(msg, res.ok ? res.data.message : errorText(res), res.ok);
          loadLessons();
        });
        side.appendChild(cancel);
      }
      row.appendChild(side);
      box.appendChild(row);
    });
  }

  loadSubjects();
  loadLessons();
})();
