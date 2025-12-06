// Content script pour ajouter des boutons "Add to download" sur anime-sama.eu/planning/

// Fonction pour obtenir les informations de l'extension
async function getExtensionConfig() {
  return new Promise((resolve) => {
    chrome.storage.sync.get(["serverUrl", "lastUser", "isLoggedIn"], (data) => {
      resolve(data);
    });
  });
}

// Fonction pour détecter le jour de la semaine depuis la page (dans le contexte d'une carte)
function detectDayFromPage(cardElement) {
  const dayMapping = {
    "lundi": "lundi",
    "mardi": "mardi",
    "mercredi": "mercredi",
    "jeudi": "jeudi",
    "vendredi": "vendredi",
    "samedi": "samedi",
    "dimanche": "dimanche"
  };

  // Chercher le conteneur parent avec selectedRow (qui contient le titre du jour)
  let current = cardElement;
  while (current && current !== document.body) {
    // Vérifier si c'est un conteneur de jour (selectedRow)
    if (current.classList && current.classList.contains("selectedRow")) {
      // Chercher le titre du jour dans ce conteneur
      const titreJours = current.querySelector(".titreJours");
      if (titreJours) {
        const dayText = titreJours.textContent.trim().toLowerCase();
        for (const [key, value] of Object.entries(dayMapping)) {
          if (dayText.includes(key)) {
            return value;
          }
        }
      }
    }
    current = current.parentElement;
  }

  return null; // Pas de jour détecté, sera ajouté dans single_download
}

// Fonction pour vérifier si un anime existe dans anime.json
async function checkAnimeExists(animeUrl) {
  const config = await getExtensionConfig();
  
  if (!config.serverUrl || !config.isLoggedIn) {
    return null;
  }

  try {
    const response = await fetch(`${config.serverUrl}/api/check-anime`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        anime_url: animeUrl,
      }),
    });

    const data = await response.json();
    if (data.ok) {
      return data.exists;
    }
    return false;
  } catch (error) {
    console.error("Erreur lors de la vérification:", error);
    return false;
  }
}

// Fonction pour ajouter un anime à la queue
async function addToDownload(animeUrl, cardElement, button) {
  const config = await getExtensionConfig();
  
  if (!config.serverUrl || !config.isLoggedIn) {
    alert("Veuillez vous connecter à l'extension d'abord.");
    return;
  }

  // Détecter le jour depuis la page (dans le contexte de la carte)
  // Si cardElement est null, on est sur une page de catalogue, donc day = null
  const day = cardElement ? detectDayFromPage(cardElement) : null;

  try {
    const response = await fetch(`${config.serverUrl}/api/add-download`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        anime_url: animeUrl,
        day: day,
      }),
    });

    const data = await response.json();
    
    if (data.ok) {
      const location = day ? `auto_download (${day})` : "single_download";
      showNotification(`Anime ajouté dans ${location} !`, "success");
      // Mettre à jour le bouton
      if (button) {
        updateButtonState(button, cardElement, true);
      }
    } else {
      showNotification(data.error || "Erreur lors de l'ajout", "error");
    }
  } catch (error) {
    console.error("Erreur:", error);
    showNotification("Erreur de connexion au serveur", "error");
  }
}

// Fonction pour supprimer un anime
async function removeFromDownload(animeUrl, cardElement, button) {
  const config = await getExtensionConfig();
  
  if (!config.serverUrl || !config.isLoggedIn) {
    alert("Veuillez vous connecter à l'extension d'abord.");
    return;
  }

  try {
    const response = await fetch(`${config.serverUrl}/api/remove-download`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        anime_url: animeUrl,
      }),
    });

    const data = await response.json();
    
    if (data.ok) {
      showNotification("Anime supprimé avec succès !", "success");
      // Mettre à jour le bouton
      if (button) {
        updateButtonState(button, cardElement, false);
      }
    } else {
      showNotification(data.error || "Erreur lors de la suppression", "error");
    }
  } catch (error) {
    console.error("Erreur:", error);
    showNotification("Erreur de connexion au serveur", "error");
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

// Fonction pour afficher une notification
function showNotification(message, type) {
  const notification = document.createElement("div");
  notification.className = `anime-download-notification ${type}`;
  notification.textContent = message;
  document.body.appendChild(notification);
  
  setTimeout(() => {
    notification.classList.add("show");
  }, 10);
  
  setTimeout(() => {
    notification.classList.remove("show");
    setTimeout(() => notification.remove(), 300);
  }, 3000);
}

// Fonction pour extraire l'URL de la carte
function extractAnimeUrl(cardElement) {
  // cardElement est la div .anime-card-premium, chercher le lien à l'intérieur
  const link = cardElement.querySelector("a[href*='/catalogue/']");
  if (!link) return null;
  
  const href = link.getAttribute("href");
  if (!href) return null;
  
  // Retourner l'URL relative (sans le domaine)
  // Format: /catalogue/egao-no-taenai-shokuba-desu/saison1/vostfr
  if (href.startsWith("http")) {
    // Extraire le chemin relatif
    try {
      const url = new URL(href);
      return url.pathname;
    } catch (e) {
      return href;
    }
  }
  
  return href;
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
function isCataloguePage() {
  const url = window.location.href;
  return /\/catalogue\/.+\/saison.+\/.+\//.test(url);
}

// Fonction pour obtenir l'URL de l'anime depuis la page de catalogue
function getAnimeUrlFromCataloguePage() {
  const path = window.location.pathname;
  // Retourner le chemin relatif (ex: /catalogue/watatabe/saison1/vostfr/)
  return path.endsWith('/') ? path : path + '/';
}

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

  // Vérifier si le bouton existe déjà
  if (container.querySelector('.catalogue-download-btn')) {
    return;
  }

  const animeUrl = getAnimeUrlFromCataloguePage();
  if (!animeUrl) {
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

