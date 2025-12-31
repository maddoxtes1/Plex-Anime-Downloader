// Content script pour ajouter des boutons "Add to download" sur les pages anime-sama

// Fonction pour obtenir les informations de l'extension
async function getExtensionConfig() {
  return new Promise(resolve => 
    chrome.storage.sync.get(["serverUrl", "lastUser", "isLoggedIn"], resolve)
  );
}

// ============================================
// SYSTÈME DE CACHE LOCAL (résout Mixed Content)
// ============================================

// Fonction pour obtenir le cache local des animes téléchargés
async function getAnimeCache() {
  return new Promise(resolve => 
    chrome.storage.local.get(["animeList", "cacheTimestamp"], (data) => 
      resolve({
        animeList: new Set(data.animeList || []),
        timestamp: data.cacheTimestamp || 0
      })
    )
  );
}

// Fonction pour sauvegarder le cache local
async function saveAnimeCache(animeList) {
  return new Promise((resolve) => {
    chrome.storage.local.set({
      animeList: Array.from(animeList),
      cacheTimestamp: Date.now()
    }, resolve);
  });
}

// Fonction pour vérifier si un anime existe dans le cache local
async function checkAnimeExistsLocal(animeUrl) {
  const normalizedUrl = normalizeAnimeUrl(animeUrl);
  if (!normalizedUrl) return false;
  
  const cache = await getAnimeCache();
  // Normaliser toutes les URLs du cache pour comparaison
  const normalizedCache = new Set([...cache.animeList].map(url => normalizeAnimeUrl(url)).filter(Boolean));
  return normalizedCache.has(normalizedUrl);
}

// Fonction pour ajouter un anime au cache local
async function addAnimeToCache(animeUrl) {
  const normalizedUrl = normalizeAnimeUrl(animeUrl);
  if (!normalizedUrl) return;
  
  const cache = await getAnimeCache();
  const animeSet = new Set([...cache.animeList].map(url => normalizeAnimeUrl(url)).filter(Boolean));
  animeSet.add(normalizedUrl);
  await saveAnimeCache(animeSet);
}

// Fonction pour supprimer un anime du cache local
async function removeAnimeFromCache(animeUrl) {
  const normalizedUrl = normalizeAnimeUrl(animeUrl);
  if (!normalizedUrl) return;
  
  const cache = await getAnimeCache();
  const animeSet = new Set([...cache.animeList].map(url => normalizeAnimeUrl(url)).filter(Boolean));
  animeSet.delete(normalizedUrl);
  await saveAnimeCache(animeSet);
}

// Fonction pour mettre en queue une action (add/remove) pour synchronisation
async function queueAction(action, animeUrl, day = null) {
  return new Promise((resolve) => {
    chrome.storage.local.get(["actionQueue"], (data) => {
      const queue = data.actionQueue || [];
      queue.push({ action, animeUrl, day, timestamp: Date.now() });
      chrome.storage.local.set({ actionQueue: queue }, resolve);
    });
  });
}

// Fonction pour détecter le jour de la semaine depuis la page (dans le contexte d'une carte)
function detectDayFromPage(cardElement) {
  const days = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"];
  let current = cardElement;
  
  while (current && current !== document.body) {
    if (current.classList?.contains("selectedRow")) {
      const titreJours = current.querySelector(".titreJours");
      if (titreJours) {
        const dayText = titreJours.textContent.trim().toLowerCase();
        const foundDay = days.find(day => dayText.includes(day));
        if (foundDay) return foundDay;
      }
    }
    current = current.parentElement;
  }
  return null;
}

// Fonction pour vérifier si un anime existe (utilise le cache local)
async function checkAnimeExists(animeUrl) {
  const config = await getExtensionConfig();
  if (!config.serverUrl || !config.isLoggedIn) return null;
  return await checkAnimeExistsLocal(animeUrl);
}

// Fonction pour ajouter un anime à la queue (utilise le cache local + queue)
async function addToDownload(animeUrl, cardElement, button) {
  const config = await getExtensionConfig();
  
  if (!config.serverUrl || !config.isLoggedIn) {
    alert("Veuillez vous connecter à l'extension d'abord.");
    return;
  }

  // Vérifier si la saison contient des suffixes non supportés (ex: saison1hs)
  if (hasUnsupportedSeasonSuffix(animeUrl)) {
    const animeName = extractAnimeName(animeUrl);
    showNotification(`${animeName} ne peut pas être ajouté car ce type de saison n'est pas supporté (ex: saison1hs)`, "error");
    return;
  }

  // Vérifier d'abord si l'anime existe déjà dans le cache local
  const alreadyExists = await checkAnimeExistsLocal(animeUrl);
  if (alreadyExists) {
    const animeName = extractAnimeName(animeUrl);
    showNotification(`${animeName} est déjà dans la liste`, "error");
    return;
  }

  // Détecter le jour depuis la page (dans le contexte de la carte)
  // Si cardElement est null, on est sur une page de catalogue, donc day = null
  const day = cardElement ? detectDayFromPage(cardElement) : null;

  // Mettre à jour le cache local immédiatement (optimiste, sera corrigé si échec)
  await addAnimeToCache(animeUrl);
  
  // Mettre l'action en queue pour synchronisation depuis le popup
  await queueAction('add', animeUrl, day);
  
  // Mettre à jour l'UI immédiatement
  const animeName = extractAnimeName(animeUrl);
  const location = day ? `auto_download (${day})` : "single_download";
  showNotification(`${animeName} ajouté dans ${location} ! Synchronisation en cours...`, "success");
  
  // Mettre à jour le bouton
  if (button) {
    updateButtonState(button, cardElement, true);
  }
  
  // Notifier le background script pour qu'il synchronise (fonctionne même si popup fermé)
  try {
    chrome.runtime.sendMessage({
      type: 'syncQueue'
    });
  } catch (e) {
    // Ignorer les erreurs
  }
}

// Fonction pour supprimer un anime (utilise le cache local + queue)
async function removeFromDownload(animeUrl, cardElement, button) {
  const config = await getExtensionConfig();
  
  if (!config.serverUrl || !config.isLoggedIn) {
    alert("Veuillez vous connecter à l'extension d'abord.");
    return;
  }

  // Mettre à jour le cache local immédiatement (pas de requête HTTP depuis la page)
  await removeAnimeFromCache(animeUrl);
  
  // Mettre l'action en queue pour synchronisation depuis le popup
  await queueAction('remove', animeUrl);
  
  // Mettre à jour l'UI immédiatement
  const animeName = extractAnimeName(animeUrl);
  showNotification(`${animeName} supprimé de la liste ! Synchronisation en cours...`, "success");
  
  // Mettre à jour le bouton
  if (button) {
    updateButtonState(button, cardElement, false);
  }
  
  // Notifier le background script pour qu'il synchronise (fonctionne même si popup fermé)
  try {
    chrome.runtime.sendMessage({
      type: 'syncQueue'
    });
  } catch (e) {
    // Ignorer les erreurs
  }
}

// Fonction pour mettre à jour l'état du bouton
function updateButtonState(button, cardElement, isInList) {
  if (isInList) {
    button.textContent = "Delete";
    button.classList.add("delete-mode");
  } else {
    button.textContent = "Download";
    button.classList.remove("delete-mode");
  }
  
  // Si c'est un bouton de catalogue, mettre à jour le style
  if (button.classList.contains("catalogue-download-btn")) {
    if (isInList) {
      button.style.background = "linear-gradient(135deg, #ef4444 0%, #dc2626 100%)";
    } else {
      button.style.background = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)";
    }
  }
}

// Fonction pour obtenir ou créer le conteneur de notifications
function getNotificationContainer() {
  let container = document.querySelector('.anime-notification-container');
  if (!container) {
    container = document.createElement("div");
    container.className = "anime-notification-container";
    document.body.appendChild(container);
  }
  return container;
}

// Fonction pour afficher une notification
function showNotification(message, type) {
  const container = getNotificationContainer();
  const notification = document.createElement("div");
  notification.className = `anime-download-notification ${type}`;
  notification.textContent = message;
  
  // Ajouter la notification en bas de la pile (les plus récentes en bas)
  container.appendChild(notification);
  
  // Animation d'entrée
  setTimeout(() => {
    notification.classList.add("show");
  }, 10);
  
  // Animation de sortie après 2 secondes
  setTimeout(() => {
    notification.classList.remove("show");
    setTimeout(() => {
      notification.remove();
      // Supprimer le conteneur s'il est vide
      if (container.children.length === 0) {
        container.remove();
      }
    }, 300);
  }, 2000); // Réduit à 2 secondes
}

// Fonction pour normaliser une URL d'anime (pour comparaison)
function normalizeAnimeUrl(url) {
  if (!url) return null;
  
  // Enlever le domaine si présent
  let normalized = url;
  if (url.startsWith("http")) {
    try {
      const urlObj = new URL(url);
      normalized = urlObj.pathname;
    } catch (e) {
      // Si l'URL est invalide, retourner tel quel
      return url;
    }
  }
  
  // Normaliser : enlever le slash final et s'assurer qu'il commence par /
  normalized = normalized.trim();
  if (normalized.endsWith('/')) {
    normalized = normalized.slice(0, -1);
  }
  if (!normalized.startsWith('/')) {
    normalized = '/' + normalized;
  }
  
  return normalized;
}

// Fonction pour vérifier si une saison contient des lettres après le numéro (ex: saison1hs)
// Accepte les saisons avec tirets (ex: saison1-2) mais rejette celles avec lettres (ex: saison1hs)
function hasUnsupportedSeasonSuffix(animeUrl) {
  if (!animeUrl) return false;
  try {
    // Format: /catalogue/name/saison1hs/vostfr/ ou /catalogue/name/saison1-2/vostfr/
    // Rejeter si on trouve saison + chiffres + lettres (sans tiret avant les lettres)
    // Accepter saison + chiffres + tiret + chiffres (ex: saison1-2)
    const match = animeUrl.match(/\/catalogue\/[^\/]+\/saison(\d+)([a-zA-Z]+|\-\d+)?\//);
    if (match && match[2]) {
      // Si match[2] existe et contient uniquement des lettres (pas de tiret), c'est non supporté
      if (/^[a-zA-Z]+$/.test(match[2])) {
        return true; // saison1hs, saison2special, etc. → non supporté
      }
      // Si c'est un tiret suivi de chiffres (ex: -2), c'est supporté → return false
    }
    return false; // saison1, saison1-2, etc. → supporté
  } catch (e) {
    return false;
  }
}

// Fonction pour extraire le nom de l'anime depuis l'URL
function extractAnimeName(animeUrl) {
  if (!animeUrl) return "Anime";
  
  try {
    // Format: /catalogue/name/saison1/vostfr/
    const match = animeUrl.match(/\/catalogue\/([^\/]+)\//);
    if (match && match[1]) {
      // Remplacer les tirets par des espaces et capitaliser
      const name = match[1]
        .split('-')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
      return name;
    }
  } catch (e) {
    // En cas d'erreur, retourner "Anime"
  }
  return "Anime";
}

// Fonction pour extraire l'URL de la carte
function extractAnimeUrl(cardElement) {
  // cardElement est la div .anime-card-premium, chercher le lien à l'intérieur
  const link = cardElement.querySelector("a[href*='/catalogue/']");
  if (!link) return null;
  
  const href = link.getAttribute("href");
  if (!href) return null;
  
  // Normaliser l'URL pour qu'elle corresponde au format de l'API
  return normalizeAnimeUrl(href);
}

// Fonction pour créer le bouton
async function createDownloadButton(cardElement) {
  // Vérifier si c'est une carte d'anime (pas de scan)
  const isAnime = cardElement.classList.contains("anime-card-premium");
  const isScan = cardElement.classList.contains("scan-card-premium");
  
  // Ne créer le bouton que pour les animes
  if (!isAnime || isScan) {
    return;
  }
  
  // Vérifier si le bouton existe déjà
  const cardContent = cardElement.querySelector(".card-content");
  if (!cardContent) {
    return;
  }
  
  if (cardContent.querySelector(".anime-download-btn")) {
    return;
  }
  
  // Vérifier que c'est bien un lien vers /catalogue/ avec saison
  const link = cardElement.querySelector("a[href*='/catalogue/']");
  if (!link) {
    return;
  }
  
  const href = link.getAttribute("href");
  // Ignorer les scans et les URLs sans saison
  if (href.includes("/scan/") || !href.match(/\/saison\d+/)) {
    return;
  }
  
  // Vérifier les saisons avec suffixes non supportés (ex: saison1hs)
  // Accepter les saisons avec tirets (ex: saison1-2)
  const seasonMatch = href.match(/\/saison(\d+)([a-zA-Z]+|\-\d+)?\//);
  if (seasonMatch && seasonMatch[2] && /^[a-zA-Z]+$/.test(seasonMatch[2])) {
    // Afficher un message au lieu d'un bouton pour les saisons non supportées
    if (cardContent.querySelector(".anime-unsupported-season")) {
      return; // Le message existe déjà
    }
    const messageDiv = document.createElement("div");
    messageDiv.className = "anime-unsupported-season";
    messageDiv.textContent = "Saison non supportée";
    const messageContainer = document.createElement("div");
    messageContainer.className = "anime-download-container";
    messageContainer.appendChild(messageDiv);
    cardContent.appendChild(messageContainer);
    return; // Ne pas créer de bouton pour les saisons avec lettres (ex: saison1hs)
  }
  
  const animeUrl = extractAnimeUrl(cardElement);
  if (!animeUrl) {
    return;
  }
  
  // Vérifier si l'anime existe déjà
  const exists = await checkAnimeExists(animeUrl);
  const isInList = exists === true;
  
  const button = document.createElement("button");
  button.className = "anime-download-btn";
  button.textContent = isInList ? "Delete" : "Download";
  button.type = "button";
  
  if (isInList) {
    button.classList.add("delete-mode");
  }
  
  button.addEventListener("click", async (e) => {
    e.preventDefault();
    e.stopPropagation();
    
    // Vérifier l'état actuel du bouton (pas l'état initial)
    const currentlyInList = button.classList.contains("delete-mode");
    
    button.disabled = true;
    button.textContent = currentlyInList ? "Suppression..." : "Ajout en cours...";
    
    if (currentlyInList) {
      await removeFromDownload(animeUrl, cardElement, button);
    } else {
      await addToDownload(animeUrl, cardElement, button);
    }
    
    button.disabled = false;
  });
  
  // Créer un conteneur pour le bouton
  const buttonContainer = document.createElement("div");
  buttonContainer.className = "anime-download-container";
  buttonContainer.appendChild(button);
  cardContent.appendChild(buttonContainer);
}

// Observer pour détecter les nouvelles cartes ajoutées dynamiquement
const observer = new MutationObserver((mutations) => {
  mutations.forEach((mutation) => {
    mutation.addedNodes.forEach((node) => {
      if (node.nodeType === 1) {
        // Vérifier si c'est une carte d'anime ou contient des cartes
        let cards = [];
        if (node.classList && node.classList.contains("anime-card-premium")) {
          cards = [node];
        } else if (node.querySelectorAll) {
          cards = Array.from(node.querySelectorAll(".anime-card-premium"));
        }
        
        // Traiter les cartes de manière asynchrone
        cards.forEach((card) => {
          createDownloadButton(card).catch(err => {
            console.error("Erreur lors de la création du bouton:", err);
          });
        });
      }
    });
  });
});

// Fonction pour initialiser les boutons sur toutes les cartes existantes
async function initButtons() {
  const cards = document.querySelectorAll(".anime-card-premium");
  
  // Traiter les cartes en parallèle par petits lots pour éviter de surcharger l'API
  const batchSize = 10;
  for (let i = 0; i < cards.length; i += batchSize) {
    const batch = Array.from(cards).slice(i, i + batchSize);
    await Promise.all(batch.map(card => createDownloadButton(card)));
  }
}

// Fonction pour vérifier si on est sur une page de catalogue
const isCataloguePage = () => {
  const url = window.location.href;
  // Vérifier que c'est une page catalogue avec saison
  return /\/catalogue\/.+\/saison.+\/.+\//.test(url);
};

// Fonction pour obtenir l'URL de l'anime depuis la page de catalogue
const getAnimeUrlFromCataloguePage = () => 
  window.location.pathname.replace(/\/$/, '') + '/';

// Fonction pour créer le bouton sur la page de catalogue
async function createCatalogueDownloadButton() {
  // Chercher le conteneur avec les selects (plusieurs sélecteurs possibles)
  let container = document.querySelector('.flex.flex-wrap.justify-start.bg-slate-900.bg-opacity-70.rounded');
  
  // Si pas trouvé, chercher par le select d'épisodes
  if (!container) {
    const selectEpisodes = document.getElementById('selectEpisodes');
    if (selectEpisodes && selectEpisodes.parentElement) {
      container = selectEpisodes.parentElement;
    }
  }
  
  if (!container) {
    return;
  }

  const animeUrl = getAnimeUrlFromCataloguePage();
  if (!animeUrl) {
    return;
  }

  // Vérifier si la saison est non supportée
  if (hasUnsupportedSeasonSuffix(animeUrl)) {
    // Afficher un message au lieu d'un bouton
    if (container.querySelector('.catalogue-unsupported-season')) {
      return; // Le message existe déjà
    }
    const messageDiv = document.createElement("div");
    messageDiv.className = "catalogue-unsupported-season scrollBarStyled bg-gray-700 outline outline-gray-600 outline-1 rounded uppercase font-semibold text-sm sm:text-base text-white items-center py-1 px-3 sm:px-4 my-2 mx-1 sm:m-2";
    messageDiv.textContent = "Saison non supportée";
    container.appendChild(messageDiv);
    return;
  }

  // Vérifier si le bouton existe déjà
  if (container.querySelector('.catalogue-download-btn')) {
    return;
  }

  // Vérifier si l'anime existe déjà
  const exists = await checkAnimeExists(animeUrl);
  const isInList = exists === true;

  const button = document.createElement("button");
  button.className = "catalogue-download-btn scrollBarStyled bg-black outline outline-sky-700 outline-1 hover:opacity-80 rounded uppercase font-semibold text-sm sm:text-base text-white items-center cursor-pointer py-1 px-3 sm:px-4 my-2 mx-1 sm:m-2 transition-all duration-200";
  
  if (isInList) {
    button.textContent = "Delete";
    button.classList.add("delete-mode");
    button.style.background = "linear-gradient(135deg, #ef4444 0%, #dc2626 100%)";
  } else {
    button.textContent = "Download";
    button.style.background = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)";
  }

  button.addEventListener("click", async (e) => {
    e.preventDefault();
    e.stopPropagation();

    const currentlyInList = button.classList.contains("delete-mode");
    
    button.disabled = true;
    button.textContent = currentlyInList ? "Suppression..." : "Ajout en cours...";

    if (currentlyInList) {
      await removeFromDownload(animeUrl, null, button);
    } else {
      await addToDownload(animeUrl, null, button);
    }

    button.disabled = false;
  });

  container.appendChild(button);
}

// Fonction pour mettre à jour le bouton de catalogue
function updateCatalogueButton(button, isInList) {
  if (isInList) {
    button.textContent = "Delete";
    button.classList.add("delete-mode");
    button.style.background = "linear-gradient(135deg, #ef4444 0%, #dc2626 100%)";
  } else {
    button.textContent = "Download";
    button.classList.remove("delete-mode");
    button.style.background = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)";
  }
}

// Fonction pour initialiser le bouton sur la page de catalogue
async function initCatalogueButton() {
  if (isCataloguePage()) {
    // Attendre que le conteneur soit disponible
    const checkContainer = setInterval(() => {
      let container = document.querySelector('.flex.flex-wrap.justify-start.bg-slate-900.bg-opacity-70.rounded');
      
      // Si pas trouvé, chercher par le select d'épisodes
      if (!container) {
        const selectEpisodes = document.getElementById('selectEpisodes');
        if (selectEpisodes && selectEpisodes.parentElement) {
          container = selectEpisodes.parentElement;
        }
      }
      
      if (container) {
        clearInterval(checkContainer);
        createCatalogueDownloadButton();
      }
    }, 100);

    // Arrêter après 5 secondes si le conteneur n'est pas trouvé
    setTimeout(() => clearInterval(checkContainer), 5000);
  }
}

// Fonction pour rafraîchir tous les boutons après mise à jour du cache
async function refreshAllButtons() {
  // Rafraîchir les boutons sur les cartes
  const cards = document.querySelectorAll(".anime-card-premium");
  for (const card of cards) {
    const button = card.querySelector(".anime-download-btn");
    if (button) {
      const animeUrl = extractAnimeUrl(card);
      if (animeUrl) {
        const exists = await checkAnimeExistsLocal(animeUrl);
        updateButtonState(button, card, exists);
      }
    }
  }
  
  // Rafraîchir le bouton de catalogue si présent
  const catalogueButton = document.querySelector(".catalogue-download-btn");
  if (catalogueButton) {
    const animeUrl = getAnimeUrlFromCataloguePage();
    if (animeUrl) {
      const exists = await checkAnimeExistsLocal(animeUrl);
      updateCatalogueButton(catalogueButton, exists);
    }
  }
}

// Écouter les messages du background script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'cacheUpdated') {
    // Le cache a été mis à jour, rafraîchir les boutons
    refreshAllButtons().then(() => {
      // Afficher une notification selon le type de message
      if (message.error) {
        // Erreur lors de l'ajout ou suppression
        // Essayer d'extraire le nom de l'anime depuis l'URL si disponible
        let errorMessage = message.error;
        if (message.animeUrl) {
          const animeName = extractAnimeName(message.animeUrl);
          errorMessage = errorMessage.replace(/Cet anime|Anime|Cet/, animeName);
        }
        showNotification(errorMessage, "error");
      } else if (message.message) {
        // Message de confirmation du serveur
        let notificationMessage = message.message;
        // Essayer d'extraire le nom de l'anime depuis l'URL si disponible
        if (message.animeUrl) {
          const animeName = extractAnimeName(message.animeUrl);
          notificationMessage = notificationMessage.replace(/Cet anime|Anime|Cet/, animeName);
        }
        
        if (notificationMessage.includes("déjà dans la liste")) {
          showNotification(notificationMessage, "warning");
        } else if (notificationMessage.includes("ajouté")) {
          showNotification(notificationMessage, "success");
        } else if (notificationMessage.includes("supprimé")) {
          showNotification(notificationMessage, "success");
        } else {
          showNotification(notificationMessage, "success");
        }
      }
      sendResponse({ ok: true });
    });
    return true; // Indique qu'on répondra de manière asynchrone
  }
  
  if (message.type === 'ping') {
    // Répondre au ping pour indiquer que le script est déjà injecté
    sendResponse({ ok: true, injected: true });
    return true;
  }
});

// Initialiser quand le DOM est prêt
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    if (isCataloguePage()) {
      initCatalogueButton();
    } else {
      initButtons();
      observer.observe(document.body, {
        childList: true,
        subtree: true,
      });
    }
  });
} else {
  if (isCataloguePage()) {
    initCatalogueButton();
  } else {
    initButtons();
    observer.observe(document.body, {
      childList: true,
      subtree: true,
    });
  }
}

