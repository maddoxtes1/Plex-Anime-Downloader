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
let appInfo = null;

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

async function loadTheme() {
  if (!currentServer) return null;
  
  try {
    const resp = await fetch(currentServer + "/api/theme");
    if (resp.ok) {
      const data = await resp.json();
      if (data.ok && data.colors) {
        applyTheme(data.colors);
        return data.colors;
      }
    }
  } catch (e) {
    console.error("Erreur lors du chargement du thème:", e);
  }
  return null;
}

function applyTheme(colors) {
  const root = document.documentElement;
  root.style.setProperty('--bg-primary', colors.bg_primary);
  root.style.setProperty('--bg-secondary', colors.bg_secondary);
  root.style.setProperty('--bg-card', colors.bg_card);
  root.style.setProperty('--accent-primary', colors.accent_primary);
  root.style.setProperty('--accent-secondary', colors.accent_secondary);
  root.style.setProperty('--accent-tertiary', colors.accent_tertiary);
  root.style.setProperty('--text-primary', colors.text_primary);
  root.style.setProperty('--text-secondary', colors.text_secondary);
  root.style.setProperty('--border', colors.border);
  root.style.setProperty('--success', colors.success);
  root.style.setProperty('--error', colors.error);
  
  // Appliquer les couleurs au body
  document.body.style.background = `linear-gradient(135deg, ${colors.bg_primary} 0%, ${colors.bg_secondary} 100%)`;
  document.body.style.color = colors.text_primary;
  
  // Appliquer les couleurs aux sections
  const sections = document.querySelectorAll('.section');
  sections.forEach(section => {
    section.style.background = colors.bg_card;
    section.style.color = colors.text_primary;
    section.style.border = `1px solid ${colors.border}`;
  });
  
  // Appliquer les couleurs aux boutons
  const buttons = document.querySelectorAll('button');
  buttons.forEach(button => {
    if (!button.classList.contains('secondary')) {
      button.style.background = `linear-gradient(135deg, ${colors.accent_primary}, ${colors.accent_secondary})`;
    }
  });
  
  // Appliquer les couleurs aux inputs
  const inputs = document.querySelectorAll('input');
  inputs.forEach(input => {
    input.style.background = colors.bg_card;
    input.style.border = `1px solid ${colors.border}`;
    input.style.color = colors.text_primary;
  });
  
  // Appliquer les couleurs aux liens d'accès rapide
  const quickLinks = document.querySelectorAll('#quick-access a');
  quickLinks.forEach(link => {
    link.style.background = `rgba(${hexToRgb(colors.accent_primary)}, 0.1)`;
    link.style.border = `1px solid rgba(${hexToRgb(colors.accent_primary)}, 0.3)`;
    link.addEventListener('mouseenter', () => {
      link.style.background = `rgba(${hexToRgb(colors.accent_primary)}, 0.2)`;
      link.style.transform = 'translateY(-2px)';
    });
    link.addEventListener('mouseleave', () => {
      link.style.background = `rgba(${hexToRgb(colors.accent_primary)}, 0.1)`;
      link.style.transform = 'translateY(0)';
    });
  });
}

function hexToRgb(hex) {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result ? 
    `${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}` : 
    '0, 212, 255';
}

async function loadAppInfo() {
  if (!currentServer) return null;
  
  try {
    const resp = await fetch(currentServer + "/api/app-info");
    if (resp.ok) {
      const data = await resp.json();
      if (data.ok) {
        return data;
      }
    }
  } catch (e) {
    console.error("Erreur lors du chargement des infos de l'app:", e);
  }
  // Valeurs par défaut
  return {
    app_name: "Plex Anime Downloader",
    local_dashboard_port: 5001,
    anime_sama_url: "https://anime-sama.eu"
  };
}

async function loadDashboard() {
  if (!currentServer || !currentUser) {
    showView("login");
    return;
  }

  // Charger le thème
  await loadTheme();

  // Charger les infos de l'application
  appInfo = await loadAppInfo();
  
  // Mettre à jour le nom de l'application
  const appNameEl = document.getElementById("app-name");
  if (appNameEl && appInfo) {
    appNameEl.textContent = appInfo.app_name || "Plex Anime Downloader";
    // Mettre à jour aussi le titre de la page
    document.title = appInfo.app_name || "Plex Anime Downloader";
  }
  
  // Mettre à jour le lien du dashboard local
  const linkDashboard = document.getElementById("link-dashboard");
  if (linkDashboard && currentServer) {
    // Extraire l'URL de base (sans le port API)
    try {
      const url = new URL(currentServer);
      const dashboardUrl = `${url.protocol}//${url.hostname}:${appInfo?.local_dashboard_port || 5001}`;
      linkDashboard.href = dashboardUrl;
    } catch (e) {
      // Si l'URL n'est pas valide, utiliser localhost
      linkDashboard.href = `http://localhost:${appInfo?.local_dashboard_port || 5001}`;
    }
  }
  
  // Mettre à jour le lien anime-sama
  const linkAnimeSama = document.getElementById("link-anime-sama");
  if (linkAnimeSama && appInfo) {
    linkAnimeSama.href = appInfo.anime_sama_url || "https://anime-sama.eu";
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
    
    // Extraire l'IP du serveur depuis l'URL
    let serverDisplay = currentServer;
    try {
      const url = new URL(currentServer);
      if (url.hostname === 'localhost' || url.hostname === '127.0.0.1') {
        serverDisplay = 'localhost';
      } else {
        serverDisplay = url.hostname;
      }
    } catch (e) {
      // Si l'URL n'est pas valide, utiliser tel quel
    }
    
    dashboardInfo.textContent = `Connecté sur ${serverDisplay}`;

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
      // Charger le thème après connexion réussie
      await loadTheme();
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


