# Système de Design getinside (Handbook)

Ce document récapitule les règles visuelles et les composants utilisés dans le Handbook pour permettre la création de nouveaux outils parfaitement alignés.

## 1. Typographie

Le système utilise un mélange de modernité (Inter) et de caractère (Garnett).

- **corps de texte :** `Inter`, system-ui (Google Fonts).
- **Titres (H1, H2) :** `Garnett` (Semibold/Bold).
- **Tailles standards :**
  - Corps de texte : `0.875rem` (14px)
  - H1 : `1.5rem` (24px)
  - H2 : `1.125rem` (18px) avec bordure latérale Mint (`3px solid var(--vp-c-brand-1)`)
  - Code / Notes : `0.8125rem` (13px)

---

## 2. Palette de Couleurs

### Variables de Base (Thème Clair)
- **Fond :** `#F7F6F3` (Off-white)
- **Brand Principal :** `#0aaa8e` (Mint Dark)
- **Accents Vifs :** 
  - Mint : `#6AE7C8`
  - Jaune : `#FCF758`
  - Violet : `#C990FC`

### Adaptations Thème Sombre
- **Fond :** `#1b1b1f`
- **Brand :** Le Mint devient plus brillant (`#6AE7C8`) pour rester lisible.
- **Code :** Fond teinté Mint transparent `rgba(106, 231, 200, 0.1)`.

---

## 3. Composants et Classes CSS

### Cartes Interactives (`.gi-card`, `.gi-nav-card`, `.gi-format-card`)
- **Structure :** Bordure `1px solid var(--vp-c-divider)`, radius `10px`, fond `var(--vp-c-bg-elv)`.
- **Interactivité :** 
  - Translation : `translateY(-2px)` au survol.
  - Ombre : `0 4px 16px rgba(0, 0, 0, 0.08)`.
  - Dark Mode : Ajout d'un glow Mint `box-shadow: 0 0 20px rgba(106, 231, 200, 0.08)`.

### Boutons (`.btn`)
- **Primary :** Fond `#6AE7C8`, texte `#0a0f1e`.
- **Hover :** Fond `#0aaa8e`, texte blanc.

### Callouts & Boxes
- **Accent Box (`.gi-accent-box`) :** Pour les mises en avant, bordure Mint 1.5px.
- **Info Box (`.gi-info-box`) :** Fond neutre `var(--vp-c-bg-soft)`.
- **Step (`.gi-step`) :** Liste numérotée avec des pastilles Mint (`.gi-step-num`).

---

## 4. Effets Visuels (Hero)
L'effet "Key Visual" (comme sur la page d'accueil) utilise des gradients radiaux en arrière-plan :
- **Blob 1 :** Mint (`rgba(106, 231, 200, 0.50)`)
- **Blob 2 :** Violet (`rgba(201, 144, 252, 0.40)`)

---

## 5. Logo
- **Light Mode :** Doit être forcé en noir (`filter: brightness(0)`).
- **Dark Mode :** Doit être forcé en blanc (`filter: brightness(0) invert(1)`).
- **Hauteur fixe :** `30px`.
