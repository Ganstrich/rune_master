"""Modern CSS and styling templates for visualization.

Principles:
- Mobile-first responsive design
- Accessibility (WCAG 2.1 AA compliant)
- Dark mode support
- Professional color scheme
- Fast load times (minimal CSS)
"""


def get_base_css() -> str:
    """Base CSS applied to all pages.
    
    Includes:
    - Reset and normalize
    - CSS variables for theming
    - Responsive grid system
    - Accessibility utilities
    """
    return """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@500;600;700;800&display=swap');

/* ========================================================================
   RESET & NORMALIZE
   ======================================================================== */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

html {
    scroll-behavior: smooth;
}

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    line-height: 1.6;
    color: var(--text-main);
    background-color: var(--bg-body);
}

/* ========================================================================
   CSS CUSTOM PROPERTIES (Theming)
   ======================================================================== */
:root {
    /* Primary Colors */
    --color-primary: #6366f1;
    --color-primary-dark: #4f46e5;
    --color-primary-light: #818cf8;
    
    /* Accent / Secondary */
    --color-accent: #a855f7;
    --color-accent-dark: #9333ea;
    --color-accent-light: #c084fc;
    
    /* Semantic Colors */
    --color-success: #10b981;
    --color-warning: #f59e0b;
    --color-danger: #ef4444;
    --color-info: #06b6d4;
    
    /* Grays */
    --color-gray-50: #f8fafc;
    --color-gray-100: #f1f5f9;
    --color-gray-200: #e2e8f0;
    --color-gray-300: #cbd5e1;
    --color-gray-400: #94a3b8;
    --color-gray-500: #64748b;
    --color-gray-600: #475569;
    --color-gray-700: #334155;
    --color-gray-800: #1e293b;
    --color-gray-900: #0f172a;

    /* Theme colors */
    --bg-body: #f8fafc;
    --bg-card: #ffffff;
    --text-main: #0f172a;
    --text-muted: #64748b;
    --border-color: #e2e8f0;
    --glass-bg: rgba(255, 255, 255, 0.7);
    --glass-border: rgba(99, 102, 241, 0.12);
    
    /* Spacing */
    --spacing-xs: 0.25rem;
    --spacing-sm: 0.5rem;
    --spacing-md: 1rem;
    --spacing-lg: 1.5rem;
    --spacing-xl: 2rem;
    --spacing-2xl: 3rem;
    
    /* Border radius */
    --radius-sm: 0.375rem;
    --radius-md: 0.5rem;
    --radius-lg: 0.75rem;
    --radius-xl: 1rem;
    --radius-2xl: 1.5rem;
    --radius-full: 9999px;
    
    /* Shadows */
    --shadow-sm: 0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px 0 rgba(0, 0, 0, 0.03);
    --shadow-md: 0 4px 6px -1px rgba(99, 102, 241, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.04);
    --shadow-lg: 0 10px 15px -3px rgba(99, 102, 241, 0.07), 0 4px 6px -2px rgba(0, 0, 0, 0.03);
    --shadow-xl: 0 20px 25px -5px rgba(99, 102, 241, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
    --shadow-glow: 0 0 15px rgba(99, 102, 241, 0.15);
    
    /* Transitions */
    --transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
    --transition-base: 250ms cubic-bezier(0.4, 0, 0.2, 1);
    --transition-slow: 350ms cubic-bezier(0.4, 0, 0.2, 1);
}

/* Dark mode colors */
@media (prefers-color-scheme: dark) {
    :root {
        --bg-body: #090d16;
        --bg-card: #111726;
        --text-main: #f8fafc;
        --text-muted: #94a3b8;
        --border-color: #1e293b;
        --glass-bg: rgba(17, 23, 38, 0.7);
        --glass-border: rgba(129, 140, 248, 0.15);
        
        --color-gray-50: #151d30;
        --color-gray-100: #1e293b;
        --color-gray-200: #334155;
    }
}

/* ========================================================================
   LAYOUT - Container & Grid
   ======================================================================== */
.container {
    max-width: 1440px;
    margin: 0 auto;
    padding: var(--spacing-xl) var(--spacing-md);
}

.container-full {
    max-width: 1440px;
    margin: 0 auto;
    padding: 0 var(--spacing-md);
}

.grid {
    display: grid;
    gap: var(--spacing-lg);
}

.grid-2 {
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
}

.grid-3 {
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
}

.grid-4 {
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
}

/* ========================================================================
   TYPOGRAPHY
   ======================================================================== */
h1, h2, h3, h4, h5, h6 {
    font-family: 'Outfit', sans-serif;
    font-weight: 700;
    line-height: 1.2;
    margin-bottom: var(--spacing-md);
    letter-spacing: -0.02em;
}

h1 { font-size: 2.5rem; }
h2 { font-size: 2rem; }
h3 { font-size: 1.5rem; }
h4 { font-size: 1.25rem; }
h5 { font-size: 1.125rem; }
h6 { font-size: 1rem; }

p {
    margin-bottom: var(--spacing-md);
}

.text-muted {
    color: var(--text-muted);
}

.text-small {
    font-size: 0.875rem;
}

.text-tiny {
    font-size: 0.75rem;
}

/* ========================================================================
   CARDS & GLASSMORPHISM
   ======================================================================== */
.card {
    background: var(--bg-card);
    border-radius: var(--radius-xl);
    border: 1px solid var(--border-color);
    box-shadow: var(--shadow-sm);
    transition: box-shadow var(--transition-base), transform var(--transition-base);
    overflow: hidden;
}

.card:hover {
    box-shadow: var(--shadow-xl), var(--shadow-glow);
    transform: translateY(-4px);
}

.glass-pane {
    background: var(--glass-bg);
    backdrop-filter: blur(16px);
    border: 1px solid var(--glass-border);
    border-radius: var(--radius-xl);
    box-shadow: var(--shadow-lg);
}

.card-header {
    padding: var(--spacing-lg);
    border-bottom: 1px solid var(--border-color);
}

.card-body {
    padding: var(--spacing-lg);
}

.card-footer {
    padding: var(--spacing-lg);
    border-top: 1px solid var(--border-color);
}

/* ========================================================================
   BADGES & LABELS
   ======================================================================== */
.badge {
    display: inline-block;
    padding: var(--spacing-xs) var(--spacing-md);
    border-radius: var(--radius-full);
    font-size: 0.75rem;
    font-weight: 600;
    white-space: nowrap;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

.badge-primary {
    background-color: rgba(99, 102, 241, 0.15);
    color: var(--color-primary-light);
    border: 1px solid rgba(99, 102, 241, 0.2);
}

.badge-success {
    background-color: rgba(16, 185, 129, 0.15);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.2);
}

.badge-warning {
    background-color: rgba(245, 158, 11, 0.15);
    color: #fbbf24;
    border: 1px solid rgba(245, 158, 11, 0.2);
}

.badge-danger {
    background-color: rgba(239, 68, 68, 0.15);
    color: #f87171;
    border: 1px solid rgba(239, 68, 68, 0.2);
}

/* ========================================================================
   STATS CARDS
   ======================================================================== */
.stat-card {
    background: var(--bg-card);
    border-radius: var(--radius-xl);
    padding: var(--spacing-xl);
    border-left: 4px solid var(--color-primary);
    box-shadow: var(--shadow-sm);
    border: 1px solid var(--border-color);
    border-left: 5px solid var(--color-primary);
}

.stat-card-label {
    font-size: 0.875rem;
    color: var(--text-muted);
    margin-bottom: var(--spacing-sm);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 600;
}

.stat-card-value {
    font-size: 2.25rem;
    font-weight: 800;
    color: var(--text-main);
    font-family: 'Outfit', sans-serif;
}

.stat-card-unit {
    font-size: 0.875rem;
    color: var(--color-gray-400);
    margin-left: var(--spacing-xs);
}

/* ========================================================================
   BUTTONS
   ======================================================================== */
.btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: var(--spacing-sm) var(--spacing-xl);
    border: none;
    border-radius: var(--radius-lg);
    font-size: 0.95rem;
    font-weight: 600;
    cursor: pointer;
    transition: all var(--transition-fast);
    text-decoration: none;
    user-select: none;
    box-shadow: var(--shadow-sm);
}

.btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.btn-primary {
    background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
    color: white;
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.btn-primary:hover:not(:disabled) {
    background: linear-gradient(135deg, var(--color-primary-light) 0%, var(--color-primary) 100%);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

.btn-secondary {
    background-color: var(--color-gray-200);
    color: var(--text-main);
    border: 1px solid var(--border-color);
}

.btn-secondary:hover:not(:disabled) {
    background-color: var(--color-gray-300);
}

/* ========================================================================
   TABLES
   ======================================================================== */
.table {
    width: 100%;
    border-collapse: collapse;
}

.table thead {
    background-color: var(--color-gray-50);
    border-bottom: 2px solid var(--color-primary);
}

.table th {
    padding: var(--spacing-md);
    text-align: left;
    font-weight: 700;
    color: var(--color-primary-dark);
}

.table td {
    padding: var(--spacing-md);
    border-bottom: 1px solid var(--border-color);
}

.table tbody tr:hover {
    background-color: rgba(99, 102, 241, 0.03);
}

/* ========================================================================
   SCROLLBARS & OVERFLOW
   ======================================================================== */
.scrollable {
    overflow-y: auto;
    max-height: 600px;
}

/* Thin premium scrollbars */
.scrollable::-webkit-scrollbar,
body::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

.scrollable::-webkit-scrollbar-track,
body::-webkit-scrollbar-track {
    background: transparent;
}

.scrollable::-webkit-scrollbar-thumb,
body::-webkit-scrollbar-thumb {
    background: var(--color-gray-300);
    border-radius: var(--radius-full);
}

@media (prefers-color-scheme: dark) {
    .scrollable::-webkit-scrollbar-thumb,
    body::-webkit-scrollbar-thumb {
        background: var(--color-gray-200);
    }
}

.scrollable::-webkit-scrollbar-thumb:hover,
body::-webkit-scrollbar-thumb:hover {
    background: var(--color-gray-400);
}

/* ========================================================================
   UTILITIES
   ======================================================================== */
.flex {
    display: flex;
}

.flex-center {
    display: flex;
    justify-content: center;
    align-items: center;
}

.flex-between {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.gap-sm {
    gap: var(--spacing-sm);
}

.gap-md {
    gap: var(--spacing-md);
}

.gap-lg {
    gap: var(--spacing-lg);
}

.mt-md {
    margin-top: var(--spacing-md);
}

.mb-md {
    margin-bottom: var(--spacing-md);
}

.px-md {
    padding-left: var(--spacing-md);
    padding-right: var(--spacing-md);
}

.py-md {
    padding-top: var(--spacing-md);
    padding-bottom: var(--spacing-md);
}

.rounded {
    border-radius: var(--radius-lg);
}

.shadow-sm {
    box-shadow: var(--shadow-sm);
}

.shadow-md {
    box-shadow: var(--shadow-md);
}

.border {
    border: 1px solid var(--border-color);
}

.bg-white {
    background-color: var(--bg-card);
}

.bg-gray-50 {
    background-color: var(--color-gray-50);
}

.bg-primary {
    background-color: var(--color-primary);
    color: white;
}

/* ========================================================================
   RESPONSIVE
   ======================================================================== */
@media (max-width: 768px) {
    h1 {
        font-size: 1.875rem;
    }
    
    h2 {
        font-size: 1.5rem;
    }
    
    .container {
        padding: var(--spacing-sm);
    }
    
    .grid-2,
    .grid-3,
    .grid-4 {
        grid-template-columns: 1fr;
    }
}

/* ========================================================================
   ACCESSIBILITY
   ======================================================================== */
@media (prefers-reduced-motion: reduce) {
    * {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
    }
}

/* Focus styles for keyboard navigation */
:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
}

/* Skip to main content link */
.skip-link {
    position: absolute;
    top: -40px;
    left: 0;
    background: var(--color-primary);
    color: white;
    padding: var(--spacing-md);
    text-decoration: none;
    z-index: 100;
}

.skip-link:focus {
    top: 0;
}

</style>
"""


def get_group_css() -> str:
    """CSS specific to equipment group visualization pages.
    
    Includes:
    - Graph container styling
    - Ingredient table styling
    - Ingredient cards
    - Equipment preview gallery
    """
    return """
<style>

/* ========================================================================
   HEADER - Group details
   ======================================================================== */
.group-header {
    background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 100%);
    color: white;
    padding: var(--spacing-2xl) var(--spacing-xl);
    margin-bottom: var(--spacing-2xl);
    border-bottom: 1px solid var(--border-color);
}

.group-header h1 {
    color: white;
    margin-bottom: var(--spacing-md);
}

.group-stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: var(--spacing-lg);
    margin-top: var(--spacing-lg);
}

.group-stat {
    background: rgba(255, 255, 255, 0.1);
    padding: var(--spacing-md);
    border-radius: var(--radius-xl);
    backdrop-filter: blur(12px);
    text-align: center;
    border: 1px solid rgba(255, 255, 255, 0.15);
}

.group-stat-label {
    font-size: 0.875rem;
    opacity: 0.9;
    margin-bottom: var(--spacing-sm);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 600;
}

.group-stat-value {
    font-size: 2rem;
    font-weight: 800;
    font-family: 'Outfit', sans-serif;
}

/* ========================================================================
   EQUIPMENT PREVIEW GALLERY
   ======================================================================== */
.equipment-gallery {
    padding: var(--spacing-xl);
    background: var(--bg-card);
    border-radius: var(--radius-xl);
    margin-bottom: var(--spacing-lg);
    border: 1px solid var(--border-color);
    box-shadow: var(--shadow-md);
}

.equipment-gallery h3 {
    margin-bottom: var(--spacing-lg);
    color: var(--text-main);
    border-bottom: 2px solid var(--border-color);
    padding-bottom: var(--spacing-sm);
}

.equipment-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
    gap: var(--spacing-md);
}

.equipment-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: var(--spacing-md);
    background: var(--color-gray-50);
    border-radius: var(--radius-lg);
    transition: all var(--transition-base);
    border: 1px solid var(--border-color);
}

.equipment-item:hover {
    background: var(--bg-card);
    box-shadow: var(--shadow-lg), var(--shadow-glow);
    transform: translateY(-4px);
    border-color: var(--color-primary-light);
}

.equipment-item-image {
    width: 80px;
    height: 80px;
    object-fit: contain;
    margin-bottom: var(--spacing-sm);
    transition: transform var(--transition-base);
}

.equipment-item:hover .equipment-item-image {
    transform: scale(1.1);
}

.equipment-item-fallback {
    width: 80px;
    height: 80px;
    background: linear-gradient(135deg, var(--color-primary-light), var(--color-accent-light));
    border-radius: var(--radius-md);
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 2rem;
    margin-bottom: var(--spacing-sm);
}

.equipment-item-name {
    font-size: 0.8rem;
    font-weight: 700;
    text-align: center;
    color: var(--text-main);
    line-height: 1.3;
    cursor: pointer;
    transition: all var(--transition-fast);
    border-radius: var(--radius-sm);
    padding: var(--spacing-xs) var(--spacing-sm);
    word-break: break-word;
}

.equipment-item-name:hover {
    background-color: var(--color-primary);
    color: white;
}

.equipment-item-name.copied {
    background-color: var(--color-success);
    color: white;
}

.equipment-item-weight {
    font-size: 0.75rem;
    font-weight: 700;
    color: var(--color-primary);
    margin-top: var(--spacing-xs);
    background-color: rgba(99, 102, 241, 0.1);
    padding: var(--spacing-xs) var(--spacing-sm);
    border-radius: var(--radius-sm);
    border: 1px solid rgba(99, 102, 241, 0.15);
}

/* ========================================================================
   GRAPH CONTAINER
   ======================================================================== */
.graph-container {
    padding: var(--spacing-xl);
    background: var(--bg-card);
    border-radius: var(--radius-xl);
    margin-bottom: var(--spacing-lg);
    border: 1px solid var(--border-color);
    box-shadow: var(--shadow-md);
}

.graph-container h3 {
    margin-bottom: var(--spacing-sm);
    color: var(--text-main);
}

#graph {
    width: 100%;
    height: 600px;
}

/* ========================================================================
   INGREDIENT TABLE
   ======================================================================== */
.ingredient-section {
    background: var(--bg-card);
    border-radius: var(--radius-xl);
    padding: var(--spacing-xl);
    border: 1px solid var(--border-color);
    box-shadow: var(--shadow-md);
}

.ingredient-section h3 {
    margin-bottom: var(--spacing-lg);
    color: var(--text-main);
    border-bottom: 2px solid var(--color-primary);
    padding-bottom: var(--spacing-md);
}

.ingredient-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
}

.ingredient-table thead {
    background-color: var(--color-gray-50);
    border-bottom: 2px solid var(--color-primary);
}

.ingredient-table th {
    padding: var(--spacing-md);
    text-align: left;
    font-weight: 700;
    color: var(--color-primary-dark);
    word-break: break-word;
}

.ingredient-table td {
    padding: var(--spacing-md);
    border-bottom: 1px solid var(--border-color);
    vertical-align: middle;
    color: var(--text-main);
}

.ingredient-table tbody tr:hover {
    background-color: rgba(99, 102, 241, 0.03);
}

/* Resource cell styling */
.ingredient-resource-cell {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
}

.ingredient-resource-icon {
    width: 36px;
    height: 36px;
    object-fit: contain;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border-color);
    background-color: var(--bg-body);
    transition: transform var(--transition-fast);
}

.ingredient-resource-icon:hover {
    transform: scale(1.2);
}

.ingredient-resource-fallback {
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.25rem;
    background-color: var(--color-gray-100);
    border-radius: var(--radius-sm);
    border: 1px solid var(--border-color);
}

.ingredient-resource-name {
    font-weight: 600;
    color: var(--text-main);
    cursor: pointer;
    transition: all var(--transition-fast);
    border-radius: var(--radius-sm);
    padding: var(--spacing-xs) var(--spacing-sm);
    display: inline-block;
}

.ingredient-resource-name:hover {
    background-color: var(--color-primary);
    color: white;
}

.ingredient-resource-name.copied {
    background-color: var(--color-success);
    color: white;
}

.ingredient-total {
    text-align: center;
    background-color: rgba(16, 185, 129, 0.15);
    font-weight: 700;
    color: var(--color-success);
    border-radius: var(--radius-sm);
    padding: var(--spacing-sm) var(--spacing-md);
    border: 1px solid rgba(16, 185, 129, 0.2);
}

.ingredient-per-equipment {
    text-align: center;
    color: var(--text-main);
    font-weight: 500;
}

.ingredient-per-equipment.none {
    color: var(--color-gray-400);
    font-style: italic;
    font-weight: 400;
}

/* ========================================================================
   EFFICIENCY INDICATOR
   ======================================================================== */
.efficiency-meter {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
}

.efficiency-bar {
    flex: 1;
    height: 8px;
    background-color: var(--color-gray-200);
    border-radius: var(--radius-full);
    overflow: hidden;
}

.efficiency-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--color-success), var(--color-primary));
    transition: width var(--transition-base);
}

.efficiency-text {
    font-weight: 700;
    font-size: 0.875rem;
    color: var(--text-main);
    min-width: 50px;
}

/* ========================================================================
   COPY TOOLTIP
   ======================================================================== */
.copy-tooltip {
    position: relative;
}

.copy-tooltip-text {
    visibility: hidden;
    background-color: var(--color-gray-800);
    color: white;
    text-align: center;
    padding: var(--spacing-sm) var(--spacing-md);
    border-radius: var(--radius-md);
    position: absolute;
    z-index: 10;
    bottom: 125%;
    left: 50%;
    transform: translateX(-50%);
    white-space: nowrap;
    opacity: 0;
    transition: opacity var(--transition-fast);
    font-size: 0.75rem;
    border: 1px solid var(--border-color);
}

.copy-tooltip:hover .copy-tooltip-text {
    visibility: visible;
    opacity: 1;
}

/* ========================================================================
   RESPONSIVE - Ingredient table
   ======================================================================== */
@media (max-width: 768px) {
    .ingredient-table {
        font-size: 0.8rem;
    }
    
    .ingredient-table th,
    .ingredient-table td {
        padding: var(--spacing-sm);
    }
    
    .equipment-list {
        grid-template-columns: repeat(auto-fill, minmax(90px, 1fr));
    }
    
    #graph {
        min-height: 450px;
    }
}

</style>
"""


def get_index_css() -> str:
    """CSS for the index/dashboard page showing all groups.
    
    Includes:
    - Grid layout for group cards
    - Group preview cards
    - Search and filter UI
    """
    return """
<style>

/* ========================================================================
   INDEX HEADER
   ======================================================================== */
.index-header {
    background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 100%);
    color: white;
    padding: var(--spacing-2xl) var(--spacing-xl);
    margin-bottom: var(--spacing-2xl);
    border-bottom: 1px solid var(--border-color);
}

.index-header h1 {
    color: white;
    margin-bottom: var(--spacing-md);
}

.index-header p {
    margin-bottom: var(--spacing-lg);
    opacity: 0.95;
    font-size: 1.125rem;
}

.index-controls {
    display: grid;
    grid-template-columns: 1fr auto auto;
    gap: var(--spacing-md);
    align-items: center;
    margin-top: var(--spacing-lg);
}

.search-box {
    background: rgba(255, 255, 255, 0.15);
    border: 1px solid rgba(255, 255, 255, 0.25);
    border-radius: var(--radius-lg);
    padding: var(--spacing-sm) var(--spacing-md);
    color: white;
    font-size: 1rem;
    backdrop-filter: blur(8px);
    transition: all var(--transition-fast);
    outline: none;
}

.search-box:focus {
    background: rgba(255, 255, 255, 0.25);
    border-color: rgba(255, 255, 255, 0.5);
    box-shadow: 0 0 10px rgba(255, 255, 255, 0.2);
}

.search-box::placeholder {
    color: rgba(255, 255, 255, 0.7);
}

.sort-select {
    background: rgba(255, 255, 255, 0.15);
    border: 1px solid rgba(255, 255, 255, 0.25);
    border-radius: var(--radius-lg);
    padding: var(--spacing-sm) var(--spacing-md);
    color: white;
    font-size: 1rem;
    cursor: pointer;
    backdrop-filter: blur(8px);
    transition: all var(--transition-fast);
    outline: none;
}

.sort-select:focus {
    background: rgba(255, 255, 255, 0.25);
    border-color: rgba(255, 255, 255, 0.5);
}

.sort-select option {
    background: var(--bg-card);
    color: var(--text-main);
}

/* ========================================================================
   GROUP CARDS GRID
   ======================================================================== */
.groups-container {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: var(--spacing-lg);
}

.group-card {
    background: var(--bg-card);
    border-radius: var(--radius-xl);
    overflow: hidden;
    box-shadow: var(--shadow-md);
    transition: all var(--transition-base);
    display: flex;
    flex-direction: column;
    border: 1px solid var(--border-color);
}

.group-card:hover {
    box-shadow: var(--shadow-xl), var(--shadow-glow);
    transform: translateY(-4px);
    border-color: var(--color-primary-light);
}

.group-card-header {
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.08) 0%, rgba(168, 85, 247, 0.08) 100%);
    padding: var(--spacing-lg);
    border-bottom: 2px solid var(--color-primary);
}

.group-card-title {
    margin: 0;
    font-size: 1.35rem;
    color: var(--color-primary-dark);
    font-family: 'Outfit', sans-serif;
}

@media (prefers-color-scheme: dark) {
    .group-card-title {
        color: var(--color-primary-light);
    }
}

.group-card-body {
    padding: var(--spacing-lg);
    flex: 1;
    display: flex;
    flex-direction: column;
}

.group-card-equipment {
    display: block;
    padding: var(--spacing-sm) 0 var(--spacing-md) 0;
    margin-bottom: var(--spacing-md);
    border-bottom: 1px solid var(--border-color);
    font-size: 0.9rem;
}

.group-card-equipment-list {
    display: block;
    color: var(--text-main);
    font-weight: 600;
    margin-top: var(--spacing-xs);
    font-size: 0.85rem;
    line-height: 1.4;
}

.group-card-stat {
    display: flex;
    justify-content: space-between;
    padding: var(--spacing-sm) 0;
    border-bottom: 1px solid var(--border-color);
    font-size: 0.9rem;
}

.group-card-stat:last-child {
    border-bottom: none;
}

.group-card-stat-label {
    color: var(--text-muted);
    font-weight: 500;
}

.group-card-stat-value {
    color: var(--text-main);
    font-weight: 700;
}

.group-card-footer {
    padding: var(--spacing-lg);
    border-top: 1px solid var(--border-color);
    background: var(--color-gray-50);
}

.group-card-link {
    display: block;
    width: 100%;
    text-align: center;
    background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
    color: white;
    padding: var(--spacing-sm) var(--spacing-md);
    border-radius: var(--radius-lg);
    text-decoration: none;
    font-weight: 600;
    transition: all var(--transition-fast);
    box-shadow: var(--shadow-sm);
}

.group-card-link:hover {
    background: linear-gradient(135deg, var(--color-primary-light) 0%, var(--color-primary) 100%);
    box-shadow: 0 4px 10px rgba(99, 102, 241, 0.25);
}

/* ========================================================================
   INDEX SUMMARY
   ======================================================================== */
.index-summary {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: var(--spacing-lg);
    margin-top: var(--spacing-xl);
}

.summary-card {
    background: rgba(255, 255, 255, 0.1);
    padding: var(--spacing-lg);
    border-radius: var(--radius-xl);
    border: 1px solid rgba(255, 255, 255, 0.15);
    box-shadow: var(--shadow-sm);
    backdrop-filter: blur(12px);
}

.summary-label {
    font-size: 0.8rem;
    color: rgba(255, 255, 255, 0.85);
    margin-bottom: var(--spacing-xs);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 600;
}

.summary-value {
    font-size: 2rem;
    font-weight: 800;
    color: white;
    font-family: 'Outfit', sans-serif;
}

/* ========================================================================
   NO RESULTS
   ======================================================================== */
.no-results {
    text-align: center;
    padding: var(--spacing-2xl);
    color: var(--text-muted);
}

.no-results-icon {
    font-size: 3rem;
    margin-bottom: var(--spacing-lg);
}

/* ========================================================================
   RESPONSIVE
   ======================================================================== */
@media (max-width: 768px) {
    .index-controls {
        grid-template-columns: 1fr;
    }
    
    .groups-container {
        grid-template-columns: 1fr;
    }
}

</style>
"""


def get_javascript_utils() -> str:
    """Utility JavaScript functions for interactivity.
    
    Features:
    - Copy to clipboard with feedback
    - Resource search/filter
    - Tooltip management
    - Modal dialogs
    """
    return """
<script>
/**
 * Utility: Copy text to clipboard with user feedback
 * Shows temporary tooltip indicating successful copy
 */
function copyToClipboard(text, element) {
    if (!navigator.clipboard) {
        // Fallback for older browsers
        const textarea = document.createElement("textarea");
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        document.body.removeChild(textarea);
    } else {
        navigator.clipboard.writeText(text);
    }
    
    // Show feedback
    const originalClass = element.className;
    element.classList.add('copied');
    element.textContent = '✓ Copied!';
    
    setTimeout(() => {
        element.className = originalClass;
        // Re-fetch the text from data attribute if available, otherwise restore original
        const originalText = element.getAttribute('data-original-text');
        if (originalText) {
            element.textContent = originalText;
        }
    }, 1500);
}

/**
 * Copy equipment or resource name and show tooltip
 */
function copyName(event) {
    event.preventDefault();
    event.stopPropagation();
    
    const element = event.target;
    const textToCopy = element.getAttribute('data-copy-text') || element.textContent;
    
    // Store original text for restoration
    if (!element.getAttribute('data-original-text')) {
        element.setAttribute('data-original-text', element.textContent);
    }
    
    copyToClipboard(textToCopy, element);
}

/**
 * Copy resource name and show tooltip
 */
function copyResourceName(resourceName) {
    copyToClipboard(resourceName, event.target);
}

/**
 * Search/filter functionality for ingredient table
 */
function filterIngredients(searchTerm) {
    const table = document.querySelector('.ingredient-table tbody');
    if (!table) return;
    
    const rows = table.querySelectorAll('tr');
    const term = searchTerm.toLowerCase();
    
    rows.forEach(row => {
        const resourceName = row.querySelector('.ingredient-resource-name')?.textContent.toLowerCase() || '';
        const isVisible = resourceName.includes(term) || term === '';
        row.style.display = isVisible ? '' : 'none';
    });
}

/**
 * Sort ingredients table by column
 */
function sortIngredientsBy(columnIndex, order = 'asc') {
    const table = document.querySelector('.ingredient-table tbody');
    if (!table) return;
    
    const rows = Array.from(table.querySelectorAll('tr'));
    
    rows.sort((a, b) => {
        const aVal = a.querySelectorAll('td')[columnIndex]?.textContent.trim() || '';
        const bVal = b.querySelectorAll('td')[columnIndex]?.textContent.trim() || '';
        
        // Try numeric sort if both are numbers
        const aNum = parseFloat(aVal);
        const bNum = parseFloat(bVal);
        
        if (!isNaN(aNum) && !isNaN(bNum)) {
            return order === 'asc' ? aNum - bNum : bNum - aNum;
        }
        
        // Fallback to string sort
        return order === 'asc' 
            ? aVal.localeCompare(bVal)
            : bVal.localeCompare(aVal);
    });
    
    // Re-append sorted rows
    rows.forEach(row => table.appendChild(row));
}

/**
 * D3.js graph initialization (called by graph-specific pages)
 * This is a placeholder - actual D3 setup is in graph_generator.py
 */
function initializeGraph(graphData) {
    console.log('Graph data loaded:', graphData);
    // D3 setup code will go here
}

/**
 * Smooth scroll to element
 */
function scrollToElement(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.scrollIntoView({ behavior: 'smooth' });
    }
}

/**
 * Toggle element visibility with smooth animation
 */
function toggleElement(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.style.display = element.style.display === 'none' ? '' : 'none';
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Add click listeners to equipment names
    document.querySelectorAll('.equipment-item-name').forEach(element => {
        element.addEventListener('click', copyName);
    });
    
    // Add click listeners to resource names
    document.querySelectorAll('.ingredient-resource-name').forEach(element => {
        element.addEventListener('click', copyName);
    });
    
    // Add event listeners to copy buttons
    document.querySelectorAll('.copy-tooltip').forEach(element => {
        element.addEventListener('click', function(e) {
            const text = e.target.getAttribute('data-copy-text') || e.target.textContent;
            copyToClipboard(text, e.target);
        });
    });
    
    // Add search box listener if it exists
    const searchBox = document.getElementById('ingredient-search');
    if (searchBox) {
        searchBox.addEventListener('input', function(e) {
            filterIngredients(e.target.value);
        });
    }
});
</script>
"""
