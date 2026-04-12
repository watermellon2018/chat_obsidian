// app.js — Alpine.js entry point (ESM, no build step)
//
// IMPORTANT: All Alpine.store() and Alpine.data() calls MUST happen
// before Alpine.start(). The ESM import gives us full control over
// this initialization order, unlike the CDN <script defer> approach.

import Alpine from 'https://cdn.jsdelivr.net/npm/alpinejs@3/dist/module.esm.js';

import { appStore }            from './api.js';
import { appShell }            from './i18n.js';
import { chatComponent }       from './chat.js';
import { flashcardsComponent } from './flashcards.js';

// Configure marked (loaded as a plain CDN script before this module)
marked.setOptions({ breaks: true, gfm: true });

// Register global store — accessible as $store.app in every component
Alpine.store('app', appStore());

// Register component factories
Alpine.data('appShell',   appShell);
Alpine.data('chat',       chatComponent);
Alpine.data('flashcards', flashcardsComponent);

Alpine.start();

// Fetch vault name after Alpine is running so the store update
// triggers reactivity in any component that reads $store.app.vaultName
Alpine.store('app').fetchVaultName();
