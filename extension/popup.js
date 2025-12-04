// Gestion simple de l'UI
const viewServer = document.getElementById("view-server");
const viewLogin = document.getElementById("view-login");
const viewDashboard = document.getElementById("view-dashboard");

const inputServerUrl = document.getElementById("server-url");
const btnTest = document.getElementById("btn-test");
const serverMessage = document.getElementById("server-message");

const inputUser = document.getElementById("login-username");
const inputPass = document.getElementById("login-password");
const btnLogin = document.getElementById("btn-login");
const btnBackServer = document.getElementById("btn-back-server");
const loginMessage = document.getElementById("login-message");

const dashboardTitle = document.getElementById("dashboard-title");
const dashboardMessage = document.getElementById("dashboard-message");
const dashboardInfo = document.getElementById("dashboard-info");
const btnLogout = document.getElementById("btn-logout");
const statusIndicator = document.getElementById("status-indicator");
const statusText = document.getElementById("status-text");

let currentUser = null;
let currentServer = null;
let statusCheckInterval = null;

function showView(name) {
  viewServer.classList.add("hidden");
  viewLogin.classList.add("hidden");
  viewDashboard.classList.add("hidden");

  if (name === "server") viewServer.classList.remove("hidden");
  if (name === "login") viewLogin.classList.remove("hidden");
  if (name === "dashboard") viewDashboard.classList.remove("hidden");
}

function setMessage(el, text, type = "") {
  el.textContent = text || "";
  el.className = "small";
  if (type === "error") el.classList.add("error");
  if (type === "success") el.classList.add("success");
}

async function loadState() {
  const data = await chrome.storage.sync.get(["serverUrl", "lastUser", "isLoggedIn"]);
  if (data.serverUrl) {
    inputServerUrl.value = data.serverUrl;
    currentServer = data.serverUrl;
  }
  if (data.lastUser) {
    currentUser = data.lastUser;
  }
  // Si l'utilisateur était connecté, restaurer la session
  if (data.isLoggedIn && currentUser && currentServer) {
    await loadDashboard();
  }
}

async function saveState() {
  await chrome.storage.sync.set({
    serverUrl: currentServer,
    lastUser: currentUser,
    isLoggedIn: currentUser !== null,
  });
}

async function checkServerStatus() {
  if (!currentServer) {
    updateServerStatus(false, "Aucun serveur configuré");
    return;
  }

  try {
    const resp = await fetch(currentServer + "/api/ping", {
      method: "GET",
      cache: "no-cache",
    });
    if (resp.ok) {
      const data = await resp.json();
      if (data.ok) {
        updateServerStatus(true, "Serveur connecté");
        return;
      }
    }
    updateServerStatus(false, "Serveur non disponible");
  } catch (e) {
    updateServerStatus(false, "Erreur de connexion");
  }
}

function updateServerStatus(connected, text) {
  if (!statusIndicator || !statusText) return;
  statusText.textContent = text;
  statusIndicator.className = "status-indicator " + (connected ? "connected" : "disconnected");
  const statusDot = statusIndicator.querySelector(".status-dot");
  if (statusDot) {
    statusDot.className = "status-dot " + (connected ? "connected" : "disconnected");
  }
}

async function loadDashboard() {
  if (!currentServer || !currentUser) {
    showView("login");
    return;
  }

  // Vérifier le statut du serveur
  await checkServerStatus();
  
  // Démarrer la vérification périodique du statut
  if (statusCheckInterval) {
    clearInterval(statusCheckInterval);
  }
  statusCheckInterval = setInterval(checkServerStatus, 5000); // Vérifier toutes les 5 secondes

  try {
    // Charger le dashboard
    const dashResp = await fetch(
      currentServer + "/api/dashboard?user=" + encodeURIComponent(currentUser)
    );
    const dashData = await dashResp.json();

    const title = dashData?.data?.title || "Dashboard";
    const message =
      dashData?.data?.message || "Bienvenue, aucun détail supplémentaire.";

    dashboardTitle.textContent = title;
    dashboardMessage.textContent = message;
    dashboardInfo.textContent = `Connecté en tant que ${currentUser} sur ${currentServer}`;

    showView("dashboard");
  } catch (e) {
    console.error(e);
    updateServerStatus(false, "Erreur de connexion");
  }
}

btnTest.addEventListener("click", async () => {
  const url = inputServerUrl.value.trim().replace(/\/+$/, "");
  if (!url) {
    setMessage(serverMessage, "Veuillez entrer l'URL du serveur.", "error");
    return;
  }

  setMessage(serverMessage, "Test de connexion en cours...");
  btnTest.disabled = true;

  try {
    const resp = await fetch(url + "/api/ping");
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    const data = await resp.json();
    if (data.ok) {
      currentServer = url;
      await saveState();
      setMessage(serverMessage, "Connexion réussie au serveur.", "success");
      showView("login");
    } else {
      setMessage(serverMessage, "Le serveur a répondu mais pas OK.", "error");
    }
  } catch (e) {
    console.error(e);
    setMessage(
      serverMessage,
      "Impossible de joindre le serveur. Vérifie l'IP / port.",
      "error"
    );
  } finally {
    btnTest.disabled = false;
  }
});

btnBackServer.addEventListener("click", () => {
  showView("server");
});

btnLogin.addEventListener("click", async () => {
  if (!currentServer) {
    setMessage(loginMessage, "Aucun serveur configuré.", "error");
    showView("server");
    return;
  }

  const username = inputUser.value.trim();
  const password = inputPass.value.trim();
  if (!username || !password) {
    setMessage(loginMessage, "Username et mot de passe obligatoires.", "error");
    return;
  }

  btnLogin.disabled = true;
  setMessage(loginMessage, "Connexion en cours...");

  try {
    const resp = await fetch(currentServer + "/api/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ username, password }),
    });

    const data = await resp.json();
    if (!resp.ok || !data.ok) {
      setMessage(
        loginMessage,
        data.error || "Erreur de connexion.",
        "error"
      );
      return;
    }

    currentUser = data.user;
    await saveState();
    setMessage(loginMessage, "Connexion réussie.", "success");

    // Charger le dashboard
    await loadDashboard();
  } catch (e) {
    console.error(e);
    setMessage(loginMessage, "Erreur réseau pendant la connexion.", "error");
  } finally {
    btnLogin.disabled = false;
  }
});

btnLogout.addEventListener("click", async () => {
  currentUser = null;
  await saveState();
  dashboardTitle.textContent = "";
  dashboardMessage.textContent = "";
  dashboardInfo.textContent = "";
  setMessage(loginMessage, "");
  
  // Arrêter la vérification du statut
  if (statusCheckInterval) {
    clearInterval(statusCheckInterval);
    statusCheckInterval = null;
  }
  
  showView("login");
});

(async function init() {
  await loadState();
  if (currentUser && currentServer) {
    // L'utilisateur est déjà connecté, afficher le dashboard
    showView("dashboard");
    await loadDashboard();
  } else if (currentServer) {
    showView("login");
  } else {
    showView("server");
  }
})();


