// ================================
// LearnHub Frontend JavaScript
// ================================


// ================================
// Mobile Menu
// ================================

function toggleMobileMenu() {

    const mobileMenu = document.getElementById("mobile-menu");

    if (mobileMenu) {
        mobileMenu.classList.toggle("hidden");
    }
}


// Close mobile menu when clicking a link
document.querySelectorAll("#mobile-menu a").forEach(link => {

    link.addEventListener("click", () => {

        const mobileMenu = document.getElementById("mobile-menu");

        if (mobileMenu) {
            mobileMenu.classList.add("hidden");
        }

    });

});


// ================================
// Smooth Scrolling
// ================================

document.querySelectorAll('a[href^="#"]').forEach(anchor => {

    anchor.addEventListener("click", function (event) {

        event.preventDefault();

        const target = document.querySelector(
            this.getAttribute("href")
        );

        if (target) {

            target.scrollIntoView({
                behavior: "smooth",
                block: "start"
            });

        }

    });

});


// ================================
// Navbar Scroll Effect
// ================================

window.addEventListener("scroll", () => {

    const nav = document.querySelector("nav");

    if (nav) {

        if (window.scrollY > 50) {
            nav.classList.add("shadow-md");
        } else {
            nav.classList.remove("shadow-md");
        }

    }

});


// ================================
// Registration
// ================================

async function registerUser(event) {

    // Stop the normal HTML form submission
    event.preventDefault();

    // Get passwords
    const password = document.getElementById("password").value;
    const confirmPassword = document.getElementById("confirmPassword").value;

    // Check that passwords match
    if (password !== confirmPassword) {
        alert("Passwords do not match.");
        return;
    }


    // Collect registration data
    const user = {

        firstname: document.getElementById("firstname").value,
        lastname: document.getElementById("lastname").value,
        idnumber: document.getElementById("idnumber").value,
        email: document.getElementById("email").value,
        role: document.getElementById("role").value,
        username: document.getElementById("username").value,
        address: document.getElementById("address").value,
        contactnumber: document.getElementById("contactnumber").value,
        password: password
    };

    try {

        // Send data to FastAPI
        const response = await fetch(
            "http://127.0.0.1:8000/users/add-users",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify(user)
            }
        );

        
        // Get API response
        const data = await response.json();
        //console.log("API response:", data);

        // Check whether registration succeeded
        if (!response.ok) {
            console.error("Registration failed:", data);
            alert("Registration failed.");
            return;
        } else {
            // Success
            alert("Registration successful!");
        }

        // Clear form
        document.querySelector("form").reset();


    } catch (error) {
        console.error("Error registering user:", error);
        alert("Could not connect to the LearnHub API.");
    }       
}

// =================================
// Login 
// =================================

async function loginUser(event) {

    event.preventDefault();

    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    const button = document.getElementById("login-button");
    const message = document.getElementById("login-message");

    button.disabled = true;
    message.textContent = "Checking your details...";
    message.style.color = "";

    try {

        const response = await fetch(
            "http://127.0.0.1:8000/login",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    email: email,
                    password: password
                })
            }
        );

        const data = await response.json();

        if (!response.ok) {
            message.textContent = data.detail || "Login failed.";
            message.style.color = "red";
            return;
        }

        message.textContent = "Login successful!";
        message.style.color = "green";

        console.log("Logged-in user:", data.user);

        if (data.user.role === "Student") {
            window.location.href = "/student";
        } else if (data.user.role === "Tutor") {
            window.location.href = "/tutor";
        } else if (data.user.role === "Admin") {
            window.location.href = "/admin";
        }

    } catch (error) {

        console.error("Error logging in:", error);

        alert("Could not connect to LearnHub API.");
    }
}
 
// ================================
// Get Users
// ================================

async function getUsers() {

    try {

        const response = await fetch(
            "http://127.0.0.1:8000/users"
        );


        const users = await response.json();


        console.log("Users:", users);


    } catch (error) {

        console.error(
            "Error getting users:",
            error
        );

    }

}


getUsers();


// ================================
// Website Loaded
// ================================
"use strict";

// ---------- helpers ----------
async function api(path, method, body) {
    try {
        const res = await fetch(path, {
            method: method || "GET",
            headers: body ? { "Content-Type": "application/json" } : {},
            body: body ? JSON.stringify(body) : undefined,
            credentials: "same-origin",
        });
        let data = {};
        try { data = await res.json(); } catch (e) { /* no JSON body */ }
        return { ok: res.ok, status: res.status, data: data };
    } catch (e) {
        return { ok: false, status: 0, data: { detail: "Could not reach the server. Check your connection." } };
    }
}

function show(el, text, ok) {
    el.textContent = text;
    el.className = "msg " + (ok ? "ok" : "error");
}

const FIELD_NAMES = {
    first_name: "first name", last_name: "last name", email: "email", username: "username",
    contact_number: "contact number", role: "role", password: "password", consent: "consent",
    name: "name", message: "message",
};

function errorText(r) {
    let text = (r.data && typeof r.data.detail === "string") ? r.data.detail : "Something went wrong. Please try again.";
    if (r.status === 422 && Array.isArray(r.data.fields) && r.data.fields.length) {
        text += " Check: " + r.data.fields.map(function(f) { return FIELD_NAMES[f] || f; }).join(", ") + ".";
    }
    return text;
}

function val(id) { return document.getElementById(id).value; }

// Runs a form submit with a disabled button and an inline message.
function handleForm(form, onSubmit) {
    const msg = form.querySelector(".msg");
    const btn = form.querySelector("button[type=submit]");
    form.addEventListener("submit", async function(e) {
        e.preventDefault();
        msg.textContent = "";
        if (!form.checkValidity()) { form.reportValidity(); return; }
        btn.disabled = true;
        try { await onSubmit(msg); } finally { btn.disabled = false; }
    });
}

// ---------- login ----------
const loginForm = document.getElementById("login-form");
if (loginForm) {
    handleForm(loginForm, async function(msg) {
        const r = await api("/api/login", "POST", { email: val("email"), password: val("password") });
        if (!r.ok) return show(msg, errorText(r), false);
        window.location.href = r.data.redirect;
    });
}

// ---------- register ----------
const registerForm = document.getElementById("register-form");
if (registerForm) {
    handleForm(registerForm, async function(msg) {
        if (val("password") !== val("confirm")) return show(msg, "Passwords do not match.", false);
        if (!/[A-Za-z]/.test(val("password")) || !/\d/.test(val("password"))) {
            return show(msg, "Password must contain letters and numbers.", false);
        }
        const r = await api("/api/register", "POST", {
            first_name: val("first_name"), last_name: val("last_name"), email: val("email"),
            username: val("username"), contact_number: val("contact_number"), role: val("role"),
            password: val("password"), consent: document.getElementById("consent").checked,
        });
        if (!r.ok) return show(msg, errorText(r), false);
        show(msg, "Account created. Taking you to the login page...", true);
        setTimeout(function() { window.location.href = "/login"; }, 1200);
    });
}

// ---------- contact ----------
const contactForm = document.getElementById("contact-form");
if (contactForm) {
    handleForm(contactForm, async function(msg) {
        const r = await api("/api/contact", "POST", {
            name: val("c-name"), email: val("c-email"), message: val("c-message"), website: val("c-website"),
        });
        if (!r.ok) return show(msg, errorText(r), false);
        show(msg, r.data.message, true);
        contactForm.reset();
    });
}

// ---------- dashboards ----------
const page = document.body.dataset.page;

const logoutBtn = document.getElementById("logout");
if (logoutBtn) {
    logoutBtn.addEventListener("click", async function() {
        await api("/api/logout", "POST");
        window.location.href = "/login";
    });
}

function cell(row, text) {
    const td = document.createElement("td");
    td.textContent = text;  // textContent, never innerHTML: user input can't run as code
    row.appendChild(td);
    return td;
}

function pillCell(row, text, cls) {
    const td = document.createElement("td");
    const span = document.createElement("span");
    span.className = "pill " + cls;
    span.textContent = text;
    td.appendChild(span);
    row.appendChild(td);
}

function setText(id, value) { document.getElementById(id).textContent = String(value); }

function fmtDate(iso) { return new Date(iso).toLocaleString("en-ZA", { dateStyle: "medium", timeStyle: "short" }); }

async function loadAdmin() {
    const msg = document.getElementById("admin-msg");
    const usersBody = document.getElementById("users-body");
    const msgsBody = document.getElementById("messages-body");

    const [u, m] = await Promise.all([api("/api/admin/users"), api("/api/admin/messages")]);
    if (u.status === 401 || u.status === 403) { window.location.href = "/login"; return; }
    if (!u.ok) return show(msg, errorText(u), false);

    setText("tile-total", u.data.length);
    setText("tile-students", u.data.filter(function(x) { return x.role === "Student"; }).length);
    setText("tile-tutors", u.data.filter(function(x) { return x.role === "Tutor"; }).length);
    setText("tile-messages", m.ok ? m.data.length : 0);

    usersBody.replaceChildren();
    u.data.forEach(function(user) {
        const tr = document.createElement("tr");
        cell(tr, user.first_name + " " + user.last_name);
        cell(tr, user.email);
        cell(tr, user.contact_number);
        pillCell(tr, user.role, user.role.toLowerCase());
        pillCell(tr, user.is_active ? "Active" : "Deactivated", user.is_active ? "on" : "off");
        cell(tr, fmtDate(user.created_at));
        const action = document.createElement("td");
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "btn small secondary";
        btn.textContent = user.is_active ? "Deactivate" : "Reactivate";
        btn.addEventListener("click", async function() {
            const r = await api("/api/admin/users/" + user.id + "/toggle-active", "POST");
            if (!r.ok) return show(msg, errorText(r), false);
            loadAdmin();
        });
        action.appendChild(btn);
        tr.appendChild(action);
        usersBody.appendChild(tr);
    });

    msgsBody.replaceChildren();
    if (m.ok && m.data.length === 0) {
        const tr = document.createElement("tr");
        const td = cell(tr, "No messages yet.");
        td.colSpan = 4;
        msgsBody.appendChild(tr);
    } else if (m.ok) {
        m.data.forEach(function(item) {
            const tr = document.createElement("tr");
            cell(tr, fmtDate(item.created_at));
            cell(tr, item.name);
            cell(tr, item.email);
            cell(tr, item.message);
            msgsBody.appendChild(tr);
        });
    }
}

async function loadDashboard() {
    const r = await api("/api/me");
    if (!r.ok) { window.location.href = "/login"; return; }
    const welcome = document.getElementById("welcome");
    if (welcome) welcome.textContent = "Welcome, " + r.data.first_name;
    if (page === "admin") loadAdmin();
}

if (page === "student" || page === "tutor" || page === "admin") loadDashboard();

