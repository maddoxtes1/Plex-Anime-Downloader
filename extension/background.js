// Service Worker (Background Script) pour synchronisation automatique
// Synchronise la liste des animes toutes les 2 minutes

let syncInterval = null;
let syncDebounceTimer = null;
const SYNC_DEBOUNCE_MS = 1000; // Attendre 1 seconde avant de synchroniser

// Fonction pour obtenir la configuration
async function getConfig() {
  return new Promise((resolve) => {
    chrome.storage.sync.get(["serverUrl", "lastUser", "isLoggedIn"], (data) => {
      resolve(data);
    });
  });
}

// Fonction pour synchroniser la liste des animes avec le serveur
async function syncAnimeList() {
  const config = await getConfig();
  
  if (!config.serverUrl || !config.isLoggedIn) {
    return;
  }

  try {
    // D'abord tester la connexion avec /api/ping
    const pingUrl = config.serverUrl.replace(/\/+$/, '') + "/api/ping";
    const pingResponse = await fetch(pingUrl);
    if (!pingResponse.ok) {
      console.error(`❌ Le serveur ne répond pas correctement (ping échoué): ${pingResponse.status}`);
      return;
    }
    
    // Récupérer la liste complète depuis le serveur
    const apiUrl = config.serverUrl.replace(/\/+$/, '') + "/api/anime-list";
    console.log("🔄 Synchronisation depuis:", apiUrl);
    
    const response = await fetch(apiUrl, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });
    
    // Vérifier si la réponse est OK
    if (!response.ok) {
      const text = await response.text();
      console.error(`❌ Erreur HTTP ${response.status} pour ${apiUrl}`);
      console.error("Réponse HTML reçue (premiers 500 caractères):", text.substring(0, 500));
      return;
    }
    
    // Vérifier que c'est bien du JSON
    const contentType = response.headers.get("content-type");
    if (!contentType || !contentType.includes("application/json")) {
      const text = await response.text();
      console.error(`❌ La réponse n'est pas du JSON pour ${apiUrl}`);
      console.error(`Content-Type reçu: ${contentType}`);
      console.error("Réponse HTML reçue (premiers 500 caractères):", text.substring(0, 500));
      
      // Si c'est une 404, la route n'existe peut-être pas encore (serveur pas redémarré)
      if (response.status === 404) {
        console.error("⚠️ La route /api/anime-list n'existe pas. Le serveur doit être redémarré pour charger la nouvelle route.");
      }
      return;
    }
    
    const data = await response.json();
    
    if (data.ok && data.anime_list) {
      // Fonction pour normaliser les URLs (enlever slash final, etc.)
      function normalizeAnimeUrl(url) {
        if (!url) return null;
        let normalized = url.trim();
        // Enlever le slash final pour normaliser
        if (normalized.endsWith('/')) {
          normalized = normalized.slice(0, -1);
        }
        // S'assurer qu'il commence par /
        if (!normalized.startsWith('/')) {
          normalized = '/' + normalized;
        }
        return normalized;
      }
      
      // Récupérer le cache actuel pour comparer
      const currentCache = await new Promise((resolve) => {
        chrome.storage.local.get(["animeList", "cacheTimestamp"], (data) => {
          // Normaliser les URLs du cache actuel
          const normalizedUrls = (data.animeList || []).map(url => normalizeAnimeUrl(url)).filter(url => url !== null);
          resolve({
            animeList: new Set(normalizedUrls),
            timestamp: data.cacheTimestamp || 0
          });
        });
      });
      
      // Créer le nouveau cache avec URLs normalisées
      const newAnimeSet = new Set(data.anime_list.map(anime => normalizeAnimeUrl(anime.url)).filter(url => url !== null));
      const newAnimeArray = Array.from(newAnimeSet);
      
      // Vérifier s'il y a des changements (comparaison avec URLs normalisées)
      const hasChanges = 
        newAnimeArray.length !== currentCache.animeList.size ||
        !newAnimeArray.every(url => currentCache.animeList.has(url));
      
      if (hasChanges) {
        // Sauvegarder le nouveau cache
        await chrome.storage.local.set({
          animeList: newAnimeArray,
          cacheTimestamp: Date.now()
        });
        
        console.log(`✅ Cache mis à jour (${data.count} animes)`);
        
        // Notifier tous les content scripts pour qu'ils rafraîchissent les boutons
        chrome.tabs.query({}, (tabs) => {
          tabs.forEach((tab) => {
            if (tab.url && (tab.url.includes('anime-sama.eu/planning') || tab.url.includes('anime-sama.eu/catalogue'))) {
              chrome.tabs.sendMessage(tab.id, {
                type: 'cacheUpdated',
                animeList: newAnimeArray
              }).catch(() => {
                // Ignorer les erreurs (tab peut ne pas avoir de content script)
              });
            }
          });
        });
      } else {
        console.log("ℹ️ Aucun changement détecté dans la liste des animes");
      }
    } else {
      console.warn("⚠️ Réponse API invalide:", data);
    }
  } catch (error) {
    console.error("❌ Erreur lors de la synchronisation:", error);
    console.error("Stack:", error.stack);
  }
}

// Fonction pour traiter la queue d'actions
async function processActionQueue() {
  const config = await getConfig();
  
  if (!config.serverUrl || !config.isLoggedIn) {
    return false;
  }

  const queue = await new Promise((resolve) => {
    chrome.storage.local.get(["actionQueue"], (data) => {
      resolve(data.actionQueue || []);
    });
  });

  if (queue.length === 0) {
    return false;
  }

  console.log(`🔄 Traitement de ${queue.length} action(s) en queue...`);

  for (const action of queue) {
    try {
      if (action.action === 'add') {
        const response = await fetch(config.serverUrl + "/api/add-download", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            anime_url: action.animeUrl,
            day: action.day,
          }),
        });
        const data = await response.json();
        if (!data.ok) {
          console.error("Erreur lors de l'ajout:", data.error);
        }
      } else if (action.action === 'remove') {
        const response = await fetch(config.serverUrl + "/api/remove-download", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            anime_url: action.animeUrl,
          }),
        });
        const data = await response.json();
        if (!data.ok) {
          console.error("Erreur lors de la suppression:", data.error);
        }
      }
    } catch (error) {
      console.error("Erreur lors du traitement de l'action:", error);
    }
  }

  // Vider la queue après traitement
  await chrome.storage.local.set({ actionQueue: [] });
  console.log("✅ Queue d'actions traitée");

  // Re-synchroniser la liste après traitement pour avoir les données à jour
  await syncAnimeList();
  
  return true; // Des actions ont été traitées
}

// Fonction pour synchroniser avec debounce
function debouncedSync() {
  if (syncDebounceTimer) {
    clearTimeout(syncDebounceTimer);
  }
  
  syncDebounceTimer = setTimeout(async () => {
    // Traiter la queue d'abord (qui synchronisera automatiquement après)
    // Si la queue est vide, processActionQueue retourne sans synchroniser, donc on synchronise quand même
    const hadActions = await processActionQueue();
    // Si aucune action n'a été traitée, synchroniser quand même pour mettre à jour le cache
    if (!hadActions) {
      await syncAnimeList();
    }
    syncDebounceTimer = null;
  }, SYNC_DEBOUNCE_MS);
}

// Fonction pour démarrer la synchronisation périodique
function startPeriodicSync() {
  // Arrêter l'intervalle existant si présent
  if (syncInterval) {
    clearInterval(syncInterval);
  }
  
  // Synchroniser immédiatement (avec debounce pour éviter les doublons)
  debouncedSync();
  
  // Puis toutes les 2 minutes (120000 ms)
  syncInterval = setInterval(async () => {
    // Traiter la queue d'abord, puis synchroniser la liste
    await processActionQueue();
    await syncAnimeList();
  }, 120000); // 2 minutes
  
  console.log("🔄 Synchronisation automatique démarrée (toutes les 2 minutes)");
}

// Fonction pour arrêter la synchronisation périodique
function stopPeriodicSync() {
  if (syncInterval) {
    clearInterval(syncInterval);
    syncInterval = null;
    console.log("⏹️ Synchronisation automatique arrêtée");
  }
  if (syncDebounceTimer) {
    clearTimeout(syncDebounceTimer);
    syncDebounceTimer = null;
  }
}

// Écouter les changements de configuration
chrome.storage.onChanged.addListener((changes, areaName) => {
  if (areaName === 'sync') {
    if (changes.isLoggedIn || changes.serverUrl) {
      // La configuration a changé, redémarrer la synchronisation
      const newIsLoggedIn = changes.isLoggedIn?.newValue ?? 
        (async () => {
          const config = await getConfig();
          return config.isLoggedIn;
        })();
      
      if (newIsLoggedIn) {
        startPeriodicSync();
      } else {
        stopPeriodicSync();
      }
    }
  }
});


// Écouter les messages du content script et du popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'syncQueue') {
    // Synchroniser immédiatement après une action (avec debounce)
    debouncedSync();
    sendResponse({ ok: true });
    return true; // Indique qu'on répondra de manière asynchrone
  }
  
  if (message.type === 'forceSync') {
    // Forcer une synchronisation immédiate (sans debounce)
    (async () => {
      await processActionQueue();
      await syncAnimeList();
      sendResponse({ ok: true });
    })();
    return true;
  }
  
  if (message.type === 'startSync') {
    startPeriodicSync();
    // Synchroniser immédiatement au démarrage
    debouncedSync();
    sendResponse({ ok: true });
  }
  
  if (message.type === 'stopSync') {
    stopPeriodicSync();
    if (syncDebounceTimer) {
      clearTimeout(syncDebounceTimer);
      syncDebounceTimer = null;
    }
    sendResponse({ ok: true });
  }
});

// Démarrer la synchronisation au démarrage du service worker
chrome.runtime.onStartup.addListener(() => {
  getConfig().then((config) => {
    if (config.isLoggedIn && config.serverUrl) {
      startPeriodicSync();
    }
  });
});

// Démarrer la synchronisation quand l'extension est installée/mise à jour
chrome.runtime.onInstalled.addListener(() => {
  getConfig().then((config) => {
    if (config.isLoggedIn && config.serverUrl) {
      startPeriodicSync();
    }
  });
});

// Démarrer la synchronisation au chargement du service worker
getConfig().then((config) => {
  if (config.isLoggedIn && config.serverUrl) {
    startPeriodicSync();
  }
});

